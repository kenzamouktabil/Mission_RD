from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv(dotenv_path="../.env")
key = os.getenv("OPENAI_API_KEY")

nom_fichier = "mlflow-end-to-end-ml-models_clean.txt"
input_file = '../outputs/'+nom_fichier
with open(input_file, "r", encoding="utf-8") as f:
    file_content = f.read()

client = OpenAI(api_key=key)

prompt = '''
You are an AI specialized in analyzing Jupyter Notebooks.

INPUT:
You will receive a .txt file containing the full textual content of a Jupyter Notebook (including code cells and markdown cells).

TASK:

Analyze the notebook content.

Identify ALL activities, processes, and tasks performed in the notebook.
Examples:

Data loading

Data cleaning

Feature engineering

Model training

Model evaluation

Visualization

Deployment steps

API creation

Experiment tracking

Saving models

etc.

Organize the extracted processes into the following dimensions:

Data Engineer

Model Engineer

Software Engineer

Plan (project planning, objectives, documentation, experimentation logic)

Ops Engineer (deployment, monitoring, CI/CD, model persistence, etc.)

Build a PROCESS FLOW showing the logical order of the activities.

OUTPUT FORMAT:

Return ONLY Mermaid code.

The diagram must represent:

The different dimensions as subgraphs

The processes inside each subgraph

Directed arrows showing the workflow between processes

Node names must not contain special characters such as parentheses (), slashes /, or any other symbols that are invalid in Mermaid node identifiers. Use plain text or underscores instead.

Do NOT add explanations.

Do NOT add markdown formatting.

Return ONLY valid Mermaid code.

CONSTRAINTS:

If a dimension has no detected activity, omit it.

Infer missing steps if necessary based on context.
'''

messages = [
    {"role": "system", "content": "You are an AI specialized in analyzing Jupyter Notebooks."},
    {"role": "user", "content": prompt + "\n\n" + file_content}
]
response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=messages
)
mermaid_code = response.choices[0].message.content
print(mermaid_code)
output_file = "../processes/"+nom_fichier+"_mermaid"+".mmd"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(mermaid_code)

print(f"Mermaid diagram saved to {output_file}")
