import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, EMAIL_RECIPIENTS, FIELDS


def build_message(report: dict) -> str:
    """メール本文組み立て"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"【Klotho/PF4/NK cell therapy 日次レポート】{today}"]

    group_labels = {
        "A":   "[A] 全ヒット (Klotho + PF4 + NK cell therapy)",
        "AB1": "[AB1] Klotho + PF4",
        "AB2": "[AB2] Klotho + NK cell therapy",
        "AB3": "[AB3] PF4 + NK cell therapy",
        "B1":  "[B1] Klothoのみ",
        "B2":  "[B2] PF4のみ",
        "B3":  "[B3] NK cell therapyのみ",
    }

    total_count = 0

    for group_key in ["A", "AB1", "AB2", "AB3", "B1", "B2", "B3"]:
        group = report.get(group_key, {})
        group_articles = [a for arts in group.values() for a in arts]
        total_count += len(group_articles)

        lines.append(f"\n{'='*25}")
        lines.append(group_labels[group_key])
        lines.append(f"{'='*25}")

        for field in FIELDS:
            articles = group.get(field, [])
            lines.append(f"\n【{field}】")
            if not articles:
                lines.append("該当なし")
                continue
            for i, article in enumerate(articles, 1):
                title = article.get("title", "タイトル不明")
                url = article.get("url", "URL不明")
                summary = article.get("summary_ja", "要約なし")
                source = article.get("source", "")
                lines.append(f"\n{i}. {title}")
                lines.append(f"出典: [{source}] {url}")
                lines.append(f"{summary}")

    if total_count == 0:
        lines.append("\n本日は全キーワードでヒットなしでした。")

    lines.append(f"\n合計: {total_count}件")
    return "\n".join(lines)


def send_email(message: str) -> bool:
    """Gmail SMTPでメール送信"""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("[GMAIL] 送信元アドレスまたはアプリパスワード未設定。標準出力に表示します。")
        print(message)
        return True

    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"【Klotho/PF4/NK cell therapy 日次レポート】{today}"

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
