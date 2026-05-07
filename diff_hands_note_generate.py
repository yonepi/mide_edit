import glob
import os
from dataclasses import dataclass

import mido


CHECK_FOLDER_PATTERN = r"checkfolder\*"
TARGET_FILE_SUFFIXES = ["初級.mid", "中級.mid", "自由形.mid"]


@dataclass
class MidiNote:
    start: int
    end: int
    pitch: int
    velocity: int


def print_input_file(file_name):
    print(f"読み込んだファイル: {os.path.abspath(file_name)}")


def print_output_file(file_name):
    print(f"出力したファイル: {os.path.abspath(file_name)}")


def get_midfile_name(midname):
    """
    midファイルの名称取得及び、mid~ファイルの削除を行う関数。
    checkfolder内で、引数で指定した文字列を含むMIDIファイルを探す。
    """
    file_list = glob.glob(CHECK_FOLDER_PATTERN)

    delete_midi_name = [del_midi for del_midi in file_list if f"{midname}~" in del_midi]
    print("delete_midi_name→", delete_midi_name)
    if delete_midi_name:
        os.remove(delete_midi_name[0])

    new_midi_name = [new_name for new_name in file_list if midname in new_name and new_name.endswith(".mid")]
    if not new_midi_name:
        print(f"{midname}で終了するファイルが存在しません。")
        input()
        return None

    print(f"{midname}に対して処理を開始します。")
    return new_midi_name[0]


def is_note_on(message):
    return message.type == "note_on" and message.velocity > 0


def is_note_off(message):
    return message.type == "note_off" or (message.type == "note_on" and message.velocity == 0)


def extract_notes(track):
    notes = []
    active_notes = {}
    current_tick = 0

    for message in track:
        current_tick += message.time
        if is_note_on(message):
            active_notes.setdefault((message.channel, message.note), []).append((current_tick, message.velocity))
        elif is_note_off(message):
            key = (message.channel, message.note)
            if key not in active_notes or not active_notes[key]:
                continue
            start_tick, velocity = active_notes[key].pop(0)
            notes.append(
                MidiNote(
                    start=start_tick,
                    end=current_tick,
                    pitch=message.note,
                    velocity=velocity,
                )
            )

    return notes


def note_key(note):
    return (note.start, note.end, note.pitch)


def split_unique_notes(notes_1, notes_2):
    """
    ノート数が少ない方を片手パートとして残し、多い方から重複ノートを除く。
    以前の処理と同じ考え方だが、秒ではなくMIDI tickで比較する。
    """
    if len(notes_1) > len(notes_2):
        print("Track2側の方が少ないよ")
        more_notes = notes_1
        few_notes = notes_2
    else:
        print("Track1側の方が少ないよ")
        more_notes = notes_2
        few_notes = notes_1

    few_keys = {note_key(note) for note in few_notes}
    more_unique_notes = [note for note in more_notes if note_key(note) not in few_keys]
    return few_notes, more_unique_notes


def average_pitch(notes):
    if not notes:
        return 0
    return sum(note.pitch for note in notes) / len(notes)


def assign_right_left(notes_1, notes_2):
    avg_1 = average_pitch(notes_1)
    avg_2 = average_pitch(notes_2)
    print(f"newnote_1の平均ピッチ→{avg_1}")
    print(f"newnote_2の平均ピッチ→{avg_2}")

    if avg_1 > avg_2:
        print("newnotes_1は右手だよ")
        return notes_1, notes_2

    print("newnotes_1は左手だよ")
    return notes_2, notes_1


def collect_meta_messages(midi_data):
    meta_events = []
    for track in midi_data.tracks:
        current_tick = 0
        for message in track:
            current_tick += message.time
            if message.is_meta and message.type != "end_of_track":
                meta_events.append((current_tick, message.copy(time=0)))
    return meta_events


def note_events(notes, channel):
    events = []
    for note in notes:
        events.append(
            (
                note.start,
                mido.Message("note_on", note=note.pitch, velocity=note.velocity, channel=channel, time=0),
            )
        )
        events.append(
            (
                note.end,
                mido.Message("note_off", note=note.pitch, velocity=0, channel=channel, time=0),
            )
        )
    return events


def build_track(events):
    track = mido.MidiTrack()
    last_tick = 0

    for absolute_tick, message in sorted(events, key=lambda item: (item[0], event_sort_order(item[1]))):
        message = message.copy(time=absolute_tick - last_tick)
        track.append(message)
        last_tick = absolute_tick

    track.append(mido.MetaMessage("end_of_track", time=0))
    return track


def event_sort_order(message):
    if message.type == "track_name":
        return 0
    if message.is_meta:
        return 1
    if is_note_off(message):
        return 2
    if is_note_on(message):
        return 3
    return 4


def write_split_midi(file_name, right_notes, left_notes, original_midi):
    """
    元MIDIのticks_per_beatとメタイベントを保ったまま2トラックで書き出す。
    Track1: メタ情報 + 右手ノート
    Track2: 左手ノート
    """
    output_midi = mido.MidiFile(type=1, ticks_per_beat=original_midi.ticks_per_beat)

    right_events = collect_meta_messages(original_midi)
    right_events.append((0, mido.MetaMessage("track_name", name="Right Hand", time=0)))
    right_events.extend(note_events(right_notes, channel=0))

    left_events = [(0, mido.MetaMessage("track_name", name="Left Hand", time=0))]
    left_events.extend(note_events(left_notes, channel=1))

    output_midi.tracks.append(build_track(right_events))
    output_midi.tracks.append(build_track(left_events))
    output_midi.save(file_name)


def find_note_tracks(midi_data):
    note_tracks = []
    for track_index, track in enumerate(midi_data.tracks):
        notes = extract_notes(track)
        if notes:
            note_tracks.append((track_index, notes))

    if len(note_tracks) < 2:
        raise ValueError("ノートが入っているトラックが2つ以上必要です。")

    return note_tracks[0], note_tracks[1]


def process_file(file_name):
    print_input_file(file_name)
    midi_data = mido.MidiFile(file_name)
    print(f"元MIDI ticks_per_beat→{midi_data.ticks_per_beat}")
    print(f"元MIDI track数→{len(midi_data.tracks)}")

    (track_1_index, notes_1), (track_2_index, notes_2) = find_note_tracks(midi_data)
    print(f"処理対象Track→{track_1_index}, {track_2_index}")

    newnotes_1, newnotes_2 = split_unique_notes(notes_1, notes_2)
    right_notes, left_notes = assign_right_left(newnotes_1, newnotes_2)
    write_split_midi(file_name, right_notes, left_notes, midi_data)

    print(f"出力MIDI ticks_per_beat→{midi_data.ticks_per_beat}")
    print_output_file(file_name)


for target_file_suffix in TARGET_FILE_SUFFIXES:
    midifile_name = get_midfile_name(target_file_suffix)
    if midifile_name is not None:
        process_file(midifile_name)

input()
