# SPCC 感情カルテ - LLM 自動評価アプリ

DataRobot Codespace 上で `datarobot-agent-application` テンプレートを SPCC（コールセンター）評価アプリにカスタマイズしたもの。

## 構成

| サービス | ディレクトリ | ポート | 役割 |
|---|---|---|---|
| Agent | `agent/` | 8842 | LangGraph で 5 項目評価（preprocess → evaluate → format）、DataRobot LLM Gateway 経由 |
| FastAPI | `fastapi_server/` | 8080 | CSV アップロード / セッション管理 / 集計 / agent 呼び出し |
| Frontend | `frontend_web/` | 5173 | `/spcc` ルートで 3 タブ UI（ダッシュボード / オペレーター別 / 通話ドリルダウン） |

> 既存のチャット/設定 UI ルートは `frontend_web/src/routesConfig.tsx` でコメントアウトして無効化済み。ブラウザは `/` を `/spcc` にリダイレクトする。

## DataRobot LLM Gateway

`agent/agent/myagent.py` の `get_llm()`（`datarobot_genai.langgraph.llm` 由来）が、Codespace の `.env` に自動セットされる `DATAROBOT_ENDPOINT` / `DATAROBOT_API_TOKEN` を読んで Gateway へ接続する。手動設定は不要。

## 起動

```bash
# Codespace 内で 全サービス起動
dr task dev

# 個別起動（デバッグ時）
dr task agent:dev        # http://localhost:8842
dr task fastapi_server:dev   # http://localhost:8080
dr task frontend_web:dev # http://localhost:5173
```

ブラウザで `http://localhost:5173/` を開くと `/spcc` にリダイレクトされる。

## ダミー CSV で素早く動作確認

```bash
cd fastapi_server
uv run python scripts/generate_dummy_csv.py /tmp
# → /tmp/masked_dummy.csv (utf-8-sig)
# → /tmp/Recognition_dummy.csv (cp932)
```

それを UI のアップロード欄に投入すれば、3 件の通話と 1 件の「要注意」が表示される。`call-002` は不満スコア 5 以上のピーク発言を持つ。

## API エンドポイント（`fastapi_server` 側）

すべて `/api/v1/spcc/` 配下:

| メソッド | パス | 用途 |
|---|---|---|
| POST | `/upload` | 2 つの CSV をアップロードしてセッション作成 |
| GET | `/session/{session_id}/dashboard` | 全体統計 |
| GET | `/session/{session_id}/operators` | オペレーター一覧 |
| GET | `/session/{session_id}/operator/{name}` | オペレーター別レポート（代表通話 LLM 評価込み） |
| GET | `/session/{session_id}/calls` | 通話の絞り込み一覧 |
| GET | `/session/{session_id}/call/{call_id}` | 通話詳細 + LLM 評価 |
| POST | `/session/{session_id}/evaluate-batch` | 並列で複数通話評価（Semaphore=5） |

Swagger UI: `http://localhost:8080/docs`

## 頑丈さ（バックエンド）

- 必須カラム検証で 400、ファイル 200MB 超で 413
- 結合キーの一致率 50% 未満で 400 + 一致率を返す
- セッションは 24h TTL、30 分ごとに自動クリーンアップ
- LLM 評価は `llm_cache[call_id]` でキャッシュ、リトライ 1 回、JSON パース失敗時はエラーフィールドに格納し 200 で返す（UI でも「評価失敗」表示可能）
- 並列評価は `asyncio.Semaphore(5)` で Gateway 飽和を防ぐ
- LLM 呼び出しタイムアウト 150 秒
- 既存の `chats/users/auth` 機構には一切触らず、`app/api/v1/spcc/` 配下に独立配置

## テスト

```bash
cd fastapi_server
uv run pytest tests/unit/spcc/ -v        # CSV ローダー、エンドポイント（LLMモック）

cd agent
uv run pytest tests/test_agent.py -v     # SPCC graph_factory のユニットテスト
```

## ファイル位置

- 通話・発話データのスキーマ: [fastapi_server/app/api/v1/spcc/data_loader.py](fastapi_server/app/api/v1/spcc/data_loader.py)
- LLM プロンプト: [agent/agent/myagent.py](agent/agent/myagent.py)
- ダッシュボード UI: [frontend_web/src/components/spcc/UploadAndDashboard.tsx](frontend_web/src/components/spcc/UploadAndDashboard.tsx)
- ルート設定: [frontend_web/src/routesConfig.tsx](frontend_web/src/routesConfig.tsx)
- カラーパレット: [frontend_web/src/constants/spccColors.ts](frontend_web/src/constants/spccColors.ts)
