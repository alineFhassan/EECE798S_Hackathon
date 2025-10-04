# graph_tools.py
from nx_graph_store import find_nodes, neighbors_of, skill_overlap, load_gpickle
import json
import os

GRAPH_PATH = r"C:\Users\aline\Desktop\hackathon\graph.gpickle"

# Initialize KG as None, will be set when graph is created
KG = None

def _ensure_kg_loaded():
    """Ensure KG is loaded, load from file if not already loaded."""
    global KG
    if KG is None:
        if os.path.exists(GRAPH_PATH):
            KG = load_gpickle(GRAPH_PATH)
        else:
            # Return empty results if no graph exists yet
            return False
    return True

def set_KG(G):
    global KG
    KG = G

def tool_find_nodes(type_: str = None, label_contains: str = None) -> str:
    """Find nodes in the graph. Can handle both correct parameters and agent's string format."""
    if not _ensure_kg_loaded():
        return json.dumps([], indent=2)
    
    # Handle the case where agent passes a single string like "type_=None, label_contains=\"Some Name\""
    if isinstance(type_, str) and "=" in type_ and label_contains is None:
        try:
            # Extract parameters from string like "type_=None, label_contains=\"Some Name\""
            parts = type_.split(", ")
            parsed_type = None
            parsed_label = None
            
            for part in parts:
                if "type_=" in part:
                    type_val = part.split("type_=")[1].strip()
                    if type_val != "None":
                        parsed_type = type_val.strip('"\'')
                elif "label_contains=" in part:
                    label_val = part.split("label_contains=")[1].strip()
                    if label_val != "None":
                        parsed_label = label_val.strip('"\'')
            
            type_ = parsed_type
            label_contains = parsed_label
        except Exception:
            # If parsing fails, just return empty results instead of special-casing names
            return json.dumps([], indent=2)
    
    results = list(find_nodes(KG, type_=type_, label_contains=label_contains))
    return json.dumps(
        [{"id": nid, "type": data.get("type"), "label": data.get("label")}
         for nid, data in results],
        indent=2
    )

def tool_neighbors(node_id: str) -> str:
    """Get neighbors of a node. Can handle quoted node IDs from the agent."""
    if not _ensure_kg_loaded():
        return json.dumps({}, indent=2)
    
    # Handle quoted node IDs from the agent
    if node_id.startswith("'") and node_id.endswith("'"):
        node_id = node_id[1:-1]
    elif node_id.startswith('"') and node_id.endswith('"'):
        node_id = node_id[1:-1]
    
    return json.dumps(neighbors_of(KG, node_id), indent=2)

def tool_skill_overlap(candidate_id: str, job_id: str = None) -> str:
    if not _ensure_kg_loaded():
        return json.dumps({"candidate_skills": [], "job_required_skills": [], "overlap": [], "missing": [], "jaccard": 0.0}, indent=2)
    
    # Handle the case where agent passes a single string like "candidate_id='cand:john_doe', job_id='job:data_scientist'"
    if job_id is None and isinstance(candidate_id, str) and "=" in candidate_id:
        try:
            # Extract parameters from string like "candidate_id='cand:john_doe', job_id='job:data_scientist'"
            parts = candidate_id.split(", ")
            parsed_candidate_id = None
            parsed_job_id = None
            
            for part in parts:
                if "candidate_id=" in part:
                    candidate_val = part.split("candidate_id=")[1].strip()
                    parsed_candidate_id = candidate_val.strip('"\'')
                elif "job_id=" in part:
                    job_val = part.split("job_id=")[1].strip()
                    parsed_job_id = job_val.strip('"\'')
            
            candidate_id = parsed_candidate_id
            job_id = parsed_job_id
        except Exception:
            return json.dumps({"error": "Failed to parse arguments"}, indent=2)
    
    if candidate_id is None or job_id is None:
        return json.dumps({"error": "Both candidate_id and job_id are required"}, indent=2)
    
    # Handle quoted node IDs from the agent
    if candidate_id.startswith("'") and candidate_id.endswith("'"):
        candidate_id = candidate_id[1:-1]
    elif candidate_id.startswith('"') and candidate_id.endswith('"'):
        candidate_id = candidate_id[1:-1]
    
    if job_id.startswith("'") and job_id.endswith("'"):
        job_id = job_id[1:-1]
    elif job_id.startswith('"') and job_id.endswith('"'):
        job_id = job_id[1:-1]
    
    return json.dumps(skill_overlap(KG, candidate_id, job_id), indent=2)

TOOLS = {
    "find_nodes": tool_find_nodes,
    "neighbors": tool_neighbors,
    "skill_overlap": tool_skill_overlap,
}
