from inspect import signature
from flask import Flask , request , abort

from linebot import LineBotApi , WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

import os

app = Flask(__name__)

#通信するためのキーを取得。
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

#そのキーでインスタンスを作る
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/callback", methods=["POST"]) #(@は、この時,,,)/callbackサーバーにリクエストが来た(POST)ら関数
def callback():
    signature = request.headers["X-Line-Signature"] #/callbackに来たデータのタイトルをとって確認
    body = request.get_data(as_text=True) #/callbackに来たデータの中身をとってtext型で返す。

    try:
        handler.handle(body,signature) #試しに処理してみる
    except InvalidSignatureError:
        abort(400) #エラーが出たら、エラーコード400を返す
    return "OK"

@handler.add(MessageEvent, message=TextMessage) #LINEに送られてきて、テキストだったとき関数
def handle_message(event):
    user_message = event.message.text
    reply = f"あなたのメッセージは「{user_message}」ですね？"
    line_bot_api.reply_message(
        event.reply_token ,#eventに返すことを宣告
        TextSendMessage(text = reply)
        )
    
@app.route("/")
def index():
    return "Hello! This is the root page."

    
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)