import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Namespaces BPMN ---
NS = {
    "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
    "bpmndi": "http://www.omg.org/spec/BPMN/20100524/DI",
    "dc": "http://www.omg.org/spec/DD/20100524/DC",
    "di": "http://www.omg.org/spec/DD/20100524/DI",
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def parse_mermaid(mermaid_code: str):
    """
    Parse Mermaid flowchart with subgraphs and return:
      - lanes: dict {lane_name: [node_id, ...]}
      - nodes: dict {node_id: display_label}
      - edges: list of (source_id, target_id)
    """
    lanes = {}        # lane_name -> list of node_ids
    nodes = {}        # node_id -> label
    edges = []        # (source, target)

    current_lane = None
    # Regex: node definition like   Ingest_Data_C3["Ingest Data"]   or   Ingest_Data_C3[Ingest Data]
    node_def_re = re.compile(r'(\w+)\s*\[\s*"?([^"\]]+)"?\s*\]')
    # Regex: subgraph header   subgraph Data_Engineer   or   subgraph Data_Engineer["Data Engineer"]
    subgraph_re = re.compile(r'subgraph\s+(\w+)')

    for raw_line in mermaid_code.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("flowchart") or line.startswith("%%"):
            continue

        if line.startswith("subgraph"):
            m = subgraph_re.match(line)
            if m:
                current_lane = m.group(1)
                lanes.setdefault(current_lane, [])
            continue

        if line == "end":
            current_lane = None
            continue

        # Extract any node definitions on the line
        for node_id, label in node_def_re.findall(line):
            if node_id not in nodes:
                nodes[node_id] = label.strip()
                if current_lane:
                    lanes[current_lane].append(node_id)

        # Extract edges:  A --> B --> C  (chained)
        if "-->" in line:
            # Remove bracketed labels so we can split cleanly
            clean = re.sub(r'\[[^\]]*\]', '', line)
            parts = [p.strip() for p in clean.split("-->")]
            parts = [p for p in parts if p and re.match(r'^\w+$', p)]
            for src, tgt in zip(parts, parts[1:]):
                edges.append((src, tgt))

    return lanes, nodes, edges


def build_bpmn(lanes, nodes, edges) -> str:
    """
    Build a valid BPMN 2.0 XML string with:
      - one Process containing a LaneSet + tasks + sequenceFlows
      - one BPMNDiagram with shapes and edges (auto-layout left-to-right)
    """
    # --- Determine linear task order from edges ---
    ordered = []
    seen = set()
    incoming = {tgt for _, tgt in edges}
    starts = [nid for nid in nodes if nid not in incoming]
    if not starts:
        starts = [next(iter(nodes))] if nodes else []

    stack = list(starts)
    while stack:
        n = stack.pop(0)
        if n in seen:
            continue
        seen.add(n)
        ordered.append(n)
        for s, t in edges:
            if s == n and t not in seen:
                stack.append(t)
    # Append any disconnected nodes
    for n in nodes:
        if n not in seen:
            ordered.append(n)

    # --- Create IDs ---
    start_id = "StartEvent_1"
    end_id = "EndEvent_1"

    # --- Build sequence flows: Start -> first task -> ... -> last task -> End ---
    flows = []
    if ordered:
        flows.append((start_id, ordered[0]))
        for a, b in zip(ordered, ordered[1:]):
            flows.append((a, b))
        flows.append((ordered[-1], end_id))

    # --- Layout constants ---
    TASK_W, TASK_H = 120, 80
    EVENT_SIZE = 36
    LANE_H = 160
    LANE_W = 200 + (len(ordered) + 1) * 160 + 80
    X_START = 220
    Y_OFFSET_IN_LANE = (LANE_H - TASK_H) // 2

    # --- Assign x positions (linear left to right) ---
    x_positions = {start_id: 170}
    for i, nid in enumerate(ordered):
        x_positions[nid] = X_START + i * 160
    x_positions[end_id] = X_START + len(ordered) * 160 + 40

    # --- Assign lane of each node ---
    node_lane = {}
    for lane, node_list in lanes.items():
        for nid in node_list:
            node_lane[nid] = lane
    # Start and End go in the first lane (or a dummy one if no lanes)
    lane_names = list(lanes.keys()) if lanes else ["Default"]
    node_lane[start_id] = lane_names[0]
    node_lane[end_id] = lane_names[-1]

    # --- Assign y per lane ---
    lane_y = {name: 80 + i * LANE_H for i, name in enumerate(lane_names)}

    # --- Build XML ---
    bpmn = "http://www.omg.org/spec/BPMN/20100524/MODEL"
    bpmndi = "http://www.omg.org/spec/BPMN/20100524/DI"
    dc = "http://www.omg.org/spec/DD/20100524/DC"
    di = "http://www.omg.org/spec/DD/20100524/DI"

    definitions = ET.Element(f"{{{bpmn}}}definitions", {
        "id": "Definitions_1",
        "targetNamespace": "http://bpmn.io/schema/bpmn",
    })

    process = ET.SubElement(definitions, f"{{{bpmn}}}process", {
        "id": "Process_1",
        "isExecutable": "false",
    })

    # LaneSet
    lane_set = ET.SubElement(process, f"{{{bpmn}}}laneSet", {"id": "LaneSet_1"})
    for i, lane_name in enumerate(lane_names):
        lane_el = ET.SubElement(lane_set, f"{{{bpmn}}}lane", {
            "id": f"Lane_{i+1}",
            "name": lane_name.replace("_", " "),
        })
        refs_for_lane = [nid for nid in (lanes.get(lane_name) or []) if nid in nodes]
        if i == 0:
            refs_for_lane = [start_id] + refs_for_lane
        if i == len(lane_names) - 1:
            refs_for_lane = refs_for_lane + [end_id]
        for nid in refs_for_lane:
            ref = ET.SubElement(lane_el, f"{{{bpmn}}}flowNodeRef")
            ref.text = nid

    # Start/End events
    ET.SubElement(process, f"{{{bpmn}}}startEvent", {"id": start_id})
    ET.SubElement(process, f"{{{bpmn}}}endEvent", {"id": end_id})

    # Tasks
    for nid in ordered:
        ET.SubElement(process, f"{{{bpmn}}}task", {
            "id": nid,
            "name": nodes[nid],
        })

    # Sequence flows
    for i, (src, tgt) in enumerate(flows, 1):
        ET.SubElement(process, f"{{{bpmn}}}sequenceFlow", {
            "id": f"Flow_{i}",
            "sourceRef": src,
            "targetRef": tgt,
        })

    # --- Diagram ---
    diagram = ET.SubElement(definitions, f"{{{bpmndi}}}BPMNDiagram", {"id": "Diagram_1"})
    plane = ET.SubElement(diagram, f"{{{bpmndi}}}BPMNPlane", {
        "id": "Plane_1",
        "bpmnElement": "Process_1",
    })

    # Lane shapes
    for i, lane_name in enumerate(lane_names):
        shape = ET.SubElement(plane, f"{{{bpmndi}}}BPMNShape", {
            "id": f"Lane_{i+1}_di",
            "bpmnElement": f"Lane_{i+1}",
            "isHorizontal": "true",
        })
        ET.SubElement(shape, f"{{{dc}}}Bounds", {
            "x": "160", "y": str(lane_y[lane_name]),
            "width": str(LANE_W), "height": str(LANE_H),
        })

    # Start event shape
    start_shape = ET.SubElement(plane, f"{{{bpmndi}}}BPMNShape", {
        "id": f"{start_id}_di", "bpmnElement": start_id,
    })
    ET.SubElement(start_shape, f"{{{dc}}}Bounds", {
        "x": str(x_positions[start_id]),
        "y": str(lane_y[node_lane[start_id]] + (LANE_H - EVENT_SIZE) // 2),
        "width": str(EVENT_SIZE), "height": str(EVENT_SIZE),
    })

    # Task shapes
    for nid in ordered:
        shape = ET.SubElement(plane, f"{{{bpmndi}}}BPMNShape", {
            "id": f"{nid}_di", "bpmnElement": nid,
        })
        ET.SubElement(shape, f"{{{dc}}}Bounds", {
            "x": str(x_positions[nid]),
            "y": str(lane_y[node_lane[nid]] + Y_OFFSET_IN_LANE),
            "width": str(TASK_W), "height": str(TASK_H),
        })

    # End event shape
    end_shape = ET.SubElement(plane, f"{{{bpmndi}}}BPMNShape", {
        "id": f"{end_id}_di", "bpmnElement": end_id,
    })
    ET.SubElement(end_shape, f"{{{dc}}}Bounds", {
        "x": str(x_positions[end_id]),
        "y": str(lane_y[node_lane[end_id]] + (LANE_H - EVENT_SIZE) // 2),
        "width": str(EVENT_SIZE), "height": str(EVENT_SIZE),
    })

    # Edges
    def center_of(nid):
        x = x_positions[nid]
        y = lane_y[node_lane[nid]] + LANE_H // 2
        if nid in (start_id, end_id):
            return x + EVENT_SIZE // 2, y
        return x + TASK_W // 2, y

    for i, (src, tgt) in enumerate(flows, 1):
        edge = ET.SubElement(plane, f"{{{bpmndi}}}BPMNEdge", {
            "id": f"Flow_{i}_di", "bpmnElement": f"Flow_{i}",
        })
        sx, sy = center_of(src)
        tx, ty = center_of(tgt)
        # exit right side of source, enter left side of target
        if src == start_id:
            sx = x_positions[src] + EVENT_SIZE
        else:
            sx = x_positions[src] + TASK_W
        if tgt == end_id:
            tx = x_positions[tgt]
        else:
            tx = x_positions[tgt]
        ET.SubElement(edge, f"{{{di}}}waypoint", {"x": str(sx), "y": str(sy)})
        ET.SubElement(edge, f"{{{di}}}waypoint", {"x": str(tx), "y": str(ty)})

    # Pretty print
    ET.indent(definitions, space="  ")
    xml_str = ET.tostring(definitions, encoding="unicode", xml_declaration=True)
    return xml_str


def main():
    nom_fichier = sys.argv[1] if len(sys.argv) > 1 else "mlops_clean.txt"
    mermaid_file = PROJECT_ROOT / "processes_mermaid" / f"{nom_fichier}_mermaid.mmd"
    bpmn_file = PROJECT_ROOT / "processes_bpmn" / f"{nom_fichier}_bpmn.bpmn"
    bpmn_file.parent.mkdir(exist_ok=True)

    mermaid_code = mermaid_file.read_text(encoding="utf-8")
    lanes, nodes, edges = parse_mermaid(mermaid_code)

    print(f"Parsed: {len(lanes)} lanes, {len(nodes)} nodes, {len(edges)} edges")
    for lane, node_list in lanes.items():
        print(f"  {lane}: {node_list}")

    xml = build_bpmn(lanes, nodes, edges)
    bpmn_file.write_text(xml, encoding="utf-8")
    print(f"\nBPMN saved to: {bpmn_file}")


if __name__ == "__main__":
    main()