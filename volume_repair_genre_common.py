import math
import os
import random

import pretty_midi


MIDI_FILE_NAME = "右手左手合算しないver(volume_repair_2につっこむ用).mid"
TOL = 0.003


def print_input_file(file_name):
    print(f"読み込んだファイル: {os.path.abspath(file_name)}")


def print_output_file(file_name):
    print(f"出力したファイル: {os.path.abspath(file_name)}")


def clamp(value, low, high):
    return max(low, min(high, value))


def group_onsets(notes):
    groups = []
    current = []
    for note in sorted(notes, key=lambda n: (n.start, n.pitch)):
        if not current or abs(note.start - current[-1].start) <= TOL:
            current.append(note)
        else:
            groups.append(current)
            current = [note]
    if current:
        groups.append(current)
    return groups


def phrase_positions(notes, min_rest):
    notes = sorted(notes, key=lambda n: (n.start, n.pitch))
    if not notes:
        return {}

    phrases = []
    current = [notes[0]]
    for prev, note in zip(notes, notes[1:]):
        if note.start - prev.end >= min_rest:
            phrases.append(current)
            current = [note]
        else:
            current.append(note)
    phrases.append(current)

    positions = {}
    for phrase in phrases:
        start = phrase[0].start
        end = max(note.end for note in phrase)
        duration = max(1e-6, end - start)
        for note in phrase:
            positions[note] = clamp((note.start - start) / duration, 0.0, 1.0)
    return positions


def get_timing(pm):
    try:
        beats = list(pm.get_beats())
    except Exception:
        beats = []
    try:
        downbeats = list(pm.get_downbeats())
    except Exception:
        downbeats = []
    return beats, downbeats


def beat_index_at(time, beats):
    index = 0
    for i, beat in enumerate(beats):
        if beat <= time:
            index = i
        else:
            break
    return index


def timing_adjust(time, beats, downbeats, preset):
    if not beats:
        return 1.0, 0.0

    index = beat_index_at(time, beats)
    factor = preset["beat_pattern"][index % len(preset["beat_pattern"])]

    if downbeats and min(abs(time - beat) for beat in downbeats) <= preset["beat_window"]:
        factor *= preset["downbeat_factor"]
    if index % 4 in (1, 3):
        factor *= preset["backbeat_factor"]

    offbeat_boost = 0.0
    if index + 1 < len(beats):
        midpoint = (beats[index] + beats[index + 1]) / 2.0
        if abs(time - midpoint) <= preset["offbeat_window"]:
            offbeat_boost = preset["offbeat_boost"]
    return factor, offbeat_boost


def pitch_adjust(pitch, which_hand, preset):
    value = 0.0
    if pitch < 36:
        value += preset["very_low"]
    elif pitch < 48:
        value += preset["low"]
    elif pitch > 84:
        value += preset["very_high"]
    elif pitch > 72:
        value += preset["high"]

    if which_hand == "left" and pitch < 52:
        value += preset["left_bass"]
    return value


def melody_factor(pitch, preset):
    if pitch >= 76:
        return preset["melody_high"]
    if pitch >= 60:
        return preset["melody_mid"]
    return preset["melody_low"]


def middle_melody_adjust(pitch, preset):
    if preset["middle_melody_low"] <= pitch <= preset["middle_melody_high"]:
        return -random.randint(preset["middle_melody_drop_min"], preset["middle_melody_drop_max"])
    return 0


