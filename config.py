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
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
EMAIL_RECIPIENTS: list[str] = [
    addr.strip()
    for addr in os.environ.get("EMAIL_RECIPIENTS", "maple0848241355@gmail.com").split(",")
    if addr.strip()
]
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID", "")

# 要約文字数
SUMMARY_MAX_CHARS = 400
