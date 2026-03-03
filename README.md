# キーワード監視 LINE通知システム

## 概要
Krotho / PF4 に関する最新情報を毎日収集し、分類・要約してLINEに通知します。

## ファイル構成
```
keyword-monitor/
├── main.py              # メイン実行
├── search.py            # PubMed / arXiv / Google / Semantic Scholar 検索
├── classifier.py        # A/B1/B2 + 分野分類
├── summarizer.py        # DeepSeek 日本語要約
├── notifier.py          # LINE Notify 送信
├── config.py            # 設定
├── requirements.txt
└── .github/workflows/
    └── daily.yml        # GitHub Actions（毎日8:00 JST）
```

## セットアップ手順

### 1. GitHubリポジトリ作成
```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/あなたのID/keyword-monitor.git
git push -u origin main
```

### 2. GitHub Secrets に登録（Settings > Secrets > Actions）
| キー名 | 内容 |
|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek APIキー |
| `LINE_NOTIFY_TOKEN` | LINE Notifyトークン |
| `GOOGLE_API_KEY` | Google Custom Search APIキー（任意） |
| `GOOGLE_CSE_ID` | Google カスタム検索エンジンID（任意） |

### 3. LINE Notifyトークン取得
1. https://notify-bot.line.me/ja/ にアクセス
2. ログイン → マイページ → トークンを発行する
3. 通知先のトークルームを選択
4. 発行されたトークンをコピー

### 4. DeepSeek APIキー取得
1. https://platform.deepseek.com/ にアクセス
2. アカウント作成 → API Keys → Create
3. $5チャージで数ヶ月動く

## 手動実行テスト
```bash
pip install -r requirements.txt
export DEEPSEEK_API_KEY=your_key
export LINE_NOTIFY_TOKEN=your_token
python main.py
```

## 費用目安（月）
| サービス | 費用 |
|----------|------|
| PubMed API | 無料 |
| arXiv API | 無料 |
| Semantic Scholar API | 無料 |
| Google Custom Search | 無料（100件/日） |
| DeepSeek API | 約$1以下 |
| LINE Notify | 無料 |
| GitHub Actions | 無料 |
| **合計** | **約$1/月** |
