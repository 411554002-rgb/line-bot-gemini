# LINE Bot 串接 Google Gemini API

本專案使用 **Python 3 (FastAPI)** 建置 LINE Messaging API Webhook 伺服器，並整合 **Google Gemini API**，讓您的 LINE 官方帳號具備智慧問答與上下文對話能力。

---

## 快速開始指引

### 步驟 1：安裝套件依賴

建議建立虛擬環境或直接使用 pip 安裝：

```bash
# 建立虛擬環境 (選用)
python -m venv .venv
# 啟動虛擬環境 (Windows PowerShell)
.venv\Scripts\Activate.ps1

# 安裝所需套件
pip install -r requirements.txt
```

---

### 步驟 2：取得必要金鑰並填入 `.env`

開啟目錄下的 `.env` 檔案，填入以下資訊：

#### 1. LINE Developers 金鑰
1. 前往 [LINE Developers Console](https://developers.line.biz/console/)。
2. 建立 Provider 並新增 **Messaging API** Channel。
3. 在 **Basic settings** 分頁中，找到 **Channel secret**，複製並填入：
   ```env
   LINE_CHANNEL_SECRET=你的_LINE_CHANNEL_SECRET
   ```
4. 在 **Messaging API** 分頁中，滾動至最下方找到 **Channel access token**，點擊 **Issue** 產生 Token，複製並填入：
   ```env
   LINE_CHANNEL_ACCESS_TOKEN=你的_LINE_CHANNEL_ACCESS_TOKEN
   ```

#### 2. Google Gemini API 金鑰
1. 前往 [Google AI Studio](https://aistudio.google.com/app/apikey)。
2. 點擊 **Create API Key** 產生金鑰。
3. 複製並填入：
   ```env
   GEMINI_API_KEY=你的_GEMINI_API_KEY
   ```

---

### 步驟 3：啟動本地伺服器

執行下列指令啟動 FastAPI 服務：

```bash
python main.py
```

或使用 uvicorn 指令：
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

啟動後可在瀏覽器開啟 `http://localhost:8000` 檢查連線狀態。

---

### 步驟 4：設定 LINE Webhook (本地測試)

LINE 伺服器需要公開的 HTTPS 網址才能將使用者的訊息轉送給你的電腦。可使用 **ngrok** 或 **localtunnel** 建立暫時通道：

#### 使用 ngrok (推薦)：
1. 下載並安裝 [ngrok](https://ngrok.com/)。
2. 執行：
   ```bash
   ngrok http 8000
   ```
3. 複製產生的 `https://xxxx.ngrok-free.app` 網址。

#### 設定至 LINE Developers：
1. 回到 **LINE Developers Console** -> **Messaging API** 分頁。
2. 找到 **Webhook settings**：
   - **Webhook URL** 填入：`https://xxxx.ngrok-free.app/callback`
   - 點擊 **Update** 後，按 **Verify** 測試（需顯示 Success）。
   - 將 **Use webhook** 開關**開啟 (Enable)**。
3. 往下拉至 **LINE Official Account features**：
   - 將 **Auto-reply messages** (自動回覆訊息) 設定為 **Disabled**（停用），避免官方預設罐頭訊息干擾。

---

### 步驟 5：開始與 Gemini 機器人對話！

掃描 LINE Developers Console 上的 QR Code 加入好友，即可傳送訊息測試！

#### 特殊指令：
- 輸入 `/reset` 或 `重設對話`：清空個人對話上下文記憶，開啟新話題。
