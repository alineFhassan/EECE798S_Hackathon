# agent_chat.py
import os, json
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor, Tool
from langchain.prompts import PromptTemplate
from graph_tools import TOOLS

# Global variables for lazy initialization
_llm = None
_agent_executor = None

def _get_llm():
    """Get or create LLM instance."""
    global _llm

    if _llm is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set. Please set it to your OpenAI API key.")
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=api_key)
    return _llm

def _get_agent_executor():
    """Get or create agent executor."""
    global _agent_executor
    if _agent_executor is None:
        # Wrap tools
        tool_defs = [
            Tool(
                name="find_nodes",
                func=TOOLS["find_nodes"],
                description=(
                    "Find nodes in the graph by type and/or label substring. "
                    "Examples: find_nodes(type_='candidate', label_contains='John Doe') "
                    "or find_nodes(label_contains='Data Scientist')."
                ),
            ),
            Tool(
                name="neighbors",
                func=TOOLS["neighbors"],
                description=(
                    "Get neighbors of a node by ID. "
                    "Example: neighbors('cand:john_doe') or neighbors('job:data_scientist')."
                ),
            ),
            Tool(
                name="skill_overlap",
                func=TOOLS["skill_overlap"],
                description=(
                    "Compute skill overlap between a candidate and a job. "
                    "Example: skill_overlap('cand:john_doe', 'job:data_scientist')."
                ),
            ),
        ]

        # Create ReAct prompt template
        react_prompt = PromptTemplate.from_template("""
You are a helpful assistant that can answer questions about a knowledge graph. You have to answwer questions like an HR expert.

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}
""")

        # Create agent
        llm = _get_llm()
        agent = create_react_agent(llm, tool_defs, react_prompt)
        _agent_executor = AgentExecutor(agent=agent, tools=tool_defs, verbose=True)
    return _agent_executor

def chat(query: str):
    """Chat with the graph agent."""
    try:
        agent_executor = _get_agent_executor()
        return agent_executor.invoke({"input": query})["output"]
    except ValueError as e:
        return f"Error: {e}. Please set your OPENAI_API_KEY environment variable."
