# LINE Bot 混合雲端與本機小模型專案

本專案實作 LINE Bot 串接大型語言模型（LLM），支援 **Google Apps Script 雲端架構 (`Code.gs`)** 與 **本機電腦轉接站 (`line_bot_lite.py`)** 兩種執行模式。

---

## 專案內容結構

| 檔案 | 說明 |
|---|---|
| `Code.gs` | **Google Apps Script (GAS) 雲端 Webhook 程式**。全天候 24h 運作，免本地開機，呼叫 Google Gemini API 並具備對話記憶與 503 尖峰自動重試機制。 |
| `line_bot_lite.py` | **電腦端轉接站程式**。接上本機 Ollama 開源小模型與 Cloudflare 通道，支援 `--search` 即時連網查詢與來源附註。 |
| `README.md` | 本說明文件（安裝、運行與修改說明）。 |

---

## 怎麼裝

### 模式 A：Google Apps Script 雲端模式
1. 準備 Google 帳號與 LINE Developers 帳號。
2. 前往 [Google AI Studio](https://aistudio.google.com/) 申請免費的 Gemini API Key。
3. 前往 [LINE Developers Console](https://developers.line.biz/) 取得 Messaging API 的 **Channel access token (長效權杖)**。

### 模式 B：電腦本機轉接站模式
1. **Python 3.10+**
   ```powershell
   winget install --id Python.Python.3.13 -e --accept-package-agreements --accept-source-agreements
   ```
2. **Ollama**（本機模型執行環境）
   ```powershell
   winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
   ```
3. **下載模型**（以 `qwen2.5:1.5b` 為例）：
   ```powershell
   ollama pull qwen2.5:1.5b
   ```
4. **Cloudflare Tunnel (cloudflared)**（將本機通道外網對接至 LINE Webhook）：
   ```powershell
   winget install --id Cloudflare.cloudflared -e --accept-package-agreements --accept-source-agreements
   ```

---

## 怎麼跑

### 1. 運行 Google Apps Script 雲端模式 (`Code.gs`)
1. 開啟 [Google Apps Script (script.google.com)](https://script.google.com/) 並新增專案。
2. 將 `Code.gs` 內容複製貼上。
3. 點選左側 **專案設定 (⚙️)** ➔ **指令碼屬性**，新增以下兩個環境變數：
   - `LINE_CHANNEL_ACCESS_TOKEN`: LINE 長效權杖
   - `GEMINI_API_KEY`: Google Gemini API 金鑰
4. 點擊 **部署 ➔ 新增部署 ➔ 網路應用程式**：
   - 執行身分：`我`
   - 誰可以存取：`所有人`
5. 將部署完成的 Web App 網址貼回 LINE Developers 的 **Webhook URL** 並開啟 **Use Webhook**。

### 2. 運行電腦轉接站模式 (`line_bot_lite.py`)
- **終端機模擬模式**（不需 LINE，直接終端機交談）：
  ```powershell
  python line_bot_lite.py --simulate
  ```
- **真的接上 LINE（支援連網搜尋並附上來源網址）**：
  ```powershell
  python line_bot_lite.py --search
  ```
  啟動後依提示輸入 LINE Channel access token 與 Channel secret，程式會自動開啟 Cloudflare 通道並換置 Webhook，手機即可進行即時查詢。

---

## 你改了什麼

1. **實作 Google Apps Script 雲端架構 (`Code.gs`)**：
   - 串接最新 `gemini-3.8-flash` 模型，達成 24 小時免本機開機的全天候服務。
   - 加入 **HTTP 503 伺服器尖峰重試與備援機制**，提升高負載連線穩定性。
   - 將輸出限制放寬至 `maxOutputTokens: 4000` 並實作長訊息自動分段（每則 2500 字以內），解決回答中途被截斷問題。
   - 整合 `CacheService` 實現 10 分鐘內的上下文多輪對話記憶（支援 `/reset` 指令）。
2. **優化本機轉接站 (`line_bot_lite.py`)**：
   - 將預設模型調整為 `qwen2.5:1.5b`，中文回答流暢且佔用資源小，純 CPU 電腦也能快速推論。
   - 限制回覆字數並於啟動歡迎訊息標示當前模型，便於測試辨識。
   - 修正 Windows PowerShell 終端機之 UTF-8 編碼輸出問題。

---

## 資安與隱私遵守

- 依規定，所有密碼、金鑰（Token / Secret）及 Webhook 通道網址均僅保存在執行階段或 Google Apps Script「指令碼屬性」中。
- 原始碼與設定檔絕無寫入任何私密 Token、Secret 或 `/exec` 網址。
