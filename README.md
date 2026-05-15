# SkeltyMLOps — Validation par extraction automatisée de processus

> **Contexte académique** : IMT Mines Alès — Recherche & Développement  
> **Auteurs** : Clement CHAFFANGEON, Kenza MOUKTABIL, Rihab SEMMAR  
> **Superviseurs** : Charbel Daoud, Sylvain Vauttier, Christelle Urtado

---

## Objectif du projet

Ce projet contribue à la **validation de l'architecture de référence SkeltyMLOps** en collectant, extrayant et formalisant des descriptions de processus MLOps issus de la littérature académique et de la documentation technique des frameworks.

SkeltyMLOps organise les activités MLOps en **5 dimensions** :

| Dimension | Acteur | Activités clés |
|---|---|---|
| **PLAN** | Product Owner | Conceptualisation, définition des exigences, initialisation |
| **DATA** | Data Engineer | Collecte, ingestion, prétraitement, validation, feature engineering |
| **MODEL** | Model Engineer | Expérimentation, entraînement, évaluation, registre de modèles |
| **SOFT** | Software Engineer | Développement, packaging, tests, release |
| **OPS** | Ops Engineer | CI/CD, déploiement, monitoring, réentraînement |

---

## Structure du dossier

```
R&D/
│
├── README.md                        ← Ce fichier
│
├── mlops_harvester/                 ← Pipeline automatisé d'extraction
│   ├── main.py                      ← Point d'entrée principal
│   ├── config.py                    ← Paramètres centralisés
│   ├── searcher.py                  ← Recherche Semantic Scholar + arXiv
│   ├── downloader.py                ← Téléchargement PDFs via Unpaywall
│   ├── extractor.py                 ← Extraction figures (PyMuPDF)
│   ├── classifier.py                ← Classification IA (Claude Vision)
│   ├── word_builder.py              ← Génération rapport Word
│   ├── excel_updater.py             ← Mise à jour base Excel
│   ├── utils.py                     ← Logger + génération BibTeX
│   ├── requirements.txt             ← Dépendances Python
│   └── data/                        ← Données locales du module
│       ├── cache/                   ← Cache JSON des requêtes API
│       ├── pdfs/                    ← PDFs téléchargés (copie locale)
│       └── figures/                 ← Figures extraites (copie locale)
│
├── data/                            ← Données du projet (volume principal)
│   ├── pdfs/                        ← 233 articles académiques en PDF
│   ├── figures/                     ← 1 590 figures PNG extraites
│   └── cache/                       ← 10 fichiers JSON de cache arXiv
│
├── logs/
│   └── harvester.log                ← Journal d'exécution du pipeline
│
├── papers_db.xlsx                   ← Base de données de suivi (36 KB)
├── papers_db_template.xlsx          ← Modèle Excel vierge
│
├── Process_img_database.docx        ← Livrable principal : 59 schémas
│                                       annotés avec légendes + BibTeX (35 MB)
├── Process img database.docx        ← Version antérieure du livrable
│
└── .venv/                           ← Environnement Python isolé
```

---

## Livrables produits

### `Process_img_database.docx` (35 MB)
Document Word contenant l'ensemble des **59 schémas de processus MLOps** validés, extraits automatiquement depuis 21 articles scientifiques. Chaque entrée comprend :
- L'image du schéma (haute résolution)
- La légende originale de la figure
- La citation BibTeX complète de l'article source

### `papers_db.xlsx`
Base de données Excel de suivi avec numérotation automatique :
- Colonne A : ID unique du papier (1, 2, 3…)
- Colonne B : Numéro de figure (1.1, 1.2, 2.1…)
- Colonne C : Code BibTeX complet

### `data/`
- **233 PDFs** téléchargés depuis Semantic Scholar, arXiv et Unpaywall
- **1 590 figures PNG** extraites par PyMuPDF (tous les candidats avant filtrage IA)

---

## Architecture technique

