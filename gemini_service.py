import os
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.client = None
        
        # 使用者對話歷史紀錄 (Key: user_id, Value: list of contents)
        # 用於保留上下文記憶，可依需求清空或擴充
        self.user_sessions: Dict[str, List[dict]] = {}
        
        if self.api_key:
            self._init_client()
        else:
            logger.warning("GEMINI_API_KEY 未設定，Gemini 功能暫時無法使用。")

    def _init_client(self):
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            logger.info("成功初始化 google-genai Client，模型: %s", self.model)
        except Exception as e:
            logger.error("初始化 Gemini Client 失敗: %s", e)
            self.client = None

    def reset_chat(self, user_id: str):
        """重置指定使用者的對話紀錄"""
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            return True
        return False

    def generate_reply(self, user_id: str, prompt: str) -> str:
        """
        向 Gemini 發送訊息並取得回覆
        """
        if not self.api_key:
            return "系統提示：目前尚未設定 GEMINI_API_KEY，請在 .env 檔案中配置金鑰。"

        if not self.client:
            self._init_client()
            if not self.client:
                return "系統提示：Gemini 客戶端初始化失敗，請檢查 API Key 或套件安裝。"

        # 指令判斷：重設對話
        if prompt.strip().lower() in ["/reset", "重設對話", "清除記憶", "清除對話"]:
            self.reset_chat(user_id)
            return "對話歷史已重置！您可以開始新的話題。"

        try:
            # 取得或初始化該使用者的對話歷程 (維護最近 10 次對話)
            history = self.user_sessions.get(user_id, [])
            
            # 組合歷史與新問題
            # 使用 google-genai 的 models.generate_content
            contents_payload = []
            for item in history:
                contents_payload.append(item)
            
            # 加入當前使用者的輸入
            current_message = {"role": "user", "parts": [{"text": prompt}]}
            contents_payload.append(current_message)

            response = self.client.models.generate_content(
                model=self.model,
                contents=contents_payload,
            )

            reply_text = response.text or "（無文字回應）"

            # 記錄到使用者對話記憶中
            history.append(current_message)
            history.append({"role": "model", "parts": [{"text": reply_text}]})

            # 僅保留最近 12 條訊息避免 Token 超限
            if len(history) > 12:
                history = history[-12:]
            self.user_sessions[user_id] = history

            return reply_text.strip()

        except Exception as e:
            logger.error(f"Gemini 生成失敗: {e}", exc_info=True)
            # 若指定的模型報錯，嘗試 fallback 至 gemini-1.5-flash
            if self.model != "gemini-3.5-flash-lite":
                try:
                    logger.info("嘗試 Fallback 至 gemini-3.5-flash-lite")
                    response = self.client.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=prompt,
                    )
                    return (response.text or "（無文字回應）").strip()
                except Exception as fallback_err:
                    logger.error(f"Fallback 亦失敗: {fallback_err}")
            
            return f"抱歉，與 Gemini 連線時發生錯誤：{str(e)}"
