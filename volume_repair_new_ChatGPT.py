import os

import pretty_midi
import math
import random

MIDI_FILE_NAME = '右手左手合算しないver(volume_repair_2につっこむ用).mid'

def print_input_file(file_name):
    print(f"読み込んだファイル: {os.path.abspath(file_name)}")

def print_output_file(file_name):
    print(f"出力したファイル: {os.path.abspath(file_name)}")

print(f"音量変更処理を開始します。問題なければEnterを押してください。対象Midiファイル:{MIDI_FILE_NAME}")
input()

TOL = 0.003  # 3ms 以内を同時発音とみなす
random.seed(42)

MIDDLE_MELODY_LOW = 52
MIDDLE_MELODY_HIGH = 64

def middle_melody_adjust(pitch):
    if MIDDLE_MELODY_LOW <= pitch <= MIDDLE_MELODY_HIGH:
        return -random.randint(3, 5)
    return 0

def group_by_onset(notes, tol=TOL):
    # onsetごとに近いノートをまとめる（安定化のため、ソート→スキャン）
    notes_sorted = sorted(notes, key=lambda n: n.start)
    groups = []
    current = [notes_sorted[0]]
    for n in notes_sorted[1:]:
        if abs(n.start - current[-1].start) <= tol:
            current.append(n)
        else:
            groups.append(current)
            current = [n]
    groups.append(current)
    return groups

def register_curve(pitch):
    # シンプルな音域カーブ（必要に応じて微調整）
    if pitch < 36:   # 低すぎ
        return -8
    if pitch < 40:   # 低域
        return -4
    if pitch > 84:   # 超高域
        return +6
    if pitch > 72:   # 高域
        return +2
    return 0         # 中域

def compress(v, mid=70, ratio=0.9):
    return mid + (v - mid) * ratio

def apply_velocity_rules(notes, which_hand):
    # 出力用にノートを複製して使う（元を破壊しない）
    out = []
    onset_groups = group_by_onset(notes)
    for grp in onset_groups:
        # グループ内のトップ音（最大ピッチ）と最低音を取る
        top = max(grp, key=lambda n: n.pitch)
        low = min(grp, key=lambda n: n.pitch)
        chord_size = len(grp)

        for n in grp:
            v = n.velocity

            # 手ごとの基礎バランス
            if which_hand == "left":
                v *= 0.90  # 左手は控えめ
            else:
                v *= 1.00

            # 和音処理
            if chord_size >= 2:
                if which_hand == "right":
                    if n is top:
                        v += 6  # メロディ持ち上げ
                    else:
                        # 内声スケール：和音数に応じて強めに抑える
                        scale = {2:0.93, 3:0.88, 4:0.84}.get(chord_size, 0.82)
                        v *= scale
                else:
                    # 左手の和音は基本抑えるが、最低音は少し残す
                    if n is low:
                        v *= 0.92
                    else:
                        scale = {2:0.90, 3:0.85, 4:0.82}.get(chord_size, 0.80)
                        v *= scale

            if which_hand == "right" and (chord_size == 1 or n is top):
                v += middle_melody_adjust(n.pitch)

            # 音域カーブ
            v += register_curve(n.pitch)

            # 軽いコンプ（ダイナミクスを残しつつ暴れを抑える）
            v = compress(v, mid=72 if which_hand=="left" else 75, ratio=0.90)

            # ヒューマナイズ（±2）
            v += random.randint(-2, 2)

            # クリップ
            v = int(max(1, min(127, round(v))))

            m = pretty_midi.Note(
                start=n.start, end=n.end, pitch=n.pitch, velocity=v
            )
            out.append(m)
    # 時間順に並べ直し
    return sorted(out, key=lambda n: n.start)

# === メイン処理 ===
print_input_file(MIDI_FILE_NAME)
midi_in = pretty_midi.PrettyMIDI(MIDI_FILE_NAME)

# 安全に：トラック存在チェックとプログラム保持
right_inst = midi_in.instruments[0]
left_inst  = midi_in.instruments[1]

right_notes = apply_velocity_rules(right_inst.notes, "right")
left_notes  = apply_velocity_rules(left_inst.notes, "left")

midi_out = pretty_midi.PrettyMIDI()

# 右手・左手を別インストゥルメントとして保持（プログラム/チャンネルも継承推奨）
inst_r = pretty_midi.Instrument(program=right_inst.program, is_drum=right_inst.is_drum, name=right_inst.name)
inst_l = pretty_midi.Instrument(program=left_inst.program,  is_drum=left_inst.is_drum,  name=left_inst.name)

inst_r.notes = right_notes
inst_l.notes = left_notes

# コントロールチェンジ（ペダル等）も可能ならコピー
inst_r.control_changes = right_inst.control_changes
inst_l.control_changes = left_inst.control_changes

midi_out.instruments.append(inst_r)
midi_out.instruments.append(inst_l)

midi_out = pretty_midi.PrettyMIDI()

# どちらかのプログラムを採用（ここでは右手を採用）
merged = pretty_midi.Instrument(
    program=right_inst.program,
    is_drum=right_inst.is_drum,
    name="merged"
)

# ノートを結合して時刻順に並べる
merged.notes = sorted(right_notes + left_notes, key=lambda n: (n.start, n.pitch))

# CC（ペダル等）も両方を結合して時刻順・重複整理（必要ならユニーク化）
merged.control_changes = sorted(
    right_inst.control_changes + left_inst.control_changes,
    key=lambda cc: (cc.time, cc.number, cc.value)
)

midi_out.instruments.append(merged)
OUT_NAME = "音量変更後.mid"
midi_out.write(OUT_NAME)
print_output_file(OUT_NAME)

print("OK: 音量変更後.mid を書き出しました。")
input()
