from dotenv import load_dotenv
import os
from pathlib import Path
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
key = os.getenv("OPENAI_API_KEY")

nom_fichier = "notebook_2_iris_classification_clean.txt"
input_file = PROJECT_ROOT / "outputs" / nom_fichier
with open(input_file, "r", encoding="utf-8") as f:
    file_content = f.read()
client = OpenAI(api_key=key)
prompt = '''
You are an AI specialized in analyzing Jupyter Notebooks and extracting their process flow, ALIGNED with the SkeltyMLOps reference architecture (Daoud et al., ECAI 2025 / SEAMS 2026).

INPUT:
A .txt file containing the full content of a Jupyter Notebook (code and markdown cells, numbered "CELL 1", "CELL 2", ...).

TASK:
Extract ONLY the activities actually performed in the notebook and map them to the 5 MLOps dimensions defined in SkeltyMLOps. Use the canonical activity names below whenever they apply.

CANONICAL ACTIVITIES PER LANE (SkeltyMLOps taxonomy):

Plan (Product Owner):
  Conceptualize Project, Define Requirements, Formulate ML Problem,
  Analyze Data Sources, Design Architecture, Plan Project, Initialize Repositories

Data Engineer:
  Collect Data, Ingest Data, Preprocess Data, Validate Data,
  Engineer Features, Label Data, Analyze Data, Manage Data

Model Engineer:
  Run Experiments, Design Model, Develop Model, Train Model, Tune Model,
  Validate Model, Evaluate and Test Model, Optimize Model, Register Model

Software Engineer:
  Develop Code, Build Components, Package Artifacts, Test Solution, Release Solution

Ops Engineer:
  Configure CI_CD, Manage Infrastructure, Execute Pipelines,
  Deploy to Testing, Deploy to Production, Serve Inference,
  Monitor Performance, Trigger Retraining, Operate and Maintain

STRICT RULES:

1. EVIDENCE-BASED EXTRACTION
   Every activity you list MUST correspond to at least one concrete cell (code or markdown) in the notebook. You must be able to justify it by pointing to a cell number.

2. USE CANONICAL NAMES
   Prefer the canonical activity names above over free-form names. Examples of mapping:
   - loader.load() / TextLoader / read_csv  -> Ingest Data
   - !unzip dataset.zip                      -> Ingest Data
   - RecursiveCharacterTextSplitter / chunking -> Preprocess Data
   - train_test_split / scaling / cleaning   -> Preprocess Data
   - HuggingFaceBgeEmbeddings / embedding generation -> Engineer Features
   - model.fit() / trainer.train()           -> Train Model
   - Chroma.from_documents / vectordb.persist() -> Register Model
   - ragas.evaluate / sklearn metrics        -> Evaluate and Test Model
   - retriever.get_relevant_documents / model.predict -> Serve Inference
   If no canonical name fits, you may create a new one, but keep it short and start with a verb.

3. NO HALLUCINATION
   Do NOT invent activities that are not directly supported by a cell. In particular:
   - Do NOT add "Define Requirements", "Conceptualize Project", "Design Architecture" unless the notebook contains explicit markdown stating project goals, requirements, or architectural decisions. Code comments or section titles like "## Import Libraries" DO NOT count.
   - Do NOT add "Manage Infrastructure", "Configure CI_CD", "Provision Environment" unless the notebook contains explicit infrastructure or CI/CD code. A pip install or a {"device": "cuda"} dict does NOT count.
   - Do NOT assume the notebook follows a standard training pipeline. Some notebooks do RAG, inference, EDA, or evaluation only.
   - Do NOT add "Develop Code" for library imports or utility function definitions. "Develop Code" refers to writing software components (APIs, services, reusable modules), not import statements or inline helpers.
   - Do NOT add "Analyze Data" for simple variable inspection (e.g., a cell with just `df` or `dataset`). "Analyze Data" requires explicit exploratory analysis: statistical summaries (describe, info), distribution checks, or visualizations (plots, histograms).
   - Do NOT add "Formulate ML Problem" for a notebook title or a one-line description. "Formulate ML Problem" requires explicit problem framing: defined input/output, success criteria, business constraints, or formal problem statement.
4. EMPTY LANES
   If a lane has no activity supported by the notebook, OMIT it entirely from the diagram. It is perfectly fine to produce a diagram with only 2 or 3 lanes. Do NOT invent activities to fill a lane.

5. PROCESS FLOW
   Build a single linear flow that follows the actual execution order of the notebook (based on cell numbering). Use directed arrows between activities.

6. UNIQUE NODE IDENTIFIERS
   Each node in the Mermaid diagram must have a UNIQUE identifier. If two different cells map to the same canonical activity (e.g., unzipping a file in CELL 3 and loading documents in CELL 5 both map to "Ingest Data"), give them distinct IDs by appending the cell number as a suffix: Ingest_Data_C3, Ingest_Data_C5. The display label can stay the same, but the identifier must differ.

7. LABEL DATA VS EVALUATION DATASET
   "Label Data" means annotating TRAINING data with ground-truth labels (e.g., manually tagging images, assigning classes to training samples for supervised learning). Preparing a list of questions and expected answers for MODEL EVALUATION is NOT "Label Data" — it is part of "Evaluate and Test Model" (building an evaluation dataset). Do NOT map evaluation question sets, ground-truth answer lists, or RAGAS/benchmark datasets to "Label Data".

OUTPUT FORMAT:

Return ONLY valid Mermaid code: a flowchart with one subgraph per non-empty lane.

- Node identifiers must be plain alphanumeric with underscores. No parentheses, slashes, quotes, ampersands, or special characters. Use "CI_CD" not "CI/CD", "Evaluate_and_Test_Model" not "Evaluate & Test Model".
- Do NOT add any explanation, comment, or markdown fences.
- Return ONLY the Mermaid code, nothing else.
'''


messages = [
    {"role": "system", "content": "You are an AI specialized in analyzing Jupyter Notebooks."},
    {"role": "user", "content": prompt + "\n\n" + file_content}
]
output_file = PROJECT_ROOT / "processes_mermaid" / f"{nom_fichier}_mermaid.mmd"
output_file.parent.mkdir(exist_ok=True)
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8") as f:
        mermaid_code = f.read()
else :
    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=messages,
        seed = 42
    )
    mermaid_code = response.choices[0].message.content
    print(mermaid_code)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(mermaid_code)

print(f"Mermaid diagram saved to {output_file}")
