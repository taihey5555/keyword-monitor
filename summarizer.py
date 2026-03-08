import requests
from config import DEEPSEEK_API_KEY, SUMMARY_MAX_CHARS

_DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

# 課金が必要な状態を検出した場合 True になるフラグ
billing_required: bool = False
# 認証エラー（キー無効など）を検出した場合 True になるフラグ
auth_failed: bool = False


def _deepseek(prompt: str, max_tokens: int = 400, temperature: float = 0.3) -> str:
    """DeepSeek API 共通呼び出し（429時は自動リトライ）"""
    global billing_required, auth_failed
    for attempt in range(4):
        resp = requests.post(
            _DEEPSEEK_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature
            },
            timeout=30
        )
        if resp.status_code == 429:
            import time
            wait = 10 * (2 ** attempt)  # 10 → 20 → 40 → 80秒
            print(f"[DeepSeek] 429 Rate limit、{wait}秒待機してリトライ ({attempt+1}/4)...")
            time.sleep(wait)
            continue
        # 残高不足（HTTP 402 または レスポンスボディの error コード）
        if resp.status_code == 402:
            billing_required = True
            print("[DeepSeek] 残高不足（HTTP 402）")
            raise Exception("DeepSeek API: 残高不足（HTTP 402）")
        if resp.status_code in (401, 403):
            auth_failed = True
            print(f"[DeepSeek] 認証エラー（HTTP {resp.status_code}）")
            raise Exception(f"DeepSeek API: 認証エラー（HTTP {resp.status_code}）")
        if resp.status_code == 200:
            body = resp.json()
            err_code = (body.get("error") or {}).get("code", "")
            if err_code in ("insufficient_balance", "billing_required"):
                billing_required = True
                print(f"[DeepSeek] 残高不足（error.code={err_code}）")
                raise Exception(f"DeepSeek API: 残高不足（{err_code}）")
            return body["choices"][0]["message"]["content"].strip()
        if resp.status_code >= 500:
            print(f"[DeepSeek] サーバーエラー（HTTP {resp.status_code}）")
        resp.raise_for_status()
    resp.raise_for_status()  # 最終的に失敗なら例外を投げる


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
        return _deepseek(prompt, max_tokens=200, temperature=0.1)
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
        result = _deepseek(prompt, max_tokens=400, temperature=0.3)
        return result[:SUMMARY_MAX_CHARS]
    except Exception as e:
        print(f"[DeepSeek ERROR] {e}")
        abstract = article.get("abstract", "")
        return abstract[:SUMMARY_MAX_CHARS] if abstract else "要約取得失敗"


def generate_daily_summary(report: dict) -> str:
    """全記事をDeepSeekに渡して本日の注目5トピックを500文字で要約"""
    if not DEEPSEEK_API_KEY:
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
        "特に注目すべき5つのトピックを選び、それぞれの重要性・背景・今後の展望を含めて"
        "合計500文字以内の日本語でまとめてください。\n\n"
        f"{articles_text}"
    )
    try:
        return _deepseek(prompt, max_tokens=700, temperature=0.4)
    except Exception as e:
        print(f"[DeepSeek DAILY SUMMARY ERROR] {e}")
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
