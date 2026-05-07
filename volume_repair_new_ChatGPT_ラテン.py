# -*- coding: utf-8 -*-
import os

import pretty_midi
import random
import math
import numpy as np

# ===== 入出力 =====
MIDI_FILE_NAME = '右手左手合算しないver(volume_repair_2につっこむ用).mid'
OUT_NAME       = '音量変更後_LATIN_merged.mid'

def print_input_file(file_name):
    print(f"読み込んだファイル: {os.path.abspath(file_name)}")

def print_output_file(file_name):
    print(f"出力したファイル: {os.path.abspath(file_name)}")

print(f"ラテン調（アップテンポ）用 音量編集を開始します。対象: {MIDI_FILE_NAME}")
input("Enterで続行：")

# ===== 基本方針 =====
# 前処理で全ノートvelocity=66に揃えている前提
BASE_V = 66.0

# ===== 調整ノブ（ラテン向け）=====
INTENSITY = 1.0  # ラテンはメリハリ強め（0.95〜1.25目安）

# 66を中心に広めのレンジ（ラテンはパーカッシブなので少し広い方が気持ちいい）
RANGE_LOW  = 28
RANGE_HIGH = 122

# 右手トップの強調（低音トップは控えめ）
def right_melody_ratio(pitch: int) -> float:
    if pitch >= 76:
        return 1.09
    elif pitch >= 64:
        return 1.06
    else:
        return 1.02  # 右手が低音でメロを弾く時は出過ぎ防止

# 右手内声（和音の内側）抑制（ラテンのコードは粒立ちが大事）
INNER_SCALE_2_4 = {2: 0.92, 3: 0.87, 4: 0.83}

# 左手：和音はかなり抑える（「ベースは芯、和音は邪魔しない」）
LEFT_BASE_SCALE = 0.98
LEFT_CHORD_SCALE_2_4 = {2: 0.95, 3: 0.91, 4: 0.88}

# 左手和音を右手に対して少しダック（モコつき防止）
DUCK_LEFT = 0.94

# 拍アクセント：1拍目を強くしすぎず、2&/4&（裏）や2・4を気持ち強く
# ※ここがラテン感の要
# 4/4想定： [1, 2, 3, 4] の基本係数（表拍）
ACCENT_44 = [1.05, 1.03, 1.00, 1.03]
ACCENT_34 = [1.01, 1.03, 1.00]
DEFAULT_ACCENT = [1.01, 1.03, 1.00, 1.03]

# 「裏拍（&）」アクセント量（ラテン感のキモ）
OFFBEAT_BOOST_RIGHT = 3.5   # 右手の裏拍を押す
OFFBEAT_BOOST_LEFT  = 2.0   # 左手の裏拍は控えめ
OFFBEAT_WINDOW = 0.045      # 秒：ビートの中間（&）に近いと判断する許容幅

# フレーズ弧：ラテンはリズム主体なので控えめ
PHRASE_MIN_REST = 0.18
PHRASE_ARC_GAIN = 3.5

# ヒューマナイズ（ラテンは“揺れ”がある方が良いがやりすぎ注意）
HUMANIZE_RANGE = 2  # ±2

# 同時発音判定
TOL = 0.003
random.seed(42)

MIDDLE_MELODY_LOW = 52
MIDDLE_MELODY_HIGH = 64

def middle_melody_adjust(pitch):
    if MIDDLE_MELODY_LOW <= pitch <= MIDDLE_MELODY_HIGH:
        return -random.randint(3, 5)
    return 0

# ===== ヘルパ =====
def clamp(v, lo, hi): return max(lo, min(hi, v))

def get_downbeats_beats(pm):
    try: db = pm.get_downbeats()
    except Exception: db = None
    try: bt = pm.get_beats()
    except Exception: bt = None
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
        if c > 0: bar_counts.append(int(c + 1))
    if not bar_counts: return None
    avg = round(sum(bar_counts)/len(bar_counts))
    return avg if avg in (3, 4) else None

def make_accent_pattern(meter):
    if meter == 4: return ACCENT_44
    if meter == 3: return ACCENT_34
    return DEFAULT_ACCENT

def beat_strength(t, downbeats, beats, meter):
    """表拍のアクセント係数を返す"""
    if downbeats.size == 0 or beats.size == 0:
        return DEFAULT_ACCENT[0]
    prev_db_idx = np.searchsorted(downbeats, t, side='right') - 1
    if prev_db_idx < 0: prev_db_idx = 0
    prev_db = downbeats[prev_db_idx]
    bar_next_db = downbeats[prev_db_idx+1] if prev_db_idx+1 < len(downbeats) else float('inf')

    mask = (beats > prev_db) & (beats < bar_next_db)
    bar_beats = [prev_db] + beats[mask].tolist()
    if len(bar_beats) == 1:
        idx = 0
    else:
        idx = 0
        for i in range(len(bar_beats)-1):
            if bar_beats[i] <= t < bar_beats[i+1]:
                idx = i; break
            idx = min(i+1, len(bar_beats)-1)
    patt = make_accent_pattern(meter)
    return patt[idx % len(patt)]

