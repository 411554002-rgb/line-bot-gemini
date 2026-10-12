# LINE Bot 多核心智慧對話機器人 (Gemini + OpenRouter + 本地 Ollama)

本專案使用 **Python 3 (FastAPI)** 建置 LINE Messaging API Webhook 伺服器，並支援 **Gemini、OpenRouter 與本機 Ollama** 三種引擎。自動模式會在引擎呼叫失敗時嘗試已設定的備援；服務仍取決於網路、API 額度、金鑰與本機 Ollama 狀態。

---

## 🌟 核心特色功能 (v3.0 多引擎混合升級版)

- 🔀 **多核心混合架構 (Hybrid AI Engine)**：
  - 🔵 **Google Gemini 3.8 Flash**：日常問答與推理（依 `.env` 設定模型）。
  - 🌐 **OpenRouter / OpenCode 免費雲端開源模型**：支援多元開源大模型，無縫切換。
  - 💻 **本機離線 Ollama 開源模型**：100% 在本機電腦運算（推薦 Qwen 2.5 1.5B / Llama 3.2），完全免外網、高隱私、零成本。
- ⚙️ **自動智慧備援 (Auto Fallback)**：當主模型遇到超額 (429)、逾時或網路異常時，自動依序嘗試已設定的備援引擎。
- 🛟 **Webhook 防卡住處理**：先驗證 LINE 簽章並快速回應 Webhook，再於背景處理訊息；雲端與本機模型均設定請求逾時，避免單一引擎長時間卡住。
- 🎯 **繁體中文精準人設引導**：預設融入在地化習慣用語、時間認知與優質條列排版。
- 🎭 **動態自訂人設 (/role)**：使用者可在聊天中隨時更換專家角色（如英文家教、程式導師、健身教練）。
- ⏳ **原生載入中動畫 (Loading Animation)**：在 AI 思考期間於 LINE 介面展示動畫，消除等待焦慮。
- 🔘 **底部快捷回覆選單 (Quick Reply)**：支援一鍵點擊「重設對話」、「系統狀態」、「使用說明」或「切換模式」。

---

## ⚡ 快捷指令說明

| 指令 | 說明 | 範例 |
| :--- | :--- | :--- |
| `/model auto` | 切換為【自動三合一智慧備援模式】（預設推薦） | `/model auto` |
| `/model gemini` | 強制切換為 Google Gemini 模型 | `/model gemini` |
| `/model open` | 強制切換為 OpenRouter 免費雲端開源模型 | `/model open` |
| `/model local` | 強制切換為本機離線 Ollama 開源模型 | `/model local` |
| `/help` 或 `說明` | 顯示所有功能與指令清單 | `/help` |
| `/status` 或 `狀態` | 即時查詢各引擎連線狀況與運行報告 | `/status` |
| `/reset` 或 `重設對話` | 清空當前對話歷史，開啟新話題 | `/reset` |
| `/role <設定>` | 即時自訂助理人設與風格 | `/role 你是一位幽默的日語家教` |

---

## 💻 如何開啟本機開源模型 (Ollama)

若您想體驗完全不用外網、在自己電腦運算的開源模型：

1. **安裝 Ollama**：
   - 瀏覽器前往 [https://ollama.com/download](https://ollama.com/download) 下載並安裝 Windows 版本。
2. **下載開源模型**（推薦專門為輕量電腦與繁體中文優化的 Qwen 2.5）：
   ```powershell
   ollama run qwen2.5:1.5b
   ```
3. 下載完成後，Ollama 會自動在背景運行（連接埠 11434）。
4. 在 LINE 對話框輸入 `/model local` 或點擊 `/status`，即可看見本地模型已就緒！

---

## 🚀 快速開始指引

### 步驟 1：安裝套件依賴

```bash
pip install -r requirements.txt
```

---

### 步驟 2：配置環境變數 (`.env`)

複製 `.env.example` 為 `.env`，填入您的金鑰：

```env
LINE_CHANNEL_SECRET=你的_LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_CHANNEL_ACCESS_TOKEN

# 1. Google Gemini Key
GEMINI_API_KEY=你的_GEMINI_API_KEY
GEMINI_MODEL=gemini-3.8-flash
GEMINI_TIMEOUT_MS=12000

# 2. OpenRouter 免費 Key (選填，至 openrouter.ai/keys 免費領取)
OPENROUTER_API_KEY=
OPENROUTER_TIMEOUT_SECONDS=12

# 3. 本地 Ollama 設定 (預設即可)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b
OLLAMA_TIMEOUT_SECONDS=18
```

---

### 步驟 3：啟動本地伺服器

```bash
python main.py
```

或直接點擊桌面資料夾中的 **`啟動LINE_BOT.bat`** 即可一鍵同時啟動 Python 與 ngrok！
