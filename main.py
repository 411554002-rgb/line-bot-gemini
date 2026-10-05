import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
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
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
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

app = FastAPI(title="LINE Bot with Gemini", version="1.0.0")

@app.get("/")
def index():
    return {
        "status": "online",
        "message": "LINE Bot Gemini Webhook Server 運行中",
        "has_line_secret": bool(LINE_CHANNEL_SECRET),
        "has_line_token": bool(LINE_CHANNEL_ACCESS_TOKEN),
        "has_gemini_key": bool(GEMINI_API_KEY),
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
        logger.error(f"處理 Webhook 時發生異常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    return JSONResponse(content={"status": "OK"})

def reply_line_message(reply_token: str, text: str):
    """
    呼叫 LINE Messaging API 回傳訊息
    支援長訊息分割 (LINE 單則文字上限為 5000 字，回覆上限 5 則)
    """
    if not LINE_CHANNEL_ACCESS_TOKEN:
        logger.error("未設定 LINE_CHANNEL_ACCESS_TOKEN，無法發送回覆。")
        return

    # 分割長文字 (每段最多 4800 字)
    chunks = [text[i:i + 4800] for i in range(0, len(text), 4800)]
    # LINE 單次回覆最多 5 則訊息
    messages = [TextMessage(text=chunk) for chunk in chunks[:5]]

    try:
        with ApiClient(line_config) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=messages
                )
            )
            logger.info("成功回覆訊息至 LINE")
    except Exception as e:
        logger.error(f"回覆 LINE 訊息失敗: {e}", exc_info=True)

# 註冊文字訊息處理事件
@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event: MessageEvent):
    user_id = event.source.user_id if event.source else "unknown"
    user_text = event.message.text
    reply_token = event.reply_token

    logger.info(f"收到來自使用者 [{user_id}] 的訊息: {user_text}")

    # 取得 Gemini 生成之回覆
    ai_reply = gemini_service.generate_reply(user_id=user_id, prompt=user_text)

    # 回覆給使用者
    reply_line_message(reply_token=reply_token, text=ai_reply)

if __name__ == "__main__":
    import uvicorn
    logger.info(f"正在啟動伺服器，連接埠: {PORT}...")
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
