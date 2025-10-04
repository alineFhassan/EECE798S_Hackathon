# nx_graph_store.py
from __future__ import annotations
import json
import hashlib
from typing import Dict, Any, Iterable, Tuple
import networkx as nx
import pickle
import os

# ----- utilities --------------------------------------------------------------

CANON_TYPES_TO_COALESCE = {
    "skill", "company", "institution", "certification", "project", "degree", "role"
}

def _norm(s: str) -> str:
    return " ".join((s or "").strip().lower().split())

def _canonical_id(n: Dict[str, Any]) -> str:
    """
    Prefer given id if it already looks namespaced (e.g., 'skill:python').
    Otherwise, synthesize stable id from type + normalized label.
    """
    nid = str(n.get("id", "")).strip()
    ntype = str(n.get("type", "")).strip().lower()
    label = _norm(n.get("label") or n.get("props", {}).get("name", "") or "")
    if nid and ":" in nid:
        return nid
    if ntype in CANON_TYPES_TO_COALESCE and label:
        return f"{ntype}:{label}"
    # fallback: hash to avoid collisions
    raw = json.dumps({"id": nid, "type": ntype, "label": label, "props": n.get("props", {})}, sort_keys=True)
    return f"node:{hashlib.sha1(raw.encode()).hexdigest()[:12]}"

