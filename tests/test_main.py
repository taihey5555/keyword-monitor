import json
from datetime import datetime, timedelta, timezone

import main


def test_filter_cross_day_duplicates_removes_seen_url_and_doi():
    articles = [
        {"title": "A", "url": "https://example.com/a", "doi": ""},
        {"title": "B", "url": "https://example.com/b", "doi": "10.1000/seen"},
        {"title": "C", "url": "https://example.com/c", "doi": "10.1000/new"},
    ]
    seen_urls = {"https://example.com/a"}
    seen_dois = {"10.1000/seen"}

    filtered, removed = main.filter_cross_day_duplicates(articles, seen_urls, seen_dois)

    assert removed == 2
    assert [a["title"] for a in filtered] == ["C"]


def test_load_historical_keys_reads_nested_report_and_skips_today(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    historical = {
        "A": {
            "医学": [
                {
                    "title": "Past",
                    "url": "https://example.com/past/",
                    "doi": "10.1000/PAST",
                }
            ]
        }
    }
    (data_dir / "2026-03-01.json").write_text(
        json.dumps(historical, ensure_ascii=False), encoding="utf-8"
    )
    (data_dir / "index.json").write_text(json.dumps(["2026-03-01"]), encoding="utf-8")

    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).strftime("%Y-%m-%d")
    today_report = {
        "A": {
            "医学": [
                {
                    "title": "Today",
                    "url": "https://example.com/today",
                    "doi": "10.1000/today",
                }
            ]
        }
    }
    (data_dir / f"{today}.json").write_text(
        json.dumps(today_report, ensure_ascii=False), encoding="utf-8"
    )

    urls, dois, scanned = main.load_historical_keys(str(data_dir))

    assert scanned == 1
    assert "https://example.com/past" in urls
    assert "https://example.com/today" not in urls
    assert "10.1000/past" in dois
    assert "10.1000/today" not in dois
