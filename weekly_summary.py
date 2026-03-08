import json
import os
import re
import html
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText

from config import (
    DEEPSEEK_API_KEY,
    GMAIL_ADDRESS,
    GMAIL_APP_PASSWORD,
    EMAIL_RECIPIENTS,
    KEYWORDS,
    validate_required_env,
)
import summarizer
from summarizer import _deepseek

_JST = timezone(timedelta(hours=9))
_KW_LABEL = " / ".join(KEYWORDS.values())
WEEKLY_TOP_N = 5


def _parse_top_json(raw: str, total_articles: int, top_n: int = WEEKLY_TOP_N) -> list[dict]:
    """DeepSeek返答からトップ候補を安全に抽出する。"""
    candidates = None
    try:
        candidates = json.loads(raw)
    except Exception:
        match = re.search(r"\[[\s\S]*\]", raw)
        if not match:
            return []
        try:
            candidates = json.loads(match.group())
        except Exception:
            return []

    if not isinstance(candidates, list):
        return []

    valid: list[dict] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        idx = item.get("index")
        if isinstance(idx, int) and 0 <= idx < total_articles:
            valid.append(item)
        if len(valid) >= top_n:
            break
    return valid


def load_weekly_articles() -> list[dict]:
    """過去7日分のJSONから全記事を収集する"""
    today = datetime.now(_JST).date()
    all_articles = []

    for i in range(7):
        date = today - timedelta(days=i)
        filepath = f"docs/data/{date}.json"
        if not os.path.exists(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                report = json.load(f)
            for group_key, group in report.items():
                if not isinstance(group, dict):
                    continue
                for articles in group.values():
                    for article in articles:
                        article["_date"] = str(date)
                        all_articles.append(article)
        except Exception as e:
            print(f"[WEEKLY] {filepath} 読み込みエラー: {e}")

    return all_articles


def select_top5(articles: list[dict]) -> list[dict]:
    """DeepSeek APIで今週のトップ5論文を選定"""
    if not DEEPSEEK_API_KEY:
        return articles[:WEEKLY_TOP_N]

    _MAX = 500

    # 500件超の場合はキーワード×日付でバランスよくサンプリング
    if len(articles) > _MAX:
        from collections import defaultdict
        buckets: dict[tuple, list] = defaultdict(list)
        for a in articles:
            key = (a.get("keyword", ""), a.get("_date", ""))
            buckets[key].append(a)

        sampled: list[dict] = []
        bucket_list = list(buckets.values())
        # ラウンドロビンで各バケットから1件ずつ取り出して500件に達するまで繰り返す
        round_idx = 0
        while len(sampled) < _MAX:
            added_this_round = False
            for bucket in bucket_list:
                if round_idx < len(bucket):
                    sampled.append(bucket[round_idx])
                    added_this_round = True
                    if len(sampled) >= _MAX:
                        break
            if not added_this_round:
                break
            round_idx += 1
        articles = sampled
        print(f"[WEEKLY] サンプリング: {len(articles)}件（キーワード×日付バランス）")

    lines = []
    for i, article in enumerate(articles):
        title = article.get("title_ja") or article.get("title", "")
        summary = article.get("summary_ja") or article.get("abstract", "")
        date = article.get("_date", "")
        lines.append(f"[{i}] ({date}) {title}: {summary[:150]}")

    articles_text = "\n".join(lines)
    prompt = (
        f"以下は今週の{_KW_LABEL}に関する論文・記事一覧です（インデックス番号付き）。\n"
        f"この中から特に重要・注目すべき上位{WEEKLY_TOP_N}本を選び、以下のJSON形式のみで返してください。\n"
        "余分な説明やMarkdownコードブロックは不要です。\n\n"
        '[{"index": 0, "reason": "選定理由100文字以内"}, ...]\n\n'
        f"{articles_text}"
    )

    for attempt in range(2):
        try:
            raw = _deepseek(prompt, max_tokens=600, temperature=0.3)
            selected = _parse_top_json(raw, len(articles))
            if selected:
                result = []
                for item in selected:
                    idx = item.get("index")
                    art = articles[idx].copy()
                    art["_reason"] = item.get("reason", "")
                    result.append(art)
                if result:
                    return result
            print(f"[WEEKLY] トップ{WEEKLY_TOP_N}選定のJSON解釈に失敗（{attempt + 1}/2）")
        except Exception as e:
            print(f"[WEEKLY] トップ{WEEKLY_TOP_N}選定エラー（{attempt + 1}/2）: {e}")

    return articles[:WEEKLY_TOP_N]


def generate_weekly_comment(top5: list[dict]) -> str:
    """今週の総括コメントをDeepSeekで生成（500文字以内）"""
    if not DEEPSEEK_API_KEY or not top5:
        return ""

    lines = []
    for i, art in enumerate(top5, 1):
        title = art.get("title_ja") or art.get("title", "")
        reason = art.get("_reason", "")
        lines.append(f"{i}. {title}（{reason}）")

    prompt = (
        f"以下は今週の注目論文トップ{WEEKLY_TOP_N}です。\n"
        "これらを踏まえて、今週の研究トレンドや注目すべき動向を500文字以内の日本語で総括してください。\n\n"
        + "\n".join(lines)
    )
    try:
        return _deepseek(prompt, max_tokens=700, temperature=0.4)
    except Exception as e:
        print(f"[WEEKLY] 総括コメント生成エラー: {e}")
        return ""


def build_weekly_message(top5: list[dict], comment: str) -> str:
    """週次サマリーのHTML本文を組み立て"""
    today = datetime.now(_JST).strftime("%Y-%m-%d")
    week_start = (datetime.now(_JST) - timedelta(days=6)).strftime("%Y-%m-%d")

    MEDAL_COLORS = ["#f59e0b", "#9ca3af", "#b45309"]
    MEDAL_LABELS = ["🥇", "🥈", "🥉"]

    h = []
    h.append(
        '<html><body style="margin:0;padding:0;background:#f3f4f6;'
        'font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">'
    )
    h.append('<div style="max-width:700px;margin:0 auto;padding:20px;">')

    # DeepSeek キー未設定警告
    if not summarizer.DEEPSEEK_API_KEY:
        h.append(
            '<div style="background:#fffbeb;border:2px solid #f59e0b;border-radius:10px;'
            'padding:16px 20px;margin-bottom:20px;">'
            '<div style="color:#92400e;font-size:15px;font-weight:700;margin-bottom:6px;">'
            '&#9888; DeepSeek APIキーが未設定です</div>'
            '<div style="color:#78350f;font-size:13px;">'
            '週次コメントは生成せず、記事情報のみで配信しています。</div>'
            '</div>'
        )

    # DeepSeek 認証エラー警告
    if summarizer.auth_failed:
        h.append(
            '<div style="background:#fef2f2;border:2px solid #ef4444;border-radius:10px;'
            'padding:16px 20px;margin-bottom:20px;">'
            '<div style="color:#b91c1c;font-size:15px;font-weight:700;margin-bottom:6px;">'
            '&#9888; DeepSeek API の認証に失敗しました</div>'
            '<div style="color:#7f1d1d;font-size:13px;">'
            'APIキーが無効または権限不足の可能性があります。'
            '<a href="https://platform.deepseek.com/" style="color:#b91c1c;">DeepSeekコンソール</a>'
            'でAPIキーを確認してください。</div>'
            '</div>'
        )

    # DeepSeek 課金警告
    if summarizer.billing_required:
        h.append(
            '<div style="background:#fef2f2;border:2px solid #ef4444;border-radius:10px;'
            'padding:16px 20px;margin-bottom:20px;">'
            '<div style="color:#b91c1c;font-size:15px;font-weight:700;margin-bottom:6px;">'
            '&#9888; DeepSeek API の残高が不足しています</div>'
            '<div style="color:#7f1d1d;font-size:13px;">'
            'AI要約・翻訳・サマリーが生成できませんでした。'
            '<a href="https://platform.deepseek.com/" style="color:#b91c1c;">DeepSeekコンソール</a>'
            'でチャージしてください。</div>'
            '</div>'
        )

    # ヘッダー
    h.append(
        f'<div style="background:linear-gradient(135deg,#7c3aed,#4f46e5);border-radius:12px;'
        f'padding:28px 32px;margin-bottom:20px;">'
        f'<div style="color:#c4b5fd;font-size:12px;letter-spacing:1px;margin-bottom:6px;">WEEKLY SUMMARY</div>'
        f'<div style="color:#fff;font-size:20px;font-weight:700;margin-bottom:10px;">'
        f'&#128202; {html.escape(_KW_LABEL)}</div>'
        f'<span style="color:#ddd6fe;font-size:13px;">&#128197; {week_start} 〜 {today}</span>'
        f'</div>'
    )

    # トップ5
    h.append('<div style="margin-bottom:24px;">')
    h.append(
        '<div style="color:#374151;font-size:16px;font-weight:700;margin-bottom:14px;">'
        f'&#127942; 今週のトップ{WEEKLY_TOP_N}論文</div>'
    )

    for i, article in enumerate(top5):
        url = article.get("url", "")
        title = html.escape(article.get("title_ja") or article.get("title", "タイトル不明"))
        reason = html.escape(article.get("_reason", ""))
        summary = html.escape(
            article.get("summary_ja") or article.get("abstract", "")[:300]
        )
        color = MEDAL_COLORS[i] if i < len(MEDAL_COLORS) else "#6b7280"
        medal = MEDAL_LABELS[i] if i < len(MEDAL_LABELS) else f"{i + 1}."
        date = article.get("_date", "")

        h.append(
            f'<div style="background:#fff;border-radius:10px;padding:18px 20px;margin-bottom:14px;'
            f'border-left:5px solid {color};box-shadow:0 1px 4px rgba(0,0,0,0.10);">'
            f'<div style="font-size:15px;font-weight:700;color:#111;margin-bottom:8px;">'
            f'{medal} {title}</div>'
        )
        if date:
            h.append(
                f'<div style="color:#9ca3af;font-size:11px;margin-bottom:6px;">'
                f'&#128197; {html.escape(date)}</div>'
            )
        if url:
            h.append(
                f'<div style="margin-bottom:8px;">'
                f'<a href="{html.escape(url)}" style="color:#4f46e5;font-size:12px;word-break:break-all;">'
                f'{html.escape(url)}</a></div>'
            )
        if reason:
            h.append(
                f'<div style="background:#f5f3ff;border-radius:6px;padding:8px 12px;'
                f'color:#6d28d9;font-size:13px;font-weight:600;margin-bottom:8px;">'
                f'&#128161; 選定理由: {reason}</div>'
            )
        if summary:
            h.append(
                f'<div style="color:#555;font-size:13px;line-height:1.7;">{summary}</div>'
            )
        h.append('</div>')

    h.append('</div>')

    # 総括コメント
    if comment:
        h.append(
            '<div style="background:#f5f3ff;border:1px solid #ddd6fe;border-radius:12px;'
            'padding:20px 24px;margin-bottom:20px;">'
            '<div style="color:#5b21b6;font-size:15px;font-weight:700;margin-bottom:10px;">'
            '&#9997; 今週の総括</div>'
            f'<div style="color:#374151;font-size:14px;line-height:1.8;">'
            f'{html.escape(comment).replace(chr(10), "<br>")}</div>'
            '</div>'
        )

    # フッター
    h.append(
        '<div style="text-align:center;padding:12px;color:#9ca3af;font-size:12px;">'
        '<a href="https://taihey5555.github.io/keyword-monitor/" style="color:#6b7280;">'
        '&#128196; サイトで過去のレポートを確認</a></div>'
    )

    h.append('</div></body></html>')
    return "\n".join(h)


def send_weekly_email(message: str) -> bool:
    """週次サマリーをGmail SMTPで送信"""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("[WEEKLY] 送信元アドレスまたはアプリパスワード未設定。標準出力に表示します。")
        print(message)
        return True

    kw_names = list(KEYWORDS.values())
    kw_short = " / ".join(kw_names[:3]) + ("..." if len(kw_names) > 3 else "")
    today = datetime.now(_JST).strftime("%Y-%m-%d")
    subject = f"【週次サマリー】{kw_short} ({today})"

    msg = MIMEText(message, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ", ".join(EMAIL_RECIPIENTS)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"[WEEKLY] 送信完了 → {', '.join(EMAIL_RECIPIENTS)}")
        return True
    except Exception as e:
        print(f"[WEEKLY GMAIL ERROR] {e}")
        return False


def main():
    print("=== 週次サマリー 開始 ===")
    missing = validate_required_env(require_deepseek=True, require_mail=True)
    if missing:
        print(f"[CONFIG WARNING] 未設定: {', '.join(missing)}（処理は継続）")

    print("[1/4] 過去7日分のJSONを読み込み中...")
    articles = load_weekly_articles()
    print(f"  → {len(articles)}件")

    if not articles:
        print("[WEEKLY] 記事が見つかりませんでした。終了します。")
        return

    print(f"[2/4] DeepSeekでトップ{WEEKLY_TOP_N}論文を選定中...")
    top5 = select_top5(articles)
    print(f"  → {len(top5)}件選定")

    print("[3/4] 総括コメント生成中...")
    comment = generate_weekly_comment(top5)

    print("[4/4] メール送信中...")
    message = build_weekly_message(top5, comment)
    send_weekly_email(message)

    print("=== 週次サマリー 完了 ===")


if __name__ == "__main__":
    main()
