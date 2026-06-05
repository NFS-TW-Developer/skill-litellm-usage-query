---
name: litellm-usage-query
description: >-
  Query LiteLLM Gateway daily usage via the aggregated activity API.
  Use when the user asks about LiteLLM usage, token consumption, spend,
  daily activity, or wants to run the usage query script.
disable-model-invocation: true
---

# LiteLLM 使用量查詢

## 用途

透過 Python 腳本查詢 LiteLLM Gateway 的每日使用量（aggregated activity），並以逐日查詢方式處理時區邊界後整理成可讀摘要。

## 前置條件

1. 已安裝依賴：`pip install -r requirements.txt`
2. 已設定 API Key（header 名稱：`x-litellm-api-key`）
3. 複製 `.env.example` 為 `.env` 並填入 `LITELLM_API_KEY`

## 執行腳本

從 `litellm-usage-query` 目錄執行：

```bash
python scripts/query_usage.py \
  --start-date 2026-06-01 \
  --end-date 2026-06-05 \
  --timezone -480
```

常用參數：

| 參數 | 說明 |
| --- | --- |
| `--start-date` | 起始日期（YYYY-MM-DD） |
| `--end-date` | 結束日期（YYYY-MM-DD） |
| `--timezone` | 時區偏移（分鐘），預設 `-480`（UTC+8） |
| `--base-url` | Gateway 網址，預設讀取 `LITELLM_BASE_URL` |
| `--raw` | 輸出逐日彙整後的完整 JSON，不做摘要 |
| `--include-key-map` | 附帶抓取 `/key/list` 的 key/user 對應，並輸出 `user_id` 排行 |
| `--user-rank-by` | 使用者排行排序欄位，可選 `spend`、`tokens`、`requests` |
| `--include-model-ranking` | 輸出 Top Public Model Names 排行 |
| `--model-rank-by` | Model 排行排序欄位，可選 `spend`、`tokens`、`requests` |
| `--top` | 排行顯示筆數，預設 `10` |
| `--chart` | 圖表類型，可選 daily / user / model 的 spend、tokens、requests |
| `--chart-output` | PNG 圖檔輸出路徑 |

Model 排行使用 aggregated API 的 `breakdown.model_groups`，例如 `gpt-5.3-codex`。
user / model 圖表會以高到低排序，並使用橫向長條圖輸出。
所有圖表標題都會帶查詢區間與時區資訊。
也支援 `user-*-pie` 與 `model-*-pie` 的圓餅圖。
圓餅圖使用右側圖例顯示名稱、數值與百分比，避免切片文字過度擁擠。
圓餅圖預設只保留前 5 名，其餘合併為 `Others`，且小於 3% 的切片不顯示百分比文字。
若未指定 `--chart-output`，預設檔名會自動帶日期區間與時區。

## API 資訊

- **Endpoint**：`GET /user/daily/activity/aggregated`
- **認證**：Header `x-litellm-api-key: <API_KEY>`
- **查詢參數**：`start_date`、`end_date`、`timezone`

## Agent 工作流程

1. 確認使用者要的日期區間與時區
2. 確認 `.env` 或環境變數已有 `LITELLM_API_KEY`
3. 執行 `scripts/query_usage.py`
4. 腳本會預設逐日查詢，並把單日查詢時 API 回傳的相鄰日期資料合併為該日結果
5. 若需要把 `api_key_breakdown` 對應回 `user_id` / `user_email`，並做使用者排行，加入 `--include-key-map`
6. 若摘要欄位對不上，加上 `--raw` 查看逐日彙整後的 JSON 後再解讀
7. 以「摘要 + 重點觀察」回覆使用者

## 輸出格式

預設輸出 Markdown 表格摘要：

- 每日：請求數、Tokens、花費
- 合計：區間總計

若 API 回傳欄位名稱不同，先用 `--raw` 確認結構。

## 錯誤處理

| HTTP 狀態 | 處理方式 |
| --- | --- |
| 401 | 提醒檢查 API Key |
| 403 | 提醒權限不足 |
| 其他 | 顯示 HTTP 狀態與回應內容前 500 字 |

## 參考資料

- `references/README.md`
- `references/example-prompts.md`
