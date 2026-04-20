import os
from dataclasses import dataclass, field
from typing import Optional
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
import tree_sitter_go as tsgo
import tree_sitter_java as tsjava
import tree_sitter_rust as tsrust
from tree_sitter import Language, Parser
from tools.ingestion import RawFile
from graph.state import Chunk

# --- Build language objects ---
PY_LANGUAGE = Language(tspython.language())
JS_LANGUAGE = Language(tsjavascript.language())
TS_LANGUAGE = Language(tstypescript.language_typescript())
GO_LANGUAGE = Language(tsgo.language())
JAVA_LANGUAGE = Language(tsjava.language())
RS_LANGUAGE = Language(tsrust.language())

LANGUAGE_MAP = {
    "python": PY_LANGUAGE,
    "javascript": JS_LANGUAGE,
    "typescript": TS_LANGUAGE,
    "go": GO_LANGUAGE,
    "java": JAVA_LANGUAGE,
    "rust": RS_LANGUAGE,
}

# Node types we want to extract per language
CHUNK_NODE_TYPES = {
    "python": {"function_definition", "class_definition"},
    "javascript": {
        "function_declaration",
        "class_declaration",
        "arrow_function",
        "method_definition",
    },
    "typescript": {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "arrow_function",
    },
    "go": {"function_declaration", "method_declaration"},
    "java": {"class_declaration", "method_declaration"},
    "rust": {"function_item", "impl_item"},
}

MAX_CHUNK_CHARS = 1500
MIN_CHUNK_CHARS = 30


def _get_node_name(node, source_bytes: bytes) -> str:
    """Try to extract the symbol name from a node."""
    for child in node.children:
        if child.type in ("identifier", "name", "field_identifier"):
            return source_bytes[child.start_byte : child.end_byte].decode(
                "utf-8", errors="ignore"
            )
    return "unknown"


def _extract_chunks_from_tree(
    root_node, source_bytes: bytes, language: str, file_path: str, repo_url: str
) -> list[Chunk]:
    """Recursively walk the AST and extract chunks for target node types."""
    chunks = []
    target_types = CHUNK_NODE_TYPES.get(language, set())

    def walk(node):
        if node.type in target_types:
            content = source_bytes[node.start_byte : node.end_byte].decode(
                "utf-8", errors="ignore"
            )

            if len(content) < MIN_CHUNK_CHARS:
                return

            if len(content) > MAX_CHUNK_CHARS:
                # Still include but truncate — better than dropping it
                content = content[:MAX_CHUNK_CHARS] + "\n# ... truncated"

            symbol_name = _get_node_name(node, source_bytes)

            chunks.append(
                Chunk(
                    content=content,
                    file_path=file_path,
                    start_line=node.start_point[0] + 1,  # tree-sitter is 0-indexed
                    end_line=node.end_point[0] + 1,
                    language=language,
                    symbol_name=symbol_name,
                    repo_url=repo_url,
                )
            )
            # Don't walk children of extracted nodes to avoid double-chunking
            return

        for child in node.children:
            walk(child)

    walk(root_node)
    return chunks


def _fallback_chunk(raw_file: RawFile) -> list[Chunk]:
    """
    For files where AST gives 0 chunks (e.g. pure config/script files),
    fall back to sliding window by lines.
    """
    lines = raw_file.content.splitlines()
    chunks = []
    window = 40
    step = 20

    for i in range(0, len(lines), step):
        block = lines[i : i + window]
        content = "\n".join(block).strip()
        if len(content) < MIN_CHUNK_CHARS:
            continue
        chunks.append(
            Chunk(
                content=content[:MAX_CHUNK_CHARS],
                file_path=raw_file.file_path,
                start_line=i + 1,
                end_line=min(i + window, len(lines)),
                language=raw_file.language,
                symbol_name="file_block",
                repo_url=raw_file.repo_url,
            )
        )

    return chunks


def chunk_file(raw_file: RawFile) -> list[Chunk]:
    """
    Parse a single file and return a list of Chunk objects.
    Uses AST extraction, falls back to sliding window if needed.
    """
    lang_obj = LANGUAGE_MAP.get(raw_file.language)

    if lang_obj is None:
        return _fallback_chunk(raw_file)

    parser = Parser(lang_obj)
    source_bytes = raw_file.content.encode("utf-8")
    tree = parser.parse(source_bytes)

    chunks = _extract_chunks_from_tree(
        tree.root_node,
        source_bytes,
        raw_file.language,
        raw_file.file_path,
        raw_file.repo_url,
    )

    if not chunks:
        chunks = _fallback_chunk(raw_file)

    return chunks


def chunk_repo(raw_files: list[RawFile]) -> list[Chunk]:
    """
    Chunk all files from an ingestion result.
    Returns a flat list of all chunks across all files.
    """
    all_chunks = []
    for raw_file in raw_files:
        file_chunks = chunk_file(raw_file)
        all_chunks.extend(file_chunks)

    print(f"Chunked {len(raw_files)} files → {len(all_chunks)} chunks")
    return all_chunks
