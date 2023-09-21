
import sys
print(sys.executable)

print("プログラム開始")
import pretty_midi

#最初にMIDIファイルのキーを入力させる
#print("キーを1～11の数値で入力してください")
#keycompose_number = input("0→C,1→C#,2→D,3→E♭,4→E,5→F,6→F#,7→G,8→G#,9→A,10→A#,11→B:")
#ks  =  pretty_midi.KeySignature(int(keycompose_number),0)
#print(ks)

#新規発行用のmidiリストを作成
midi_data_new = pretty_midi.PrettyMIDI()
#新規のピアノ楽器を生成（(0)がmidiのAcoustic Grand Pianoに対応している。数値を変えたら楽器も変わる）
new_instrument = pretty_midi.Instrument(0)

#過去の曲を楽譜にする場合用のやつ。普通は使わない
old_musicsheet_data = pretty_midi.PrettyMIDI()
musicsheet_midi = [pretty_midi.Instrument(0),pretty_midi.Instrument(0)]

#既存のmidiデータを読み込み
midi_data = pretty_midi.PrettyMIDI('右手左手分けた後.mid')
midi_tracks = midi_data.instruments
# トラック１（右手）、トラック2（左手）のノートを取得
notes_right = midi_tracks[0].notes
notes_left = midi_tracks[1].notes

#配列の次のnoteを取得するための変数(最初から次のnoteを取得したいため初期値を1とする)
next_int = 1
next_note = 0
#和音だった場合に、ネクストノートを飛ばして、さらに次のノートを取得するための変数
moreover_next_int = 0

for note in notes_right:
    print(str(note)+"←今回処理しているnote")
    if next_int<len(notes_right):
        next_note = notes_right[next_int]
        print(str(next_note)+"next_note")
        #処理中のノートと次のノートのスタート場所が一緒（つまり和音）の場合
        if note.start == next_note.start:
            moreover_next_int = next_int+1
            if moreover_next_int >= len(notes_right):#最後の音が和音だった場合の処理
                print("最後の音は和音ですね。")
                new_instrument.notes.append(note)
                musicsheet_midi[0].notes.append(note)
                next_int +=1
                continue
            print("これは和音です")
            moreover_next_note = notes_right[moreover_next_int]
            print(str(moreover_next_note)+"←処理前のmoreover_next_note")
            #スタートタイムが異なる位置の音を取得するまで繰り返し処理
            while next_note.start == moreover_next_note.start:
                moreover_next_int += 1
                moreover_next_note = notes_right[moreover_next_int]
                if next_note.start != moreover_next_note.start:
                    break
            print(str(moreover_next_note)+"←処理後のmoreover_next_note")
            print(str(note.end)+"←note.end編集前")
            note.end = moreover_next_note.start
            print(str(note.end)+"←note.end編集後")
            #編集したnoteを楽器に格納
            new_instrument.notes.append(note)
            musicsheet_midi[0].notes.append(note)
            next_int +=1
            continue
        print(str(note.end)+"←note.end編集前")
        note.end = next_note.start
        print(str(note.end)+"←note.end編集後")
        #編集したnoteを楽器に格納
        new_instrument.notes.append(note)
        musicsheet_midi[0].notes.append(note)
        next_int +=1
    else:
        #最後の音の場合は、追加処理なしでnoteを新規楽器に格納
        print("最後の音だよ")
        new_instrument.notes.append(note)
        musicsheet_midi[0].notes.append(note)


#右手の処理が終わったので変数を初期値に戻す(最初から次のnoteを取得したいため初期値を1とする)
next_int = 1
next_note = 0
moreover_next_int = 0


for note in notes_left:
    print(str(note)+"←今回処理しているnote")
    if next_int<len(notes_left):
        next_note = notes_left[next_int]
        print(str(next_note)+"next_note")
        #処理中のノートと次のノートのスタート場所が一緒（つまり和音）の場合
        if note.start == next_note.start:
            moreover_next_int = next_int+1
            if moreover_next_int >= len(notes_left):#最後の音が和音だった場合の処理
                print("最後の音は和音ですね。")
                new_instrument.notes.append(note)
                musicsheet_midi[1].notes.append(note)
                next_int +=1
                continue
            moreover_next_note = notes_left[moreover_next_int]
            print(str(moreover_next_note)+"←処理前のmoreover_next_note")
            #スタートタイムが異なる位置の音を取得するまで繰り返し処理
            while next_note.start == moreover_next_note.start:
                moreover_next_int += 1
                moreover_next_note = notes_left[moreover_next_int]
                if next_note.start != moreover_next_note.start:
                    break
            print(str(moreover_next_note)+"←処理後のmoreover_next_note")
            print(str(note.end)+"←note.end編集前")
            note.end = moreover_next_note.start
            print(str(note.end)+"←note.end編集後")
            #編集したnoteを楽器に格納
            new_instrument.notes.append(note)
            musicsheet_midi[1].notes.append(note)
            next_int +=1
            continue
        print(str(note.end)+"←note.end編集前")
        note.end = next_note.start
        print(str(note.end)+"←note.end編集後")
        #編集したnoteを楽器に格納
        new_instrument.notes.append(note)
        musicsheet_midi[1].notes.append(note)
        next_int +=1
    else:
        #最後の音の場合は、追加処理なしでnoteを新規楽器に格納
        print("最後の音だよ")
        new_instrument.notes.append(note)
        musicsheet_midi[1].notes.append(note)

midi_data_new.instruments.append(new_instrument)
old_musicsheet_data.instruments.append(musicsheet_midi[0])
old_musicsheet_data.instruments.append(musicsheet_midi[1])



#midi_data_new.key_signature_changes.append(ks)
#old_musicsheet_data.key_signature_changes.append(ks)

midi_data_new.write("右手左手伸ばした後(音量変更前).mid")
old_musicsheet_data.write("右手左手合算しないver(volume_repair_2につっこむ用).mid")

print(old_musicsheet_data.instruments)