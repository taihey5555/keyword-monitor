import requests
from datetime import datetime
from config import LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, FIELDS


def build_message(report: dict) -> str:
    """LINE通知メッセージ組み立て"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"【Klotho/PF4 日次レポート】{today}"]

    group_labels = {
        "A":  "🔵 [A] 両キーワードヒット (Klotho + PF4)",
        "B1": "🟡 [B1] Klothoのみ",
        "B2": "🟢 [B2] PF4のみ"
    }

    total_count = 0

    for group_key in ["A", "B1", "B2"]:
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


def send_line(message: str) -> bool:
    """LINE Messaging APIで送信（5000文字制限で分割）"""
    if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_USER_ID:
        print("[LINE] トークンまたはユーザーID未設定。標準出力に表示します。")
        print(message)
        return True

    chunks = _split_message(message, max_len=5000)
    success = True
    for chunk in chunks:
        try:
            r = requests.post(
                "https://api.line.me/v2/bot/message/push",
                headers={
                    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "to": LINE_USER_ID,
                    "messages": [{"type": "text", "text": chunk}]
                },
                timeout=10
            )
            if r.status_code != 200:
                print(f"[LINE ERROR] status={r.status_code} {r.text}")
                success = False
        except Exception as e:
            print(f"[LINE ERROR] {e}")
            success = False
    return success


def _split_message(message: str, max_len: int = 5000) -> list[str]:
    """メッセージを分割"""
    if len(message) <= max_len:
        return [message]
    chunks = []
    while message:
        chunks.append(message[:max_len])
        message = message[max_len:]
    return chunks
