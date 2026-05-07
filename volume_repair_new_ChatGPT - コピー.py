# -*- coding: utf-8 -*-
import os

import pretty_midi
import random
import math
import numpy as np

# ===== 入出力 =====
MIDI_FILE_NAME = '右手左手合算しないver(volume_repair_2につっこむ用).mid'
OUT_NAME       = '音量変更後_POP_merged_tuned.mid'

def print_input_file(file_name):
    print(f"読み込んだファイル: {os.path.abspath(file_name)}")

def print_output_file(file_name):
    print(f"出力したファイル: {os.path.abspath(file_name)}")

# ===== ポップス向けチューニング（統合版）=============================
# りのさん前処理：全ノートを一旦 velocity=66 にしてから本スクリプトへ
INTENSITY = 1.0          # 全体の強弱の効き具合（0.9〜1.2目安）
RANGE_LOW  = 51          # 最小ベロシティ（pp 目安）
RANGE_HIGH = 104         # 最大ベロシティ（ff 目安）

# 右手トップの持ち上げ：固定加点ではなく“割合”＋ピッチで減衰（低音は控えめ）
def right_melody_ratio(pitch: int) -> float:
    if pitch >= 72:   # 高音
        return 1.03
    elif pitch >= 60: # 中音
        return 1.01
    else:             # 低音（右手低音メロは出過ぎ防止）
        return 1.002

# 右手内声（和音の内側）は薄めに抑える
INNER_SCALE_2_4 = {2: 0.92, 3: 0.88, 4: 0.84}

# 左手の基礎抑え＋和音抑え（「左手の和音が大きい」を解消する方向に強め）
LEFT_BASE_SCALE = 0.98
LEFT_CHORD_SCALE_2_4 = {2: 0.86, 3: 0.82, 4: 0.78}

# 右手トップが乗るシーンで左手を“うっすら”ダック（常時わずかに適用して耳の前出を防止）
DUCK_LEFT_ON_RIGHT_TOP = 0.96

# 拍アクセント：押し出し弱め（のっぺり回避しつつ歌モノに馴染む設定）
ACCENT_44 = [1.02, 1.00, 1.01, 0.99]
ACCENT_34 = [1.03, 1.00, 0.99]
DEFAULT_ACCENT = [1.02, 1.00, 1.00, 0.99]

# フレーズ弧（弱め）：休符で区切ったフレーズに軽いカーブ
PHRASE_MIN_REST = 0.20   # s：これ以上の休符でフレーズ区切り
PHRASE_ARC_GAIN = 6.0

# ランダム揺らぎ（打ち込み臭の軽減）
HUMANIZE_RANGE = 2       # ±2

# 同時発音の許容（3ms以内は同時とみなす）
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
    if downbeats.size == 0 or beats.size == 0: return None
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
    """低音の聴感補正：左手は強め、右手は低音メロの違和感軽減に薄く適用"""
    if which_hand != "left":
        return -2 if pitch < 60 else 0
    if pitch < 36: return -8
    if pitch < 48: return -6
    if pitch < 52: return -4
    if pitch < 57: return -2
    return 0

# ===== 本体 =====
def apply_dynamics_hand(notes, which_hand, pm):
    base = 66.0  # りのさん前処理の基準
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

            # 1) 拍アクセント（弱め）：左手はさらに薄く
            accent = beat_index_in_bar(n.start, db, bt, meter, accent_len)
            v *= (accent ** (0.70 if which_hand == "left" else 0.85))

            # 2) 和音処理：右手トップは“割合”で、左手は和音を強めに抑える
            if chord_size >= 2:
                if which_hand == "right":
                    if n is top:
                        v *= (right_melody_ratio(n.pitch) ** INTENSITY)
                    else:
                        scale = INNER_SCALE_2_4.get(chord_size, 0.82)
                        v *= (scale ** INTENSITY)
                else:
                    if n is low:
                        v *= (LEFT_BASE_SCALE ** INTENSITY)      # 土台はわずかに残す
                        v += bass_shelf_adjust(n.pitch, "left")   # 低音聴感補正
                    else:
                        scale = LEFT_CHORD_SCALE_2_4.get(chord_size, 0.76)
                        v *= (scale ** INTENSITY)
                        v += bass_shelf_adjust(n.pitch, "left")
                    v *= DUCK_LEFT_ON_RIGHT_TOP                   # 薄いダック
            else:
                if which_hand == "left":
                    v *= (LEFT_BASE_SCALE ** INTENSITY)
                    v += bass_shelf_adjust(n.pitch, "left")

            if which_hand == "right" and (chord_size == 1 or n is top):
                v += middle_melody_adjust(n.pitch)

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

            # 5) フレーズ弧（弱め）
            p = phrase_pos.get(n, 0.5)
            v += (math.sin((p - 0.15) * math.pi) * PHRASE_ARC_GAIN - 1.5) * INTENSITY

            # 6) 右手の単音メロはほんの少しだけ前へ（ピッチ依存で自然に）
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
            # 66±26 を基準幅として指定レンジへ拡大/縮小（メリハリをしっかり付ける）
            v = center + (v - center) * (span / 26.0)
            v = int(round(clamp(v, low, high)))

            out.append(pretty_midi.Note(start=n.start, end=n.end, pitch=n.pitch, velocity=v))

    return sorted(out, key=lambda n: n.start)

# ===== 実行 =====
print(f"音量変更（統合版：拍頭弱め・右手低音メロ控えめ・左手和音抑制・レンジ拡張・Merged出力）を開始します。対象: {MIDI_FILE_NAME}")
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

# CC（ペダル等）も結合（重複は基本“後勝ち”で問題ないケースが多い）
cc_all = right.control_changes + left.control_changes
cc_all.sort(key=lambda cc: (cc.time, cc.number, cc.value))
merged.control_changes = cc_all

pm_out.instruments.append(merged)
pm_out.write(OUT_NAME)
print_output_file(OUT_NAME)
print(f"OK: {OUT_NAME} を書き出しました。Enterで終了。")
input()
