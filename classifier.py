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


def classify_ab(articles_kw1: list[dict], articles_kw2: list[dict]) -> dict:
    """
    A: 両キーワードヒット
    B1: Krothoのみ
    B2: PF4のみ
    """
    urls_kw1 = {a["url"] for a in articles_kw1}
    urls_kw2 = {a["url"] for a in articles_kw2}

    # 両方に含まれるURL
    both_urls = urls_kw1 & urls_kw2

    result = {"A": [], "B1": [], "B2": []}

    # A: 両方ヒット（kw1側のデータを使用）
    for a in articles_kw1:
        if a["url"] in both_urls:
            result["A"].append(a)

    # B1: Krothoのみ
    for a in articles_kw1:
        if a["url"] not in both_urls:
            result["B1"].append(a)

    # B2: PF4のみ
    for a in articles_kw2:
        if a["url"] not in both_urls:
            result["B2"].append(a)

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

    # スコア最大の分野を返す（同点なら医学優先）
    best = max(scores, key=lambda f: scores[f])
    if scores[best] == 0:
        return "医学"  # デフォルト
    return best


def build_classified_report(ab_groups: dict) -> dict:
    """
    {
      "A": {"医学": [...], "生物学": [...], ...},
      "B1": {...},
      "B2": {...}
    }
    """
    report = {}
    for group_key, articles in ab_groups.items():
        report[group_key] = {field: [] for field in FIELDS}
        for article in articles:
            field = classify_field(article)
            report[group_key][field].append(article)
    return report
