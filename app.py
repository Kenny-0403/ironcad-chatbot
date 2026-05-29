from flask import Flask, request, abort
import requests
import os
import json

app = Flask(__name__)

# 從環境變數讀取設定（部署時在 Render 填入）
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
DIFY_API_KEY = os.environ.get("DIFY_API_KEY")
DIFY_API_URL = "https://api.dify.ai/v1/chat-messages"

def reply_to_line(reply_token, message):
    """回覆 LINE 訊息"""
    print(f"[LINE] 準備回覆，token前10碼: {reply_token[:10] if reply_token else 'None'}")
    print(f"[LINE] 訊息內容: {message[:50]}")

    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("[LINE] 錯誤：LINE_CHANNEL_ACCESS_TOKEN 未設定！")
        return

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }
    try:
        r = requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=payload, timeout=10)
        print(f"[LINE] 回覆狀態碼: {r.status_code}")
        if r.status_code != 200:
            print(f"[LINE] 回覆錯誤內容: {r.text}")
    except Exception as e:
        print(f"[LINE] 回覆發生例外: {e}")

def ask_dify(user_message, user_id):
    """向 Dify 發送問題並取得回答"""
    print(f"[DIFY] 發送問題: {user_message[:50]}")

    if not DIFY_API_KEY:
        print("[DIFY] 錯誤：DIFY_API_KEY 未設定！")
        return "系統設定錯誤，請聯繫工程師。"

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
        response = requests.post(DIFY_API_URL, headers=headers, json=payload, timeout=60)
        print(f"[DIFY] 狀態碼: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"[DIFY] 回應欄位: {list(data.keys())}")
            # 嘗試各種可能的回應欄位（Chatflow 用 outputs，一般 Chatbot 用 answer）
            answer = (
                data.get("answer") or
                data.get("outputs", {}).get("answer") or
                data.get("outputs", {}).get("text") or
                data.get("data", {}).get("outputs", {}).get("answer") or
                "抱歉，我無法處理您的問題，請稍後再試。"
            )
            print(f"[DIFY] 取得回答: {answer[:50]}")
            return answer
        else:
            print(f"[DIFY] 錯誤回應: {response.text[:200]}")
            return "系統暫時無法回應，請稍後再試或直接聯繫工程師。"
    except Exception as e:
        print(f"[DIFY] 發生例外: {e}")
        return "系統連線異常，請稍後再試。"

@app.route("/webhook", methods=["POST"])
def webhook():
    """接收 LINE webhook 事件"""
    body = request.get_json()
    print(f"[WEBHOOK] 收到請求，events數量: {len(body.get('events', [])) if body else 0}")

    if not body or "events" not in body:
        return "OK", 200

    for event in body["events"]:
        event_type = event.get("type")
        print(f"[WEBHOOK] 事件類型: {event_type}")

        # 只處理文字訊息
        if event_type != "message":
            continue
        if event.get("message", {}).get("type") != "text":
            continue

        reply_token = event.get("replyToken")
        user_message = event["message"]["text"]
        user_id = event.get("source", {}).get("userId", "unknown")

        print(f"[WEBHOOK] 用戶ID: {user_id}, 訊息: {user_message}")

        # 向 Dify 詢問
        answer = ask_dify(user_message, user_id)

        # 回覆 LINE
        reply_to_line(reply_token, answer)

    return "OK", 200

@app.route("/", methods=["GET"])
def health():
    return "IronCAD ChatBot is running!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
