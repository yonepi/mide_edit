"""
■スクリプト概要

・使用外部ライブラリ
pip install pyautogui
pip install moviepy
pip install pywin32 (ウィンドウの最大化に使用)

・スクリプトの流れ
①ディレクトリを引数で取得する。（または「ディレクトリを指定してください」といった感じでinputで受け取る。）
②受けとったディレクトリのエクスプローラーを開く。
③Waveファイルの秒数を取得して、変数に格納しておく。
④"○○自由形.mid"等のファイルを右クリック→Synthesiaで開く。
ー－－－－－－－－－－－－－－－－－－－－－－－－－－－
synthesia開いてやること。
=========
①画面が最大化になっているかを確認
②「手、色、楽器」メニューを選択して、左手→赤、右手→青にする。その後「戻る」を押す。
③「観て聞くだけ」を押してピアノ画面を開いて、右上の「La」を押す。
　┗日本語の場合は、「キーのラベル」→「固定ドレミのノーツ名」+「ノーツのラベル」→「固定ドレミのノーツ名」を選択。その後。戻る。
　┗英語の場合は、「キーのラベル」→「英語のノーツ名」+「ノーツのラベル」→「英語のノーツ名」を選択。その後。戻る。
　
④「win」+「g」を押して、左上の●ボタン（録画ボタン）を押して、録画が開始される（ただし、右上の秒数が表示されるまでラグあり）。
⑤その後、何もないところを押して、「観て聞くだけ」を押す。
⑥曲が終了するまで待って、録画終了ボタンを押す。
⑦録画ファイルが保存されるディレクトリの最新のmp4ファイルが録画されたファイルなので、名前を編集して、保存する。
=========
↑↑ここまでが一連の流れ。
ー－－－－－－－－－－－－－－－－－－－－－－－－－－－
⑤日本語分→録画ボタンを押してから、Waveファイルの秒数分プラス余白分待つ。（初級、中級、自由形）
⑥英語分→録画ボタンを押してから、Waveファイルの秒数分プラス余白分待つ。（初級、中級、自由形、演奏してみた）
録画ファイルの作成終了。
※以下、可能であれば。
⑦動画ファイルと、waveファイルを融合させる。
⑧最後に⑦で融合したファイルを全て結合させる。←いらないかな？？間の部分とかはpowerdirecterで編集必要だし。
"""

import sys
import glob
import os
import wave
import time

import pyautogui
import win32gui
import win32.lib.win32con as win32con


#初期設定の変数を定義
synthesia_window_title = 'Synthesia 10.7.5567'

#初期情報を格納した辞書リストを定義。
record_dic_list = [{"difficult":"初級", "language":"eng", "midi_image_name":"easy_midi.png"},
                    {"difficult":"中級", "language":"eng", "midi_image_name":"medium_midi.png"},
                    {"difficult":"自由形", "language":"eng", "midi_image_name":"freestyle_midi.png"},
                    {"difficult":"演奏してみた", "language":"eng", "midi_image_name":"ensou_midi.png"},
                    {"difficult":"初級", "language":"jpn", "midi_image_name":"easy_midi.png"},
                    {"difficult":"中級", "language":"jpn", "midi_image_name":"medium_midi.png"},
                    {"difficult":"自由形", "language":"jpn", "midi_image_name":"freestyle_midi.png"},
                    ]

#開発用。座標の位置取得を行いたいときには下記関数を実行。
def get_locate():
    x = input("取得したい箇所にカーソルを当てEnterキー押してください\n")
    print(pyautogui.position())


#クリック操作の一連の流れを関数化したもの。
def pyauto_image_click(image_file, print_message="", confidence=0.9):
    button_locate = pyautogui.locateCenterOnScreen(image_file, confidence=confidence)
    x, y = button_locate[0], button_locate[1] #type: ignore
    pyautogui.moveTo(x, y)
    time.sleep(2)
    pyautogui.click()
    print(print_message)
    time.sleep(2)


