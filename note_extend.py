import pretty_midi

def extend_notes(notes):
    """
    引数で渡されたnotesオブジェクトに対して、次の音まで音を伸ばす処理を行う関数。
    具体的には、処理対象の次のnoteオブジェクトのstart位置を読み取り、そのstart位置までendの位置を伸ばすことで、音を伸ばす処理を実現させている。
    ※処理対象のend位置=次の音のstart位置に変更している。

    -------
    Params

    notes : any
    音を伸ばす前のnotesオブジェクト
    -------
    Return

    notes : any
    音を伸ばした後のnotesオブジェクト
    """
    #配列の次のnoteを取得するための変数を定義(最初から次のnoteを取得したいため初期値を1とする)
    next_index = 1

    for note in notes:
        if next_index < len(notes):
            # 次の音のnoteオブジェクトを取得
            next_note = notes[next_index]

            # 和音の場合(処理対象の音のstart位置と、次の音のstart位置が同じ場合は和音判定)
            if note.start == next_note.start:
                moreover_next_index = next_index + 1

                # 和音の次の音のインデックスが取得できるまで、繰り返し処理を行う。（最後の和音の場合、この処理はスキップする。）
                while moreover_next_index < len(notes) and next_note.start == notes[moreover_next_index].start:
                    moreover_next_index += 1

                # 最後の音じゃなければ、和音の次のnoteのstart位置まで、処理対象の音のend位置を伸ばす。
                if moreover_next_index < len(notes):
                    note.end = notes[moreover_next_index].start

            # 単音の場合
            else:
                note.end = next_note.start

            next_index += 1
    return notes

def main():
    print("音の長さ調整処理を開始します。問題なければEnterを押してください。")
    input()

    # MIDIデータの準備
    midi_data_new = pretty_midi.PrettyMIDI()
    new_instrument = pretty_midi.Instrument(0)

    old_musicsheet_data = pretty_midi.PrettyMIDI()
    musicsheet_midi = [pretty_midi.Instrument(0), pretty_midi.Instrument(0)]

    midi_data = pretty_midi.PrettyMIDI('右手左手分けた後.mid')
    notes_right = midi_data.instruments[0].notes
    notes_left = midi_data.instruments[1].notes

    # ノートの長さを調整
    extended_notes_right = extend_notes(notes_right)
    extended_notes_left = extend_notes(notes_left)

    # 楽器にノートを追加
    new_instrument.notes.extend(extended_notes_right)
    new_instrument.notes.extend(extended_notes_left)
    musicsheet_midi[0].notes.extend(extended_notes_right)
    musicsheet_midi[1].notes.extend(extended_notes_left)

    midi_data_new.instruments.append(new_instrument)
    old_musicsheet_data.instruments.extend(musicsheet_midi)

    # MIDIデータを書き込み
    midi_data_new.write("右手左手伸ばした後(音量変更前).mid")
    old_musicsheet_data.write("右手左手合算しないver(volume_repair_2につっこむ用).mid")

    print("処理が正常に終了しました。Enterを押してください。")
    input()

if __name__ == "__main__":
    main()