Le projet repose sur deux composants complémentaires.

### 1 — Pipeline `mlops_harvester` (documents académiques)

Automatise 4 étapes séquentielles :

```
[1] RECHERCHE (~30 sec)
    searcher.py → Semantic Scholar API + arXiv API
    Requêtes booléennes sur 10 mots-clés MLOps
    Cache JSON local pour éviter les appels redondants
    → ~235 articles identifiés

[2] TÉLÉCHARGEMENT (~40 sec)
    downloader.py → Unpaywall API + liens directs arXiv
    Récupère les PDFs en open access sans paywall
    → 233 PDFs en cache local

[3] EXTRACTION + CLASSIFICATION (~2-3 min)
    extractor.py (PyMuPDF) → détection légendes par RegEx
    Calcul boîte englobante spatiale au-dessus de chaque légende
    classifier.py (Claude Vision API) → score de confiance [0.0, 1.0]
    Seuil de sélection : score ≥ 0.6
    → ~300 candidats → 59 schémas validés

[4] GÉNÉRATION
    word_builder.py → Process_img_database.docx (images + BibTeX)
    excel_updater.py → papers_db.xlsx (IDs + numérotation + BibTeX)
```

### 2 — Agent `Skelty-Extractor` (documentation web)

Agent LLM autonome basé sur **LangGraph** pour extraire des processus depuis la documentation officielle des frameworks MLOps (TFX, MLflow, etc.).

Fonctionnement :
1. **Navigation** : machine à états LangGraph, profondeur maximale configurable
2. **Nettoyage** : BeautifulSoup → suppression menus/footers → Markdown via `markdownify`
3. **Extraction** : OpenAI API avec schéma Pydantic strict (`MLOpsProcess`)
4. **Déduplication** : ChromaDB + embeddings `all-MiniLM-L6-v2`, seuil cosinus < 0.15
5. **Export** : JSON + rapport Markdown + file de révision humaine

Schéma de données extrait (`MLOpsProcess`) :
```python
{
  "name": str,                 # Nom du processus
  "framework": str,            # Framework source (TFX, MLflow…)
  "classification": str,       # "Processus complet" | "Brique de processus"
  "dimensions": list[str],     # Dimensions SkeltyMLOps impactées
  "actors": list[str],         # Acteurs impliqués
  "justification": str,        # Preuve technique du mapping
  "confidence_score": float,   # Score [0.0, 1.0]
  "is_uncertain": bool         # Flag pour révision humaine
}
```

---

## Installation et configuration

### Prérequis

| Élément | Version | Requis |
|---|---|---|
| Python | 3.10+ | ✅ |
| Clé API Unpaywall (email) | — | ✅ |
| Clé API Anthropic | — | Recommandé (meilleure classification) |
| Clé API OpenAI | — | Requis pour Skelty-Extractor |
| Clé API Semantic Scholar | — | Optionnel (augmente les quotas) |

### Installation

```bash
# Depuis la racine du projet
python -m venv .venv
source .venv/bin/activate        # Linux/Mac
.venv\Scripts\activate           # Windows

pip install -r mlops_harvester/requirements.txt
```

### Configuration obligatoire

Éditer `mlops_harvester/config.py` :

```python
# 1. Email Unpaywall (OBLIGATOIRE pour télécharger les PDFs)
"unpaywall": {
    "email": "prenom.nom@institution.fr",
}

# 2. Mots-clés de recherche (adaptables)
"keywords": [
    "Machine Learning Pipeline",
    "Machine Learning Process",
    "Machine Learning Workflow",
    "Machine Learning BPMN",
    "MLOps Pipeline",
    # Ajouter les vôtres…
]

# 3. Seuil de classification IA (0.6 par défaut)
"classifier": {
    "ai_threshold": 0.6,   # Augmenter pour plus de précision
}
```

Variables d'environnement :