#作業対象のファイルを取得する関数。
def file_get():
    print("自動録画を開始します。下記の条件が満たされていることを確認してください。")
    print("1.作業対象ディレクトリが開かれていること。")
    print("2.初級、中級、自由形、演奏してみたのmidファイルが画面上に表示されており、非選択状態にあること。（灰色になっていない状態）")
    print("3.各MidiファイルのSynthesia上のBPM設定が、wavと一致していること")
    print("4.録画後の保存フォルダにファイルが存在していないこと。")
    print("\n")
    print("※動作に問題がある場合※")
    print(f"画面最大化が行われない場合、Synthesiaのウィンドウに表示されている名前と設定が一致しているか確認してください。現在の設定は{synthesia_window_title}です。")

    #作業対象のディレクトリ選択
    print("\n問題なければ、作業対象のディレクトリを選択してください。")
    dir_path = input()
    print(dir_path)

    #ディレクトリ内のファイルを全て取得。
    file_list = glob.glob(f'{dir_path}//*')
    print(file_list)

    #親ディレクトリの情報が必要ない場合はos.path.basename()で末尾のファイル名のみを抽出できるので、それを使用してfile名のみに修正。
    file_list = [os.path.basename(p) for p in file_list if os.path.isfile(p)]
    print(file_list)

    #ファイルのリストから、ファイルパス、BPMを取得し、録画対象の辞書リストに格納する。
    for dic in record_dic_list:
        print(f"対象：{dic}")
        for file_name in file_list:
            #対象難易度のmidファイルパスやwaveファイルパスを取得。
            if dic["difficult"] in file_name and ".mid" == file_name[-4:]:
                dic["mid_file_name"] = file_name
            if dic["difficult"] in file_name and ".wav" in file_name[-4:]:
                dic["wav_file_name"] = file_name

    return dir_path


#録画時間を設定するため、wavファイルの秒数を取得。
def wave_time_get(dir_path):
    #作業対象ディレクトリパスの末尾にバックスペースを加える。
    dir_path = dir_path + r"/"

    #対象のwaveファイルの特定し、再生時間を録画対象の辞書リストに格納する。
    for dic in record_dic_list:
        print(f"対象：{dic}")
        file_path = dir_path + dic["wav_file_name"]
        # 読み込みモードでWAVファイルを開く
        with wave.open(file_path, 'rb') as wav:
            # 再生時間を取得。（フレームレート÷サンプリングレートで取得できる。）
            fr = wav.getframerate()
            fn = wav.getnframes()
            music_time = 1.0 * fn / fr

        #辞書に再生時間を格納
        dic["music_time"] = music_time
    print("各Waveファイルの再生時間を取得しました。")
    print(record_dic_list)


#ディレクトリから、synthsiaを開く関数。
def open_synthesia(midi_difficult_image):
    #対象ファイルを検索して、右クリック→Synthesiaで開く。
    button_locate = pyautogui.locateCenterOnScreen(midi_difficult_image, confidence=0.9)
    x, y = button_locate[0], button_locate[1] #type: ignore
    pyautogui.moveTo(x, y)
    time.sleep(2)
    pyautogui.rightClick()
    print("Midiを右クリックしました。")
    time.sleep(5)
    #pyautogui.click('menu_program_button.png')
    pyauto_image_click('menu_program_button.png', "プログラムから開くをクリックしました。")
    time.sleep(5)
    #pyautogui.doubleClick('menu_synthesia_button.png')
    pyauto_image_click('menu_synthesia_button.png', "Synthsiaから開くをクリックしました。")
    time.sleep(2)
    pyautogui.click() #←プログラムから開くがたまにうまくいかないので、再度クリック操作を入れる。
    time.sleep(2)


