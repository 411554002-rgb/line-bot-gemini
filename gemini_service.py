import os
import logging
from typing import Dict, List, Optional
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# 預設 System Instruction：設定繁體中文助理人設、風格與時間認知
DEFAULT_SYSTEM_INSTRUCTION = """你是運作於 LINE 上的智慧 AI 個人助理，由 Google Gemini 最新模型驅動。
你的任務是提供準確、結構清晰、親切友善的回答。

回答原則：
1. 請一律使用繁體中文（台灣習慣用語）回答。
2. 回答語氣保持親切、專業、有耐心。
3. 若使用者詢問時間，請注意當前基準年份為 2026 年，若遇到需要最新即時動態或時事，請明確告知並盡力依據已有知識提供分析與建議。
4. 排版請善用條列點與粗體，讓在手機 LINE 螢幕上閱讀更加舒適。
5. 若使用者提出問題過於簡略，可主動給予具體建議與追問引導。
"""

class GeminiService:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.fallback_model = "gemini-3.5-flash-lite"
        self.client: Optional[genai.Client] = None
        
        # 使用者對話歷史紀錄 (Key: user_id, Value: list of contents)
        self.user_sessions: Dict[str, List[dict]] = {}
        # 使用者自訂 System Instruction / 人設設定
        self.user_custom_instructions: Dict[str, str] = {}
        
        if self.api_key:
            self._init_client()
        else:
            logger.warning("GEMINI_API_KEY 未設定，Gemini 功能暫時無法使用。")

    def _init_client(self):
        try:
            self.client = genai.Client(api_key=self.api_key)
            logger.info("成功初始化 google-genai Client，主模型: %s，備援: %s", self.model, self.fallback_model)
        except Exception as e:
            logger.error("初始化 Gemini Client 失敗: %s", e)
            self.client = None

    def reset_chat(self, user_id: str) -> str:
        """重置指定使用者的對話紀錄"""
        had_history = user_id in self.user_sessions
        if had_history:
            del self.user_sessions[user_id]
        return "🧹 對話記憶已成功重置！您可以開啟新的話題了。"

    def set_system_prompt(self, user_id: str, instruction: str) -> str:
        """設定自訂人設"""
        self.user_custom_instructions[user_id] = instruction
        # 重設歷史以套用新人設
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        return f"🎭 已為您切換全新助理人設：\n「{instruction}」\n對話記憶已同步重設，歡迎開始交談！"

    def get_help_message(self) -> str:
        """取得快捷指令幫助清單"""
        return (
            "🤖 【LINE Gemini 智慧助理 指令清單】\n\n"
            "📌 基本操作：\n"
            "• 直接輸入任何文字或問題即可交談\n"
            "• 支援多輪上下文記憶，可延續上一句話題\n\n"
            "⚡ 快捷功能指令：\n"
            "• /help 或 「說明」：顯示此指令選單\n"
            "• /reset 或 「重設對話」：清空記憶、開啟新話題\n"
            "• /role <設定>：自訂專屬人設風格（例如：/role 你是熱血健身教練）\n"
            "• /status 或 「狀態」：查看當前連線狀態與模型版本\n\n"
            "💡 提示：每次點擊下方快捷按鈕也能一鍵操作喔！"
        )

    def get_status_message(self) -> str:
        """取得系統狀態"""
        return (
            "📊 【系統連線狀態報告】\n\n"
            f"• 核心架構：FastAPI + LINE Messaging API v3\n"
            f"• AI 核心引擎：Google GenAI SDK\n"
            f"• 主要模型：{self.model}\n"
            f"• 備援模型：{self.fallback_model}\n"
            "• 上下文記憶窗口：最多 12 輪滑動視窗\n"
            "• 狀態：🟢 連線正常，運行中"
        )

    def generate_reply(self, user_id: str, prompt: str) -> str:
        """
        向 Gemini 發送訊息並取得回覆
        """
        if not self.api_key:
            return "⚠️ 系統提示：目前尚未設定 GEMINI_API_KEY，請在 .env 檔案中配置金鑰。"

        if not self.client:
            self._init_client()
            if not self.client:
                return "⚠️ 系統提示：Gemini 客戶端初始化失敗，請檢查 API Key 或網路連線。"

        cleaned = prompt.strip()
        cleaned_lower = cleaned.lower()

        # 指令 1: 說明 / Help
        if cleaned_lower in ["/help", "help", "說明", "功能說明", "指令"]:
            return self.get_help_message()

        # 指令 2: 重設對話
        if cleaned_lower in ["/reset", "重設對話", "清除記憶", "清除對話", "重設"]:
            return self.reset_chat(user_id)

        # 指令 3: 查看狀態
        if cleaned_lower in ["/status", "status", "狀態", "系統狀態"]:
            return self.get_status_message()

        # 指令 4: 切換人設 /role
        if cleaned.startswith("/role ") or cleaned.startswith("/人設 "):
            parts = cleaned.split(" ", 1)
            if len(parts) > 1 and parts[1].strip():
                return self.set_system_prompt(user_id, parts[1].strip())
            else:
                return "💡 格式說明：請輸入 `/role 角色說明`，例如：`/role 你是一位專業的繁體中文英文家教`"

        try:
            # 取得該使用者目前的人設設定
            sys_instruct = self.user_custom_instructions.get(user_id, DEFAULT_SYSTEM_INSTRUCTION)
            config = types.GenerateContentConfig(
                system_instruction=sys_instruct,
                temperature=0.7,
            )

            # 取得歷史紀錄
            history = self.user_sessions.get(user_id, [])
            contents_payload = list(history)

            # 加入當前使用者的輸入
            current_message = {"role": "user", "parts": [{"text": cleaned}]}
            contents_payload.append(current_message)

            # 調用主模型
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=contents_payload,
                    config=config,
                )
            except Exception as primary_err:
                logger.warning("主模型 %s 調用失敗: %s，嘗試切換備援模型 %s", self.model, primary_err, self.fallback_model)
                response = self.client.models.generate_content(
                    model=self.fallback_model,
                    contents=contents_payload,
                    config=config,
                )

            reply_text = response.text or "（無文字回應）"

            # 記錄到使用者對話記憶中
            history.append(current_message)
            history.append({"role": "model", "parts": [{"text": reply_text}]})

            # 保留最近 12 條訊息避免 Token 超限
            if len(history) > 12:
                history = history[-12:]
            self.user_sessions[user_id] = history

            return reply_text.strip()

        except Exception as e:
            logger.error(f"Gemini 生成失敗: {e}", exc_info=True)
            return (
                "抱歉，目前與 Gemini 雲端連線遭遇暫時性問題。\n"
                f"錯誤代碼/細節：{str(e)[:150]}\n"
                "建議您可以稍後再試，或輸入 /reset 重設目前對話。"
            )
