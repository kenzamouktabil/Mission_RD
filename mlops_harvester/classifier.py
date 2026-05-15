"""
Classification des figures : schéma de processus ML ou non ?

Deux modes :
  1. Mode IA (défaut si ANTHROPIC_API_KEY est défini)  : envoie l'image à
     Claude qui répond par un JSON {is_diagram, score, reason}.
  2. Mode heuristique (fallback)                        : compte les mots-clés
     dans la légende et le nom de fichier.
"""

import base64
import os
from pathlib import Path

from config import CONFIG
from utils import logger


class DiagramClassifier:
    """Classifie une figure comme schéma de processus ML ou non."""

    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai and self._has_api_key()
        self.threshold = CONFIG["classifier"]["ai_threshold"]
        self.heuristic_min = CONFIG["classifier"]["heuristic_threshold"]
        self.caption_kws = [kw.lower() for kw in CONFIG["extraction"]["caption_keywords"]]

        if self.use_ai:
            import anthropic
            self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            logger.info("  Classificateur : mode IA (Claude Vision)")
        else:
            logger.info("  Classificateur : mode heuristique (mots-clés)")

    # ─────────────────────────────────────────────────────────────────
    #  PUBLIC
    # ─────────────────────────────────────────────────────────────────

    def classify(self, image_path: Path, caption: str) -> tuple[float, bool]:
        """
        Retourne (score: float, is_diagram: bool).
        score ∈ [0, 1]  ;  is_diagram = score >= threshold
        """
        if self.use_ai:
            return self._classify_ai(image_path, caption)
        else:
            return self._classify_heuristic(caption)

    # ─────────────────────────────────────────────────────────────────
    #  IA
    # ─────────────────────────────────────────────────────────────────

    def _classify_ai(self, image_path: Path, caption: str) -> tuple[float, bool]:
        """Appelle Claude Vision pour analyser l'image."""
        try:
            img_bytes = image_path.read_bytes()
            b64 = base64.standard_b64encode(img_bytes).decode("utf-8")
            ext = image_path.suffix.lstrip(".")
            media_type = f"image/{'jpeg' if ext in ('jpg','jpeg') else ext}"

            prompt = f"""You are a scientific figure classifier specializing in Machine Learning papers.

Analyze this figure and determine if it shows a MACHINE LEARNING PROCESS DIAGRAM.
A qualifying diagram contains:
- Boxes/nodes representing steps, phases, or components
- Arrows or flow indicators showing data/process flow
- Labels related to ML concepts: data, features, training, model, pipeline, preprocessing, etc.
- Could be a flowchart, BPMN diagram, architecture diagram, lifecycle diagram, or workflow

Figure caption: "{caption}"

Respond ONLY with a JSON object (no markdown, no explanation):
{{
  "is_process_diagram": true/false,
  "confidence": 0.0-1.0,
  "reason": "brief reason (max 20 words)"
}}"""

            response = self._client.messages.create(
                model=CONFIG["classifier"]["model"],
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }]
            )

            import json
            text = response.content[0].text.strip()
            # Nettoyer les éventuels backticks
            text = text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            score = float(result.get("confidence", 0))
            is_diag = bool(result.get("is_process_diagram", False)) and score >= self.threshold
            return score, is_diag

        except Exception as e:
            logger.warning(f"    Classificateur IA erreur: {e} — fallback heuristique")
            return self._classify_heuristic(caption)

    # ─────────────────────────────────────────────────────────────────
    #  HEURISTIQUE
    # ─────────────────────────────────────────────────────────────────

    def _classify_heuristic(self, caption: str) -> tuple[float, bool]:
        """Compte les mots-clés dans la légende."""
        text = caption.lower()
        hits = sum(1 for kw in self.caption_kws if kw in text)
        score = min(1.0, hits / max(1, self.heuristic_min * 2))
        is_diag = hits >= self.heuristic_min
        return score, is_diag

    # ─────────────────────────────────────────────────────────────────
    #  UTILITAIRE
    # ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _has_api_key() -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
