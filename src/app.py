import streamlit as st
from pathlib import Path
import os
import base64
from dotenv import load_dotenv
import streamlit.components.v1 as components
from streamlit_mermaid import st_mermaid

from notebook_reader import read_notebook
from mermaid_to_bpmn import parse_mermaid, build_bpmn
from prompts import generate_mermaid_from_file, generate_mermaid_from_image

# --- Setup ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

def render_bpmn(bpmn_xml: str, height: int = 500):
    encoded = base64.b64encode(bpmn_xml.encode()).decode()
    html = f"""
    <link rel="stylesheet" href="https://unpkg.com/bpmn-js@17.11.1/dist/assets/diagram-js.css">
    <link rel="stylesheet" href="https://unpkg.com/bpmn-js@17.11.1/dist/assets/bpmn-js.css">
    <link rel="stylesheet" href="https://unpkg.com/bpmn-js@17.11.1/dist/assets/bpmn-font/css/bpmn-embedded.css">
    <div id="canvas" style="height:{height}px; border:1px solid #ccc; background:white;"></div>
    <script src="https://unpkg.com/bpmn-js@17.11.1/dist/bpmn-viewer.production.min.js"></script>
    <script>
      var viewer = new BpmnJS({{ container: '#canvas' }});
      var xml = atob("{encoded}");
      viewer.importXML(xml).then(function(result) {{
        viewer.get('canvas').zoom('fit-viewport');
      }}).catch(function(err) {{
        document.getElementById('canvas').innerHTML = '<p style="color:red;">Erreur: ' + err.message + '</p>';
      }});
    </script>
    """
    components.html(html, height=height + 20)


def show_results(mermaid_code, bpmn_xml, file_name):
    st.subheader("Diagramme Mermaid")
    st_mermaid(mermaid_code, height=500)

    st.subheader("Diagramme BPMN")
    task_count = bpmn_xml.count("<bpmn:task")
    if task_count > 0:
        render_bpmn(bpmn_xml, height=400)
    else:
        st.warning("Le BPMN semble vide")

    st.subheader("Telecharger les fichiers")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Telecharger Mermaid (.mmd)", mermaid_code, file_name=f"{file_name}.mmd")
    with col2:
        st.download_button("Telecharger BPMN (.bpmn)", bpmn_xml, file_name=f"{file_name}.bpmn")

    with st.expander("Code Mermaid brut"):
        st.code(mermaid_code, language="text")
    with st.expander("Code BPMN XML brut"):
        st.code(bpmn_xml, language="xml")


def save_bpmn(bpmn_xml: str, file_name: str):
    bpmn_dir = PROJECT_ROOT / "processes_bpmn"
    bpmn_dir.mkdir(exist_ok=True)
    bpmn_path = bpmn_dir / f"{file_name}.bpmn"
    bpmn_path.write_text(bpmn_xml, encoding="utf-8")
    print(f"BPMN saved to {bpmn_path}")


# --- UI ---
st.set_page_config(page_title="MLOps Analyzer", layout="wide")
st.title("MLOps Notebook Analyzer")
st.markdown("Analyse automatiquement un notebook ou une image de processus et genere un pipeline **Mermaid + BPMN**")

st.sidebar.header("Configuration")
max_chars = st.sidebar.slider("Max caracteres par cellule", 1000, 20000, 8000)

tab1, tab2 = st.tabs(["Notebook", "Image de processus"])

# =============================================
# TAB 1 : NOTEBOOK
# =============================================
with tab1:
    st.header("Analyser un notebook Jupyter")
    uploaded_notebook = st.file_uploader(
        "Upload ton notebook (.ipynb)",
        type=["ipynb"],
        key="notebook_uploader",
    )

    if uploaded_notebook:
        notebook_name = uploaded_notebook.name.replace(".ipynb", "")
        notebook_path = PROJECT_ROOT / "notebooks" / uploaded_notebook.name
        notebook_path.parent.mkdir(exist_ok=True)

        with open(notebook_path, "wb") as f:
            f.write(uploaded_notebook.getbuffer())

        st.success("Notebook uploade : " + uploaded_notebook.name)

        if st.button("Lancer l analyse", key="btn_notebook"):
            progress = st.progress(0)
            status = st.empty()

            status.text("Lecture du notebook...")
            nom_notebook = read_notebook(str(notebook_path), max_chars)
            progress.progress(30)

            status.text("Generation du diagramme Mermaid...")
            nom_fichier = f"{nom_notebook}_clean.txt"
            mermaid_code = generate_mermaid_from_file(nom_fichier)
            progress.progress(70)

            status.text("Conversion en BPMN...")
            lanes, nodes, edges = parse_mermaid(mermaid_code)
            bpmn_xml = build_bpmn(lanes, nodes, edges)
            progress.progress(100)
            status.text("Termine !")

            save_bpmn(bpmn_xml, notebook_name)

            st.session_state["notebook_mermaid"] = mermaid_code
            st.session_state["notebook_bpmn"] = bpmn_xml
            st.session_state["notebook_name"] = notebook_name

        if "notebook_mermaid" in st.session_state:
            show_results(
                st.session_state["notebook_mermaid"],
                st.session_state["notebook_bpmn"],
                st.session_state["notebook_name"],
            )

# =============================================
# TAB 2 : IMAGE
# =============================================
with tab2:
    st.header("Analyser une image de processus MLOps")
    st.markdown("Upload un screenshot d un diagramme de processus (article, documentation, etc.)")

    uploaded_image = st.file_uploader(
        "Upload une image (.png, .jpg, .jpeg, .webp)",
        type=["png", "jpg", "jpeg", "webp"],
        key="image_uploader",
    )

    if uploaded_image:
        image_name = uploaded_image.name.rsplit(".", 1)[0]

        images_dir = PROJECT_ROOT / "images"
        images_dir.mkdir(exist_ok=True)
        image_path = images_dir / uploaded_image.name

        with open(image_path, "wb") as f:
            f.write(uploaded_image.getbuffer())

        st.image(str(image_path), caption=uploaded_image.name, use_container_width=True)

        if st.button("Extraire le processus", key="btn_image"):
            progress = st.progress(0)
            status = st.empty()

            status.text("Analyse de l image via GPT Vision...")
            mermaid_code = generate_mermaid_from_image(str(image_path), image_name)
            progress.progress(60)

            status.text("Conversion en BPMN...")
            lanes, nodes, edges = parse_mermaid(mermaid_code)
            bpmn_xml = build_bpmn(lanes, nodes, edges)
            progress.progress(100)
            status.text("Termine !")

            save_bpmn(bpmn_xml, image_name)

            st.session_state["image_mermaid"] = mermaid_code
            st.session_state["image_bpmn"] = bpmn_xml
            st.session_state["image_name"] = image_name

        if "image_mermaid" in st.session_state:
            show_results(
                st.session_state["image_mermaid"],
                st.session_state["image_bpmn"],
                st.session_state["image_name"],
            )