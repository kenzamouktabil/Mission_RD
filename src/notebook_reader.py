import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def read_notebook(ipynb_path: str, max_cell_chars: int = 8000) -> str:
    """
    Lit un fichier .ipynb, retourne un texte structuré
    et sauvegarde le résultat dans /outputs.

    Returns:
        str: nom du fichier généré (sans extension)
    """

    path = Path(ipynb_path)

    if not path.exists():
        raise FileNotFoundError(f"Notebook introuvable : {ipynb_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cells = data.get("cells", [])

    extracted_content = []

    for i, cell in enumerate(cells, start=1):
        cell_type = cell.get("cell_type", "")
        source = "".join(cell.get("source", [])).strip()

        if not source:
            continue

        # Tronquer si trop long
        if len(source) > max_cell_chars:
            source = source[:max_cell_chars] + "\n... [TRUNCATED]"

        if cell_type == "markdown":
            extracted_content.append(
                f"\n### MARKDOWN CELL {i}\n{source}\n"
            )

        elif cell_type == "code":
            extracted_content.append(
                f"\n### CODE CELL {i}\n```python\n{source}\n```\n"
            )

    # --- CREATE OUTPUT (UNE SEULE FOIS) ---
    content = "\n".join(extracted_content)

    nom_notebook = path.stem
    output_path = PROJECT_ROOT / "outputs" / f"{nom_notebook}_clean.txt"

    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Notebook transformé et sauvegardé ✅")
    print(f"Fichier créé : {output_path}")

    return nom_notebook


# Petit test local
if __name__ == "__main__":
    # Racine du projet = dossier parent de src/
    

    nom_notebook = "mlops-how-to-be-rock-of-ml"
    notebook_path = PROJECT_ROOT / "notebooks" / f"{nom_notebook}.ipynb"
    output_path = PROJECT_ROOT / "outputs" / f"{nom_notebook}_clean.txt"

    content = read_notebook(str(notebook_path))

    # Créer le dossier outputs si pas existant
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Notebook transformé et sauvegardé ✅")
    print(f"Fichier créé : {output_path}")