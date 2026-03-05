import requests
import urllib.parse
from datetime import datetime, timedelta
from config import GOOGLE_API_KEY, GOOGLE_CSE_ID


def search_pubmed(keyword: str, days: int = 1) -> list[dict]:
    """PubMed APIで論文検索"""
    results = []
    try:
        date_from = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
        query = f"{keyword} AND (\"{date_from}\"[PDat] : \"3000\"[PDat])"
        encoded = urllib.parse.quote(query)

        # 検索してIDリスト取得
        search_url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=pubmed&term={encoded}&retmax=10&retmode=json"
        )
        r = requests.get(search_url, timeout=10)
        ids = r.json().get("esearchresult", {}).get("idlist", [])

        if not ids:
            return []

        # 詳細取得
        fetch_url = (
            f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
            f"?db=pubmed&id={','.join(ids)}&retmode=xml&rettype=abstract"
        )
        rf = requests.get(fetch_url, timeout=10)

        # XMLを簡易パース
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(rf.content)
        except ET.ParseError as e:
            print(f"[PubMed ERROR] XML parse error: {e}")
            print(f"[PubMed ERROR] status={rf.status_code}, body_head={rf.text[:200]!r}")
            return results
        for article in root.findall(".//PubmedArticle"):
            title_el = article.find(".//ArticleTitle")
            abstract_el = article.find(".//AbstractText")
            pmid_el = article.find(".//PMID")

            title = title_el.text if title_el is not None else "タイトル不明"
            abstract = abstract_el.text if abstract_el is not None else ""
            pmid = pmid_el.text if pmid_el is not None else ""
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

            doi = ""
            for aid in article.findall(".//ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = (aid.text or "").strip()
                    break

            results.append({
                "title": title,
                "url": url,
                "abstract": abstract,
                "source": "PubMed",
                "doi": doi,
            })
    except Exception as e:
        print(f"[PubMed ERROR] {e}")
    return results


def search_arxiv(keyword: str, days: int = 1) -> list[dict]:
    """arXiv APIで論文検索"""
    results = []
    try:
        encoded = urllib.parse.quote(keyword)
        url = (
            f"http://export.arxiv.org/api/query"
            f"?search_query=all:{encoded}&start=0&max_results=10"
            f"&sortBy=submittedDate&sortOrder=descending"
        )
        r = requests.get(url, timeout=10)

        import xml.etree.ElementTree as ET
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        root = ET.fromstring(r.text)

        cutoff = datetime.now() - timedelta(days=days)
        for entry in root.findall("atom:entry", ns):
            published_el = entry.find("atom:published", ns)
            published_str = published_el.text if published_el is not None else ""
            try:
                published_dt = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                if published_dt.replace(tzinfo=None) < cutoff:
                    continue
            except Exception:
                pass

            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            link_el = entry.find("atom:id", ns)
            doi_el = entry.find("arxiv:doi", ns)
            doi = (doi_el.text or "").strip() if doi_el is not None else ""

            results.append({
                "title": (title_el.text or "").strip(),
                "url": (link_el.text or "").strip(),
                "abstract": (summary_el.text or "").strip(),
                "source": "arXiv",
                "doi": doi,
            })
    except Exception as e:
        print(f"[arXiv ERROR] {e}")
    return results


def search_semantic_scholar(keyword: str) -> list[dict]:
    """Semantic Scholar APIで検索"""
    results = []
    try:
        encoded = urllib.parse.quote(keyword)
        url = (
            f"https://api.semanticscholar.org/graph/v1/paper/search"
            f"?query={encoded}&limit=10&fields=title,abstract,url,year,externalIds"
        )
        r = requests.get(url, timeout=10, headers={"User-Agent": "keyword-monitor/1.0"})
        data = r.json().get("data", [])

        current_year = datetime.now().year
        for item in data:
            if item.get("year") and item["year"] < current_year - 1:
                continue
            doi = (item.get("externalIds") or {}).get("DOI") or ""
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", "") or f"https://www.semanticscholar.org/paper/{item.get('paperId','')}",
                "abstract": item.get("abstract", "") or "",
                "source": "SemanticScholar",
                "doi": doi,
            })
    except Exception as e:
        print(f"[SemanticScholar ERROR] {e}")
    return results


def search_google(keyword: str) -> list[dict]:
    """Google Custom Search APIで検索"""
    results = []
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        print("[Google] APIキー未設定のためスキップ")
        return []
    try:
        encoded = urllib.parse.quote(keyword)
        url = (
            f"https://www.googleapis.com/customsearch/v1"
            f"?key={GOOGLE_API_KEY}&cx={GOOGLE_CSE_ID}&q={encoded}&num=5"
            f"&dateRestrict=d1"
        )
        r = requests.get(url, timeout=10)
        items = r.json().get("items", [])
        for item in items:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "abstract": item.get("snippet", ""),
                "source": "Google",
                "doi": "",
            })
    except Exception as e:
        print(f"[Google ERROR] {e}")
    return results


def collect_all(keyword: str) -> list[dict]:
    """全ソースから収集してまとめて返す"""
    all_results = []
    all_results.extend(search_pubmed(keyword))
    all_results.extend(search_arxiv(keyword))
    all_results.extend(search_semantic_scholar(keyword))
    all_results.extend(search_google(keyword))

    # URLとDOIでdedup（同一キーワード内）
    seen_urls: set = set()
    seen_dois: set = set()
    deduped = []
    for item in all_results:
        url = item.get("url", "")
        doi = item.get("doi", "")
        if url and url in seen_urls:
            continue
        if doi and doi in seen_dois:
            continue
        if url:
            seen_urls.add(url)
        if doi:
            seen_dois.add(doi)
        item["keyword"] = keyword
        deduped.append(item)
    return deduped
