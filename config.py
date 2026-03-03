import os
from dotenv import load_dotenv

load_dotenv()

# キーワード設定
KEYWORDS = {
    "kw1": "Klotho",
    "kw2": "PF4"
}

# 分野リスト
FIELDS = ["医学", "生物学", "農学", "工学", "産業", "ビジネス"]

# API Keys（.envから取得）
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")

# 要約文字数
SUMMARY_MAX_CHARS = 200
