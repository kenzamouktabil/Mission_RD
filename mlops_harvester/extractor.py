"""
Extraction des figures depuis les PDFs.

Approche :
  - Pour chaque page, on cherche les blocs de texte qui ressemblent à
    des légendes de figures (« Fig. », « Figure », « Scheme »…)
  - On extrait la région de la page correspondant à la figure
  - On filtre par taille minimale pour exclure les icônes

Dépendance : PyMuPDF  →  pip install PyMuPDF
"""

import re
from pathlib import Path

import fitz   # PyMuPDF

from config import CONFIG
from utils import logger


# ── Patterns de légendes ──────────────────────────────────────────
CAPTION_RE = re.compile(
    r"^(fig(?:ure)?\.?\s*\d+|scheme\s*\d+|algorithm\s*\d+|fig\.\s*\d+)",
    re.IGNORECASE
)


class FigureExtractor:
    """Extrait les figures d'un PDF avec leurs légendes."""

    def __init__(self):
        self.fig_dir = CONFIG["dirs"]["figures"]
        self.fig_dir.mkdir(parents=True, exist_ok=True)
        self.cfg = CONFIG["extraction"]

    # ─────────────────────────────────────────────────────────────────
    #  PUBLIC
    # ─────────────────────────────────────────────────────────────────

    def extract_figures(self, pdf_info: dict) -> list[dict]:
        """
        Retourne une liste de figures :
        [{ image_path, caption, page_num, paper }, ...]
        """
        pdf_path: Path = pdf_info["pdf_path"]
        paper: dict    = pdf_info["paper"]
        figures = []

        try:
            doc = fitz.open(str(pdf_path))
        except Exception as e:
            logger.warning(f"    Erreur ouverture PDF {pdf_path.name}: {e}")
            return []

        slug = pdf_path.stem

        for page_num, page in enumerate(doc, start=1):
            page_figs = self._extract_page_figures(
                page, page_num, slug, paper
            )
            figures.extend(page_figs)

        doc.close()
        return figures

    # ─────────────────────────────────────────────────────────────────
    #  PRIVATE
    # ─────────────────────────────────────────────────────────────────

    def _extract_page_figures(
        self, page: fitz.Page, page_num: int, slug: str, paper: dict
    ) -> list[dict]:
        """Extrait les figures d'une seule page."""
        # Chercher des légendes
        blocks = page.get_text("blocks")  # [(x0,y0,x1,y1, text, bno, type)]
        captions = self._find_captions(blocks)

        figures = []

        if captions:
            # Pour chaque légende, extraire la zone au-dessus
            for caption_block in captions:
                fig = self._extract_figure_above_caption(
                    page, caption_block, page_num, slug, paper
                )
                if fig:
                    figures.append(fig)
        else:
            # Pas de légende trouvée : extraire les images embarquées
            embedded = self._extract_embedded_images(
                page, page_num, slug, paper
            )
            figures.extend(embedded)

        return figures

    def _find_captions(self, blocks: list) -> list[dict]:
        """Repère les blocs de texte qui sont des légendes de figures."""
        captions = []
        for block in blocks:
            if len(block) < 5:
                continue
            x0, y0, x1, y1, text, *_ = block
            text = text.strip()
            if CAPTION_RE.match(text):
                captions.append({
                    "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                    "text": text[:300]
                })
        return captions

    def _extract_figure_above_caption(
        self,
        page: fitz.Page,
        caption: dict,
        page_num: int,
        slug: str,
        paper: dict,
    ) -> dict | None:
        """
        Rend en image la zone juste au-dessus de la légende.
        On prend jusqu'à 300 pt au-dessus de la légende.
        """
        page_h = page.rect.height
        page_w = page.rect.width
        margin = 5

        # Zone figure : du bord gauche/droit de la page, de y_haut à y0 de la légende
        y_bottom = caption["y0"] - margin
        y_top    = max(0, y_bottom - 350)  # 350 pt max de hauteur figure

        clip = fitz.Rect(margin, y_top, page_w - margin, y_bottom)

        if clip.is_empty or clip.width < self.cfg["min_width"] * 0.5:
            return None

        try:
            mat = fitz.Matrix(self.cfg["dpi"] / 72, self.cfg["dpi"] / 72)
            pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
        except (RuntimeError, KeyboardInterrupt, Exception) as e:
            # PyMuPDF peut crash sur certains PDFs complexes — on skip
            return None

        if (pix.width  < self.cfg["min_width"]  or
                pix.height < self.cfg["min_height"]):
            return None

        fname = f"{slug}_p{page_num}_fig.{self.cfg['image_format']}"
        img_path = self.fig_dir / fname
        pix.save(str(img_path))

        return {
            "image_path": img_path,
            "caption":    caption["text"],
            "page_num":   page_num,
            "paper":      paper,
        }

    def _extract_embedded_images(
        self,
        page: fitz.Page,
        page_num: int,
        slug: str,
        paper: dict,
    ) -> list[dict]:
        """Extrait les images embarquées dans la page (xref)."""
        figures = []
        img_list = page.get_images(full=True)

        for img_idx, img_info in enumerate(img_list):
            xref = img_info[0]
            try:
                base_image = page.parent.extract_image(xref)
            except Exception:
                continue

            w = base_image.get("width", 0)
            h = base_image.get("height", 0)

            if (w < self.cfg["min_width"]  or
                    h < self.cfg["min_height"] or
                    w > self.cfg["max_width"]  or
                    h > self.cfg["max_height"]):
                continue

            ext = base_image.get("ext", "png")
            fname = f"{slug}_p{page_num}_img{img_idx}.{ext}"
            img_path = self.fig_dir / fname
            img_path.write_bytes(base_image["image"])

            # Essayer de trouver une légende proche dans la page
            caption = self._find_nearby_caption(page, page_num)

            figures.append({
                "image_path": img_path,
                "caption":    caption,
                "page_num":   page_num,
                "paper":      paper,
            })

        return figures

    @staticmethod
    def _find_nearby_caption(page: fitz.Page, page_num: int) -> str:
        """Cherche n'importe quelle légende dans la page."""
        blocks = page.get_text("blocks")
        for block in blocks:
            if len(block) < 5:
                continue
            text = block[4].strip()
            if CAPTION_RE.match(text):
                return text[:300]
        return f"Figure (page {page_num})"
