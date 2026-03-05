import time
import requests
from config import GEMINI_API_KEY, SUMMARY_MAX_CHARS

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta"
    "/models/gemini-2.0-flash:generateContent"
)

# 15 RPM制限対策: 呼び出し間隔（秒）
_CALL_INTERVAL = 5


def _gemini(prompt: str, max_tokens: int = 400, temperature: float = 0.3) -> str:
    """Gemini API 共通呼び出し（429時は自動リトライ）"""
    for attempt in range(4):
        resp = requests.post(
            f"{_GEMINI_URL}?key={GEMINI_API_KEY}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": temperature
                }
            },
            timeout=30
        )
        if resp.status_code == 429:
            wait = _CALL_INTERVAL * (2 ** attempt)  # 5 → 10 → 20 → 40秒
            print(f"[Gemini] 429 Rate limit、{wait}秒待機してリトライ ({attempt+1}/4)...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        time.sleep(_CALL_INTERVAL)  # 成功後も次の呼び出しまで待機
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    resp.raise_for_status()  # 最終的に失敗なら例外を投げる


def translate_title(title: str) -> str:
    """Gemini APIで英語タイトルを日本語に翻訳"""
    if not GEMINI_API_KEY or not title:
        return title

    prompt = (
        "以下の英語タイトルを自然な日本語に翻訳してください。"
        "翻訳文のみ出力してください。\n\n"
        f"{title}"
    )
    try:
        return _gemini(prompt, max_tokens=200, temperature=0.1)
    except Exception as e:
        print(f"[Gemini TRANSLATE ERROR] {e}")
        return title


def summarize(article: dict) -> str:
    """Gemini APIで日本語要約"""
    if not GEMINI_API_KEY:
        abstract = article.get("abstract", "")
        return abstract[:SUMMARY_MAX_CHARS] if abstract else "要約なし"

    title = article.get("title", "")
    abstract = article.get("abstract", "")

    if not abstract and not title:
        return "要約なし"

    prompt = (
        f"以下の論文・記事を日本語で{SUMMARY_MAX_CHARS}文字以内に要約してください。"
        f"専門用語はそのまま使い、内容を簡潔にまとめてください。\n\n"
        f"タイトル: {title}\n"
        f"内容: {abstract}"
    )
    try:
        result = _gemini(prompt, max_tokens=400, temperature=0.3)
        return result[:SUMMARY_MAX_CHARS]
    except Exception as e:
        print(f"[Gemini ERROR] {e}")
        abstract = article.get("abstract", "")
        return abstract[:SUMMARY_MAX_CHARS] if abstract else "要約取得失敗"


def generate_daily_summary(report: dict) -> str:
    """全記事をGeminiに渡して本日の注目3トピックを500文字で要約"""
    if not GEMINI_API_KEY:
        return ""

    lines = []
    for group_key, group in report.items():
        if not isinstance(group, dict):
            continue
        for articles in group.values():
            for article in articles:
                title = article.get("title", "")
                summary = article.get("summary_ja", "") or article.get("abstract", "")
                if title:
                    lines.append(f"- {title}: {summary[:120]}")

    if not lines:
        return ""

    articles_text = "\n".join(lines[:50])
    prompt = (
        "以下はKlotho、PF4、NK cell therapy、Exosomes、sEVsに関する本日の論文・記事一覧です。\n"
        "特に注目すべき3つのトピックを選び、それぞれの重要性・背景・今後の展望を含めて"
        "合計500文字以内の日本語でまとめてください。\n\n"
        f"{articles_text}"
    )
    try:
        return _gemini(prompt, max_tokens=700, temperature=0.4)
    except Exception as e:
        print(f"[Gemini DAILY SUMMARY ERROR] {e}")
        return ""


def summarize_all(report: dict) -> dict:
    """reportの全記事に日本語タイトル訳・要約を付与"""
    for group in report.values():
        if not isinstance(group, dict):
            continue
        for articles in group.values():
            for article in articles:
                article["title_ja"] = translate_title(article.get("title", ""))
                article["summary_ja"] = summarize(article)
    return report