def adjust_notes(notes, which_hand, pm, preset):
    random.seed(preset["seed"] + (0 if which_hand == "right" else 1000))
    beats, downbeats = get_timing(pm)
    phrase_pos = phrase_positions(notes, preset["phrase_min_rest"])
    result = []

    for group in group_onsets(notes):
        top = max(group, key=lambda n: n.pitch)
        low = min(group, key=lambda n: n.pitch)
        chord_size = len(group)

        for note in group:
            velocity = float(note.velocity) * preset[f"{which_hand}_base"]
            beat_factor, offbeat_boost = timing_adjust(note.start, beats, downbeats, preset)
            velocity = velocity * beat_factor + offbeat_boost

            if chord_size >= 2:
                if which_hand == "right":
                    if note is top:
                        velocity += preset["right_top"]
                        velocity *= melody_factor(note.pitch, preset)
                        velocity += middle_melody_adjust(note.pitch, preset)
                    else:
                        velocity *= preset["right_inner"].get(chord_size, preset["right_inner_default"])
                else:
                    if note is low:
                        velocity += preset["left_low"]
                    else:
                        velocity *= preset["left_inner"].get(chord_size, preset["left_inner_default"])
                    velocity *= preset["left_chord_duck"]
            elif which_hand == "right":
                velocity *= melody_factor(note.pitch, preset)
                velocity += middle_melody_adjust(note.pitch, preset)

            velocity += pitch_adjust(note.pitch, which_hand, preset)
            if note.end - note.start >= preset["long_threshold"]:
                velocity += preset["long_boost"]

            position = phrase_pos.get(note, 0.5)
            velocity += math.sin(position * math.pi) * preset["phrase_arc"]
            velocity += random.randint(-preset["humanize"], preset["humanize"])
            velocity = preset["center"] + (velocity - preset["center"]) * preset["range_ratio"]
            velocity = int(round(clamp(velocity, preset["range_low"], preset["range_high"])))

            result.append(
                pretty_midi.Note(
                    velocity=velocity,
                    pitch=note.pitch,
                    start=note.start,
                    end=note.end,
                )
            )

    return sorted(result, key=lambda n: (n.start, n.pitch))


def write_merged(pm_in, right_notes, left_notes, out_name):
    right = pm_in.instruments[0]
    left = pm_in.instruments[1]
    pm_out = pretty_midi.PrettyMIDI()
    merged = pretty_midi.Instrument(program=right.program, is_drum=right.is_drum, name="Merged")
    merged.notes = sorted(right_notes + left_notes, key=lambda n: (n.start, n.pitch))
    merged.control_changes = sorted(
        right.control_changes + left.control_changes,
        key=lambda cc: (cc.time, cc.number, cc.value),
    )
    pm_out.instruments.append(merged)
    pm_out.write(out_name)


def run_volume_repair(preset):
    print(f"{preset['label']} 用の音量変更処理を開始します。対象: {MIDI_FILE_NAME}")
    input("Enterで続行: ")

    print_input_file(MIDI_FILE_NAME)
    pm_in = pretty_midi.PrettyMIDI(MIDI_FILE_NAME)
    if len(pm_in.instruments) < 2:
        raise ValueError("右手・左手の2トラックが必要です。")

    right_notes = adjust_notes(pm_in.instruments[0].notes, "right", pm_in, preset)
    left_notes = adjust_notes(pm_in.instruments[1].notes, "left", pm_in, preset)
    write_merged(pm_in, right_notes, left_notes, preset["out_name"])

    print_output_file(preset["out_name"])
    print(f"OK: {preset['out_name']} を書き出しました。")
    input("Enterで終了: ")


BASE_PRESET = {
    "seed": 100,
    "range_low": 40,
    "range_high": 112,
    "center": 66.0,
    "range_ratio": 1.0,
    "right_base": 1.0,
    "left_base": 0.9,
    "right_top": 5.0,
    "left_low": 1.0,
    "left_chord_duck": 0.9,
    "right_inner": {2: 0.9, 3: 0.85, 4: 0.8},
    "right_inner_default": 0.76,
    "left_inner": {2: 0.85, 3: 0.8, 4: 0.75},
    "left_inner_default": 0.72,
    "melody_high": 1.06,
    "melody_mid": 1.03,
    "melody_low": 1.0,
    "middle_melody_low": 52,
    "middle_melody_high": 64,
    "middle_melody_drop_min": 3,
    "middle_melody_drop_max": 5,
    "very_low": -7.0,
    "low": -3.0,
    "high": 2.0,
    "very_high": 4.0,
    "left_bass": -1.0,
    "long_threshold": 0.5,
    "long_boost": 2.0,
    "phrase_min_rest": 0.2,
    "phrase_arc": 4.0,
    "humanize": 2,
    "beat_pattern": [1.02, 1.0, 1.0, 0.99],
    "downbeat_factor": 1.0,
    "backbeat_factor": 1.0,
    "beat_window": 0.035,
    "offbeat_boost": 0.0,
    "offbeat_window": 0.045,
}


