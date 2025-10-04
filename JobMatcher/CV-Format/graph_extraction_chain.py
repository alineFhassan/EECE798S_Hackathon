# graph_extraction_chain.py
# Structured CV/JD → Graph JSON via LLM (LangChain ≥ 0.1.17)

import json
import os
from typing import Literal, Dict, Any

from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# --- Model (env var OPENAI_API_KEY must be set in Colab) ---

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# --- Schema vocab (for the prompt text only) ---
ALLOWED_NODE_TYPES = [
    "candidate", "job", "skill", "role", "company",
    "degree", "institution", "responsibility", "project", "certification"
]
ALLOWED_RELATIONS = [
    "has_skill", "worked_as", "studied", "achieved",
    "has_project", "has_cert", "at_company", "at_institution",
    "requires_skill", "has_responsibility", "requires_cert"
]

# IMPORTANT: put the example JSON in a variable, not in the template body.
SCHEMA_EXAMPLE = """
{
  "nodes": [{"id":"...","type":"<one of the allowed types>","label":"...","props":{}} ],
  "edges": [{"source":"<id>","relation":"<one of the allowed relations>","target":"<id>"}]
}
""".strip()

CONSTRAINTS_TMPL = """
Rules:
- Return ONLY valid JSON (no prose, no markdown fences).
- Structure (example below, follow the same shape):
{schema_example}
- Allowed node types: {allowed_types}
- Allowed relations: {allowed_relations}
- Use descriptive, unique ids (e.g., "cand:alice_johnson", "skill:python").
- Extra details (GPA, years, stack, issuer, etc.) go inside "props".
- Never invent data not present in the input.
""".strip()

# Build a single constraints string via partial variables
CONSTRAINTS = CONSTRAINTS_TMPL.format(
    schema_example=SCHEMA_EXAMPLE,
    allowed_types=", ".join(ALLOWED_NODE_TYPES),
    allowed_relations=", ".join(ALLOWED_RELATIONS),
)

# --- Prompts (no raw braces inside; only {input_text} placeholder) ---
cv_prompt = PromptTemplate.from_template(
    """
You are given a structured CV (as JSON).
Convert it into a graph of nodes and edges following the schema below.

{constraints}

Mapping:
- One "candidate" node.
- Education → degree/institution nodes → candidate-[studied]->degree, degree-[at_institution]->institution
- Experience → role/company/responsibility nodes → candidate-[worked_as]->role; role-[at_company]->company
- Skills → skill nodes → candidate-[has_skill]->skill
- Projects → project nodes → candidate-[has_project]->project
- Certifications → certification nodes → candidate-[has_cert]->certification

Input CV JSON:
{input_text}
""".strip()
)

jd_prompt = PromptTemplate.from_template(
    """
You are given a structured Job Description (as JSON).
Convert it into a graph of nodes and edges following the schema below.

{constraints}

Mapping:
- One "job" node.
- Requirements → extract key skill nodes → job-[requires_skill]->skill
- Responsibilities → responsibility nodes → job-[has_responsibility]->responsibility
- Required certifications → certification nodes → job-[requires_cert]->certification
- Include job_level, years_experience, etc. in job.props.

Input JD JSON:
{input_text}
""".strip()
)

# --- Chains: Prompt → LLM → str ---
parser = StrOutputParser()
cv_chain = cv_prompt | llm | parser
jd_chain = jd_prompt | llm | parser

def _parse_json_safely(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        # strip accidental fences
        raw = raw.strip("`").replace("json", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end+1])
        raise ValueError("Failed to parse JSON from model output.")

def extract_graph_from_text(data: Dict[str, Any], kind: Literal["cv", "jd"]) -> Dict[str, Any]:
    """
    Converts a structured CV or JD dict to a graph using LLM.
    Returns: {"nodes":[...], "edges":[...]}
    """
    chain = cv_chain if kind == "cv" else jd_chain
    formatted_input = json.dumps(data, indent=2, ensure_ascii=False)

    raw = chain.invoke({"input_text": formatted_input, "constraints": CONSTRAINTS})
    graph = _parse_json_safely(raw)

    if not isinstance(graph, dict) or "nodes" not in graph or "edges" not in graph:
        raise ValueError("Invalid graph JSON: missing 'nodes'/'edges'.")
    return graph


