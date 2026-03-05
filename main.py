import json
import os
import traceback
from datetime import datetime

from search import collect_all
from classifier import classify_ab, build_classified_report
from summarizer import summarize_all, generate_daily_summary
from notifier import build_message, send_email
from config import KEYWORDS


def save_report(report: dict):
    """docs/data/YYYY-MM-DD.json に保存し、index.json を更新"""
    today = datetime.now().strftime("%Y-%m-%d")

    try:
        os.makedirs("docs/data", exist_ok=True)

        # --- 日次 JSON 保存 ---
        filepath = f"docs/data/{today}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        size = os.path.getsize(filepath)
        print(f"[SAVE] {filepath}  ({size:,} bytes)")

        # --- index.json 更新 ---
        index_path = "docs/data/index.json"
        dates = []
        if os.path.exists(index_path):
            try:
                with open(index_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, list):
                    dates = loaded
                else:
                    print(f"[SAVE] index.json の形式が不正なため初期化します: {loaded!r}")
            except Exception as e:
                print(f"[SAVE] index.json の読み込みに失敗したため初期化します: {e}")

        if today not in dates:
            dates.append(today)
        dates.sort(reverse=True)

        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(dates, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        print(f"[SAVE] {index_path}  dates={dates}")

    except Exception as e:
        print(f"[SAVE ERROR] JSON保存に失敗しました: {e}")
        traceback.print_exc()


def main():
    print("=== キーワード監視 開始 ===")

    # 1. 全キーワードを検索
    article_lists = []
    for kw in KEYWORDS.values():
        print(f"[1/5] 検索中: {kw}")
        arts = collect_all(kw)
        print(f"  → {len(arts)}件")
        article_lists.append(arts)

    # 2. グループ分類
    print("[2/5] グループ分類中...")
    ab_groups = classify_ab(article_lists)
    for k, v in ab_groups.items():
        print(f"  {k}: {len(v)}件")

    # 3. 分野分類
    print("[3/5] 分野分類中...")
    report = build_classified_report(ab_groups)

    # 4. 要約・タイトル翻訳
    print("[4/5] 日本語要約・タイトル翻訳中...")
    report = summarize_all(report)

    # 4.5. Gemini デイリーサマリー生成
    print("[4.5/5] Gemini デイリーサマリー生成中...")
    try:
        report["summary"] = generate_daily_summary(report)
        print(f"[Gemini] サマリー生成完了 ({len(report['summary'])}文字)")
    except Exception as e:
        print(f"[Gemini SUMMARY ERROR] {e}")
        report["summary"] = ""

    # 5. JSON保存（メール送信より先に実行。エラーでも処理を続行）
    print("[5/5] docs/data/ に保存中...")
    try:
        save_report(report)
    except Exception as e:
        print(f"[SAVE ERROR] 予期しないエラー: {e}")
        traceback.print_exc()

    # 6. メール通知
    print("[送信] Gmail通知...")
    try:
        message = build_message(report)
        send_email(message)
    except Exception as e:
        print(f"[MAIL ERROR] メール送信に失敗しました: {e}")
        traceback.print_exc()

    print("=== 完了 ===")


if __name__ == "__main__":
    main()
