import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from graph.state import AgentState
from tools.retriever import retrieve, get_file_chunks, find_symbol_references

load_dotenv()

SYSTEM_PROMPT = """You are RepoMind, an expert AI assistant that answers questions about codebases.

You have access to these tools:
- search_codebase: Hybrid semantic + keyword search. Use for broad questions.
- get_file: Get all chunks from a specific file. Use when you know the file.
- find_references: Find where a function/class is defined or used.

RULES:
1. Always search before answering — never answer from memory.
2. Cite every claim with file_path and line numbers from the chunks you retrieved.
3. If one search is not enough, search again with a different query.
4. When you have enough context, write your final answer directly as a message (no tool call).
5. Maximum 6 tool calls per query.
6. Format your final answer clearly with code snippets where relevant.
7. If you have searched 4+ times and are not finding new information, stop searching and write your best answer with what you have found. Do not keep rephrasing the same search query.

CITATION FORMAT:
When referencing code, always say: "In `file_path` (lines X-Y), the `symbol_name` function..."
"""


def make_tools(repo_url: str):
    """Create tool functions bound to a specific repo_url."""

    @tool
    def search_codebase(query: str) -> str:
        """Search the codebase using hybrid semantic + keyword search."""
        chunks = retrieve(query, repo_url)
        if not chunks:
            return "No results found."
        lines = [f"Found {len(chunks)} chunks:"]
        for chunk in chunks:
            lines.append(
                f"\n[{chunk.symbol_name}] {chunk.file_path} "
                f"(lines {chunk.start_line}-{chunk.end_line})\n"
                f"```{chunk.language}\n{chunk.content[:600]}\n```"
            )
        return "\n".join(lines)

    @tool
    def get_file(file_path: str) -> str:
        """Get all chunks from a specific file path."""
        chunks = get_file_chunks(file_path, repo_url)
        if not chunks:
            return f"No chunks found for {file_path}."
        lines = [f"File: {file_path} — {len(chunks)} chunks:"]
        for chunk in chunks:
            lines.append(
                f"\n[{chunk.symbol_name}] lines {chunk.start_line}-{chunk.end_line}\n"
                f"```{chunk.language}\n{chunk.content[:600]}\n```"
            )
        return "\n".join(lines)

    @tool
    def find_references(symbol_name: str) -> str:
        """Find where a function or class is defined or called."""
        chunks = find_symbol_references(symbol_name, repo_url)
        if not chunks:
            return f"No references found for '{symbol_name}'."
        lines = [f"References to '{symbol_name}':"]
        for chunk in chunks:
            lines.append(
                f"\n[{chunk.symbol_name}] {chunk.file_path} "
                f"(lines {chunk.start_line}-{chunk.end_line})\n"
                f"```{chunk.language}\n{chunk.content[:400]}\n```"
            )
        return "\n".join(lines)

    return [search_codebase, get_file, find_references]


def make_llm_with_tools(repo_url: str):
    """Create LLM with tools bound for a specific repo."""
    tools = make_tools(repo_url)
    llm = ChatOpenAI(
        model="gpt-5-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    return llm.bind_tools(tools), tools
