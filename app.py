from inspect import signature
from flask import Flask , request , abort

from linebot import LineBotApi , WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import os

from datetime import datetime

import pandas as pd

from pathlib import Path

import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

#通信するためのキーを取得。
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

#そのキーでインスタンスを作る
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

def append_excel(message_text, timestamp_str):

    #許可できる動作を定義
    scope = [
  "https://www.googleapis.com/auth/spreadsheets",
  "https://www.googleapis.com/auth/drive"
  ]
    
    #認証情報を取得
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    
    #認証→通信のためのものを格納。
    client = gspread.authorize(creds)

    #通信のためのものを使ってシート１(1枚目)を取得
    sheet = client.open("LINEbot-log").sheet1

    #現存データをdfに
    try:
        df = get_as_dataframe(sheet).dropna(how="all")
    except:
        df = pd.DataFrame(columns=["投稿時間","メッセージ"])

    
    new = {"投稿時間":timestamp_str,"メッセージ":message_text}

    df = df.concat([df,pd.DataFrame([new])], ignore_index=True) #つなげる((もとのdf,新しく作ったdf(newの1行),indexは振りなおす)

    sheet.clear()
    set_with_dataframe(sheet, df)

@app.route("/callback", methods=["POST"]) #(@は、この時,,,)/callbackサーバーにリクエストが来た(POST)ら関数を作動。
def callback():
    signature = request.headers["X-Line-Signature"] #/callbackに来たデータのタイトルをとって確認
    body = request.get_data(as_text=True) #/callbackに来たデータの中身をとってtext型で返す。

    try:
        handler.handle(body,signature) #試しに処理してみる
    except InvalidSignatureError:
        abort(400) #エラーが出たら、エラーコード400を返す
    return "OK"

@handler.add(MessageEvent, message=TextMessage) #LINEに送られてきて、テキストだったとき関数を作動
def handle_message(event):
    user_message = event.message.text
    timestamp = event.timestamp / 1000 #ミリ秒を秒に
    dt = datetime.fromtimestamp(timestamp) #それを人間が見れる形に

    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")

    append_excel(user_message,dt_str)  
    
@app.route("/")
def index():
    return "Hello! This is the root page."

    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)