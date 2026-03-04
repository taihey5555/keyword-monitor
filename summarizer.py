import requests
from config import DEEPSEEK_API_KEY, SUMMARY_MAX_CHARS


def translate_title(title: str) -> str:
    """DeepSeek APIで英語タイトルを日本語に翻訳"""
    if not DEEPSEEK_API_KEY or not title:
        return title

    prompt = (
        "以下の英語タイトルを自然な日本語に翻訳してください。"
        "翻訳文のみ出力してください。\n\n"
        f"{title}"
    )

    try:
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.1
            },
            timeout=30
        )
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[DeepSeek TRANSLATE ERROR] {e}")
        return title


def summarize(article: dict) -> str:
    """DeepSeek APIで日本語要約"""
    if not DEEPSEEK_API_KEY:
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
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 400,
                "temperature": 0.3
            },
            timeout=30
        )
        data = resp.json()
        summary = data["choices"][0]["message"]["content"].strip()
        return summary[:SUMMARY_MAX_CHARS]
    except Exception as e:
        print(f"[DeepSeek ERROR] {e}")
        abstract = article.get("abstract", "")
        return abstract[:SUMMARY_MAX_CHARS] if abstract else "要約取得失敗"


def summarize_all(report: dict) -> dict:
    """reportの全記事に日本語タイトル訳・要約を付与"""
    for group in report.values():
        for articles in group.values():
            for article in articles:
                article["title_ja"] = translate_title(article.get("title", ""))
                article["summary_ja"] = summarize(article)
    return report
