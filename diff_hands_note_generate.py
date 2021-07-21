import glob
import os

from numpy.lib.function_base import average

import pretty_midi

def get_midfile_name(midname):
    """
    ■midファイルの名称取得及び、mid~ファイルの削除を行う関数
    指定のフォルダ内のファイル名を全て取得後、引数で指定したファイル名が、あればリストに加えるという流れで処理を行う。
    """
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
    else:
        print(f"{midname}に対して処理を開始します。")
        return new_midi_name[0]

def diff_note_get():
    """
    ・Noteオブジェクトの場合、同じ音であっても重複判定されないので（trackが違うため？idが異なっている）、まずは文字列に変換する必要がある。
    ・文字列に変換したものをnotesオブジェクトに足した場合は、最終的なMIDIファイルの生成時にエラーが発生する。
    ・つまり、比較は文字列変換したノートで行いつつ、削除は元のノートオブジェクトを削除するよう実装している。
    """
    if len(notes_right) > len(notes_left):
        print("左手の方が少ないよ")
        more_notelist = notes_right
        few_notelist = notes_left
    else:
        print("右手の方が少ないよ")
        more_notelist = notes_left
        few_notelist = notes_right

    few_strnote = []

    for str_note in few_notelist:
        few_strnote.append(str(str_note))

    """
    ここでリストに変換している理由について、prrety_midiが提供しているnotesオブジェクトのままでは、for文がうまく動いてくれない時がある。
    ※原因不明だが、notesオブジェクトのままだと、for文直下でduplicate_noteを出力した際に、全てのノートが出力されないことが確認できる。
    そのため、リストに変換してfor文で回すことですべてのオブジェクトに対して、処理を実行することができる
    """
    for duplicate_note in list(more_notelist):
        print(duplicate_note)
        duplicate_str = str(duplicate_note)
        if duplicate_str in few_strnote:
            more_notelist.remove(duplicate_note)
    return few_notelist,more_notelist

#変換したノートを新規のMIDIファイルに格納する関数
def generate_new_midfile():
    #新規発行用のmidiリストを作成
    newmidi_in_def = pretty_midi.PrettyMIDI()
    new_instrument = [pretty_midi.Instrument(0),pretty_midi.Instrument(0)]
    sum_pitch1 = 0
    sum_pitch2 = 0
    for i in newnotes_1:
        print(i.pitch)
        sum_pitch1 += i.pitch
    for i in newnotes_2:
        print(i.pitch)
        sum_pitch2 += i.pitch

    print(f"newnote_1の平均ピッチ→{sum_pitch1 / len(newnotes_1)}")
    print(f"newnote_2の平均ピッチ→{sum_pitch2 / len(newnotes_2)}")

    if (sum_pitch1 / len(newnotes_1)) > (sum_pitch2 / len(newnotes_2)):
        print("newnotes_1は右手だよ")
        for instrument_1 in newnotes_1:
            new_instrument[0].notes.append(instrument_1)
        for instrument_2 in newnotes_2:
            new_instrument[1].notes.append(instrument_2)
    else:
        print("newnotes_1は左手だよ")
        for instrument_1 in newnotes_2:
            new_instrument[0].notes.append(instrument_1)
        for instrument_2 in newnotes_1:
            new_instrument[1].notes.append(instrument_2)

    #右手と左手のピッチの平均値を出して、高ければ右手（つまり最初のトラック）に入れる処理を書きたいよ。
    newmidi_in_def.instruments.append(new_instrument[0])
    newmidi_in_def.instruments.append(new_instrument[1])
    print(f"length→{len(newmidi_in_def.instruments)}")
    print(newmidi_in_def.instruments[0])
    return newmidi_in_def


#既存midiデータの読み込み
midifile_name = get_midfile_name("初級.mid")
if midifile_name is not None:
    midi_data = pretty_midi.PrettyMIDI(midifile_name)
    midi_tracks = midi_data.instruments
    # トラック１（右手）、トラック2（左手）のノートを取得
    notes_right = midi_tracks[0].notes
    notes_left = midi_tracks[1].notes

    newnotes_1, newnotes_2 = diff_note_get()
    midi_data_new = generate_new_midfile()
    midi_data_new.write(midifile_name)
    del midifile_name

#既存midiデータの読み込み
midifile_name = get_midfile_name("中級.mid")
if midifile_name is not None:
    midi_data = pretty_midi.PrettyMIDI(midifile_name)
    midi_tracks = midi_data.instruments
    # トラック１（右手）、トラック2（左手）のノートを取得
    notes_right = midi_tracks[0].notes
    notes_left = midi_tracks[1].notes

    newnotes_1, newnotes_2 = diff_note_get()
    midi_data_new = generate_new_midfile()
    midi_data_new.write(midifile_name)
    del midifile_name

#既存midiデータの読み込み
midifile_name = get_midfile_name("自由形.mid")

if midifile_name is not None:
    midi_data = pretty_midi.PrettyMIDI(midifile_name)
    midi_tracks = midi_data.instruments
    # トラック１（右手）、トラック2（左手）のノートを取得
    notes_right = midi_tracks[0].notes
    notes_left = midi_tracks[1].notes
    newnotes_1, newnotes_2 = diff_note_get()
    midi_data_new = generate_new_midfile()
    midi_data_new.write(midifile_name)
    del midifile_name