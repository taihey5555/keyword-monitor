from search import collect_all
from classifier import classify_ab, build_classified_report
from summarizer import summarize_all
from notifier import build_message, send_line
from config import KEYWORDS


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

    # 4. 要約生成
    print("[4/4] 日本語要約生成中...")
    report = summarize_all(report)

    # 5. LINE通知
    print("[送信] LINE通知...")
    message = build_message(report)
    send_line(message)

    print("=== 完了 ===")


if __name__ == "__main__":
    main()