def _merge_props(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(dst or {})
    for k, v in (src or {}).items():
        if k not in out or out[k] in (None, "", [], {}):
            out[k] = v
        # simple union for lists (best-effort)
        elif isinstance(out[k], list) and isinstance(v, list):
            seen = set(json.dumps(x, sort_keys=True) for x in out[k])
            for item in v:
                j = json.dumps(item, sort_keys=True)
                if j not in seen:
                    out[k].append(item)
                    seen.add(j)
        # simple merge for dicts
        elif isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _merge_props(out[k], v)
    return out

# ----- builders / mergers -----------------------------------------------------

def build_nx_from_graph(graph_json: Dict[str, Any]) -> Tuple[nx.MultiDiGraph, Dict[str, str]]:
    """
    Convert {"nodes":[...], "edges":[...]} to a MultiDiGraph.
    Returns (G, id_map) where id_map maps original ids -> canonical ids.
    """
    G = nx.MultiDiGraph()
    id_map: Dict[str, str] = {}

    # add nodes
    for n in graph_json.get("nodes", []):
        orig_id = str(n.get("id"))
        ntype = (n.get("type") or "").lower()
        label = n.get("label") or ""
        props = n.get("props") or {}

        cid = _canonical_id(n)
        id_map[orig_id] = cid

        if cid not in G:
            G.add_node(cid, type=ntype, label=label, props=props, sources=set(["llm"]))
        else:
            # merge with existing
            G.nodes[cid]["props"] = _merge_props(G.nodes[cid].get("props", {}), props)
            G.nodes[cid]["sources"].add("llm")

    # add edges
    for e in graph_json.get("edges", []):
        src = id_map.get(str(e.get("source")), str(e.get("source")))
        tgt = id_map.get(str(e.get("target")), str(e.get("target")))
        rel = (e.get("relation") or "").lower()
        # store relation/weight; use key to keep parallel edges if needed
        key = rel or "related_to"
        G.add_edge(src, tgt, key=key, relation=rel, weight=1, sources=set(["llm"]))
    return G, id_map

def merge_graphs(graphs: Iterable[nx.MultiDiGraph]) -> nx.MultiDiGraph:
    """
    Merge multiple MultiDiGraphs into one. Coalesce nodes/edges and accumulate weights.
    """
    KG = nx.MultiDiGraph()
    for g in graphs:
        for nid, data in g.nodes(data=True):
            if nid not in KG:
                KG.add_node(nid, **{**data, "sources": set(data.get("sources", set()))})
            else:
                KG.nodes[nid]["props"] = _merge_props(KG.nodes[nid].get("props", {}), data.get("props", {}))
                KG.nodes[nid]["sources"].update(data.get("sources", set()))
                # ensure type/label preserved
                if not KG.nodes[nid].get("label") and data.get("label"):
                    KG.nodes[nid]["label"] = data["label"]
                if not KG.nodes[nid].get("type") and data.get("type"):
                    KG.nodes[nid]["type"] = data["type"]

        for u, v, key, edata in g.edges(keys=True, data=True):
            if KG.has_edge(u, v, key=key):
                KG[u][v][key]["weight"] = KG[u][v][key].get("weight", 1) + edata.get("weight", 1)
                KG[u][v][key]["sources"].update(edata.get("sources", set()))
            else:
                KG.add_edge(u, v, key=key, **{**edata, "sources": set(edata.get("sources", set()))})
    return KG

# ----- quick queries ----------------------------------------------------------

def neighbors_of(G: nx.MultiDiGraph, node_id: str) -> Dict[str, Any]:
    """Return a snapshot of immediate neighbors grouped by relation."""
    out = {}
    if node_id not in G:
        return out
    for _, v, key, data in G.out_edges(node_id, keys=True, data=True):
        rel = data.get("relation", key) or key
        out.setdefault(rel, []).append(v)
    return out

def find_nodes(G: nx.MultiDiGraph, *, type_: str | None = None, label_contains: str | None = None):
    """Tiny search helper."""
    t = (type_ or "").lower().strip()
    q = _norm(label_contains or "")
    for nid, data in G.nodes(data=True):
        if t and data.get("type") != t:
            continue
        label = _norm(data.get("label", "")) or _norm(data.get("props", {}).get("name", ""))
        if q and q not in label:
            continue
        yield nid, data

def skill_overlap(G: nx.MultiDiGraph, candidate_id: str, job_id: str) -> Dict[str, Any]:
    """Compute overlapping skills between a candidate and a job."""
    def _skills_for(node_id: str, rel: str) -> set[str]:
        skill_ids = set()
        for _, v, key, data in G.out_edges(node_id, keys=True, data=True):
            if (data.get("relation") or key) == rel:
                if G.nodes[v].get("type") == "skill":
                    skill_ids.add(v)
        return skill_ids

    cand_sk = _skills_for(candidate_id, "has_skill")
    job_sk = _skills_for(job_id, "requires_skill")
    overlap = cand_sk & job_sk
    missing = job_sk - cand_sk
    return {
        "candidate_skills": sorted(cand_sk),
        "job_required_skills": sorted(job_sk),
        "overlap": sorted(overlap),
        "missing": sorted(missing),
        "jaccard": (len(overlap) / len(job_sk)) if job_sk else 0.0
    }

# ----- visualization & persistence -------------------------------------------

def simple_draw(G: nx.MultiDiGraph, node_limit: int = 80) -> None:
    """
    Quick-and-dirty matplotlib draw for local debugging.
    """
    import matplotlib.pyplot as plt

    # limit nodes for readability
    H = G.copy()
    if H.number_of_nodes() > node_limit:
        # keep the highest-degree nodes
        deg_sorted = sorted(H.degree, key=lambda x: x[1], reverse=True)[:node_limit]
        keep = {n for n, _ in deg_sorted}
        H = H.subgraph(keep).copy()

    pos = nx.spring_layout(H, seed=42, k=0.4)
    # color by type
    by_type = {}
    for n, data in H.nodes(data=True):
        by_type.setdefault(data.get("type", "other"), []).append(n)

    for t, nodes in by_type.items():
        nx.draw_networkx_nodes(H, pos, nodelist=nodes, label=t, node_size=500, alpha=0.85)
    nx.draw_networkx_labels(H, pos, labels={n: H.nodes[n].get("label", n) for n in H.nodes}, font_size=8)
    # edges with relation as label (light)
    nx.draw_networkx_edges(H, pos, alpha=0.25)
    edge_labels = {(u, v): d.get("relation", k) for u, v, k, d in H.edges(keys=True, data=True)}
    nx.draw_networkx_edge_labels(H, pos, edge_labels=edge_labels, font_size=6)
    plt.axis("off")
    plt.tight_layout()
    plt.show()

# nx_graph_store.py
def save_gpickle(G: nx.MultiDiGraph, path: str) -> None:
    if not path.endswith(".gpickle"):
        path = os.path.join(path, "graph.gpickle")
    with open(path, "wb") as f:
        pickle.dump(G, f)
    print(f"[✓] Graph saved at {path}")

def load_gpickle(path: str) -> nx.MultiDiGraph:
    with open(path, "rb") as f:
        return pickle.load(f)

