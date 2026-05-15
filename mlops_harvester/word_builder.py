"""
Construction/mise à jour du document Word.

Pour chaque schéma identifié :
  1. Insère l'image (redimensionnée à image_width_inches)
  2. Insère la légende sous l'image
  3. Ajoute un commentaire Word contenant le BibTeX du papier

Gère le cas d'un document existant (--existing) en ajoutant à la suite.

Dépendance : python-docx  →  pip install python-docx
"""

from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from config import CONFIG
from utils import logger, build_bibtex


class WordDocumentBuilder:

    def __init__(self, output_path: str, existing_path: str | None = None):
        self.output_path = Path(output_path)
        self.cfg = CONFIG["word"]

        if existing_path and Path(existing_path).exists():
            self.doc = Document(existing_path)
            logger.info(f"  Document existant chargé : {existing_path}")
        else:
            self.doc = Document()
            self._setup_styles()

    # ─────────────────────────────────────────────────────────────────
    #  PUBLIC
    # ─────────────────────────────────────────────────────────────────

    def build(self, diagrams: list[dict]) -> None:
        """Insère tous les schémas dans le document."""
        for i, diagram in enumerate(diagrams, 1):
            logger.info(f"  [{i}/{len(diagrams)}] {diagram['caption'][:60]}...")
            self._insert_diagram(diagram)

        self.doc.save(str(self.output_path))
        logger.info(f"  Document sauvegardé : {self.output_path}")

    # ─────────────────────────────────────────────────────────────────
    #  INSERTION D'UN SCHÉMA
    # ─────────────────────────────────────────────────────────────────

    def _insert_diagram(self, diagram: dict) -> None:
        paper     = diagram["paper"]
        img_path  = diagram["image_path"]
        caption   = diagram["caption"]
        page_num  = diagram.get("page_num", "?")

        # ── Image ──────────────────────────────────────────────────
        try:
            p_img = self.doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p_img.add_run()
            run.add_picture(
                str(img_path),
                width=Inches(self.cfg["image_width_inches"])
            )
        except Exception as e:
            logger.warning(f"    Erreur insertion image: {e}")
            return

        # ── Légende ────────────────────────────────────────────────
        # Format : "Fig. X. <caption text> (p<page_num>)"
        caption_text = self._format_caption(caption, page_num)
        p_caption = self.doc.add_paragraph(caption_text)
        p_caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run_cap = p_caption.runs[0] if p_caption.runs else p_caption.add_run(caption_text)
        run_cap.font.size = Pt(9)
        run_cap.font.italic = True

        # ── BibTeX en tant que texte normal (fallback) ─────────────
        # Note: Les commentaires Word natifs ont des problèmes de compatibilité
        # Solution : ajouter le BibTeX en texte normal après la légende
        bibtex = build_bibtex(paper)
        self._add_bibtex_text(bibtex)

        # ── Séparateur ─────────────────────────────────────────────
        if self.cfg["add_separator"]:
            sep = self.doc.add_paragraph()
            sep.add_run("─" * 60)
            sep.runs[0].font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC)

    # ─────────────────────────────────────────────────────────────────
    #  BIBTEX EN TEXTE SIMPLE (Robuste & Compatible)
    # ─────────────────────────────────────────────────────────────────

    def _add_bibtex_text(self, bibtex: str) -> None:
        """
        Ajoute le BibTeX en tant que texte dans un paragraphe gris clair.
        Approche simple et 100% compatible avec toutes les versions Word.
        """
        # Ajouter une ligne vierge
        self.doc.add_paragraph()
        
        # Ajouter le titre "BibTeX:"
        p_header = self.doc.add_paragraph()
        run = p_header.add_run("📌 BibTeX:")
        run.font.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x44, 0x72, 0xC4)
        
        # Ajouter le code BibTeX
        p_bibtex = self.doc.add_paragraph(bibtex)
        p_bibtex.alignment = WD_ALIGN_PARAGRAPH.LEFT
        for run in p_bibtex.runs:
            run.font.name = "Courier New"  # Monospace pour le code
            run.font.size = Pt(8)
        
        # Ajouter une couleur de fond gris très léger
        shading_elm = OxmlElement("w:shd")
        shading_elm.set(qn("w:fill"), "F5F5F5")  # Gris très clair
        p_bibtex._element.get_or_add_pPr().append(shading_elm)

    # ─────────────────────────────────────────────────────────────────
    #  UTILITAIRES
    # ─────────────────────────────────────────────────────────────────

    def _setup_styles(self) -> None:
        """Configure les styles de base du nouveau document."""
        from docx.shared import Pt
        style = self.doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(11)

    @staticmethod
    def _format_caption(caption: str, page_num) -> str:
        """Formate la légende comme dans le document exemple."""
        # Nettoyage basique
        caption = caption.strip().rstrip(".")
        return f"{caption} (p{page_num})"
