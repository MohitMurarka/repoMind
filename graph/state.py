from typing import TypedDict, Optional
from dataclass import dataclass


@dataclass
class Chunk:
    content: str
    file_path: str
    start_line: str
    end_line: str
    language: str
    symbol_name: str
    repo_url = str
    score: float = 0.0


class AgentState(TypedDict):
    repo_link: str
    query: str
    messages: list
    retrieved_chunks: list
    iteration_count: int
    final_answer: str
    cited_files: list
    error: Optional[str]
