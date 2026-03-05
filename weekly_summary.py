import json
import os
import re
import html
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText

from config import DEEPSEEK_API_KEY, GMAIL_ADDRESS, GMAIL_APP_PASSWORD, EMAIL_RECIPIENTS, KEYWORDS
from summarizer import _deepseek

_JST = timezone(timedelta(hours=9))
_KW_LABEL = " / ".join(KEYWORDS.values())


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


def select_top3(articles: list[dict]) -> list[dict]:
    """DeepSeek APIで今週のトップ3論文を選定"""
    if not DEEPSEEK_API_KEY:
        return articles[:3]

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
        "この中から特に重要・注目すべき上位3本を選び、以下のJSON形式のみで返してください。\n"
        "余分な説明やMarkdownコードブロックは不要です。\n\n"
        '[{"index": 0, "reason": "選定理由100文字以内"}, ...]\n\n'
        f"{articles_text}"
    )

    try:
        raw = _deepseek(prompt, max_tokens=600, temperature=0.3)
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        if match:
            selected = json.loads(match.group())
            result = []
            for item in selected[:3]:
                idx = item.get("index")
                if idx is not None and 0 <= idx < len(articles):
                    art = articles[idx].copy()
                    art["_reason"] = item.get("reason", "")
                    result.append(art)
            if result:
                return result
    except Exception as e:
        print(f"[WEEKLY] トップ3選定エラー: {e}")

    return articles[:3]


def generate_weekly_comment(top3: list[dict]) -> str:
    """今週の総括コメントをDeepSeekで生成（500文字以内）"""
    if not DEEPSEEK_API_KEY or not top3:
        return ""

    lines = []
    for i, art in enumerate(top3, 1):
        title = art.get("title_ja") or art.get("title", "")
        reason = art.get("_reason", "")
        lines.append(f"{i}. {title}（{reason}）")

    prompt = (
        "以下は今週の注目論文トップ3です。\n"
        "これらを踏まえて、今週の研究トレンドや注目すべき動向を200文字以内の日本語で総括してください。\n\n"
        + "\n".join(lines)
    )
    try:
        return _deepseek(prompt, max_tokens=700, temperature=0.4)
    except Exception as e:
        print(f"[WEEKLY] 総括コメント生成エラー: {e}")
        return ""


def build_weekly_message(top3: list[dict], comment: str) -> str:
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

    # トップ3
    h.append('<div style="margin-bottom:24px;">')
    h.append(
        '<div style="color:#374151;font-size:16px;font-weight:700;margin-bottom:14px;">'
        '&#127942; 今週のトップ3論文</div>'
    )

    for i, article in enumerate(top3):
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

    print("[1/4] 過去7日分のJSONを読み込み中...")
    articles = load_weekly_articles()
    print(f"  → {len(articles)}件")

    if not articles:
        print("[WEEKLY] 記事が見つかりませんでした。終了します。")
        return

    print("[2/4] DeepSeekでトップ3論文を選定中...")
    top3 = select_top3(articles)
    print(f"  → {len(top3)}件選定")

    print("[3/4] 総括コメント生成中...")
    comment = generate_weekly_comment(top3)

    print("[4/4] メール送信中...")
    message = build_weekly_message(top3, comment)
    send_weekly_email(message)

    print("=== 週次サマリー 完了 ===")


if __name__ == "__main__":
    main()
