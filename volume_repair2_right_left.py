import  pretty_midi

#新規発行用のmidiリストを作成
midi_data_new = pretty_midi.PrettyMIDI()
#ピアノの楽器を生成（(0)がmidiのAcoustic Grand Pianoに対応している。数値を変えたら楽器も変わる）
instrument = pretty_midi.Instrument(0)

#既存のmidiデータを読み込み
midi_data = pretty_midi.PrettyMIDI('右手左手合算しないver(volume_repair_2につっこむ用).mid')
midi_tracks = midi_data.instruments
# トラック１（右手）、トラック2（左手）のノートを取得
notes_right = midi_tracks[0].notes
notes_left = midi_tracks[1].notes

#-----------ここから右手の展開---------------------

#startが同一の値を格納するための空リストを作成
midi_list_right = []
for note in notes_right:
    midi_list_right.append(note.start)

#midi_listの中から、重複がある値の抽出（startの秒数）と、重複している数（和音の数）を抽出している
#https://www.souya.biz/blog2/pinevillage/2017/09/08/python%E3%81%A7%E3%83%AA%E3%82%B9%E3%83%88%E3%81%AE%E9%87%8D%E8%A4%87%E8%A6%81%E7%B4%A0%E3%82%A2%E3%83%AC%E3%82%B3%E3%83%AC/
chords = [[e, midi_list_right.count(e)] for e in set(midi_list_right) if midi_list_right.count(e) > 1]
#②set→重複要素を消している。  ①if→midi_list内の重複している数が1以上の値をリストに追加（この時点で重複のみ取得は済んでいる）
#内包表記の詳しい記載
#https://qiita.com/y__sama/items/a2c458de97c4aa5a98e7

#コード配列の中にpitchのデータを入れるため、start_timeとpitchのkeyを持つ辞書を作る。
note_dic = {}
pitch_list=[]
for note in notes_right:
    note_dic["start_time"] = note.start
    note_dic["pitch"] = note.pitch
    pitch_list.append(note_dic)
    note_dic = {}

#pitch_listに入ったpitchをchordに入れる。
for chord in chords:
    for pitch_num in pitch_list:
        if pitch_num["start_time"] == chord[0]:
            chord.append(pitch_num["pitch"])
#配列を[スタートタイムと和音数][和音のピッチ]に分けて、一つの配列に格納
chords_list=[]
for chord in chords:
    finale=[chord[:2],chord[2:]]
    chords_list.append(finale)

chord_num = 0
#全てのnoteに順番に処理をかける。
for note in notes_right:
    print(note)
    for chord_num in range(len(chords_list)):
        if chords_list[chord_num][0][0] == note.start:
            if chords_list[chord_num][0][1] == 2:
                print("和音の数は2つです")
                if not note.pitch == max(chords_list[chord_num][1]):
                    note.velocity -= 5
            elif chords_list[chord_num][0][1] == 3:
                print("和音の数は3つです")
                if not note.pitch == max(chords_list[chord_num][1]):
                    note.velocity -= 8
            elif chords_list[chord_num][0][1] == 4:
                print("和音の数は4つです")
                if not note.pitch == max(chords_list[chord_num][1]):
                    note.velocity -= 12
            elif chords_list[chord_num][0][1] == 5:
                print("和音の数は5つです")
                if not note.pitch == max(chords_list[chord_num][1]):
                    note.velocity -= 12
            elif chords_list[chord_num][0][1] == 6:
                print("和音の数は6つです")
                if not note.pitch == max(chords_list[chord_num][1]):
                    note.velocity -= 15
            elif chords_list[chord_num][0][1] >= 7:
                print("和音の数は7つ以上です")
                if not note.pitch == max(chords_list[chord_num][1]):
                    note.velocity -= 18
    #pitch36(36は多分C1)以下の音を一律でベロシティ-10する。
    if note.pitch <36:
        note.velocity -= 10
    #編集したnoteを楽器に格納
    instrument.notes.append(note)


#-----------ここまで右手の展開---------------------



#-----------ここから左手の展開---------------------
#startが同一の値を格納するための空リストを作成
midi_list_left = []
for note in notes_left:
    midi_list_left.append(note.start)

#midi_listの中から、重複がある値の抽出（startの秒数）と、重複している数（和音の数）を抽出している
#https://www.souya.biz/blog2/pinevillage/2017/09/08/python%E3%81%A7%E3%83%AA%E3%82%B9%E3%83%88%E3%81%AE%E9%87%8D%E8%A4%87%E8%A6%81%E7%B4%A0%E3%82%A2%E3%83%AC%E3%82%B3%E3%83%AC/
chords = [[e, midi_list_left.count(e)] for e in set(midi_list_left) if midi_list_left.count(e) > 1]
#②set→重複要素を消している。  ①if→midi_list内の重複している数が1以上の値をリストに追加（この時点で重複のみ取得は済んでいる）
#内包表記の詳しい記載
#https://qiita.com/y__sama/items/a2c458de97c4aa5a98e7

#コード配列の中にpitchのデータを入れるため、start_timeとpitchのkeyを持つ辞書を作る。
note_dic = {}
pitch_list=[]
for note in notes_left:
    note_dic["start_time"] = note.start
    note_dic["pitch"] = note.pitch
    pitch_list.append(note_dic)
    note_dic = {}

#pitch_listに入ったpitchをchordに入れる。
for chord in chords:
    for pitch_num in pitch_list:
        if pitch_num["start_time"] == chord[0]:
            chord.append(pitch_num["pitch"])
#配列を[スタートタイムと和音数][和音のピッチ]に分けて、一つの配列に格納
chords_list=[]
for chord in chords:
    finale=[chord[:2],chord[2:]]
    chords_list.append(finale)

chord_num = 0
#全てのnoteに順番に処理をかける。
for note in notes_left:
    #左手なので、一律でマイナス5
    note.velocity -= 5
    print(note)
    for chord_num in range(len(chords_list)):
        if chords_list[chord_num][0][0] == note.start:
            if chords_list[chord_num][0][1] == 2:
                print("和音の数は2つです")
                note.velocity -= 8
            elif chords_list[chord_num][0][1] == 3:
                print("和音の数は3つです")
                note.velocity -= 8
            elif chords_list[chord_num][0][1] == 4:
                print("和音の数は4つです")
                note.velocity -= 12
            elif chords_list[chord_num][0][1] == 5:
                print("和音の数は5つです")
                if not note.pitch == max(chords_list[chord_num][1]):
                    note.velocity -= 12
            elif chords_list[chord_num][0][1] == 6:
                print("和音の数は6つです")
                if not note.pitch == max(chords_list[chord_num][1]):
                    note.velocity -= 15
            elif chords_list[chord_num][0][1] >= 7:
                print("和音の数は7つ以上です")
                if not note.pitch == max(chords_list[chord_num][1]):
                    note.velocity -= 18
    #pitch36(36は多分C1)以下の音を一律でベロシティ-10する。
    if note.pitch <36:
        note.velocity -= 10
    #編集したnoteを楽器に格納
    instrument.notes.append(note)


#-----------ここまで左手の展開---------------------

midi_data_new.instruments.append(instrument)

print(str(type(midi_data_new))+"←midi_data_newのクラス")
print(str(type(midi_data))+"←midi_dataのクラス")
print(str(type(midi_tracks))+"←midi_tracksのクラス")

midi_data_new.write("音量変更後.mid")