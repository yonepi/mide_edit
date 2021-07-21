import copy
import glob
import os

import pretty_midi

#midファイルの名称取得及び、mid~ファイルの削除を行う関数
def get_midfile_name(midname):
    folder_path = r"checkfolder\*"
    file_list = glob.glob(folder_path)

    #MSPでmidiファイルを作成した場合、mid~という拡張子の謎ファイルができるので、最初にそれを削除する
    delete_midi_name = [del_midi for del_midi in file_list if f"{midname}~" in del_midi]
    print("delete_midi_name→",delete_midi_name)
    if delete_midi_name:
        os.remove(delete_midi_name[0])
    new_midi_name = [new_name for new_name in file_list if midname in new_name]
    if not new_midi_name:
        print(f"{midname}で終了するファイルが存在しません。")
        input()
    return new_midi_name[0]

#①片手ずつの和音で「スタートタイム（key）とピッチを抽出した辞書」、「スタートタイム（key）とエンドタイムを抽出した辞書」を作成する関数
def get_allchords(which_hands_note):
    #start_timeが同一の値を格納するための空リストを作成
    midi_list = []
    for note in which_hands_note:
        midi_list.append(note.start)
    all_chords = set(midi_list)

    chord_pitch_dic = {}
    for note in which_hands_note:
        if note.start in all_chords:
            #setdefaultを使用することで、スタートタイム（key）が同一のピッチをリスト型にして、一つのキーに複数のピッチを格納している
            #https://qiita.com/tag1216/items/b2765e9e87025c01e57f
            chord_pitch_dic.setdefault(note.start, []).append(note.pitch)

    chord_endtime_dic = {}
    for note in which_hands_note:
        if note.start in all_chords:
            #setdefaultを使用することで、スタートタイム（key）が同一のピッチをリスト型にして、一つのキーに複数のピッチを格納している
            #https://qiita.com/tag1216/items/b2765e9e87025c01e57f
            chord_endtime_dic.setdefault(note.start, []).append(note.end)
    return chord_pitch_dic,chord_endtime_dic

#①で取得した片手ずつの全ての和音の中で、距離が12以上（つまりオクターブ）離れている場合警告を出す関数。
def check_hands_range(which_hand_chords):
    for chord_start in which_hand_chords.keys():
        hand_range_list = which_hand_chords.get(chord_start)
        if (max(hand_range_list) - min(hand_range_list)) > 12:
            print((chord_start+2)/2,"のレンジが1オクターブ以上離れています。→",max(hand_range_list)," ",min(hand_range_list))
    print("チェック終了")

#①で取得した片手ずつの全ての和音の中で、片手で5音以上弾いてたら警告を出す関数。
def check_hands_notecount(which_hand_chords):
    for chord_start in which_hand_chords.keys():
        hand_range_list = which_hand_chords.get(chord_start)
        if len(hand_range_list) > 4 :
            print((chord_start+2)/2,"で5音以上弾いています。→",hand_range_list)
    print("チェック終了")

#①で取得した片手ずつの全ての和音の中で、終了タイミングが異なる和音があれば、警告を出す。
def check_hands_endtime(which_hand_chords):
    for chord_start in which_hand_chords.keys():
        hand_range_list = which_hand_chords.get(chord_start)
        if not len(list(set(hand_range_list))) == 1:
            print((chord_start+2)/2,"で終了タイミングが異なる和音があります→",hand_range_list)
    print("チェック終了")

def check_easy_note(which_hand_chords):
    for chord_start in which_hand_chords.keys():
        hand_range_list = which_hand_chords.get(chord_start)
        if len(list(set(hand_range_list))) > 1:
            print((chord_start+2)/2,"初級にも関わらず和音があります→",hand_range_list)
    print("チェック終了")

#両手の音の数から片手分をマイナスして、自動で分ける関数
def hands_subtraction(both_note):
    both_note

#初級のmidiデータを読み込み
midifile_name = get_midfile_name("初級.mid")
midi_data = pretty_midi.PrettyMIDI(midifile_name)
midi_tracks = midi_data.instruments
# トラック１（右手）、トラック2（左手）のノートを取得
notes_right = midi_tracks[0].notes
notes_left = midi_tracks[1].notes
right_all_chords_pitch, right_all_chords_endtime = get_allchords(notes_right)
check_hands_range(right_all_chords_pitch)
check_hands_notecount(right_all_chords_pitch)
check_hands_endtime(right_all_chords_endtime)
check_easy_note(right_all_chords_pitch)

left_all_chords_pitch, left_all_chords_endtime = get_allchords(notes_left)
check_hands_range(left_all_chords_pitch)
check_hands_notecount(left_all_chords_pitch)
check_hands_endtime(left_all_chords_endtime)
check_easy_note(left_all_chords_pitch)
print("初級のチェックが終了しました。Enterキーを押してください。")
input()

#中級のmidiデータを読み込み
midifile_name = get_midfile_name("中級.mid")
midi_data = pretty_midi.PrettyMIDI(midifile_name)
midi_tracks = midi_data.instruments
notes_right = midi_tracks[0].notes
notes_left = midi_tracks[1].notes
right_all_chords_pitch, right_all_chords_endtime = get_allchords(notes_right)
check_hands_range(right_all_chords_pitch)
check_hands_notecount(right_all_chords_pitch)
check_hands_endtime(right_all_chords_endtime)

left_all_chords_pitch, left_all_chords_endtime = get_allchords(notes_left)
check_hands_range(left_all_chords_pitch)
check_hands_notecount(left_all_chords_pitch)
check_hands_endtime(left_all_chords_endtime)
print("中級のチェックが終了しました。Enterキーを押してください。")
input()

#自由形のmidiデータを読み込み
midifile_name = get_midfile_name("自由形.mid")
midi_data = pretty_midi.PrettyMIDI(midifile_name)
midi_tracks = midi_data.instruments
notes_right = midi_tracks[0].notes
notes_left = midi_tracks[1].notes
right_all_chords_pitch, right_all_chords_endtime = get_allchords(notes_right)
check_hands_range(right_all_chords_pitch)
check_hands_notecount(right_all_chords_pitch)
check_hands_endtime(right_all_chords_endtime)

left_all_chords_pitch, left_all_chords_endtime = get_allchords(notes_left)
check_hands_range(left_all_chords_pitch)
check_hands_notecount(left_all_chords_pitch)
check_hands_endtime(left_all_chords_endtime)
print("自由形のチェックが終了しました。Enterキーを押してください。")
input()

"""
pretty_midyのデータ構造チェック用
print(notes_right)
print(notes_left)
print(notes_right[0])
print(notes_right[0].start)
print(notes_right[1])
"""