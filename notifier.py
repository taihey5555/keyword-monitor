import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, EMAIL_RECIPIENTS, FIELDS, KEYWORDS


# グループラベル（KEYWORDS から自動生成）
_kw_names = list(KEYWORDS.values())
_kw_label = " / ".join(_kw_names)

GROUP_LABELS: dict[str, str] = {"A": "[A] 複数キーワードヒット"}
for _i, _name in enumerate(_kw_names, 1):
    GROUP_LABELS[f"B{_i}"] = f"[B{_i}] {_name}のみ"

GROUP_ORDER = ["A"] + [f"B{i+1}" for i in range(len(KEYWORDS))]


def build_message(report: dict) -> str:
    """メール本文組み立て"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"【{_kw_label} 日次レポート】{today}"]

    total_count = 0

    for group_key in GROUP_ORDER:
        group = report.get(group_key, {})
        group_articles = [a for arts in group.values() for a in arts]
        total_count += len(group_articles)

        lines.append(f"\n{'='*25}")
        lines.append(GROUP_LABELS[group_key])
        lines.append(f"{'='*25}")

        for field in FIELDS:
            articles = group.get(field, [])
            lines.append(f"\n【{field}】")
            if not articles:
                lines.append("該当なし")
                continue
            for i, article in enumerate(articles, 1):
                title_ja = article.get("title_ja") or article.get("title", "タイトル不明")
                url = article.get("url", "URL不明")
                summary = article.get("summary_ja", "要約なし")
                lines.append(f"\n{i}. {title_ja}")
                lines.append(url)
                lines.append(f"{summary}")

    if total_count == 0:
        lines.append("\n本日は全キーワードでヒットなしでした。")

    lines.append(f"\n合計: {total_count}件")

    ai_summary = report.get("summary", "")
    if ai_summary:
        lines.append(f"\n{'='*25}")
        lines.append("■ 本日のAIサマリー")
        lines.append(f"{'='*25}")
        lines.append(ai_summary)

    return "\n".join(lines)


def send_email(message: str) -> bool:
    """Gmail SMTPでメール送信"""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("[GMAIL] 送信元アドレスまたはアプリパスワード未設定。標準出力に表示します。")
        print(message)
        return True

    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"【{_kw_label} 日次レポート】{today}"

    msg = MIMEText(message, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = ", ".join(EMAIL_RECIPIENTS)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        print(f"[GMAIL] 送信完了 → {', '.join(EMAIL_RECIPIENTS)}")
        return True
    except Exception as e:
        print(f"[GMAIL ERROR] {e}")
        return False
