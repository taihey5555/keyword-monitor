import html
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
    """メール本文組み立て（HTML）"""
    today = datetime.now().strftime("%Y-%m-%d")

    h = []
    h.append('<html><body style="font-family:sans-serif;font-size:14px;color:#222;max-width:800px;">')
    h.append(f'<h2 style="color:#111;">【{html.escape(_kw_label)} 日次レポート】{today}</h2>')

    total_count = 0

    for group_key in GROUP_ORDER:
        group = report.get(group_key, {})
        group_articles = [a for arts in group.values() for a in arts]
        total_count += len(group_articles)

        h.append(f'<hr><h3 style="margin:6px 0;">{html.escape(GROUP_LABELS[group_key])}</h3><hr>')

        for field in FIELDS:
            articles = group.get(field, [])
            h.append(f'<p style="margin:8px 0 4px;"><b>【{html.escape(field)}】</b></p>')
            if not articles:
                h.append('<p style="margin:2px 0;color:#888;">該当なし</p>')
                continue
            for i, article in enumerate(articles, 1):
                title   = html.escape(article.get("title", "タイトル不明"))
                url     = article.get("url", "")
                summary = html.escape(article.get("summary_ja", "要約なし"))
                source  = html.escape(article.get("source", ""))
                matched = article.get("matched_keywords", [])

                h.append('<div style="margin:8px 0 12px;padding:8px;border-left:3px solid #ccc;">')
                h.append(f'<b>{i}. {title}</b><br>')
                if matched:
                    h.append(f'マッチ: {html.escape(" + ".join(matched))}<br>')
                if url:
                    h.append(f'出典: [{source}] <a href="{html.escape(url)}">{html.escape(url)}</a><br>')
                elif source:
                    h.append(f'出典: [{source}]<br>')
                h.append(f'<span style="color:#444;">{summary}</span>')
                h.append('</div>')

    if total_count == 0:
        h.append('<p>本日は全キーワードでヒットなしでした。</p>')

    h.append(f'<p><b>合計: {total_count}件</b></p>')

    ai_summary = report.get("summary", "")
    if ai_summary:
        h.append('<hr>')
        h.append('<p style="font-size:16px;font-weight:bold;color:#000;margin:8px 0;">■ 本日のAIサマリー</p>')
        h.append('<hr>')
        h.append(f'<p>{html.escape(ai_summary).replace(chr(10), "<br>")}</p>')

    h.append('</body></html>')
    return "\n".join(h)


def send_email(message: str) -> bool:
    """Gmail SMTPでメール送信（HTML形式）"""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("[GMAIL] 送信元アドレスまたはアプリパスワード未設定。標準出力に表示します。")
        print(message)
        return True

    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"【{_kw_label} 日次レポート】{today}"

    msg = MIMEText(message, "html", "utf-8")
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
