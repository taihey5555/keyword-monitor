import os
from dotenv import load_dotenv

load_dotenv()

# キーワード設定
KEYWORDS = {
    "kw1": "Klotho",
    "kw2": "PF4",
    "kw3": "NK cell therapy",
    "kw4": "Exosomes",
    "kw5": "sEVs"
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


def validate_required_env(require_deepseek: bool = True, require_mail: bool = True) -> None:
    """必須環境変数が不足している場合は例外を投げる。"""
    missing: list[str] = []
    if require_deepseek and not DEEPSEEK_API_KEY:
        missing.append("DEEPSEEK_API_KEY")
    if require_mail and not GMAIL_ADDRESS:
        missing.append("GMAIL_ADDRESS")
    if require_mail and not GMAIL_APP_PASSWORD:
        missing.append("GMAIL_APP_PASSWORD")
    if missing:
        raise RuntimeError(f"必須環境変数が未設定です: {', '.join(missing)}")
