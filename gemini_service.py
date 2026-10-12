import os
import logging
from typing import Dict, List, Optional
import requests
from openai import OpenAI
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# 預設 System Instruction：繁體中文在地化引導
DEFAULT_SYSTEM_INSTRUCTION = """你是運作於 LINE 上的智慧 AI 個人助理。
你的任務是提供準確、結構清晰、親切友善的回答。

回答原則：
1. 請一律使用繁體中文（台灣習慣用語）回答。
2. 回答語氣保持親切、專業、有耐心。
3. 若使用者詢問時間，請注意當前基準年份為 2026 年。
4. 排版請善用條列點與粗體，讓在手機 LINE 螢幕上閱讀更加舒適。
5. 若使用者提出問題過於簡略，可主動給予具體建議與追問引導。
"""

class LLMService:
    def __init__(self):
        # 1. Google Gemini 設定
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.gemini_timeout_ms = int(os.getenv("GEMINI_TIMEOUT_MS", "12000"))
        self.gemini_client: Optional[genai.Client] = None
        if self.gemini_key:
            try:
                self.gemini_client = genai.Client(
                    api_key=self.gemini_key,
                    http_options=types.HttpOptions(
                        timeout=self.gemini_timeout_ms,
                        retry_options=types.HttpRetryOptions(attempts=1),
                    ),
                )
                logger.info("Gemini 客戶端初始化成功 (模型: %s)", self.gemini_model)
            except Exception as e:
                logger.error("Gemini 初始化失敗: %s", e)

        # 2. OpenRouter / OpenCode 雲端開源模型設定 (OpenAI 相容協議)
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "liquid/lfm-2.5-2.6b:free")
        self.openrouter_timeout_seconds = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "12"))
        self.openrouter_client: Optional[OpenAI] = None
        if self.openrouter_key:
            try:
                self.openrouter_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.openrouter_key,
                    timeout=self.openrouter_timeout_seconds,
                    max_retries=0,
                )
                logger.info("OpenRouter 客戶端初始化成功 (模型: %s)", self.openrouter_model)
            except Exception as e:
                logger.error("OpenRouter 初始化失敗: %s", e)

        # 3. 本地 Ollama 模型設定
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
        self.ollama_timeout_seconds = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "18"))
        self.ollama_client = OpenAI(
            base_url=f"{self.ollama_base_url}/v1",
            api_key="ollama", # 本地無需 key
            timeout=self.ollama_timeout_seconds,
            max_retries=0,
        )

        # 使用者設定快取
        # user_modes: 'auto', 'gemini', 'openrouter', 'local' (預設 auto)
        self.user_modes: Dict[str, str] = {}
        self.user_sessions: Dict[str, List[dict]] = {}
        self.user_custom_instructions: Dict[str, str] = {}

    def is_ollama_alive(self) -> bool:
        """檢查本地 Ollama 服務是否正在運行"""
        try:
            r = requests.get(f"{self.ollama_base_url}/api/tags", timeout=1.0)
            return r.status_code == 200
        except Exception:
            return False

    def reset_chat(self, user_id: str) -> str:
        """重置指定使用者的對話記憶"""
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        return "🧹 對話記憶已成功清空！您可以開啟新的話題了。"

    def set_mode(self, user_id: str, mode: str) -> str:
        """切換模型引擎模式"""
        m = mode.lower().strip()
        if m in ["auto", "自動"]:
            self.user_modes[user_id] = "auto"
            return "⚙️ 已切換為【自動三合一智慧備援模式】\n優先順序：Gemini ➔ OpenRouter 免費模型 ➔ 本地 Ollama 模型。"
        elif m in ["gemini", "谷歌"]:
            self.user_modes[user_id] = "gemini"
            return f"🔵 已切換為【Google Gemini 雲端模型】 (模型: {self.gemini_model})"
        elif m in ["openrouter", "open", "opencode", "雲端開源"]:
            self.user_modes[user_id] = "openrouter"
            return f"🌐 已切換為【OpenRouter / OpenCode 免費雲端模型】 (模型: {self.openrouter_model})"
        elif m in ["local", "ollama", "本地"]:
            self.user_modes[user_id] = "local"
            alive = self.is_ollama_alive()
            status_text = "🟢 本地 Ollama 連線正常" if alive else "⚠️ 提醒：目前尚未偵測到本地 Ollama 服務 (http://localhost:11434)"
            return f"💻 已切換為【本機開源模型 Ollama】 (模型: {self.ollama_model})\n{status_text}"
        else:
            return (
                "💡 格式說明：請輸入 `/model <選項>`\n"
                "• `/model auto` ：自動備援（推薦）\n"
                "• `/model gemini` ：Google Gemini\n"
                "• `/model open` ：OpenRouter 免費開源模型\n"
                "• `/model local` ：本機 Ollama 開源模型"
            )

    def set_system_prompt(self, user_id: str, instruction: str) -> str:
        """設定自訂人設"""
        self.user_custom_instructions[user_id] = instruction
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
        return f"🎭 已為您切換全新助理人設：\n「{instruction}」\n對話記憶已同步重設，歡迎開始交談！"

    def get_help_message(self) -> str:
        """取得快捷指令清單"""
        return (
            "🤖 【LINE 多核心 AI 助理 指令指南】\n\n"
            "⚡ 核心切換指令：\n"
            "• /model auto ：自動備援（推薦）\n"
            "• /model gemini ：使用 Google Gemini\n"
            "• /model open ：使用 OpenRouter 免費雲端模型\n"
            "• /model local ：使用本機離線 Ollama 模型\n\n"
            "📌 常用功能指令：\n"
            "• /help ：顯示此說明選單\n"
            "• /status ：查詢當前核心狀態與連線報告\n"
            "• /reset ：清空對話上下文記憶\n"
            "• /role <人設> ：例如「/role 你是一位幽默英文家教」\n\n"
            "💡 提示：點擊下方快捷按鈕也能一鍵操作！"
        )

    def get_status_message(self, user_id: str) -> str:
        """取得系統即時狀態報告"""
        current_mode = self.user_modes.get(user_id, "auto")
        ollama_ok = self.is_ollama_alive()
        gemini_ok = bool(self.gemini_client)
        openrouter_ok = bool(self.openrouter_client)

        return (
            "📊 【多核心 AI 連線狀態報告】\n\n"
            f"• 目前選擇模式：【{current_mode.upper()}】\n\n"
            "引擎連線狀況：\n"
            f"1. 🔵 Google Gemini: {'🟢 已設定 (' + self.gemini_model + ')' if gemini_ok else '⚪ 未配置'}\n"
            f"2. 🌐 OpenRouter (雲端免費): {'🟢 已設定 (' + self.openrouter_model + ')' if openrouter_ok else '⚪ 未配置 Key'}\n"
            f"3. 💻 本地 Ollama (離線開源): {'🟢 運行中 (' + self.ollama_model + ')' if ollama_ok else '🔴 離線 (未開啟服務)'}\n\n"
            "💡 AUTO 模式會在呼叫失敗或逾時時嘗試已設定的備援引擎。"
        )

    # 內部調用 1: Gemini
    def _call_gemini(self, user_id: str, prompt: str, system_instruct: str, history: list) -> str:
        if not self.gemini_client:
            raise RuntimeError("Gemini 客戶端未初始化或 Key 未設定")
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruct,
            temperature=0.7,
        )
        contents_payload = list(history)
        current_msg = {"role": "user", "parts": [{"text": prompt}]}
        contents_payload.append(current_msg)

        res = self.gemini_client.models.generate_content(
            model=self.gemini_model,
            contents=contents_payload,
            config=config,
        )
        text = (res.text or "").strip()
        if not text:
            raise RuntimeError("Gemini 回傳空白內容")
        return text

    # 內部調用 2: OpenRouter (雲端免費開源模型)
    def _call_openrouter(self, user_id: str, prompt: str, system_instruct: str, history: list) -> str:
        if not self.openrouter_client:
            raise RuntimeError("OpenRouter Key 未設定")
        
        messages = [{"role": "system", "content": system_instruct}]
        # 將歷史轉換為 OpenAI 格式
        for h in history:
            role = "user" if h.get("role") == "user" else "assistant"
            txt = ""
            for p in h.get("parts", []):
                txt += p.get("text", "")
            if txt:
                messages.append({"role": role, "content": txt})
        messages.append({"role": "user", "content": prompt})

        res = self.openrouter_client.chat.completions.create(
            model=self.openrouter_model,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )
        content = res.choices[0].message.content
        if not content or not content.strip():
            raise RuntimeError("OpenRouter 回傳空白內容")
        return content.strip()

    # 內部調用 3: Ollama (本機開源模型)
    def _call_ollama(self, user_id: str, prompt: str, system_instruct: str, history: list) -> str:
        if not self.is_ollama_alive():
            raise RuntimeError("本地 Ollama 服務未啟動 (請啟動 Ollama 應用程式)")

        messages = [{"role": "system", "content": system_instruct}]
        for h in history:
            role = "user" if h.get("role") == "user" else "assistant"
            txt = "".join([p.get("text", "") for p in h.get("parts", [])])
            if txt:
                messages.append({"role": role, "content": txt})
        messages.append({"role": "user", "content": prompt})

        res = self.ollama_client.chat.completions.create(
            model=self.ollama_model,
            messages=messages,
            temperature=0.7,
            max_tokens=1500,
        )
        content = res.choices[0].message.content
        if not content or not content.strip():
            raise RuntimeError("Ollama 回傳空白內容")
        return content.strip()

    def generate_reply(self, user_id: str, prompt: str) -> str:
        """核心對話處理入口"""
        cleaned = prompt.strip()
        cleaned_lower = cleaned.lower()

        # 指令分發
        if cleaned_lower in ["/help", "help", "說明", "功能說明", "指令"]:
            return self.get_help_message()

        if cleaned_lower in ["/reset", "重設對話", "清除記憶", "清除對話", "重設"]:
            return self.reset_chat(user_id)

        if cleaned_lower in ["/status", "status", "狀態", "系統狀態"]:
            return self.get_status_message(user_id)

        if cleaned.startswith("/model") or cleaned.startswith("/模型"):
            parts = cleaned.split(" ", 1)
            target = parts[1].strip() if len(parts) > 1 else ""
            return self.set_mode(user_id, target)

        if cleaned.startswith("/role ") or cleaned.startswith("/人設 "):
            parts = cleaned.split(" ", 1)
            if len(parts) > 1 and parts[1].strip():
                return self.set_system_prompt(user_id, parts[1].strip())
            else:
                return "💡 格式說明：請輸入 `/role 角色說明`，例如：`/role 你是一位專業的日語口說教練`"

        # 準備上下文與 Prompt
        sys_instruct = self.user_custom_instructions.get(user_id, DEFAULT_SYSTEM_INSTRUCTION)
        history = self.user_sessions.get(user_id, [])
        mode = self.user_modes.get(user_id, "auto")

        reply_text = ""
        engine_used = ""

        # 模式執行
        if mode == "gemini":
            try:
                reply_text = self._call_gemini(user_id, cleaned, sys_instruct, history)
                engine_used = "Gemini"
            except Exception as e:
                logger.warning("Gemini 呼叫失敗: %s", e)
                return "⚠️ Gemini 目前無法回應（可能是額度、模型設定或連線問題）。\n請稍後重試，或輸入 `/model auto` 使用備援。"

        elif mode == "openrouter":
            try:
                reply_text = self._call_openrouter(user_id, cleaned, sys_instruct, history)
                engine_used = f"OpenRouter ({self.openrouter_model})"
            except Exception as e:
                logger.warning("OpenRouter 呼叫失敗: %s", e)
                return "⚠️ OpenRouter 目前無法回應。\n請確認 API Key、模型設定與連線，或輸入 `/model auto` 使用備援。"

        elif mode == "local":
            try:
                reply_text = self._call_ollama(user_id, cleaned, sys_instruct, history)
                engine_used = f"Ollama 本地 ({self.ollama_model})"
            except Exception as e:
                logger.warning("Ollama 呼叫失敗: %s", e)
                return "⚠️ 本機 Ollama 目前無法回應。\n請確認 Ollama 正在執行且已下載指定模型。"

        else: # auto 自動三重容錯備援
            # 第一順位：Gemini
            try:
                reply_text = self._call_gemini(user_id, cleaned, sys_instruct, history)
                engine_used = "Gemini 3.8"
            except Exception as gemini_err:
                logger.warning("Auto 模式 - Gemini 失敗: %s，嘗試切換至備援引擎", gemini_err)
                
                # 第二順位：OpenRouter (若有設定 Key)
                if self.openrouter_client:
                    try:
                        reply_text = self._call_openrouter(user_id, cleaned, sys_instruct, history)
                        engine_used = f"OpenRouter ({self.openrouter_model})"
                    except Exception as open_err:
                        logger.warning("Auto 模式 - OpenRouter 失敗: %s", open_err)

                # 第三順位：本地 Ollama (若運行中)
                if not reply_text and self.is_ollama_alive():
                    try:
                        reply_text = self._call_ollama(user_id, cleaned, sys_instruct, history)
                        engine_used = f"本地 Ollama ({self.ollama_model})"
                    except Exception as local_err:
                        logger.warning("Auto 模式 - Ollama 失敗: %s", local_err)

                if not reply_text:
                    return (
                        "⚠️ 目前所有已設定的 AI 引擎都無法回應。\n"
                        "Gemini 可能遇到額度或連線限制；雲端備援或本機 Ollama 也可能尚未設定或啟動。\n\n"
                        "請稍後重試，或輸入 `/status` 查看設定狀態。"
                    )

        # 更新對話記憶
        current_user_part = {"role": "user", "parts": [{"text": cleaned}]}
        model_part = {"role": "model", "parts": [{"text": reply_text}]}
        history.append(current_user_part)
        history.append(model_part)
        if len(history) > 12:
            history = history[-12:]
        self.user_sessions[user_id] = history

        return reply_text
