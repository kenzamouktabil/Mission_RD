import json
from pathlib import Path


def read_notebook(ipynb_path: str, max_cell_chars: int = 8000) -> str:
    """
    Lit un fichier .ipynb et retourne un texte structuré
    contenant les cellules markdown et code (sans outputs).
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

    return "\n".join(extracted_content)


# Petit test local
if __name__ == "__main__":
    notebook_path = "notebooks/notebook_1_test.ipynb"
    output_path = "outputs/notebook_1_test_clean.txt"

    content = read_notebook(notebook_path)

    # Créer le dossier outputs si pas existant
    Path("outputs").mkdir(exist_ok=True)

    # Sauvegarder dans un fichier
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("Notebook transformé et sauvegardé ✅")
    print(f"Fichier créé : {output_path}")
