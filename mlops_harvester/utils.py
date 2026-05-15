"""
Utilitaires partagés.
"""

import logging
import re
from pathlib import Path

from config import CONFIG


# ── Logger ────────────────────────────────────────────────────────
def _setup_logger() -> logging.Logger:
    log_dir = CONFIG["dirs"]["logs"]
    log_dir.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(
        level=logging.INFO,
        format=fmt,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / "harvester.log", encoding="utf-8"),
        ]
    )
    return logging.getLogger("mlops_harvester")


logger = _setup_logger()


# ── Répertoires ───────────────────────────────────────────────────
def ensure_dirs() -> None:
    for d in CONFIG["dirs"].values():
        Path(d).mkdir(parents=True, exist_ok=True)


# ── BibTeX ────────────────────────────────────────────────────────
def build_bibtex(paper: dict) -> str:
    """
    Génère une entrée BibTeX à partir des métadonnées d'un papier.

    Exemple de sortie :
        @article{smith2022mlpipeline,
          title  = {A machine learning pipeline for ...},
          author = {Smith, John and Doe, Jane},
          year   = {2022},
          doi    = {10.1234/example},
        }
    """
    title   = paper.get("title", "Unknown Title")
    authors = paper.get("authors", [])
    year    = str(paper.get("year", "n.d."))
    doi     = paper.get("doi")
    arxiv   = paper.get("arxiv_id")
    url     = paper.get("pdf_url", "")

    # Clé : premier_auteur_annee_premiers_mots_titre
    key = _make_cite_key(authors, year, title)

    # Format auteurs LaTeX : "Last, First and Last, First"
    author_str = _format_authors(authors)

    lines = [
        f"@article{{{key},",
        f"  title  = {{{title}}},",
        f"  author = {{{author_str}}},",
        f"  year   = {{{year}}},",
    ]
    if doi:
        lines.append(f"  doi    = {{{doi}}},")
    if arxiv:
        lines.append(f"  eprint = {{{arxiv}}},")
        lines.append(f"  archivePrefix = {{arXiv}},")
    if url and not doi:
        lines.append(f"  url    = {{{url}}},")
    lines.append("}")

    return "\n".join(lines)


def _make_cite_key(authors: list[str], year: str, title: str) -> str:
    """Génère une clé BibTeX unique et lisible."""
    # Nom du premier auteur
    first_author = ""
    if authors:
        # "John Smith" → "smith"
        parts = authors[0].split()
        first_author = re.sub(r"[^a-zA-Z]", "", parts[-1]).lower()

    # 2-3 premiers mots significatifs du titre
    stop_words = {"a", "an", "the", "of", "in", "for", "on", "with", "and",
                  "to", "is", "are", "using", "via", "based", "towards"}
    title_words = [
        re.sub(r"[^a-zA-Z]", "", w).lower()
        for w in title.split()
        if re.sub(r"[^a-zA-Z]", "", w).lower() not in stop_words
    ]
    title_slug = "".join(title_words[:3])

    return f"{first_author}{year}{title_slug}"


def _format_authors(authors: list[str]) -> str:
    """Formate une liste d'auteurs pour BibTeX."""
    if not authors:
        return "Unknown"

    formatted = []
    for name in authors[:6]:   # BibTeX : au-delà de 6, on met "et al."
        parts = name.strip().split()
        if len(parts) >= 2:
            last = parts[-1]
            first = " ".join(parts[:-1])
            formatted.append(f"{last}, {first}")
        else:
            formatted.append(name)

    result = " and ".join(formatted)
    if len(authors) > 6:
        result += " and others"
    return result
