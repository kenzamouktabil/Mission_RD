"""
MLOps Diagram Harvester
=======================
Automatise la recherche et l'extraction de schémas de processus ML
depuis des papiers scientifiques vers un document Word.

Usage:
    python main.py [--output output.docx] [--limit 50] [--keywords custom.txt]

Requirements:
    pip install requests PyMuPDF python-docx Pillow tqdm anthropic
"""

import argparse
import sys
from pathlib import Path

from config import CONFIG
from searcher import PaperSearcher
from downloader import PDFDownloader
from extractor import FigureExtractor
from classifier import DiagramClassifier
from word_builder import WordDocumentBuilder
from excel_updater import update_excel_from_diagrams
from utils import logger, ensure_dirs


def main():
    parser = argparse.ArgumentParser(
        description="Automatise la récolte de schémas MLOps dans des papiers scientifiques"
    )
    parser.add_argument(
        "--output",
        default="Process_img_database.docx",
        help="Fichier Word de sortie (défaut: Process_img_database.docx)"
    )
    parser.add_argument(
        "--excel",
        default=None,
        help="Fichier Excel papers_db.xlsx à mettre à jour (optionnel)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Nombre max de papiers à traiter par mot-clé (défaut: 30)"
    )
    parser.add_argument(
        "--existing",
        default=None,
        help="Fichier Word existant à mettre à jour (pour ajouter des entrées)"
    )
    parser.add_argument(
        "--no-classify",
        action="store_true",
        help="Désactiver la classification IA (prend toutes les figures)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simule sans télécharger ni modifier le Word"
    )
    args = parser.parse_args()

    ensure_dirs()

    logger.info("=" * 60)
    logger.info("  MLOps Diagram Harvester")
    logger.info("=" * 60)

    # ── 1. RECHERCHE ──────────────────────────────────────────────
    logger.info("\n[ÉTAPE 1/4] Recherche de papiers scientifiques...")
    searcher = PaperSearcher(limit_per_keyword=args.limit)
    papers = searcher.search_all()
    logger.info(f"  → {len(papers)} papiers uniques trouvés")

    if args.dry_run:
        logger.info("\n[DRY RUN] Papiers qui seraient traités :")
        for i, p in enumerate(papers[:10], 1):
            logger.info(f"  {i}. {p['title'][:70]}...")
        return

    # ── 2. TÉLÉCHARGEMENT PDFs ────────────────────────────────────
    logger.info("\n[ÉTAPE 2/4] Téléchargement des PDFs open-access...")
    downloader = PDFDownloader()
    downloaded = downloader.download_all(papers)
    logger.info(f"  → {len(downloaded)} PDFs téléchargés")

    if not downloaded:
        logger.warning("  Aucun PDF téléchargé. Vérifiez votre connexion.")
        sys.exit(1)

    # ── 3. EXTRACTION DES FIGURES ─────────────────────────────────
    logger.info("\n[ÉTAPE 3/4] Extraction et classification des figures...")
    extractor = FigureExtractor()
    classifier = DiagramClassifier(use_ai=not args.no_classify)

    all_diagrams = []
    for pdf_info in downloaded:
        figures = extractor.extract_figures(pdf_info)
        logger.info(
            f"  {pdf_info['paper']['title'][:50]}... → {len(figures)} figure(s)"
        )
        for fig in figures:
            score, is_diagram = classifier.classify(fig["image_path"], fig["caption"])
            if is_diagram:
                fig["confidence"] = score
                fig["paper"] = pdf_info["paper"]
                all_diagrams.append(fig)

    logger.info(f"  → {len(all_diagrams)} schémas de processus identifiés")

    if not all_diagrams:
        logger.warning("  Aucun schéma trouvé. Essayez --no-classify.")
        sys.exit(0)

    # ── 4. GÉNÉRATION DU DOCUMENT WORD ───────────────────────────
    logger.info("\n[ÉTAPE 4/4] Génération du document Word...")
    builder = WordDocumentBuilder(
        output_path=args.output,
        existing_path=args.existing
    )
    builder.build(all_diagrams)
    logger.info(f"\n✓ Document créé : {args.output}")
    logger.info(f"  {len(all_diagrams)} schémas insérés")

    # ── 5. MISE À JOUR EXCEL (optionnel) ──────────────────────────
    if args.excel:
        logger.info(f"\n[BONUS] Mise à jour de la base Excel...")
        try:
            update_excel_from_diagrams(args.excel, all_diagrams)
        except Exception as e:
            logger.error(f"  Erreur Excel : {e}")


if __name__ == "__main__":
    main()
