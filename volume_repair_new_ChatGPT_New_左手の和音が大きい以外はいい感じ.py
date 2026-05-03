import os

import pretty_midi
import random
import math
import numpy as np

MIDI_FILE_NAME = '右手左手合算しないver(volume_repair_2につっこむ用).mid'
OUT_NAME = '音量変更後_POP_merged.mid'

def print_input_file(file_name):
    print(f"読み込んだファイル: {os.path.abspath(file_name)}")

def print_output_file(file_name):
    print(f"出力したファイル: {os.path.abspath(file_name)}")

# ===== ポップス向け調整ノブ =====
INTENSITY = 1.0          # 全体ダイナミクス強度（0.8〜1.3目安）
GLOBAL_RANGE_MIN = 48     # 最終ベロシティ下限
GLOBAL_RANGE_MAX = 112    # 最終ベロシティ上限
RIGHT_MELODY_RATIO = 1.04   # 4%だけ強くする（控えめ）
INNER_SCALE_2_4 = {2:0.92, 3:0.88, 4:0.84}  # 右手内声の抑え（やや弱め）
LEFT_BASE_SCALE = 0.94    # 左手基礎抑え（控えめ）
LEFT_CHORD_SCALE_2_4 = {2:0.90, 3:0.86, 4:0.82}

# ★拍アクセント（押し出しを弱めたポップス用。1拍目だけほんのり強い）
ACCENT_44 = [1.04, 0.99, 1.01, 0.98]
ACCENT_34 = [1.05, 0.99, 0.98]
DEFAULT_ACCENT = [1.03, 0.99, 0.99, 0.99]   # 拍推定できない場合の控えめ設定

# フレーズ弧の強さ（弱め）
PHRASE_MIN_REST = 0.20   # s：これ以上の休符でフレーズ切り
PHRASE_ARC_GAIN = 6.0    # フレーズ弧の最大振れ（8→6に下げて穏やかに）

# ランダム揺らぎ（控えめ）
HUMANIZE_RANGE = 2       # ±2

TOL = 0.003              # 3ms以内を同時発音とみなす
random.seed(42)

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def get_downbeats_beats(pm):
    try:
        db = pm.get_downbeats()
    except Exception:
        db = None
    try:
        bt = pm.get_beats()
    except Exception:
        bt = None
    if db is None: db = np.array([])
    if bt is None: bt = np.array([])
    return db, bt

def guess_meter(downbeats, beats):
    if downbeats.size == 0 or beats.size == 0:
        return None
    bar_counts = []
    for i in range(len(downbeats)-1):
        start, end = downbeats[i], downbeats[i+1]
        c = ((beats > start) & (beats < end)).sum()
        if c > 0:
            bar_counts.append(int(c + 1))
    if not bar_counts:
        return None
    avg = round(sum(bar_counts)/len(bar_counts))
    return avg if avg in (3,4) else None

def make_accent_pattern(meter):
    if meter == 4: return ACCENT_44
    if meter == 3: return ACCENT_34
    return DEFAULT_ACCENT

def beat_index_in_bar(t, downbeats, beats, meter, accent_len):
    if downbeats.size == 0 or beats.size == 0:
        return DEFAULT_ACCENT[0]
    prev_db_idx = np.searchsorted(downbeats, t, side='right') - 1
    if prev_db_idx < 0: prev_db_idx = 0
    prev_db = downbeats[prev_db_idx]
    bar_next_db = downbeats[prev_db_idx+1] if prev_db_idx+1 < len(downbeats) else float('inf')
    mask = (beats > prev_db) & (beats < bar_next_db)
    bar_beats = [prev_db] + beats[mask].tolist()
    idx = 0
    for i in range(len(bar_beats)-1):
        if bar_beats[i] <= t < bar_beats[i+1]:
            idx = i; break
        idx = min(i+1, len(bar_beats)-1)
    return make_accent_pattern(meter)[idx % accent_len]

def group_onsets(notes, tol=TOL):
    notes_sorted = sorted(notes, key=lambda n: n.start)
    groups, cur = [], []
    for n in notes_sorted:
        if not cur: cur = [n]
        else:
            if abs(n.start - cur[-1].start) <= tol: cur.append(n)
            else: groups.append(cur); cur = [n]
    if cur: groups.append(cur)
    return groups

def split_phrases(notes, gap=PHRASE_MIN_REST):
    if not notes: return []
    ns = sorted(notes, key=lambda n: n.start)
    phrases, cur = [], [ns[0]]
    for a, b in zip(ns, ns[1:]):
        cur.append(b)
        if b.start - a.end >= gap:
            phrases.append(cur); cur = []
    if cur: phrases.append(cur)
    return phrases

