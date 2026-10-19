/**
 * LINE Bot + Google Gemini API on Google Apps Script (GAS)
 * 
 * 設定說明：
 * 請在 Apps Script 專案設定 ->「指令碼屬性 (Script Properties)」中新增兩個變數：
 * 1. LINE_CHANNEL_ACCESS_TOKEN : LINE Messaging API 的 Channel Access Token (長效)
 * 2. GEMINI_API_KEY            : Google AI Studio 申請的 Gemini API Key
 */

// 讀取指令碼屬性（環境變數）
const SCRIPT_PROPERTIES = PropertiesService.getScriptProperties();
const LINE_CHANNEL_ACCESS_TOKEN = SCRIPT_PROPERTIES.getProperty("LINE_CHANNEL_ACCESS_TOKEN");
const GEMINI_API_KEY = SCRIPT_PROPERTIES.getProperty("GEMINI_API_KEY");

// 可用模型清單（若主力模型遇尖峰高負載 503，自動重試或切換備援）
const CANDIDATE_MODELS = ["gemini-3.8-flash", "gemini-1.5-flash"];

// 系統人格提示詞 (System Instruction)
const SYSTEM_INSTRUCTION = `你是運作於 LINE 上的智慧 AI 個人助理。
你的任務是提供準確、結構清晰、親切友善的回答。

回答原則：
1. 請一律使用繁體中文（台灣習慣用語）回答。
2. 回答語氣保持親切、專業、有耐心。
3. 排版請善用條列點與粗體，讓在手機 LINE 螢幕上閱讀更加舒適。
4. 若使用者提出問題過於簡略，可主動給予具體建議與追問引導。`;

/**
 * 處理 GET 請求（用於測試 Webhook 網址是否正常運作）
 */
function doGet(e) {
  return ContentService.createTextOutput("LINE Bot (GAS + Gemini) 服務運作中！");
}

/**
 * 處理 LINE Webhook 傳來的 POST 請求
 */
