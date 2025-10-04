# demo_nx.py
import json
from nx_graph_store import build_nx_from_graph, merge_graphs, find_nodes, skill_overlap, simple_draw

# Pretend these are the LLM outputs from graph_extraction_chain.extract_graph_from_text(...)
cv_graph = {
    "nodes": [
        {"id":"cand:alice_johnson","type":"candidate","label":"Alice Johnson","props":{"location":"Paris"}},
        {"id":"skill:python","type":"skill","label":"Python","props":{}},
        {"id":"skill:sql","type":"skill","label":"SQL","props":{}},
    ],
    "edges": [
        {"source":"cand:alice_johnson","relation":"has_skill","target":"skill:python"},
        {"source":"cand:alice_johnson","relation":"has_skill","target":"skill:sql"},
    ]
}

jd_graph = {
    "nodes": [
        {"id":"job:data_scientist_acme","type":"job","label":"Data Scientist @ ACME","props":{"job_level":"mid","years_experience":"3-5"}},
        {"id":"skill:python","type":"skill","label":"Python","props":{}},
        {"id":"skill:mlops","type":"skill","label":"MLOps","props":{}},
    ],
    "edges": [
        {"source":"job:data_scientist_acme","relation":"requires_skill","target":"skill:python"},
        {"source":"job:data_scientist_acme","relation":"requires_skill","target":"skill:mlops"},
    ]
}

# Build graphs
G_cv, _ = build_nx_from_graph(cv_graph)
G_jd, _ = build_nx_from_graph(jd_graph)

# Merge into a single knowledge graph
KG = merge_graphs([G_cv, G_jd])

# Quick searches
print("\nAll skills:")
for nid, data in find_nodes(KG, type_="skill"):
    print(" ", nid, data.get("label"))

print("\nOverlap cand vs job:")
ov = skill_overlap(KG, "cand:alice_johnson", "job:data_scientist_acme")
print(json.dumps(ov, indent=2))

# Visualize (local debug)
simple_draw(KG, node_limit=50)