def apply_dynamics_hand(notes, which_hand, pm):
    base = 66.0  # 事前に66で揃えて渡している前提
    db, bt = get_downbeats_beats(pm)
    meter = guess_meter(db, bt)
    accents = make_accent_pattern(meter)
    accent_len = len(accents)

    out = []
    onset_groups = group_onsets(notes)
    phrases = split_phrases(notes)
    phrase_pos = {}
    for ph in phrases:
        t0 = ph[0].start
        t1 = max(n.end for n in ph)
        dur = max(1e-6, t1 - t0)
        for n in ph:
            phrase_pos[n] = clamp((n.start - t0)/dur, 0.0, 1.0)

    prev_pitch = None
    repeat_count = 0

    for grp in onset_groups:
        top = max(grp, key=lambda n: n.pitch)
        low = min(grp, key=lambda n: n.pitch)
        chord_size = len(grp)

        for n in grp:
            v = base

            # 1) 拍アクセント（控えめ／ポップ向け）
            accent = beat_index_in_bar(n.start, db, bt, meter, accent_len)
            # 左手はさらに控えめに適用
            v *= (accent ** (0.7 if which_hand=="left" else 0.85))

            # 2) 和音：トップ強調／内声抑制
            if chord_size >= 2:
                if which_hand == "right":
                    if n is top:
                        # ★ ピッチ依存でブースト割合を調整
                        if n.pitch >= 72:
                            boost_ratio = 1.08   # 高音はしっかり
                        elif n.pitch >= 60:
                            boost_ratio = 1.05   # 中音は控えめ
                        else:
                            boost_ratio = 1.02   # 低音はほんのり
                        v *= boost_ratio ** INTENSITY
                    else:
                        scale = INNER_SCALE_2_4.get(chord_size, 0.82)
                        v *= (scale ** INTENSITY)
            else:
                if which_hand == "left":
                    v *= (LEFT_BASE_SCALE ** INTENSITY)

            # 3) 音価による打ち出し（控えめ）
            length = max(0.0, n.end - n.start)
            if length > 0.8:      v += 4 * INTENSITY
            elif length > 0.4:    v += 2 * INTENSITY

            # 4) 旋律の方向感 & 反復弱化（控えめ）
            if prev_pitch is None:
                pass
            else:
                if n.pitch > prev_pitch:
                    v += 3 * INTENSITY
                    repeat_count = 0
                elif n.pitch < prev_pitch:
                    v -= 2 * INTENSITY
                    repeat_count = 0
                else:
                    repeat_count += 1
                    v -= min(1 + repeat_count*2, 8) * INTENSITY
            prev_pitch = n.pitch

            # 5) フレーズ弧（弱めの弧）
            p = phrase_pos.get(n, 0.5)
            arc = (math.sin((p-0.15)*math.pi) * PHRASE_ARC_GAIN - 1.5) * INTENSITY
            v += arc

            # 6) 単音メロの粒立ち ほんの少し
            if which_hand == "right" and chord_size == 1:
                v += 1 * INTENSITY

            # 7) 微ゆらぎ（±HUMANIZE_RANGE）
            v += random.randint(-HUMANIZE_RANGE, HUMANIZE_RANGE)

            # 8) レンジへ正規化（66をmfとして40〜112にマップ）
            center = 66.0
            low, high = 40.0, 112.0
            span = (high - low) / 2.0
            v = center + (v - center) * (span / 26.0)
            v = int(round(clamp(v, low, high)))

            out.append(pretty_midi.Note(start=n.start, end=n.end, pitch=n.pitch, velocity=v))

    return sorted(out, key=lambda n: n.start)

# ==== メイン ====
print(f"音量変更（ポップス向け・拍頭弱め・マージ出力）を開始します。対象: {MIDI_FILE_NAME}")
input("Enterで続行：")

print_input_file(MIDI_FILE_NAME)
pm_in = pretty_midi.PrettyMIDI(MIDI_FILE_NAME)
right = pm_in.instruments[0]
left  = pm_in.instruments[1]

right_notes = apply_dynamics_hand(right.notes, "right", pm_in)
left_notes  = apply_dynamics_hand(left.notes,  "left",  pm_in)

# --- ここから Merged 出力 ---
pm_out = pretty_midi.PrettyMIDI()
# 右手のプログラムを採用（必要なら固定数値にしてもOK）
merged = pretty_midi.Instrument(program=right.program, is_drum=right.is_drum, name="Merged")

# ノート結合＆ソート
merged.notes = sorted(right_notes + left_notes, key=lambda n: (n.start, n.pitch))

# CC（ペダル等）も両方結合。重複が多い場合は「後勝ち」で簡易マージ
cc_all = right.control_changes + left.control_changes
cc_all.sort(key=lambda cc: (cc.time, cc.number, cc.value))
merged.control_changes = cc_all

pm_out.instruments.append(merged)
pm_out.write(OUT_NAME)
print_output_file(OUT_NAME)
print(f"OK: {OUT_NAME} を書き出しました。Enterで終了。")
input()