def is_offbeat(t, beats):
    """ビート間の中間（&）に近ければTrue（アップテンポのラテン向け）"""
    if beats.size < 2:
        return False
    # tの直前のbeatを探す
    i = np.searchsorted(beats, t, side='right') - 1
    if i < 0 or i+1 >= len(beats):
        return False
    b0, b1 = beats[i], beats[i+1]
    mid = (b0 + b1) / 2.0
    return abs(t - mid) <= OFFBEAT_WINDOW

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
    """低音の聴感補正：左手は強め、右手は低音メロ控えめ用に薄く"""
    if which_hand != "left":
        return -2 if pitch < 60 else 0
    if pitch < 36: return -8
    if pitch < 48: return -6
    if pitch < 52: return -4
    if pitch < 57: return -2
    return 0

def apply_dynamics_hand(notes, which_hand, pm, beats, downbeats, meter):
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
            v = BASE_V

            # 1) 表拍アクセント（ラテン：1拍目強すぎNG、2/4やや強め）
            a = beat_strength(n.start, downbeats, beats, meter)
            v *= (a ** (0.70 if which_hand == "left" else 0.85))

            # 2) 裏拍アクセント（&）
            if is_offbeat(n.start, beats):
                v += (OFFBEAT_BOOST_LEFT if which_hand == "left" else OFFBEAT_BOOST_RIGHT) * INTENSITY

            # 3) 和音処理
            if chord_size >= 2:
                if which_hand == "right":
                    if n is top:
                        v *= (right_melody_ratio(n.pitch) ** INTENSITY)
                    else:
                        scale = INNER_SCALE_2_4.get(chord_size, 0.82)
                        v *= (scale ** INTENSITY)
                else:
                    # 左手：最低音を芯として少し残し、和音はしっかり抑える
                    if n is low:
                        v *= (LEFT_BASE_SCALE ** INTENSITY)
                    else:
                        scale = LEFT_CHORD_SCALE_2_4.get(chord_size, 0.72)
                        v *= (scale ** INTENSITY)
                    v *= DUCK_LEFT
            else:
                if which_hand == "left":
                    v *= (LEFT_BASE_SCALE ** INTENSITY)

            if which_hand == "right" and (chord_size == 1 or n is top):
                v += middle_melody_adjust(n.pitch)

            # 4) 音価：ラテンは短いアタックが多いので、長音だけ少し押し出し
            length = max(0.0, n.end - n.start)
            if length > 0.9:
                v += 3.5 * INTENSITY
            elif length > 0.5:
                v += 1.5 * INTENSITY

            # 5) 旋律方向＆反復弱化（控えめ）
            if prev_pitch is not None:
                if n.pitch > prev_pitch:
                    v += 2.0 * INTENSITY; repeat_count = 0
                elif n.pitch < prev_pitch:
                    v -= 1.5 * INTENSITY; repeat_count = 0
                else:
                    repeat_count += 1
                    v -= min(1 + repeat_count*2, 8) * INTENSITY
            prev_pitch = n.pitch

            # 6) フレーズ弧（控えめ：リズム優先）
            p = phrase_pos.get(n, 0.5)
            v += (math.sin((p - 0.15) * math.pi) * PHRASE_ARC_GAIN - 1.0) * INTENSITY

            # 7) 低音補正（左手強め、右手は低音メロ出過ぎ防止）
            v += bass_shelf_adjust(n.pitch, which_hand)

            # 8) ヒューマナイズ
            v += random.randint(-HUMANIZE_RANGE, HUMANIZE_RANGE)

            # 9) レンジ正規化（66中心でRANGE_LOW〜RANGE_HIGH）
            v = clamp(v, 1, 127)
            center = 66.0
            low_r, high_r = float(RANGE_LOW), float(RANGE_HIGH)
            span = (high_r - low_r) / 2.0
            v = center + (v - center) * (span / 24.0)  # ラテンは少し強めに広げる
            v = int(round(clamp(v, low_r, high_r)))

            out.append(pretty_midi.Note(start=n.start, end=n.end, pitch=n.pitch, velocity=v))

    return sorted(out, key=lambda n: (n.start, n.pitch))

# ===== 実行 =====
print_input_file(MIDI_FILE_NAME)
pm_in = pretty_midi.PrettyMIDI(MIDI_FILE_NAME)
right = pm_in.instruments[0]
left  = pm_in.instruments[1]

downbeats, beats = None, None
db, bt = get_downbeats_beats(pm_in)
meter = guess_meter(db, bt)
if meter is None:
    meter = 4  # 推定できなければ4/4扱い（ラテンポップ想定）

right_notes = apply_dynamics_hand(right.notes, "right", pm_in, bt, db, meter)
left_notes  = apply_dynamics_hand(left.notes,  "left",  pm_in, bt, db, meter)

# --- Merged 出力 ---
pm_out = pretty_midi.PrettyMIDI()
merged = pretty_midi.Instrument(program=right.program, is_drum=right.is_drum, name="Merged")

merged.notes = sorted(right_notes + left_notes, key=lambda n: (n.start, n.pitch))

# CC（ペダル等）も結合（ラテンでも基本OK。必要ならCC64だけ残すなども可）
cc_all = right.control_changes + left.control_changes
cc_all.sort(key=lambda cc: (cc.time, cc.number, cc.value))
merged.control_changes = cc_all

pm_out.instruments.append(merged)
pm_out.write(OUT_NAME)
print_output_file(OUT_NAME)
print(f"OK: {OUT_NAME} を書き出しました。Enterで終了。")
input()
