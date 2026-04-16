from dotenv import load_dotenv
import os
from pathlib import Path
from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
key = os.getenv("OPENAI_API_KEY")

nom_fichier_sans_extension = "data-science-and-mlops-landscape-in-industry_clean"
nom_fichier = nom_fichier_sans_extension + ".txt"
input_file = PROJECT_ROOT / "outputs" / nom_fichier
with open(input_file, "r", encoding="utf-8") as f:
    file_content = f.read()

client = OpenAI(api_key=key)

prompt = '''
You are an AI specialized in analyzing Jupyter Notebooks and generating valid BPMN 2.0 diagrams.

INPUT:
You will receive a .txt file containing the full textual content of a Jupyter Notebook, including code and markdown.

TASK:
- Analyze the notebook and identify all meaningful activities and process steps.
- Assign each activity to exactly one role lane based on responsibility.
- Build a single linear process flow showing the actual order of activities.
- Do not create parallel branches, gateways, or multiple start/end events.
- Infer only missing steps necessary to make the process coherent.

Examples:
- Data loading
- Data cleaning
- Feature engineering
- Model training
- Model evaluation
- Visualization
- Deployment steps
- API creation
- Experiment tracking
- Saving models

Organize the extracted processes into the following BPMN lanes:

- Data Engineer
- Model Engineer
- Software Engineer
- Plan
- Ops Engineer

Each lane must contain only <bpmn:flowNodeRef> references and no actual task elements.
Do not include empty lanes.

Build a SINGLE linear PROCESS FLOW showing the logical order of activities.

Infer missing steps if necessary.



OUTPUT FORMAT:

Return ONLY valid BPMN 2.0 XML.

Do NOT add explanations, comments, or markdown formatting.
Do NOT include any text before or after the XML.
If the model wraps the response in markdown code fences, remove them.
Output must begin exactly with:
<?xml version="1.0" encoding="UTF-8"?>



XML STRUCTURE (STRICT):

1. ROOT ELEMENT:

<bpmn:definitions 
  xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
  id="Definitions_1">



2. PROCESS SECTION:

<bpmn:process id="Process_1" isExecutable="false">

    <bpmn:laneSet id="LaneSet_1">
        Lanes here
    </bpmn:laneSet>

    Start event, tasks, end event here

    Sequence flows here

</bpmn:process>



3. LANES RULES:

Each lane MUST follow this structure:

<bpmn:lane id="Lane_X" name="Lane Name">
    <bpmn:flowNodeRef>StartEvent_1</bpmn:flowNodeRef>
    <bpmn:flowNodeRef>Task_1</bpmn:flowNodeRef>
</bpmn:lane>

IMPORTANT:
- Lanes contain ONLY flowNodeRef (no tasks inside)
- flowNodeRef must reference existing elements



4. FLOW ELEMENTS:

Include:

<bpmn:startEvent id="StartEvent_1"/>

<bpmn:task id="Task_1" name="Task name"/>

<bpmn:endEvent id="EndEvent_1"/>

Sequence flows:

<bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_1"/>



5. CONNECTIVITY CONSTRAINTS (MANDATORY):

- The process MUST be a SINGLE continuous chain of activities

- The sequence MUST strictly follow:

  StartEvent_1 → Task_1 → Task_2 → Task_3 → ... → Task_N → EndEvent_1

- NO parallel flows
- NO branching
- NO disconnected tasks
- NO multiple start or end points

FLOW RULES:

- StartEvent_1 must have EXACTLY ONE outgoing sequenceFlow
- EndEvent_1 must have EXACTLY ONE incoming sequenceFlow

- Each Task must have:
  - exactly ONE incoming flow (except Task_1)
  - exactly ONE outgoing flow (except last task)

- Total number of sequenceFlow MUST equal number_of_tasks + 1



6. ID CONSISTENCY RULE:

- sourceRef and targetRef MUST exactly match existing element IDs
- No missing or mismatched IDs allowed



7. DIAGRAM SECTION (VERY IMPORTANT):

The diagram MUST be OUTSIDE the process.

Correct structure:

</bpmn:process>

<bpmndi:BPMNDiagram id="Diagram_1">
    <bpmndi:BPMNPlane id="Plane_1" bpmnElement="Process_1">

        Shapes here
        Edges here

    </bpmndi:BPMNPlane>
</bpmndi:BPMNDiagram>



8. SHAPES (MANDATORY):

Create one BPMNShape for EACH element:

- StartEvent
- Every Task
- EndEvent
- Every Lane

Example:

<bpmndi:BPMNShape id="Shape_Task_1" bpmnElement="Task_1">
    <dc:Bounds x="300" y="100" width="120" height="80"/>
</bpmndi:BPMNShape>



9. EDGES (MANDATORY):

Each sequenceFlow MUST have a BPMNEdge:

<bpmndi:BPMNEdge id="Edge_Flow_1" bpmnElement="Flow_1">
    <di:waypoint x="200" y="120"/>
    <di:waypoint x="300" y="120"/>
</bpmndi:BPMNEdge>



10. EDGE AND VISUAL CONNECTION RULES (MANDATORY):

- EACH sequenceFlow MUST have EXACTLY ONE matching BPMNEdge
- The BPMNEdge MUST reference the SAME flow ID

- Waypoints MUST connect elements from left to right
- X coordinates MUST strictly increase across the process

Example layout:

StartEvent_1 → x=150  
Task_1 → x=300  
Task_2 → x=500  
EndEvent_1 → x=700

- Waypoints MUST visually connect source and target elements



11. LAYOUT RULES:

- Lanes:
  width=1400, height=120, stacked vertically

- Tasks:
  width=120, height=80, aligned horizontally

- StartEvent:
  width=36, height=36

- EndEvent:
  width=36, height=36



12. STRICT VALIDATION RULES:

- ALL tags must be properly opened and closed
- NO overlapping or misplaced closing tags
- BPMNDiagram MUST NOT be inside process
- NO missing closing tags
- NO duplicate IDs
- IDs must be alphanumeric with underscores ONLY
- EVERY flowNodeRef must match an existing element
- EVERY sequenceFlow must have a BPMNEdge
- OMIT empty lanes



13. FINAL STRUCTURE:

<bpmn:definitions>
    <bpmn:process>
        ...
    </bpmn:process>

    <bpmndi:BPMNDiagram>
        ...
    </bpmndi:BPMNDiagram>
</bpmn:definitions>



Return ONLY valid XML.
'''
messages = [
    {"role": "system", "content": "You are an AI specialized in analyzing Jupyter Notebooks."},
    {"role": "user", "content": prompt + "\n\n" + file_content}
]

output_file = PROJECT_ROOT / "processes_bpmn" / f"{nom_fichier_sans_extension}_bpmn.bpmn"
output_file.parent.mkdir(exist_ok=True)
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8") as f:
        bpmn_code = f.read()
else:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        seed=42
    )
    bpmn_code = response.choices[0].message.content

    # Strip markdown code fences if the model wraps output anyway
    if bpmn_code.strip().startswith("```"):
        lines = bpmn_code.strip().splitlines()
        bpmn_code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    print(bpmn_code)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(bpmn_code)

print(f"BPMN diagram saved to {output_file}")