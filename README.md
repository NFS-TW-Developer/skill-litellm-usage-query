# skill-litellm-usage-query

LiteLLM Gateway 使用量查詢 skill repo，提供：

- `SKILL.md`：可供 Agent 載入的 skill 定義
- `scripts/query_usage.py`：本地查詢腳本
- `references/`：操作說明與提示詞範例
- `examples/`：可安全分享的示例輸出
- `tests/`：基本單元測試

## 功能

- 查詢 `/user/daily/activity/aggregated`
- 預設逐日查詢並處理時區邊界
- 輸出每日摘要、使用者排行、Top Public Model Names 排行
- 支援 JSON 原始輸出
- 支援 PNG 圖表與圓餅圖
- 設定一律從專案根目錄 `.env` 讀取，不使用作業系統環境變數

## 快速開始

```bash
pip install -r requirements.txt
cp .env.example .env
# 編輯 .env，填入 LITELLM_API_KEY
# 如需自訂 Gateway，也在 .env 填入 LITELLM_BASE_URL

python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05
```

## 常用指令

```bash
# 每日摘要
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05

# 使用者排行
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05 --include-key-map

# Model 排行圖
python scripts/query_usage.py --start-date 2026-06-01 --end-date 2026-06-05 --include-model-ranking --chart model-spend
```

## 測試

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## 結構

```text
litellm-usage-query/
├─ SKILL.md
├─ README.md
├─ requirements.txt
├─ .env.example
├─ scripts/
│  └─ query_usage.py
├─ references/
│  ├─ README.md
│  └─ example-prompts.md
├─ examples/
│  ├─ daily-summary.md
│  └─ raw-response.json
├─ tests/
│  └─ test_query_usage.py
└─ CHANGELOG.md
```

更多細節見 `references/README.md`。
