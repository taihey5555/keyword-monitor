import notifier


def test_b5_group_uses_configured_color():
    report = {
        "A": {},
        "B1": {},
        "B2": {},
        "B3": {},
        "B4": {},
        "B5": {
            "医学": [
                {
                    "title": "sample",
                    "title_ja": "サンプル",
                    "summary_ja": "要約",
                    "url": "https://example.com",
                }
            ],
            "生物学": [],
            "農学": [],
            "工学": [],
            "産業": [],
            "ビジネス": [],
        },
    }

    html = notifier.build_message(report)
    assert "border-left:4px solid #f97316" in html
