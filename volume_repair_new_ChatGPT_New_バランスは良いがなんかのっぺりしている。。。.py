# -*- coding: utf-8 -*-
import os

import pretty_midi
import random
import math
import numpy as np

# ===== 入出力 =====
MIDI_FILE_NAME = '右手左手合算しないver(volume_repair_2につっこむ用).mid'
OUT_NAME       = '音量変更後_POP_merged_expanded.mid'

def print_input_file(file_name):
    print(f"読み込んだファイル: {os.path.abspath(file_name)}")

def print_output_file(file_name):
    print(f"出力したファイル: {os.path.abspath(file_name)}")

# ===== ポップス向け調整ノブ =====
INTENSITY = 1.0

# 66をmfとし、pp≈32〜ff≈120へマップ
RANGE_LOW  = 45
RANGE_HIGH = 112

# 右手トップは“割合”で上げる（ピッチで減衰）
def right_melody_ratio(pitch: int) -> float:
    if pitch >= 72:  # 高音
        return 1.08
    elif pitch >= 60:  # 中音
        return 1.05
    else:  # 低音（右手の低音メロは控えめ）
        return 1.02

# 右手内声の抑え（和音が厚いほど）
INNER_SCALE_2_4 = {2: 0.92, 3: 0.88, 4: 0.84}

# 左手の基礎抑え＋和音強め抑制
LEFT_BASE_SCALE = 0.98
LEFT_CHORD_SCALE_2_4 = {2: 0.97, 3: 0.94, 4: 0.90}

# 右手トップが想定されるオンセットで左手を薄くダック（サイドチェイン風・常時薄めに適用）
DUCK_LEFT_ON_RIGHT_TOP = 0.96

# 拍アクセント（押し出し弱め・ポップ寄り）
ACCENT_44 = [1.02, 1.00, 1.01, 0.99]
ACCENT_34 = [1.03, 1.00, 0.99]
DEFAULT_ACCENT = [1.02, 1.00, 1.00, 0.99]

# フレーズ弧（弱め）
PHRASE_MIN_REST = 0.20   # s：これ以上の休符でフレーズ切り
PHRASE_ARC_GAIN = 6.0

# ランダム揺らぎ（控えめ）
HUMANIZE_RANGE = 2       # ±2

# 同時発音判定の許容
TOL = 0.003              # 3ms
random.seed(42)

# ===== ヘルパ =====
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
    return avg if avg in (3, 4) else None

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

def bass_shelf_adjust(pitch, which_hand):
    """低音の聴感補正：左手強め、右手は低音メロの違和感軽減に薄く適用"""
    if which_hand != "left":
        return -2 if pitch < 60 else 0
    # 左手は段階的に強めに抑える
    if pitch < 36: return -8
    if pitch < 48: return -6
    if pitch < 52: return -4
    if pitch < 57: return -2
    return 0

# ===== 本体 =====
def apply_dynamics_hand(notes, which_hand, pm):
    base = 66.0  # りのさんが前処理で全ノート66にしている前提
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

            # 1) 拍アクセント（弱め／左手はさらに薄く）
            accent = beat_index_in_bar(n.start, db, bt, meter, accent_len)
            v *= (accent ** (0.70 if which_hand == "left" else 0.85))

            # 2) 和音処理：右手トップは割合ブースト（ピッチで減衰）、左手は強めに抑える
            if chord_size >= 2:
                if which_hand == "right":
                    if n is top:
                        v *= (right_melody_ratio(n.pitch) ** INTENSITY)
                    else:
                        scale = INNER_SCALE_2_4.get(chord_size, 0.82)
                        v *= (scale ** INTENSITY)
                else:
                    if n is low:
                        v *= (LEFT_BASE_SCALE ** INTENSITY)  # 土台は少し残す
                        v += bass_shelf_adjust(n.pitch, "left")
                    else:
                        scale = LEFT_CHORD_SCALE_2_4.get(chord_size, 0.76)
                        v *= (scale ** INTENSITY)
                        v += bass_shelf_adjust(n.pitch, "left")
                    # サイドチェイン風に薄くダック（常時薄め）
                    v *= DUCK_LEFT_ON_RIGHT_TOP
            else:
                if which_hand == "left":
                    v *= (LEFT_BASE_SCALE ** INTENSITY)
                    v += bass_shelf_adjust(n.pitch, "left")

            # 3) 音価（長い音はやや強めに立ち上げ）
            length = max(0.0, n.end - n.start)
            if length > 0.8:      v += 4 * INTENSITY
            elif length > 0.4:    v += 2 * INTENSITY

            # 4) 旋律方向＆反復弱化（控えめ）
            if prev_pitch is not None:
                if n.pitch > prev_pitch:
                    v += 3 * INTENSITY; repeat_count = 0
                elif n.pitch < prev_pitch:
                    v -= 2 * INTENSITY; repeat_count = 0
                else:
                    repeat_count += 1
                    v -= min(1 + repeat_count*2, 8) * INTENSITY
            prev_pitch = n.pitch

            # 5) フレーズ弧（弱めの弧）
            p = phrase_pos.get(n, 0.5)
            v += (math.sin((p - 0.15) * math.pi) * PHRASE_ARC_GAIN - 1.5) * INTENSITY

            # 6) 右手の単音メロはほんの少しだけ前へ（ピッチ依存）
            if which_hand == "right" and chord_size == 1:
                v *= right_melody_ratio(n.pitch) ** (0.5 * INTENSITY)

            # 7) 低音の聴感補正（右手にも薄く適用）
            v += bass_shelf_adjust(n.pitch, which_hand)

            # 8) ヒューマナイズ
            v += random.randint(-HUMANIZE_RANGE, HUMANIZE_RANGE)

            # 9) レンジ正規化（66をmf、RANGE_LOW〜HIGHへ線形写像）
            v = clamp(v, 1, 127)
            center = 66.0
            low, high = float(RANGE_LOW), float(RANGE_HIGH)
            span = (high - low) / 2.0
            # 66±26 を基準幅として指定レンジへ拡大/縮小
            v = center + (v - center) * (span / 26.0)
            v = int(round(clamp(v, low, high)))

            out.append(pretty_midi.Note(start=n.start, end=n.end, pitch=n.pitch, velocity=v))

    return sorted(out, key=lambda n: n.start)

# ===== 実行 =====
print(f"音量変更（ポップス向け・拍頭弱め・左手和音抑制・レンジ拡張・Merged出力）を開始します。対象: {MIDI_FILE_NAME}")
input("Enterで続行：")

print_input_file(MIDI_FILE_NAME)
pm_in = pretty_midi.PrettyMIDI(MIDI_FILE_NAME)
right = pm_in.instruments[0]
left  = pm_in.instruments[1]

right_notes = apply_dynamics_hand(right.notes, "right", pm_in)
left_notes  = apply_dynamics_hand(left.notes,  "left",  pm_in)

# --- Merged 出力 ---
pm_out = pretty_midi.PrettyMIDI()
merged = pretty_midi.Instrument(program=right.program, is_drum=right.is_drum, name="Merged")

# ノート結合＆ソート
merged.notes = sorted(right_notes + left_notes, key=lambda n: (n.start, n.pitch))

# CC（ペダル等）も結合。重複が多い場合は基本「後勝ち」でOK
cc_all = right.control_changes + left.control_changes
cc_all.sort(key=lambda cc: (cc.time, cc.number, cc.value))
merged.control_changes = cc_all

pm_out.instruments.append(merged)
pm_out.write(OUT_NAME)
print_output_file(OUT_NAME)
print(f"OK: {OUT_NAME} を書き出しました。Enterで終了。")
input()
