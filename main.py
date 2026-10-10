import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

# 載入 .env 環境變數
load_dotenv()

# LINE SDK v3 模組匯入
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ShowLoadingAnimationRequest,
    QuickReply,
    QuickReplyItem,
    MessageAction,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent,
)

from gemini_service import GeminiService

# 設定 Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("linebot-gemini")

# 讀取環境變數
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PORT = int(os.getenv("PORT", 8000))

# 初始化 LINE SDK 與 Gemini
line_config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
line_handler = WebhookHandler(LINE_CHANNEL_SECRET)
gemini_service = GeminiService(api_key=GEMINI_API_KEY)

app = FastAPI(title="LINE Bot with Gemini 3.8", version="2.0.0")

def get_default_quick_reply() -> QuickReply:
    """提供使用者便捷的底部快捷按鈕"""
    return QuickReply(items=[
        QuickReplyItem(action=MessageAction(label="重設對話", text="/reset")),
        QuickReplyItem(action=MessageAction(label="使用說明", text="/help")),
        QuickReplyItem(action=MessageAction(label="系統狀態", text="/status")),
        QuickReplyItem(action=MessageAction(label="自我介紹", text="請介紹你自己與能為我做的事")),
    ])

def show_loading_animation(chat_id: str):
    """觸發 LINE 官方『輸入中...』載入動畫，提升使用者等待體驗"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not chat_id or chat_id == "unknown":
        return
    try:
        with ApiClient(line_config) as api_client:
            line_bot_api = MessagingApi(api_client)
            req = ShowLoadingAnimationRequest(chat_id=chat_id, loading_seconds=10)
            line_bot_api.show_loading_animation(req)
            logger.info("已為聊天室 [%s] 觸發載入動畫", chat_id)
    except Exception as e:
        logger.debug("觸發載入動畫非關鍵異常（可能為群組或無權限）：%s", e)

@app.get("/")
def index():
    return {
        "status": "online",
        "version": "2.0.0 (Enhanced with System Prompt & Quick Reply)",
        "message": "LINE Bot Gemini Webhook Server 運行中",
        "has_line_secret": bool(LINE_CHANNEL_SECRET),
        "has_line_token": bool(LINE_CHANNEL_ACCESS_TOKEN),
        "has_gemini_key": bool(GEMINI_API_KEY),
        "active_model": gemini_service.model,
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/callback")
async def callback(request: Request):
    """
    LINE Webhook 進入點
    """
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    body_text = body.decode("utf-8")

    if not LINE_CHANNEL_SECRET:
        logger.error("尚未配置 LINE_CHANNEL_SECRET！")
        raise HTTPException(status_code=500, detail="LINE_CHANNEL_SECRET is not configured")

    try:
        line_handler.handle(body_text, signature)
    except InvalidSignatureError:
        logger.warning("無效的 LINE 簽章，請求被拒絕。")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error("處理 Webhook 時發生異常: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    return JSONResponse(content={"status": "OK"})

def reply_line_message(reply_token: str, text: str, attach_quick_reply: bool = True):
    """
    呼叫 LINE Messaging API 回傳訊息
    支援長訊息智慧分割 (每段最多 4800 字，LINE 上限 5 則)，並附帶 Quick Reply 選單
    """
    if not LINE_CHANNEL_ACCESS_TOKEN:
        logger.error("未設定 LINE_CHANNEL_ACCESS_TOKEN，無法發送回覆。")
        return

    # 分割長文字 (每段最多 4800 字)
    chunks = [text[i:i + 4800] for i in range(0, len(text), 4800)]
    if not chunks:
        chunks = ["（無內容）"]

    messages = []
    total = len(chunks[:5])
    for idx, chunk in enumerate(chunks[:5]):
        # 在最後一則訊息加上快捷回覆選單
        qr = get_default_quick_reply() if (attach_quick_reply and idx == total - 1) else None
        messages.append(TextMessage(text=chunk, quick_reply=qr))

    try:
        with ApiClient(line_config) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=messages
                )
            )
            logger.info("成功回覆訊息至 LINE (共 %d 則)", len(messages))
    except Exception as e:
        logger.error("回覆 LINE 訊息失敗: %s", e, exc_info=True)

# 註冊好友加入事件 (Follow Event)
@line_handler.add(FollowEvent)
def handle_follow_event(event: FollowEvent):
    user_id = event.source.user_id if event.source else "unknown"
    reply_token = event.reply_token
    logger.info("收到新用戶關注/加好友: [%s]", user_id)
    
    welcome_text = (
        "👋 您好！我是由最新 Google Gemini 模型驅動的 LINE 智慧個人助理！\n\n"
        "我可以協助您：\n"
        "✨ 日常智慧諮詢與生活問題解答\n"
        "📝 文本翻譯、文案撰寫與重點摘要\n"
        "💻 程式撰寫、除錯與邏輯分析\n"
        "🧠 支援上下文連續對話（記得剛才說過的話）\n\n"
        "您隨時可以點擊下方的快捷按鈕，或輸入 `/help` 查看使用說明。現在就試著向我提出一個問題吧！"
    )
    reply_line_message(reply_token=reply_token, text=welcome_text, attach_quick_reply=True)

# 註冊文字訊息處理事件
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    user_id = event.source.user_id if event.source else "unknown"
    user_text = event.message.text
    reply_token = event.reply_token

    logger.info("收到來自使用者 [%s] 的訊息: %s", user_id, user_text)

    # 1. 觸發 LINE 等待載入動畫
    show_loading_animation(user_id)

    # 2. 取得 Gemini 生成之回覆
    ai_reply = gemini_service.generate_reply(user_id=user_id, prompt=user_text)

    # 3. 回覆給使用者（附帶 Quick Reply 快捷按鈕）
    reply_line_message(reply_token=reply_token, text=ai_reply, attach_quick_reply=True)

if __name__ == "__main__":
    import uvicorn
    logger.info("正在啟動升級版 LINE Bot 伺服器，連接埠: %s...", PORT)
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
