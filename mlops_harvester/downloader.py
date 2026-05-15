"""
Téléchargement des PDFs open-access.

Stratégie par ordre de priorité :
  1. URL PDF directe fournie par Semantic Scholar / arXiv
  2. Unpaywall (cherche un PDF libre via le DOI)
  3. Lien direct arXiv (/pdf/{id})
"""

import re
import time
import hashlib
from pathlib import Path

import requests

from config import CONFIG
from utils import logger


class PDFDownloader:

    def __init__(self):
        self.pdf_dir = CONFIG["dirs"]["pdfs"]
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MLOps-Harvester/1.0 (research; contact: your@email.com)"
        })

    # ─────────────────────────────────────────────────────────────────
    #  PUBLIC
    # ─────────────────────────────────────────────────────────────────

    def download_all(self, papers: list[dict]) -> list[dict]:
        """Tente de télécharger un PDF pour chaque papier."""
        downloaded = []
        for i, paper in enumerate(papers, 1):
            logger.info(f"  [{i}/{len(papers)}] {paper['title'][:60]}...")
            result = self._download_one(paper)
            if result:
                downloaded.append(result)
            time.sleep(0.3)   # politesse
        return downloaded

    # ─────────────────────────────────────────────────────────────────
    #  PRIVATE
    # ─────────────────────────────────────────────────────────────────

    def _download_one(self, paper: dict) -> dict | None:
        """Retourne un dict {paper, pdf_path} ou None si échec."""
        slug = self._slug(paper["title"])
        dest = self.pdf_dir / f"{slug}.pdf"

        if dest.exists() and dest.stat().st_size > 5_000:
            logger.info(f"    ✓ (cache) {dest.name}")
            return {"paper": paper, "pdf_path": dest}

        # Essai 1 : URL directe dans les métadonnées
        if paper.get("pdf_url"):
            if self._fetch(paper["pdf_url"], dest):
                logger.info(f"    ✓ direct url")
                return {"paper": paper, "pdf_path": dest}

        # Essai 2 : Unpaywall via DOI
        if paper.get("doi"):
            url = self._unpaywall_url(paper["doi"])
            if url and self._fetch(url, dest):
                logger.info(f"    ✓ unpaywall")
                return {"paper": paper, "pdf_path": dest}

        # Essai 3 : arXiv direct
        if paper.get("arxiv_id"):
            url = f"https://arxiv.org/pdf/{paper['arxiv_id']}"
            if self._fetch(url, dest):
                logger.info(f"    ✓ arxiv direct")
                return {"paper": paper, "pdf_path": dest}

        logger.info(f"    ✗ pas de PDF accessible")
        return None

    def _fetch(self, url: str, dest: Path) -> bool:
        """Télécharge l'URL vers dest. Retourne True si succès."""
        try:
            resp = self.session.get(url, timeout=20, allow_redirects=True, stream=True)
            if resp.status_code != 200:
                return False
            content_type = resp.headers.get("Content-Type", "")
            if "pdf" not in content_type and "octet-stream" not in content_type:
                # Parfois le serveur retourne HTML (mur de paiement)
                # On vérifie les premiers octets
                first_chunk = b""
                for chunk in resp.iter_content(1024):
                    first_chunk = chunk
                    break
                if not first_chunk.startswith(b"%PDF"):
                    return False
                with open(dest, "wb") as f:
                    f.write(first_chunk)
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
            else:
                with open(dest, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
            return dest.stat().st_size > 5_000
        except requests.RequestException:
            return False

    def _unpaywall_url(self, doi: str) -> str | None:
        """Interroge Unpaywall pour obtenir un lien PDF libre."""
        email = CONFIG["unpaywall"]["email"]
        if email == "your@email.com":
            logger.warning(
                "    Unpaywall désactivé — configurez votre email dans config.py"
            )
            return None
        url = f"{CONFIG['unpaywall']['base_url']}/{doi}?email={email}"
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            data = resp.json()
            oa_location = data.get("best_oa_location") or {}
            return oa_location.get("url_for_pdf") or oa_location.get("url")
        except Exception:
            return None

    @staticmethod
    def _slug(title: str) -> str:
        """Convertit un titre en nom de fichier sûr."""
        slug = re.sub(r"[^a-zA-Z0-9 ]", "", title)
        slug = slug.lower().replace(" ", "_")[:80]
        h = hashlib.md5(title.encode()).hexdigest()[:8]
        return f"{slug}_{h}"