```bash
export ANTHROPIC_API_KEY="sk-ant-..."    # Classification IA (Claude Vision)
export OPENAI_API_KEY="sk-..."           # Agent Skelty-Extractor
```

---

## Utilisation

### Lancement standard

```bash
cd mlops_harvester
python main.py
```

### Options disponibles

```bash
# Limiter le nombre de papiers traités (test rapide)
python main.py --limit 5

# Spécifier un fichier Word de sortie
python main.py --output mon_rapport.docx

# Mettre à jour la base Excel
python main.py --excel ../papers_db.xlsx

# Word + Excel en une commande
python main.py --output Process_img_database.docx --excel ../papers_db.xlsx

# Ajouter à un document Word existant
python main.py --existing Process_img_database.docx --output Process_img_database_v2.docx

# Désactiver la classification IA (conserver toutes les figures)
python main.py --no-classify

# Test sans téléchargement ni écriture
python main.py --dry-run --limit 3
```

### Workflow recommandé

```bash
# Étape 1 : Test avec 5 papiers (vérifier la config)
python main.py --limit 5 --excel ../papers_db_test.xlsx

# Étape 2 : Lancement complet
python main.py \
  --output ../Process_img_database.docx \
  --excel ../papers_db.xlsx
```

---

## Résultats du corpus collecté

| Métrique | Valeur |
|---|---|
| Articles uniques validés | 21 |
| Figures de processus documentées | 59 |
| PDFs téléchargés | 233 |
| Figures candidates extraites | ~1 590 |
| Fenêtre temporelle | 2020 – 2026 |

### Distribution par année

| 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| 2 | 3 | 5 | 6 | 3 | 2 |

### Distribution par éditeur

| Éditeur | Articles |
|---|---|
| IEEE | 7 |
| O'Reilly Media | 3 |
| arXiv | 3 |
| Thèses académiques | 2 |
| Autres revues | 6 |

---

## Dépannage

| Problème | Cause probable | Solution |
|---|---|---|
| `ModuleNotFoundError: fitz` | PyMuPDF non installé | `pip install PyMuPDF` |
| `ModuleNotFoundError: docx` | python-docx non installé | `pip install python-docx` |
| Aucun PDF téléchargé | Email Unpaywall manquant | Vérifier `config.py` → `unpaywall.email` |
| Aucun schéma extrait | Seuil IA trop élevé | Baisser `ai_threshold` à 0.4 ou utiliser `--no-classify` |
| `#VALUE!` dans Excel | Fichier ouvert dans Excel | Fermer Excel avant de lancer le script |
| Crash mémoire sur un PDF | Graphique vectoriel infini (Vector Bomb) | Comportement normal, le script continue automatiquement |
| Quota API dépassé | Trop de requêtes Semantic Scholar | Ajouter une clé API dans `config.py` ou attendre 5 min |
| `KeyError: ANTHROPIC_API_KEY` | Variable d'environnement manquante | `export ANTHROPIC_API_KEY="sk-ant-..."` |

---

## Limites connues

- Environ 40–60 % des articles académiques sont derrière paywall et ne peuvent pas être téléchargés automatiquement.
- Les figures couvrant plusieurs pages peuvent être rognées lors de l'extraction spatiale.
- La classification VLM (Claude Vision) peut sur-interpréter un script séquentiel simple comme un processus orchestré (hallucination mineure) — le score de confiance permet de filtrer ces cas.
- Semantic Scholar impose un quota de 100 requêtes / 5 min sans clé API.

---

## Références des APIs utilisées

- [Semantic Scholar API](https://www.semanticscholar.org/product/api)
- [arXiv API](https://arxiv.org/help/api)
- [Unpaywall API](https://unpaywall.org/products/api)
- [Anthropic Claude API](https://docs.anthropic.com)
- [OpenAI API](https://platform.openai.com/docs)
- [PyMuPDF](https://pymupdf.readthedocs.io)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [ChromaDB](https://docs.trychroma.com)
