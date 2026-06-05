# 使用範例

## 直接執行腳本

```bash
# 查詢 6 月 1 日到 5 日的使用量（預設逐日查詢並處理時區邊界）
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05

# 查看逐日彙整後的 JSON（欄位對不上時用）
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05 --raw

# 同時取回 key 與 user_id 的對應資料，並輸出使用者排行
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05 --raw --include-key-map

# 依 Tokens 排使用者排行
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05 --include-key-map --user-rank-by tokens

# 輸出 Top Public Model Names，依花費排序
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05 --include-model-ranking --model-rank-by spend

# 只看前 5 名排行
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05 --include-key-map --include-model-ranking --top 5

# 輸出 Top Public Model Names 花費圖
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05 --include-model-ranking --chart model-spend --chart-output reports/model-spend.png

# 輸出 user spend 圓餅圖
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05 --include-key-map --chart user-spend-pie --chart-output reports/user-spend-pie.png

# 不指定 chart-output，使用自動帶日期區間與時區的檔名
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05 --include-model-ranking --chart model-spend

# 指定自訂 Gateway 網址
python scripts/query_usage.py \
  --start-date 2026-06-01 \
  --end-date 2026-06-05 \
  --base-url http://litellm:4000
```

## 在 Agent 裡請求查詢

```text
幫我查 LiteLLM 6/1 到 6/5 的使用量
```

```text
用 litellm-usage-query skill 查這週 token 花費
```

```text
執行 query_usage.py，start_date=2026-06-01，end_date=2026-06-05，把結果整理給我
```

```text
查 LiteLLM 使用量，並把 api_key_breakdown 對應回 user_id 與 key_alias
```

```text
查 LiteLLM 使用量，幫我列出 user_id 排行
```

```text
查 LiteLLM 使用量，使用 tokens 排使用者排行
```

```text
查 LiteLLM 使用量，使用者排行請顯示 user_email
```

```text
查 LiteLLM 使用量，列出 Top Public Model Names 排行
```

```text
查 LiteLLM 使用量，只顯示前 5 名 user 與 model 排行
```

```text
查 LiteLLM 使用量，產出 model spend 的 PNG 圖檔
```

```text
查 LiteLLM 使用量，產出 user spend 圓餅圖
```