#Synthsiaを開いた後に初期設定を行う関数。
def synthesia_setting(dic):
    #Synthesiaの画面を最大化。
    synthesia = win32gui.FindWindow(None, synthesia_window_title)
    win32gui.SetForegroundWindow(synthesia) #ウィンドウを最前面に移動してアクティブ化
    win32gui.ShowWindow(synthesia, win32con.SW_MAXIMIZE)
    print("画面を最大化しました。")
    time.sleep(2)

    #両手の色を変更。左手＝青→赤。右手＝緑→青
    pyauto_image_click('synthesia_color_change_button_mini.png', "手、楽器、色ボタンを押しました。")
    #Synthsiaの右手、左手の色を変える。(既に変更されている場合は、処理をスルーする。)
    if pyautogui.locateOnScreen('synthesia_left_hand_bule.png', confidence=0.8):
        pyauto_image_click('synthesia_color_change_blue_button.png', print_message="色変更ボタンをクリックしました。")
        pyauto_image_click('synthesia_to_red_button.png', print_message="左手を赤に変更しました。", confidence=0.96)
    if pyautogui.locateOnScreen('synthesia_right_hand_green.png', confidence=0.8):
        pyauto_image_click('synthesia_color_change_green_button.png', print_message="色変更ボタンをクリックしました。")
        pyauto_image_click('synthesia_to_blue_button.png', print_message="右手を青に変更しました。")
    pyauto_image_click('synthesia_back_menu_button.png', print_message="色変更メニューから戻りました。")

    #バーと鍵盤の設定を変更。
    if dic["language"] == "eng":
        pyauto_image_click('synthesia_music_start_button.png', print_message="演奏画面を開きました。")
        pyauto_image_click('synthesia_language_button.png', print_message="鍵盤、ノート設定画面を開きました。")
        pyauto_image_click('synthesia_eng_notes_button.png', print_message="キーのラベルを英語に変更しました。")
        pyauto_image_click('synthesia_notes_label_button.png', print_message="ノーツのラベルの設定画面を開きました。")
        pyauto_image_click('synthesia_eng_notes_button.png', print_message="ノーツのラベルを英語に変更しました。")
        pyauto_image_click('synthesia_back_menu_button.png', print_message="鍵盤、ノート設定画面から戻りました。")
        pyauto_image_click('synthesia_back_menu_button.png', print_message="演奏画面から戻りました。")
    elif dic["language"] == "jpn":
        pyauto_image_click('synthesia_music_start_button.png', print_message="演奏画面を開きました。")
        pyauto_image_click('synthesia_language_button.png', print_message="鍵盤、ノート設定画面を開きました。")
        pyauto_image_click('synthesia_jpn_notes_button.png', print_message="キーのラベルを英語に変更しました。")
        pyauto_image_click('synthesia_notes_label_button.png', print_message="ノーツのラベルの設定画面を開きました。")
        pyauto_image_click('synthesia_jpn_notes_button.png', print_message="ノーツのラベルを英語に変更しました。")
        pyauto_image_click('synthesia_back_menu_button.png', print_message="鍵盤、ノート設定画面から戻りました。")
        pyauto_image_click('synthesia_back_menu_button.png', print_message="演奏画面から戻りました。")

