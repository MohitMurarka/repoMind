from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage
from graph.state import AgentState
from agents.router import make_llm_with_tools, SYSTEM_PROMPT


def build_graph(repo_url: str):
    """
    Build a RepoMind agent graph for a specific repo.
    Uses LangGraph's create_react_agent which handles the
    AIMessage → ToolMessage → AIMessage loop correctly.
    """
    llm_with_tools, tools = make_llm_with_tools(repo_url)

    graph = create_react_agent(
        model=llm_with_tools,
        tools=tools,
        prompt=SYSTEM_PROMPT,
        max_iterations=6,  # ← add this
    )

    return graph
