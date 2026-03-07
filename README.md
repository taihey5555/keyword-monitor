# Keyword Monitor

## 概要
`Klotho / PF4 / NK cell therapy / Exosomes / sEVs` の最新論文・記事を収集し、
DeepSeekで日本語要約して Gmail で配信する自動監視システムです。

- 日次: 記事収集、分類、翻訳・要約、デイリーサマリー、メール送信、`docs/data` 保存
- 週次: 過去7日から注目トップ3選定、週次総括コメント生成、メール送信

## 構成
```text
keyword-monitor/
├── main.py                  # 日次処理エントリポイント
├── weekly_summary.py        # 週次処理エントリポイント
├── search.py                # PubMed / arXiv / Semantic Scholar / Google CSE
├── classifier.py            # A/B分類 + 分野分類
├── summarizer.py            # DeepSeek 呼び出し（翻訳・要約）
├── notifier.py              # HTMLメール生成・Gmail送信
├── config.py                # 環境変数・キーワード設定
├── docs/data/               # 日次JSON保存先（GitHub Pages用）
└── .github/workflows/
   ├── daily.yml             # 毎日 20:48 UTC（翌 5:48 JST）
   └── weekly.yml            # 毎週日曜 21:00 UTC（月曜 6:00 JST）
```

## 必須環境変数
`.env` または GitHub Actions Secrets に設定します。

- `DEEPSEEK_API_KEY`
- `GMAIL_ADDRESS`
- `GMAIL_APP_PASSWORD`
- `EMAIL_RECIPIENTS`（カンマ区切り、未指定時は既定値）

任意:
- `GOOGLE_API_KEY`
- `GOOGLE_CSE_ID`

## ローカル実行
```bash
pip install -r requirements.txt
python main.py
python weekly_summary.py
```

## GitHub Actions
- Actions: `https://github.com/<OWNER>/<REPO>/actions`
- Secrets: `https://github.com/<OWNER>/<REPO>/settings/secrets/actions`

## 依存ライブラリ
- `requests`
- `python-dotenv`
