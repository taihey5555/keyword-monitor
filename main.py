import json
import os
import traceback
from datetime import datetime, timezone, timedelta

from search import collect_all
from classifier import classify_ab, build_classified_report
from summarizer import summarize_all, generate_daily_summary
from notifier import build_message, send_email
from config import KEYWORDS, validate_required_env


def _normalize_doi(doi: str) -> str:
    return (doi or "").strip().lower()


def _normalize_url(url: str) -> str:
    return (url or "").strip().rstrip("/")


def _iter_report_articles(node):
    if isinstance(node, dict):
        if "title" in node and "url" in node:
            yield node
        for value in node.values():
            yield from _iter_report_articles(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_report_articles(item)


def load_historical_keys(data_dir: str = "docs/data") -> tuple[set[str], set[str], int]:
    """過去日付JSONの URL/DOI を収集（当日分は除外）。"""
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).strftime("%Y-%m-%d")

    urls: set[str] = set()
    dois: set[str] = set()
    scanned_files = 0

    if not os.path.isdir(data_dir):
        return urls, dois, scanned_files

    for name in sorted(os.listdir(data_dir)):
        if not name.endswith(".json") or name == "index.json" or name == f"{today}.json":
            continue

        path = os.path.join(data_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                report = json.load(f)
            scanned_files += 1
            for article in _iter_report_articles(report):
                url = _normalize_url(article.get("url", ""))
                doi = _normalize_doi(article.get("doi", ""))
                if url:
                    urls.add(url)
                if doi:
                    dois.add(doi)
        except Exception as e:
            print(f"[DEDUP WARNING] 履歴読み込み失敗: {path} ({e})")

    return urls, dois, scanned_files


def filter_cross_day_duplicates(
    articles: list[dict], seen_urls: set[str], seen_dois: set[str]
) -> tuple[list[dict], int]:
    """過去日付で既出の URL/DOI を除外。"""
    filtered = []
    removed = 0

    for article in articles:
        url = _normalize_url(article.get("url", ""))
        doi = _normalize_doi(article.get("doi", ""))

        if url and url in seen_urls:
            removed += 1
            continue
        if doi and doi in seen_dois:
            removed += 1
            continue
        filtered.append(article)

    return filtered, removed


def save_report(report: dict):
    """docs/data/YYYY-MM-DD.json に保存し、index.json を更新"""
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).strftime("%Y-%m-%d")

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
    missing = validate_required_env(require_deepseek=True, require_mail=True)
    if missing:
        print(f"[CONFIG WARNING] 未設定: {', '.join(missing)}（処理は継続）")

    seen_urls, seen_dois, scanned_files = load_historical_keys()
    print(
        f"[DEDUP] 過去データ読込: {scanned_files}ファイル / "
        f"URL {len(seen_urls)}件 / DOI {len(seen_dois)}件"
    )

    # 1. 全キーワードを検索
    article_lists = []
    for kw in KEYWORDS.values():
        print(f"[1/5] 検索中: {kw}")
        arts = collect_all(kw)
        arts, removed = filter_cross_day_duplicates(arts, seen_urls, seen_dois)
        print(f"  → {len(arts)}件（過去重複除外: {removed}件）")
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

    # 4.5. DeepSeek デイリーサマリー生成
    print("[4.5/5] DeepSeek デイリーサマリー生成中...")
    try:
        report["summary"] = generate_daily_summary(report)
        print(f"[DeepSeek] サマリー生成完了 ({len(report['summary'])}文字)")
    except Exception as e:
        print(f"[DeepSeek SUMMARY ERROR] {e}")
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