def make_preset(**overrides):
    preset = BASE_PRESET.copy()
    preset.update(overrides)
    return preset


PRESETS = {
    "ballad": make_preset(
        label="バラード系",
        out_name="音量変更後_BALLAD_merged.mid",
        seed=110,
        range_low=30,
        range_high=116,
        range_ratio=1.05,
        left_base=0.82,
        right_top=9.0,
        left_chord_duck=0.86,
        right_inner={2: 0.86, 3: 0.78, 4: 0.72},
        left_inner={2: 0.78, 3: 0.70, 4: 0.66},
        long_threshold=0.65,
        long_boost=6.0,
        phrase_min_rest=0.25,
        phrase_arc=9.0,
        beat_pattern=[1.03, 0.98, 1.00, 0.97],
        offbeat_boost=0.0,
    ),
    "rock": make_preset(
        label="ロック系",
        out_name="音量変更後_ROCK_merged.mid",
        seed=210,
        range_low=50,
        range_high=122,
        center=70.0,
        range_ratio=1.1,
        right_base=1.06,
        left_base=1.02,
        left_low=6.0,
        left_bass=4.0,
        left_chord_duck=0.96,
        right_inner={2: 0.94, 3: 0.9, 4: 0.86},
        left_inner={2: 0.92, 3: 0.88, 4: 0.84},
        phrase_arc=2.5,
        beat_pattern=[1.08, 1.0, 1.04, 1.02],
        downbeat_factor=1.05,
        backbeat_factor=1.04,
        offbeat_boost=1.0,
    ),
    "jazz": make_preset(
        label="ジャズ系",
        out_name="音量変更後_JAZZ_merged.mid",
        seed=310,
        range_low=34,
        range_high=112,
        center=62.0,
        range_ratio=1.04,
        right_base=0.96,
        left_base=0.88,
        right_top=1.5,
        humanize=5,
        left_chord_duck=0.98,
        right_inner={2: 0.98, 3: 0.95, 4: 0.92},
        left_inner={2: 0.94, 3: 0.90, 4: 0.86},
        phrase_arc=2.0,
        beat_pattern=[0.98, 1.06, 0.96, 1.08],
        downbeat_factor=0.96,
        backbeat_factor=1.06,
        offbeat_boost=6.0,
        offbeat_window=0.06,
    ),
    "citypop": make_preset(
        label="シティポップ系",
        out_name="音量変更後_CITYPOP_merged.mid",
        seed=410,
        range_low=54,
        range_high=108,
        center=68.0,
        range_ratio=0.82,
        right_base=1.06,
        left_base=0.82,
        right_top=8.0,
        left_chord_duck=0.82,
        right_inner={2: 0.86, 3: 0.80, 4: 0.76},
        left_inner={2: 0.78, 3: 0.72, 4: 0.68},
        phrase_arc=3.0,
        humanize=1,
        beat_pattern=[1.02, 1.00, 1.02, 1.00],
        backbeat_factor=1.05,
        offbeat_boost=2.0,
    ),
    "shibuyakei": make_preset(
        label="渋谷系",
        out_name="音量変更後_SHIBUYAKEI_merged.mid",
        seed=510,
        range_low=42,
        range_high=120,
        center=67.0,
        range_ratio=1.12,
        right_base=1.04,
        left_base=0.84,
        right_top=6.0,
        left_chord_duck=0.84,
        right_inner={2: 0.88, 3: 0.80, 4: 0.74},
        left_inner={2: 0.80, 3: 0.74, 4: 0.70},
        humanize=5,
        phrase_min_rest=0.16,
        phrase_arc=2.0,
        beat_pattern=[0.98, 1.07, 0.95, 1.09],
        downbeat_factor=0.97,
        backbeat_factor=1.07,
        offbeat_boost=5.0,
        offbeat_window=0.05,
    ),
}
