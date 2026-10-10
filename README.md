# LINE Bot 串接 Google Gemini 智慧對話機器人

本專案使用 **Python 3 (FastAPI)** 建置 LINE Messaging API Webhook 伺服器，並深度整合 **Google Gemini 最新大型語言模型**，具備繁體中文引導、多輪記憶、自訂角色人設（System Instruction Prompt）、載入動畫與底部快捷選單（Quick Reply）。

---

## 🌟 核心特色功能 (v2.0 改善升級版)

- ⚡ **雙模型高可用架構**：以 `gemini-3.8-flash` 為主力模型，搭配 `gemini-3.5-flash-lite` 自動降級容錯。
- 🎯 **繁體中文精準人設引導**：預設融入在地化習慣用語、時間邊界認知與優質排版原則。
- 🎭 **動態自訂人設 (/role)**：使用者可在聊天中隨時更換專家角色（如英文家教、程式導師、健身教練）。
- ⏳ **原生載入中動畫 (Loading Animation)**：在 AI 思考期間於 LINE 介面展示動畫，消除等待焦慮。
- 🔘 **底部快捷回覆選單 (Quick Reply)**：支援一鍵點擊「重設對話」、「使用說明」、「系統狀態」或「自我介紹」。
- 👋 **新好友加入自動迎賓 (Follow Event)**：自動發送功能總覽與指引說明。
- 🛡️ **超長訊息智慧分割**：突破 LINE 單則 5,000 字限制，自動安全分段發送。

---

## ⚡ 快捷指令說明

| 指令 | 說明 | 範例 |
| :--- | :--- | :--- |
| `/help` 或 `說明` | 顯示所有功能與指令清單 | `/help` |
| `/reset` 或 `重設對話` | 清空當前對話歷史，開啟新話題 | `/reset` |
| `/role <設定>` | 即時自訂助理人設與風格 | `/role 你是一位熱血的日語家教` |
| `/status` 或 `狀態` | 查詢伺服器連線狀態與當前使用模型 | `/status` |

---

## 🚀 快速開始指引

### 步驟 1：安裝套件依賴

```bash
# 建議使用虛擬環境
python -m venv .venv
.venv\Scripts\Activate.ps1

# 安裝所需套件
pip install -r requirements.txt
```

---

### 步驟 2：配置環境變數 (`.env`)

複製 `.env.example` 為 `.env`，並填入以下金鑰：

```env
# LINE Developers 設定
LINE_CHANNEL_SECRET=你的_LINE_CHANNEL_SECRET
LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_CHANNEL_ACCESS_TOKEN

# Google Gemini API 金鑰 (請至 https://aistudio.google.com/ 取得)
GEMINI_API_KEY=你的_GEMINI_API_KEY

# Gemini 模型設定 (預設 gemini-3.8-flash)
GEMINI_MODEL=gemini-3.8-flash

# 伺服器連接埠
PORT=8000
```

---

### 步驟 3：啟動本地伺服器

執行下列指令啟動 FastAPI Webhook 服務：

```bash
python main.py
```

伺服器就緒後會監聽在 `http://0.0.0.0:8000`，可開啟該網址檢查在線狀態。

---

### 步驟 4：設定 LINE Webhook (本地穿透測試)

1. **啟動 ngrok 轉發**：
   ```bash
   .\ngrok http 8000
   ```
2. **複製產生的 HTTPS 轉發網址**：例如 `https://xxxx.ngrok-free.dev`
3. **前往 LINE Developers Console**：
   - 進入你的 **Messaging API** 頻道
   - 將 **Webhook URL** 設定為：`https://xxxx.ngrok-free.dev/callback`
   - 點擊 **Update** 並點擊 **Verify** 確認回傳 Success
   - 將 **Use webhook** 設定為 **Enabled (開啟)**
   - 在 **LINE Official Account features** 中將 **Auto-reply messages (自動回覆訊息)** 設為 **Disabled (停用)**

---

### 步驟 5：開始交談！

用手機 LINE 掃描該頻道的 QR Code 加入好友，即可開始體驗具備記憶與人設的智慧對話！
