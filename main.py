import json
import os
from datetime import datetime

from search import collect_all
from classifier import classify_ab, build_classified_report
from summarizer import summarize_all
from notifier import build_message, send_email
from config import KEYWORDS


def save_report(report: dict):
    """docs/data/YYYY-MM-DD.json に保存し、index.json を更新"""
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs("docs/data", exist_ok=True)

    # 日次JSONを保存
    filepath = f"docs/data/{today}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[SAVE] {filepath}")

    # index.json を更新
    index_path = "docs/data/index.json"
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            dates = json.load(f)
    else:
        dates = []

    if today not in dates:
        dates.append(today)
        dates.sort(reverse=True)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(dates, f, ensure_ascii=False, indent=2)
    print(f"[SAVE] {index_path}")


def main():
    print("=== キーワード監視 開始 ===")

    kw1 = KEYWORDS["kw1"]
    kw2 = KEYWORDS["kw2"]

    # 1. 検索
    print(f"[1/4] 検索中: {kw1}")
    articles_kw1 = collect_all(kw1)
    print(f"  → {len(articles_kw1)}件")

    print(f"[1/4] 検索中: {kw2}")
    articles_kw2 = collect_all(kw2)
    print(f"  → {len(articles_kw2)}件")

    # 2. A/B1/B2分類
    print("[2/4] A/B1/B2 分類中...")
    ab_groups = classify_ab(articles_kw1, articles_kw2)
    for k, v in ab_groups.items():
        print(f"  {k}: {len(v)}件")

    # 3. 分野分類
    print("[3/4] 分野分類中...")
    report = build_classified_report(ab_groups)

    # 4. 要約・タイトル翻訳
    print("[4/4] 日本語要約・タイトル翻訳中...")
    report = summarize_all(report)

    # 5. JSON保存
    print("[保存] docs/data/ に保存中...")
    save_report(report)

    # 6. メール通知
    print("[送信] Gmail通知...")
    message = build_message(report)
    send_email(message)

    print("=== 完了 ===")


if __name__ == "__main__":
    main()
