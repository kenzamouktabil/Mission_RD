"""
Recherche de papiers scientifiques via Semantic Scholar et arXiv.

Sources utilisées (toutes gratuites et légales) :
- Semantic Scholar API  : https://api.semanticscholar.org
- arXiv API             : https://arxiv.org/help/api
"""

import json
import time
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests

from config import CONFIG
from utils import logger


class PaperSearcher:
    """Orchestre la recherche sur plusieurs sources et déduplique les résultats."""

    def __init__(self, limit_per_keyword: int = 20):
        self.limit = limit_per_keyword
        self.cache_dir = CONFIG["dirs"]["cache"]
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._seen_ids: set[str] = set()

    # ─────────────────────────────────────────────────────────────────
    #  PUBLIC
    # ─────────────────────────────────────────────────────────────────

    def search_all(self) -> list[dict]:
        """Lance toutes les recherches et retourne une liste dédupliquée."""
        papers: list[dict] = []

        for keyword in CONFIG["keywords"]:
            logger.info(f"  Recherche : « {keyword} »")

            # Semantic Scholar
            ss_results = self._search_semantic_scholar(keyword)
            new_ss = self._deduplicate(ss_results)
            logger.info(f"    Semantic Scholar : {len(new_ss)} nouveaux")
            papers.extend(new_ss)

            # arXiv
            arxiv_results = self._search_arxiv(keyword)
            new_arxiv = self._deduplicate(arxiv_results)
            logger.info(f"    arXiv            : {len(new_arxiv)} nouveaux")
            papers.extend(new_arxiv)

            time.sleep(0.5)  # Respecter les rate limits

        return papers

    # ─────────────────────────────────────────────────────────────────
    #  SEMANTIC SCHOLAR
    # ─────────────────────────────────────────────────────────────────

    def _search_semantic_scholar(self, keyword: str) -> list[dict]:
        cache_key = self._cache_key("ss", keyword)
        cached = self._load_cache(cache_key)
        if cached is not None:
            return cached

        cfg = CONFIG["semantic_scholar"]
        headers = {}
        if cfg["api_key"]:
            headers["x-api-key"] = cfg["api_key"]

        params = {
            "query": keyword,
            "fields": cfg["fields"],
            "limit": self.limit,
            "year": f"{cfg['min_year']}-",
        }

        try:
            resp = requests.get(
                f"{cfg['base_url']}/paper/search",
                params=params,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json().get("data", [])
        except requests.RequestException as e:
            logger.warning(f"    Semantic Scholar error: {e}")
            return []

        results = []
        for item in data:
            paper = self._normalize_ss(item, keyword)
            if paper:
                results.append(paper)

        self._save_cache(cache_key, results)
        return results

    def _normalize_ss(self, item: dict, keyword: str) -> Optional[dict]:
        """Normalise un résultat Semantic Scholar vers le format interne."""
        title = item.get("title", "").strip()
        if not title:
            return None

        authors = item.get("authors", [])
        author_names = [a.get("name", "") for a in authors]

        pdf_url = None
        oap = item.get("openAccessPdf")
        if oap and isinstance(oap, dict):
            pdf_url = oap.get("url")

        doi = None
        ext_ids = item.get("externalIds") or {}
        doi = ext_ids.get("DOI")
        arxiv_id = ext_ids.get("ArXiv")

        return {
            "id":        item.get("paperId", ""),
            "title":     title,
            "authors":   author_names,
            "year":      item.get("year") or "n.d.",
            "doi":       doi,
            "arxiv_id":  arxiv_id,
            "pdf_url":   pdf_url,
            "abstract":  item.get("abstract", ""),
            "source":    "semantic_scholar",
            "keyword":   keyword,
        }

    # ─────────────────────────────────────────────────────────────────
    #  arXiv
    # ─────────────────────────────────────────────────────────────────

    def _search_arxiv(self, keyword: str) -> list[dict]:
        cache_key = self._cache_key("arxiv", keyword)
        cached = self._load_cache(cache_key)
        if cached is not None:
            return cached

        cfg = CONFIG["arxiv"]
        query = f"all:{keyword.replace(' ', '+AND+')}"
        params = {
            "search_query": query,
            "start": 0,
            "max_results": self.limit,
            "sortBy": "relevance",
        }

        try:
            resp = requests.get(cfg["base_url"], params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"    arXiv error: {e}")
            return []

        results = self._parse_arxiv_xml(resp.text, keyword)
        self._save_cache(cache_key, results)
        return results

    def _parse_arxiv_xml(self, xml_text: str, keyword: str) -> list[dict]:
        ns = {
            "atom":  "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        papers = []
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            title = title_el.text.strip().replace("\n", " ") if title_el is not None else ""
            if not title:
                continue

            # arXiv ID & PDF link
            arxiv_id = ""
            pdf_url = ""
            id_el = entry.find("atom:id", ns)
            if id_el is not None:
                raw_id = id_el.text.strip()
                arxiv_id = raw_id.split("/abs/")[-1]
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"

            authors = []
            for auth in entry.findall("atom:author", ns):
                name_el = auth.find("atom:name", ns)
                if name_el is not None:
                    authors.append(name_el.text.strip())

            published_el = entry.find("atom:published", ns)
            year = published_el.text[:4] if published_el is not None else "n.d."

            # DOI si disponible
            doi_el = entry.find("arxiv:doi", ns)
            doi = doi_el.text.strip() if doi_el is not None else None

            papers.append({
                "id":       arxiv_id,
                "title":    title,
                "authors":  authors,
                "year":     year,
                "doi":      doi,
                "arxiv_id": arxiv_id,
                "pdf_url":  pdf_url,
                "abstract": "",
                "source":   "arxiv",
                "keyword":  keyword,
            })
        return papers

    # ─────────────────────────────────────────────────────────────────
    #  UTILITAIRES
    # ─────────────────────────────────────────────────────────────────

    def _deduplicate(self, papers: list[dict]) -> list[dict]:
        new_papers = []
        for p in papers:
            uid = self._uid(p)
            if uid not in self._seen_ids:
                self._seen_ids.add(uid)
                new_papers.append(p)
        return new_papers

    @staticmethod
    def _uid(paper: dict) -> str:
        """Identifiant unique basé sur le titre normalisé."""
        title_norm = paper["title"].lower().strip()
        return hashlib.md5(title_norm.encode()).hexdigest()

    @staticmethod
    def _cache_key(source: str, keyword: str) -> str:
        k = hashlib.md5(f"{source}:{keyword}".encode()).hexdigest()
        return f"{source}_{k}"

    def _load_cache(self, key: str) -> Optional[list]:
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                logger.debug(f"    (cache hit: {key})")
                return data
            except Exception:
                pass
        return None

    def _save_cache(self, key: str, data: list) -> None:
        path = self.cache_dir / f"{key}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
