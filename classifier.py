import re
from difflib import SequenceMatcher

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

# グループの表示順（KEYWORDS数に応じて自動生成）
GROUP_ORDER = ["A"] + [f"B{i+1}" for i in range(len(KEYWORDS))]

_TITLE_SIMILARITY_THRESHOLD = 0.8


def _normalize_title(title: str) -> str:
    """タイトルを正規化（英字小文字化・記号除去）"""
    t = (title or "").lower()
    t = re.sub(r'[^a-z0-9\u3040-\u9fff]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def classify_ab(article_lists: list[list[dict]]) -> dict:
    """
    A:      2つ以上のキーワードにヒット（article["matched_keywords"] に組み合わせを記録）
    B1-B5:  各キーワードのみにヒット

    重複排除（キーワードをまたいで適用）:
      1. URL完全一致
      2. DOI一致
      3. タイトル類似度80%以上
    """
    kw_names = list(KEYWORDS.values())
    n = len(kw_names)

    # 正規記事リスト: [(article, [matched_kw, ...])]
    canonical: list[tuple[dict, list[str]]] = []
    url_map: dict[str, int] = {}   # url → canonical index
    doi_map: dict[str, int] = {}   # doi → canonical index
    title_map: list[tuple[str, int]] = []  # (normalized_title, canonical index)

    for i, articles in enumerate(article_lists):
        for a in articles:
            url = (a.get("url") or "").strip()
            doi = (a.get("doi") or "").strip()
            title = (a.get("title") or "").strip()

            # 1. URL完全一致
            dup_idx = url_map.get(url) if url else None

            # 2. DOI一致
            if dup_idx is None and doi:
                dup_idx = doi_map.get(doi)

            # 3. タイトル類似度
            if dup_idx is None and title:
                norm = _normalize_title(title)
                if norm:
                    for existing_norm, idx in title_map:
                        if SequenceMatcher(None, norm, existing_norm).ratio() >= _TITLE_SIMILARITY_THRESHOLD:
                            dup_idx = idx
                            break

            if dup_idx is not None:
                _, matched = canonical[dup_idx]
                if kw_names[i] not in matched:
                    matched.append(kw_names[i])
                continue

            # 新規記事として登録
            new_idx = len(canonical)
            canonical.append((a, [kw_names[i]]))
            if url:
                url_map[url] = new_idx
            if doi:
                doi_map[doi] = new_idx
            if title:
                norm = _normalize_title(title)
                if norm:
                    title_map.append((norm, new_idx))

    result: dict[str, list] = {"A": []}
    for i in range(n):
        result[f"B{i+1}"] = []

    for article, matched in canonical:
        art = article.copy()
        if len(matched) >= 2:
            art["matched_keywords"] = matched
            result["A"].append(art)
        else:
            idx = kw_names.index(matched[0])
            result[f"B{idx+1}"].append(art)

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
      "A":  {"医学": [...], "生物学": [...], ...},
      "B1": {...}, "B2": {...}, ..., "B5": {...}
    }
    """
    report = {}
    for group_key, articles in ab_groups.items():
        report[group_key] = {field: [] for field in FIELDS}
        for article in articles:
            field = classify_field(article)
            report[group_key][field].append(article)
    return report
