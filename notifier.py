import html
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, EMAIL_RECIPIENTS, FIELDS, KEYWORDS
import summarizer


# グループラベル（KEYWORDS から自動生成）
_kw_names = list(KEYWORDS.values())
_kw_label = " / ".join(_kw_names)

GROUP_LABELS: dict[str, str] = {"A": "[A] 複数キーワードヒット"}
for _i, _name in enumerate(_kw_names, 1):
    GROUP_LABELS[f"B{_i}"] = f"[B{_i}] {_name}のみ"

GROUP_ORDER = ["A"] + [f"B{i+1}" for i in range(len(KEYWORDS))]


def build_message(report: dict) -> str:
    """メール本文組み立て（HTML）"""
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).strftime("%Y-%m-%d")

    GROUP_COLORS = {
        "A": "#f59e0b",
        "B1": "#3b82f6",
        "B2": "#8b5cf6",
        "B3": "#10b981",
        "B4": "#ef4444",
        "B5": "#f97316",
    }

    total_count = sum(
        len([a for arts in report.get(gk, {}).values() for a in arts])
        for gk in GROUP_ORDER
    )

    h = []
    h.append('<html><body style="margin:0;padding:0;background:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;">')
    h.append('<div style="max-width:700px;margin:0 auto;padding:20px;">')

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
        f'<div style="background:linear-gradient(135deg,#1a73e8,#0d47a1);border-radius:12px;padding:28px 32px;margin-bottom:20px;">'
        f'<div style="color:#90caf9;font-size:12px;letter-spacing:1px;margin-bottom:6px;">DAILY REPORT</div>'
        f'<div style="color:#fff;font-size:20px;font-weight:700;margin-bottom:10px;">&#128269; {html.escape(_kw_label)}</div>'
        f'<span style="color:#bbdefb;font-size:13px;">&#128197; {today} &nbsp;&nbsp; &#128196; {total_count}件</span>'
        f'</div>'
    )

    for group_key in GROUP_ORDER:
        group = report.get(group_key, {})
        group_articles = [a for arts in group.values() for a in arts]
        if not group_articles:
            continue

        color = GROUP_COLORS.get(group_key, "#6b7280")
        label = html.escape(GROUP_LABELS[group_key])

        h.append('<div style="margin-bottom:24px;">')
        h.append(
            f'<div style="display:inline-block;background:{color};color:#fff;font-size:12px;font-weight:700;'
            f'padding:4px 14px;border-radius:20px;margin-bottom:12px;">'
            f'{label} &nbsp;{len(group_articles)}件</div>'
        )

        for field in FIELDS:
            articles = group.get(field, [])
            if not articles:
                continue

            h.append(
                f'<div style="color:#6b7280;font-size:11px;font-weight:600;letter-spacing:0.5px;'
                f'margin:10px 0 6px 4px;">&#9656; {html.escape(field)}</div>'
            )

            for i, article in enumerate(articles, 1):
                url      = article.get("url", "")
                summary  = html.escape(article.get("summary_ja", "要約なし"))
                title_ja = html.escape(article.get("title_ja", "") or article.get("title", "タイトル不明"))

                h.append(
                    f'<div style="background:#fff;border-radius:8px;padding:14px 16px;margin-bottom:8px;'
                    f'border-left:4px solid {color};box-shadow:0 1px 3px rgba(0,0,0,0.08);">'
                    f'<div style="font-weight:600;color:#111;font-size:14px;margin-bottom:6px;">{i}. {title_ja}</div>'
                )
                if url:
                    h.append(
                        f'<div style="margin-bottom:6px;">'
                        f'<a href="{html.escape(url)}" style="color:#1a73e8;font-size:12px;word-break:break-all;">'
                        f'{html.escape(url)}</a></div>'
                    )
                h.append(f'<div style="color:#555;font-size:13px;line-height:1.6;">{summary}</div>')
                h.append('</div>')

        h.append('</div>')

    if total_count == 0:
        h.append('<div style="background:#fff;border-radius:8px;padding:20px;text-align:center;color:#888;">本日は全キーワードでヒットなしでした。</div>')

    # AIサマリー
    ai_summary = report.get("summary", "")
    if ai_summary:
        h.append(
            '<div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;'
            'padding:20px 24px;margin-bottom:20px;">'
            '<div style="color:#1e40af;font-size:15px;font-weight:700;margin-bottom:12px;">&#10022; 本日のAIサマリー</div>'
            f'<div style="color:#374151;font-size:14px;line-height:1.8;">{html.escape(ai_summary).replace(chr(10), "<br>")}</div>'
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


def send_email(message: str) -> bool:
    """Gmail SMTPでメール送信（HTML形式）"""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("[GMAIL] 送信元アドレスまたはアプリパスワード未設定。標準出力に表示します。")
        print(message)
        return True

    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).strftime("%Y-%m-%d")
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
