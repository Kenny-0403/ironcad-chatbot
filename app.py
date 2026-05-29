from flask import Flask, request, abort
import requests
import os

app = Flask(__name__)

LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"

def reply_to_line(reply_token, message):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }
    requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=payload)

def ask_dify(user_message, user_id):
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {},
        "query": user_message,
        "response_mode": "blocking",
        "user": user_id,
        "conversation_id": ""
    }
    try:
        response = requests.post(DIFY_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json().get("answer", "抱歉，我無法處理您的問題，請稍後再試。")
        else:
            return "系統暫時無法回應，請稍後再試或直接聯繫工程師。"
    except Exception:
        return "系統連線異常，請稍後再試。"

@app.route("/webhook", methods=["POST"])
def webhook():
    body = request.get_json()
    if not body or "events" not in body:
        return "OK", 200
    for event in body["events"]:
        if event.get("type") != "message":
            continue
        if event.get("message", {}).get("type") != "text":
            continue
        reply_token = event.get("replyToken")
        user_message = event["message"]["text"]
        user_id = event.get("source", {}).get("userId", "unknown")
        answer = ask_dify(user_message, user_id)
        reply_to_line(reply_token, answer)
    return "OK", 200

@app.route("/", methods=["GET"])
def health():
    return "IronCAD ChatBot is running!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
