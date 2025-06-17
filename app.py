from inspect import signature
from tkinter import Image
from flask import Flask , request , abort

from linebot import LineBotApi , WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage

import os

from datetime import datetime , timezone , timedelta

import pandas as pd

import gspread
from gspread_dataframe import get_as_dataframe, set_with_dataframe
from oauth2client.service_account import ServiceAccountCredentials

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.service_account import ServiceAccountCredentials
from pytz import timezone


app = Flask(__name__)

#通信するためのキーを取得。
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

#そのキーでインスタンスを作る
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

def append_excel(user_name,message_text, timestamp_str):

    #許可できる動作を定義
    scope = [
  "https://www.googleapis.com/auth/spreadsheets",
  "https://www.googleapis.com/auth/drive"
  ]
    
    #認証情報を取得
    creds = ServiceAccountCredentials.from_json_keyfile_name("formal-analyzer-463112-c6-e394ee3ce1d7.json", scope)
    
    #認証→通信のためのものを格納。
    client = gspread.authorize(creds)

    #通信のためのものを使ってシート１(1枚目)を取得
    sheet = client.open("LINEbot-log").sheet1

    #現存データをdfに
    try:
        df = get_as_dataframe(sheet).dropna(how="all")
    except:
        df = pd.DataFrame(columns=["投稿者","投稿時間","メッセージ"])

    
    new = {"投稿者":user_name,"投稿時間":timestamp_str,"メッセージ":message_text}

    df = pd.concat([df,pd.DataFrame([new])], ignore_index=True) #つなげる((もとのdf,新しく作ったdf(newの1行),indexは振りなおす)

    sheet.clear()
    set_with_dataframe(sheet, df)

def upload_to_drive(file_path,file_name):

    #許可できる動作を定義
    scope = [
  "https://www.googleapis.com/auth/drive"
  ]
    
    #認証情報を取得
    creds = ServiceAccountCredentials.from_json_keyfile_name("formal-analyzer-463112-c6-e394ee3ce1d7.json", scope)
    
    #認証→通信のためのものを格納。
    service = build("drive","v3",credentials=creds)

    file_metadata = {
        "name":file_name,
        "parents":["1fUL7eyb4WpHIXZSLGLR49PYLwgpkASZg"]
    }

    media = MediaFileUpload(file_path,miethtype=("image/jpeg"))

    uploaded_file = service.files().create(
        body=file_metadata,
        media_dody=media,
        fileds="id"
    ).execute()

    service.permissions().create(
        fileId=uploaded_file["id"],
        body={"role":"reader","type":"anyone"}
    ).execute()

    file_url = f"https://drive.google.comuc?id={uploaded_file["id"]}"

    return file_url

#名前取得の関数
def getname(event):
    id = event.source.user_id
    profile = line_bot_api.get_profile(id)
    user_name = profile.display_name
    return user_name

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
    user_name = getname(event)
    user_message = event.message.text
    timestamp = event.timestamp / 1000 #ミリ秒を秒に
    dt = datetime.fromtimestamp(timestamp,tz=timezone.utc) #それを人間が見れる形に
    dt = dt.astimezone(timezone(timedelta(hours=9)))
    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")

    print(f"Received message: {user_message} at {dt_str}")

    append_excel(user_name,user_message,dt_str)

@handler.add(MessageEvent, message=ImageMessage)
def handle_message(event):
    user_name = getname(event)

    timestamp = event.timestamp / 1000 #ミリ秒を秒に
    dt = datetime.fromtimestamp(timestamp,tz=timezone.utc) #それを人間が見れる形に
    dt = dt.astimezone(timezone(timedelta(hours=9)))
    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")

    image_id = event.message.id
    message_contect = line_bot_api.get_message_content(image_id)

    file_name = f"{user_name}_{timestamp}.jpg"
    file_path = f"/tmp/{file_name}"

    with open(file_path, "wd") as f:
        for chunk in message_contect.iter_content():
            f.write(chunk)

    file_url = upload_to_drive(file_path, file_name)
    
    append_excel(user_name,file_url, timestamp)

@app.route("/")
def index():
    return "Hello! This is the root page."

    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)