import streamlit as st
from pathlib import Path
import os
from dotenv import load_dotenv
from openai import OpenAI

from notebook_reader import read_notebook
from mermaid_to_bpmn import parse_mermaid, build_bpmn

# --- Setup ---
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- Prompt ---
from prompts import generate_mermaid_from_file



# --- UI ---
st.set_page_config(page_title="MLOps Analyzer", layout="wide")

st.title("🚀 MLOps Notebook Analyzer")
st.markdown("Analyse automatiquement un notebook et génère un pipeline **Mermaid + BPMN**")

# Sidebar
st.sidebar.header("⚙️ Configuration")
max_chars = st.sidebar.slider("Max caractères par cellule", 1000, 20000, 8000)

# Upload
uploaded_file = st.file_uploader("📂 Upload ton notebook (.ipynb)", type=["ipynb"])

if uploaded_file:
    notebook_name = uploaded_file.name.replace(".ipynb", "")

    # Sauvegarde temporaire
    notebook_path = PROJECT_ROOT / "notebooks" / uploaded_file.name
    notebook_path.parent.mkdir(exist_ok=True)

    with open(notebook_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success("✅ Notebook uploadé")

    if st.button("🚀 Lancer l'analyse"):

        progress = st.progress(0)
        status = st.empty()

        # --- Step 1 ---
        status.text("📘 Lecture du notebook...")
        clean_file = read_notebook(str(notebook_path), max_chars)
        progress.progress(30)

        # --- Step 2 ---
        status.text("🧠 Génération du diagramme Mermaid...")
        mermaid_code = generate_mermaid_from_file(Path(clean_file).stem + "_clean.txt")
        progress.progress(70)

        # --- Step 3 ---
        status.text("🔄 Conversion en BPMN...")
        lanes, nodes, edges = parse_mermaid(mermaid_code)
        bpmn_xml = build_bpmn(lanes, nodes, edges)
        progress.progress(100)

        status.text("✅ Terminé !")

        # --- Layout résultats ---
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 Mermaid Diagram")
            st.code(mermaid_code, language="mermaid")

            st.download_button(
                "⬇️ Télécharger Mermaid",
                mermaid_code,
                file_name=f"{notebook_name}.mmd"
            )

        with col2:
            st.subheader("📄 BPMN XML")
            st.code(bpmn_xml, language="xml")

            st.download_button(
                "⬇️ Télécharger BPMN",
                bpmn_xml,
                file_name=f"{notebook_name}.bpmn"
            )

        # Bonus debug
        with st.expander("🔍 Debug infos"):
            st.write("Lanes:", lanes)
            st.write("Nodes:", nodes)
            st.write("Edges:", edges)