def game_bar_record_start(dic):
    time.sleep(2)
    #録画ボタンを確実に表示させるため、Synthsiaをアクティブウィンドウにする。
    synthesia = win32gui.FindWindow(None, synthesia_window_title)
    win32gui.SetForegroundWindow(synthesia)
    #windowsキーとgを押して、ゲームバー（キャプチャ用のソフト）を起動
    pyautogui.hotkey('win', 'g')
    time.sleep(2)
    #録画ボタンの座標位置でクリック→Point(x=236, y=105)
    pyautogui.click(x=236, y=105)
    time.sleep(4)
    #その後、何も表示されていない位置をクリックし、ゲームバー画面を抜ける。座標位置→Point(x=415, y=111)
    pyautogui.click(x=415, y=111)
    time.sleep(1)
    #Synthsiaの画面にマウスカーソルが入らないよう、カーソルを上に移動。
    pyautogui.moveTo(x=1, y=1)
    time.sleep(5)
    #★★★録画ストップボタンが表示されなかったときに、3回リトライする処理を追加。リトライの流れは、('win', 'g')で画面を戻った後、(alt + tab)で画面を切り替えて、再度実行する。★★★
    if not pyautogui.locateCenterOnScreen('record_stop_button.png', confidence=0.9):
        for i in range(3):
            print("録画ストップボタンが表示されていないため、リトライします。")
            #pyautogui.hotkey('alt', 'tab')
            pyautogui.hotkey('alt', 'f4')
            print("Synthsiaを閉じました。")
            time.sleep(2)
            open_synthesia(dic["midi_image_name"])
            time.sleep(2)
            print(f"リトライ{i}回目")

            #録画ボタンを確実に表示させるため、Synthsiaをアクティブウィンドウにする。
            synthesia = win32gui.FindWindow(None, synthesia_window_title)
            win32gui.SetForegroundWindow(synthesia)
            #windowsキーとgを押して、ゲームバー（キャプチャ用のソフト）を起動
            pyautogui.hotkey('win', 'g')
            time.sleep(2)
            #録画ボタンの座標位置でクリック→Point(x=236, y=105)
            pyautogui.click(x=236, y=105)
            time.sleep(4)
            #その後、何も表示されていない位置をクリックし、ゲームバー画面を抜ける。座標位置→Point(x=415, y=111)
            pyautogui.click(x=415, y=111)
            time.sleep(1)
            #Synthsiaの画面にマウスカーソルが入らないよう、カーソルを上に移動。
            pyautogui.moveTo(x=1, y=1)
            time.sleep(15)
            if pyautogui.locateCenterOnScreen('record_stop_button.png', confidence=0.9):
                break

    #ゲームバー画面を抜けた後、Synthesiaの「観て聴くだけ」ボタンを押す。
    pyauto_image_click('synthesia_music_start_button.png', print_message="演奏画面を開きました。")
    #曲数の時間 + 前後余白分待つ。
    time.sleep(20 + dic['music_time'])
    #録画終了ボタンをクリック。
    pyauto_image_click('record_stop_button.png', print_message="録画を終了します。")
    #アクティブウィンドウ（Synthsia）を閉じる。
    pyautogui.hotkey('alt', 'f4')
    print("synthsiaを閉じました。")
    time.sleep(2)


#録画のファイル名を変更する関数。
def filename_change(dic, new_dir_path):
    #引数の辞書からmid_file_nameを取得し、タイトルの部分を抽出。
    title = dic['mid_file_name']
    title = title.split()
    title = title[0]
    #タイトルに付属情報をくっつけて、ファイル名とする。
    new_file_name = f"{title} {dic['mid_file_name']} {dic['difficult']} Synthesia {dic['language']}"
    #動画保存場所の最新のmp4ファイルを検索。
    file_list = glob.glob(r'C:\Users\yoneo\Videos\Captures\*')
    recent_file_dict = {f:os.path.getctime(f) for f in file_list}
    print("最新のファイルは下記です。ファイル名を変更します。")
    recent = max(recent_file_dict, key=recent_file_dict.get) #type: ignore
    #ファイル名変更、フォルダ移動を行う。
    # 変更前ファイル
    path1 = recent
    # 変更後ファイル(最初に指定したディレクトリ+新しいファイル名)
    new_dir_path = new_dir_path + "\\"
    print(f"new_dir_path→{new_dir_path}")
    path2= new_dir_path + new_file_name + '.mp4'
    print(f"new_file_path→{path2}")
    os.rename(path1, path2)


def main():
    try:
        dir_path = file_get()
        wave_time_get(dir_path)
        for dic in record_dic_list:
            print(f"対象：{dic}")
            open_synthesia(dic["midi_image_name"])
            synthesia_setting(dic)
            game_bar_record_start(dic)
            filename_change(dic, dir_path)
        print("全ての処理が終了しました。")

    except Exception as e:
        print("例外エラーが発生しました。")
        print(e)
        input()
        print("ボタンを押すと、作業を終了します。")
        input()

#get_locate()
main()
