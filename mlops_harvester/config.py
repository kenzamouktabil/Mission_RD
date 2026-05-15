"""
Configuration centrale du MLOps Diagram Harvester
"""

import os
from pathlib import Path

CONFIG = {
    # ── Répertoires ────────────────────────────────────────────────
    "dirs": {
        "pdfs":    Path("data/pdfs"),        # PDFs téléchargés
        "figures": Path("data/figures"),     # Images extraites
        "cache":   Path("data/cache"),       # Cache des résultats de recherche
        "logs":    Path("logs"),
    },

    # ── Mots-clés de recherche ─────────────────────────────────────
    "keywords": [
        "Machine Learning Pipeline",
        "Machine Learning Process",
        "Machine Learning Workflow",
        "Machine Learning BPMN",
        "Machine Learning Mermaid diagram",
        "Machine Learning Lifecycle",
        "Machine Learning Activities",
        "MLOps Pipeline",
        "Data Science Workflow",
        "ML Pipeline Architecture",
    ],

    # ── APIs de recherche ──────────────────────────────────────────
    # Semantic Scholar : gratuit, 100 req/5min sans clé, 1000/5min avec clé
    "semantic_scholar": {
        "api_key": os.environ.get("SEMANTIC_SCHOLAR_API_KEY", ""),  # Optionnel : https://www.semanticscholar.org/product/api
        "base_url": "https://api.semanticscholar.org/graph/v1",
        "fields": "paperId,title,authors,year,externalIds,openAccessPdf,abstract",
        "min_year": 2018,       # Filtrer les papiers trop anciens
        "max_results_per_query": 20,
    },

    # arXiv : gratuit, aucune clé requise
    "arxiv": {
        "base_url": "https://export.arxiv.org/api/query",
        "max_results_per_query": 15,
    },

    # Unpaywall : trouve des PDF open-access légaux par DOI
    "unpaywall": {
        "base_url": "https://api.unpaywall.org/v2",
        "email": "clement.chaf@gmail.com",   # OBLIGATOIRE : mettez votre email
    },

    # ── Extraction de figures ──────────────────────────────────────
    "extraction": {
        "min_width":  200,      # px — ignorer les icônes/logos trop petits
        "min_height": 150,
        "max_width":  3000,
        "max_height": 3000,
        "dpi":        150,      # Résolution pour le rendu des pages PDF
        "image_format": "png",
        # Mots-clés dans les légendes qui signalent un schéma de processus
        "caption_keywords": [
            "pipeline", "workflow", "process", "architecture", "framework",
            "flow", "diagram", "overview", "lifecycle", "step", "phase",
            "methodology", "approach", "system", "model", "stage",
            "flowchart", "bpmn", "activity", "sequence",
        ],
    },

    # ── Classification IA ──────────────────────────────────────────
    # Utilise l'API Claude pour analyser les images si ANTHROPIC_API_KEY est défini
    "classifier": {
        "use_ai": True,
        "ai_threshold": 0.6,     # Score minimum pour accepter un schéma (0-1)
        "heuristic_threshold": 2, # Nombre de mots-clés caption minimum si pas d'IA
        "model": "claude-opus-4-5",
    },

    # ── Document Word ──────────────────────────────────────────────
    "word": {
        "author": "Clement CHAFFANGEON",
        "image_width_inches": 5.5,  # Largeur des images insérées
        "caption_style": "Caption",
        "add_separator": True,      # Ajouter une ligne de séparation entre entrées
    },
}
