# LiteLLM 使用量查詢

可分享的 LiteLLM Gateway 使用量查詢工具包，包含 Python 腳本與 Agent Skill。

## 功能

- 查詢 `/user/daily/activity/aggregated` 端點
- 以 `x-litellm-api-key` header 認證
- 預設逐日查詢並合併 API 回傳的相鄰日期資料，避開時區邊界問題
- 輸出每日使用量摘要（請求數、Tokens、花費）
- 支援 `--raw` 查看逐日彙整後的 JSON
- 支援 `--include-key-map` 附帶抓取 `/key/list` 的 key/user 對應資料
- 支援依 `user_id` 聚合的使用者排行
- 支援 Top Public Model Names 排行
- 支援輸出 PNG 圖表

## 快速開始

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 設定環境變數
cp .env.example .env
# 編輯 .env，填入 LITELLM_API_KEY

# 3. 查詢使用量
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05
```

## 環境變數

| 變數 | 說明 | 必填 |
| --- | --- | --- |
| `LITELLM_API_KEY` | API Key，以 `x-litellm-api-key` header 送出 | 是 |
| `LITELLM_BASE_URL` | Gateway 基底網址 | 否（有預設值） |

## API 規格

```text
GET {BASE_URL}/user/daily/activity/aggregated
  ?start_date=YYYY-MM-DD
  &end_date=YYYY-MM-DD
  &timezone=-480

Header: x-litellm-api-key: <your-api-key>
```

## 查詢邏輯

- 腳本會把區間拆成每天各查一次
- 每次單日查詢若 API 回傳前一天或後一天的資料，會一併加總到該查詢日
- 因此輸出結果以「你的 `timezone` 下的最終每日數據」為準

## User / Key 對應

- 可加上 `--include-key-map` 取得 key 與 user 的對應資料
- 腳本會呼叫 `/key/list?return_full_object=true&expand=user`
- 可將 usage breakdown 裡的 `api_key_breakdown` 對應回 `user_id`、`user_email`、`team_id`、`key_alias`
- 適合後續做使用者排名、金額歸戶或 key owner 分析；若需顯示使用者名稱，可再用 `user_id` 對接其他資料來源
- 加上 `--include-key-map` 時，摘要也會附上依 `user_id` 聚合的排行榜
- 使用者排行與 user 圖表會優先顯示 `user_email`
- 可用 `--user-rank-by spend|tokens|requests` 控制排行排序方式
- 可用 `--include-model-ranking` 輸出 model 排行
- 可用 `--model-rank-by spend|tokens|requests` 控制 model 排序方式
- Model 排行直接使用 aggregated API 的 `breakdown.model_groups`
- 可用 `--top N` 控制 user/model 排行顯示筆數
- user 與 model 排行都會顯示 `successful_requests` / `failed_requests`
- 可用 `--chart` 與 `--chart-output` 產生圖檔
- user / model 圖表會以高到低排序，並使用橫向長條圖提升可讀性
- 所有圖表標題都會帶查詢區間與時區資訊
- 也支援 user / model 的圓餅圖，例如 `user-spend-pie`、`model-tokens-pie`
- 圓餅圖使用右側圖例顯示名稱、數值與百分比，避免切片文字過度擁擠
- 圓餅圖預設只保留前 5 名，其餘合併為 `Others`，且小於 3% 的切片不顯示百分比文字
- 若未指定 `--chart-output`，預設檔名會自動帶日期區間與時區

## 依賴版本

- `requirements.txt` 使用固定版本號，避免不同環境解析出不同結果

```bash
python scripts/query_usage.py \
  --start-date 2026-06-04 \
  --end-date 2026-06-04 \
  --raw \
  --include-key-map

python scripts/query_usage.py \
  --start-date 2026-06-04 \
  --end-date 2026-06-04 \
  --include-key-map \
  --user-rank-by tokens

python scripts/query_usage.py \
  --start-date 2026-06-04 \
  --end-date 2026-06-04 \
  --include-model-ranking \
  --model-rank-by spend

python scripts/query_usage.py \
  --start-date 2026-06-04 \
  --end-date 2026-06-04 \
  --include-key-map \
  --include-model-ranking \
  --top 5

python scripts/query_usage.py \
  --start-date 2026-06-04 \
  --end-date 2026-06-04 \
  --include-model-ranking \
  --model-rank-by spend \
  --chart model-spend \
  --chart-output reports/model-spend.png

python scripts/query_usage.py \
  --start-date 2026-06-04 \
  --end-date 2026-06-04 \
  --include-model-ranking \
  --chart model-spend-pie \
  --chart-output reports/model-spend-pie.png
```

## 目錄結構

```text
litellm-usage-query/
├── SKILL.md
├── .env.example
├── requirements.txt
├── scripts/
│   └── query_usage.py
└── references/
    ├── README.md
    └── example-prompts.md
```
