from config import KEYWORDS, FIELDS


# 分野キーワードマッピング（英語・日本語両対応）
FIELD_KEYWORDS = {
    "医学": [
        "medicine", "medical", "clinical", "disease", "patient", "therapy",
        "drug", "treatment", "diagnosis", "hospital", "cancer", "tumor",
        "infection", "virus", "bacteria", "pharmaceutical", "疾患", "治療", "医学", "臨床"
    ],
    "生物学": [
        "biology", "gene", "protein", "cell", "molecular", "biochemistry",
        "organism", "evolution", "ecology", "microbiome", "dna", "rna",
        "enzyme", "biological", "生物", "遺伝子", "タンパク質", "分子"
    ],
    "農学": [
        "agriculture", "crop", "soil", "plant", "farm", "pesticide",
        "fertilizer", "livestock", "harvest", "cultivation", "agricultural",
        "food production", "農業", "作物", "農学", "土壌"
    ],
    "工学": [
        "engineering", "material", "chemical engineering", "process",
        "reactor", "synthesis", "polymer", "nanotechnology", "sensor",
        "device", "fabrication", "工学", "材料", "ナノ", "製造"
    ],
    "産業": [
        "industry", "industrial", "production", "manufacturing", "supply chain",
        "factory", "plant", "processing", "commodity", "petroleum", "mining",
        "産業", "製造業", "工場", "生産"
    ],
    "ビジネス": [
        "business", "market", "investment", "startup", "company", "revenue",
        "commercial", "finance", "economy", "trade", "patent", "license",
        "ビジネス", "市場", "投資", "企業", "特許"
    ]
}

# グループの表示順
GROUP_ORDER = ["A", "AB1", "AB2", "AB3", "B1", "B2", "B3"]


def classify_ab(
    articles_kw1: list[dict],
    articles_kw2: list[dict],
    articles_kw3: list[dict]
) -> dict:
    """
    A:   Klotho + PF4 + NK cell therapy（3つ全部）
    AB1: Klotho + PF4のみ
    AB2: Klotho + NK cell therapyのみ
    AB3: PF4 + NK cell therapyのみ
    B1:  Klothoのみ
    B2:  PF4のみ
    B3:  NK cell therapyのみ
    """
    # URL → article の辞書（重複URLは先勝ち）
    map1 = {a["url"]: a for a in reversed(articles_kw1)}
    map2 = {a["url"]: a for a in reversed(articles_kw2)}
    map3 = {a["url"]: a for a in reversed(articles_kw3)}

    s1, s2, s3 = set(map1), set(map2), set(map3)

    result = {g: [] for g in GROUP_ORDER}

    for url in s1 & s2 & s3:
        result["A"].append(map1[url])

    for url in (s1 & s2) - s3:
        result["AB1"].append(map1[url])

    for url in (s1 & s3) - s2:
        result["AB2"].append(map1[url])

    for url in (s2 & s3) - s1:
        result["AB3"].append(map2[url])

    for url in s1 - s2 - s3:
        result["B1"].append(map1[url])

    for url in s2 - s1 - s3:
        result["B2"].append(map2[url])

    for url in s3 - s1 - s2:
        result["B3"].append(map3[url])

    return result


def classify_field(article: dict) -> str:
    """記事をテキストで分野分類"""
    text = (
        (article.get("title") or "") + " " +
        (article.get("abstract") or "") +
        (article.get("summary_ja") or "")
    ).lower()

    scores = {field: 0 for field in FIELDS}
    for field, keywords in FIELD_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                scores[field] += 1

    best = max(scores, key=lambda f: scores[f])
    if scores[best] == 0:
        return "医学"  # デフォルト
    return best


def build_classified_report(ab_groups: dict) -> dict:
    """
    {
      "A":   {"医学": [...], "生物学": [...], ...},
      "AB1": {...}, "AB2": {...}, "AB3": {...},
      "B1":  {...}, "B2":  {...}, "B3":  {...}
    }
    """
    report = {}
    for group_key, articles in ab_groups.items():
        report[group_key] = {field: [] for field in FIELDS}
        for article in articles:
            field = classify_field(article)
            report[group_key][field].append(article)
    return report
