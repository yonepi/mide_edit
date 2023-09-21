import pretty_midi

print("音量変更処理を開始します。問題なければEnterを押してください。")
input()

def adjust_velocity_for_chords(notes, which_hand):
    # notesのスタート位置をリスト化
    start_times = [note.start for note in notes]
    # リスト化したstart位置から、同じstart位置が存在している場合、和音として抽出
    chords = [[e, start_times.count(e)] for e in set(start_times) if start_times.count(e) > 1]

    # スタートタイムとピッチの情報を持つ辞書を作成
    note_data = [{"start_time": note.start, "pitch": note.pitch} for note in notes]

    # 和音の情報を辞書に追加
    for chord in chords:
        chord.extend([data["pitch"] for data in note_data if data["start_time"] == chord[0]])

    # 和音情報をリストに整理
    chords_list = [[chord[:2], chord[2:]] for chord in chords]

    # ノートごとの音量調整
    for note in notes:
        # 左手の場合、一律で音量を下げる
        if which_hand == "left":
            note.velocity -= 5

        # 和音の場合、音の数に応じて音量を下げる
        for chord_data in chords_list:

            # 右手かつ、最高音の場合は、和音でも音量を下げない。
            if which_hand == "right" and note.pitch == max(chord_data[1]):
                pass

            elif chord_data[0][0] == note.start:
                chord_count = chord_data[0][1]
                if chord_count == 2:
                    #左手の場合、2和音でもちょっと多めに下げる。
                    if which_hand == "left":
                        note.velocity -= 8
                    else:
                        note.velocity -= 5
                elif chord_count == 3:
                    note.velocity -= 8
                elif chord_count == 4:
                    note.velocity -= 12
                elif chord_count >= 5:
                    note.velocity -= 12

        # 低い音域のノートの音量をさらに調整
        if note.pitch < 36:
            note.velocity -= 10

        # 調整したノートを楽器に追加
        instrument.notes.append(note)

# 既存のMIDIデータを読み込む
midi_data = pretty_midi.PrettyMIDI('右手左手合算しないver(volume_repair_2につっこむ用).mid')

# 右手と左手のノートを取得
notes_right = midi_data.instruments[0].notes
notes_left = midi_data.instruments[1].notes

# 新しいMIDIデータの初期化
midi_data_new = pretty_midi.PrettyMIDI()
instrument = pretty_midi.Instrument(0)

# 音量調整の実行
adjust_velocity_for_chords(notes = notes_right, which_hand = "right")
adjust_velocity_for_chords(notes = notes_left, which_hand = "left")

# 新しいMIDIデータに楽器を追加
midi_data_new.instruments.append(instrument)

# 新しいMIDIファイルとして保存
midi_data_new.write("音量変更後.mid")

print("処理が正常に終了しました。Enterを押してください。")
input()