function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput(JSON.stringify({ status: "no data" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    const eventData = JSON.parse(e.postData.contents);
    const events = eventData.events;

    if (!events || events.length === 0) {
      return ContentService.createTextOutput(JSON.stringify({ status: "ok" }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    for (let i = 0; i < events.length; i++) {
      const event = events[i];

      // 只處理文字訊息事件
      if (event.type === "message" && event.message.type === "text") {
        const replyToken = event.replyToken;
        const userMessage = event.message.text.trim();
        const userId = event.source.userId;

        // 特殊指令處理
        if (userMessage === "/reset" || userMessage === "重設對話") {
          clearHistory(userId);
          replyLineMessage(replyToken, "✅ 對話歷史已清除，我們重新開始吧！");
          continue;
        }

        if (userMessage === "/help" || userMessage === "使用說明") {
          const helpText = "🤖 **LINE AI 助理使用說明**\n\n" +
            "• 直接傳送任何文字，我會透過 Google Gemini 為您解答。\n" +
            "• 輸入 `/reset` 可清除近期的對話記憶。\n" +
            "• 輸入 `/help` 可再次查看本說明。";
          replyLineMessage(replyToken, helpText);
          continue;
        }

        // 呼叫 Gemini 生成回應（含自動重試與備援機制）
        const aiReply = askGemini(userId, userMessage);

        // 回傳給 LINE
        replyLineMessage(replyToken, aiReply);
      }
    }

    return ContentService.createTextOutput(JSON.stringify({ status: "success" }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    console.error("處理 doPost 失敗: " + error.toString());
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * 呼叫 Google Gemini API（支援自動重試、備援模型與上下文記憶）
 */
function askGemini(userId, userMessage) {
  try {
    if (!GEMINI_API_KEY) {
      return "⚠️ 尚未設定 GEMINI_API_KEY，請在指令碼屬性中配置。";
    }

    // 取得歷史記憶（存於 CacheService，預設保存 10 分鐘）
    let history = getHistory(userId);
    history.push({
      role: "user",
      parts: [{ text: userMessage }]
    });

    const payload = {
      systemInstruction: {
        parts: [{ text: SYSTEM_INSTRUCTION }]
      },
      contents: history,
      generationConfig: {
        temperature: 0.7,
        maxOutputTokens: 4000
      }
    };

    const options = {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify(payload),
      muteHttpExceptions: true
    };

    let modelReply = null;
    let lastError = "";

    // 依序嘗試候選模型（若 3.8-flash 尖峰塞車，自動切換備援）
    for (let m = 0; m < CANDIDATE_MODELS.length; m++) {
      const modelName = CANDIDATE_MODELS[m];
      const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${modelName}:generateContent?key=${GEMINI_API_KEY}`;

      // 遇到 503 暫時尖峰時自動重試一次
      for (let attempt = 0; attempt < 2; attempt++) {
        if (attempt > 0) {
          Utilities.sleep(1500); // 稍微暫停 1.5 秒再重試
        }

        const response = UrlFetchApp.fetch(apiUrl, options);
        const responseCode = response.getResponseCode();
        const result = JSON.parse(response.getContentText());

        if (responseCode === 200) {
          modelReply = result.candidates?.[0]?.content?.parts?.[0]?.text;
          break;
        }

        lastError = result.error ? result.error.message : `HTTP ${responseCode}`;
        console.warn(`[${modelName}] 第 ${attempt + 1} 次呼叫失敗 (${responseCode}): ${lastError}`);

        // 如果不是 503/429 伺服器忙碌，換下一個模型，不再此模型重試
        if (responseCode !== 503 && responseCode !== 429) {
          break;
        }
      }

      if (modelReply) break;
    }

    if (!modelReply) {
      return `⚠️ 目前 Google AI 伺服器正在尖峰分流中，請稍候 3~5 秒後再試一次！\n(伺服器回應: ${lastError})`;
    }

    // 將模型的回應寫入歷史記錄
    history.push({
      role: "model",
      parts: [{ text: modelReply }]
    });
    saveHistory(userId, history);

    return modelReply;

  } catch (err) {
    console.error("呼叫 Gemini 發生異常: " + err.toString());
    return "系統發生錯誤，請稍後再試。(" + err.message + ")";
  }
}

/**
 * 回覆訊息給 LINE 使用者（長訊息自動切分成多個氣泡，避免被截斷）
 */
function replyLineMessage(replyToken, text) {
  if (!LINE_CHANNEL_ACCESS_TOKEN) {
    console.error("尚未設定 LINE_CHANNEL_ACCESS_TOKEN");
    return;
  }

  // LINE 限制單則訊息上限約 4,000 字，超過自動分段成最多 5 個對話框
  const messages = [];
  const chunkSize = 2500;
  for (let i = 0; i < text.length && messages.length < 5; i += chunkSize) {
    messages.push({
      type: "text",
      text: text.substring(i, i + chunkSize)
    });
  }

  const url = "https://api.line.me/v2/bot/message/reply";
  const payload = {
    replyToken: replyToken,
    messages: messages
  };

  const options = {
    method: "post",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + LINE_CHANNEL_ACCESS_TOKEN
    },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  if (response.getResponseCode() !== 200) {
    console.error("LINE 回覆失敗: " + response.getContentText());
  }
}

/**
 * 記憶體管理：使用 Google CacheService 保存用戶近 10 分鐘對話（上限保留最新 6 輪）
 */
function getHistory(userId) {
  try {
    const cache = CacheService.getUserCache();
    const raw = cache.get("history_" + userId);
    if (!raw) return [];
    return JSON.parse(raw);
  } catch (e) {
    return [];
  }
}

function saveHistory(userId, history) {
  try {
    // 保留最近 6 個對話輪次 (12 則訊息)
    const trimmed = history.slice(-12);
    const cache = CacheService.getUserCache();
    // 快取 600 秒 (10 分鐘)
    cache.put("history_" + userId, JSON.stringify(trimmed), 600);
  } catch (e) {
    console.warn("快取儲存失敗: " + e.toString());
  }
}

function clearHistory(userId) {
  try {
    const cache = CacheService.getUserCache();
    cache.remove("history_" + userId);
  } catch (e) {
    console.warn("快取清除失敗: " + e.toString());
  }
}
