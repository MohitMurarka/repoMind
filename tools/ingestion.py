import os
import shutil
import tempfile
from dataclasses import dataclass, field
from typing import Optional
import git
from dotenv import load_dotenv

load_dotenv()

SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
}

EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "target",
    ".mypy_cache",
    ".pytest_cache",
    "eggs",
}

MAX_FILE_SIZE_BYTES = 100_000


@dataclass
class RawFile:
    file_path: str  # relative path inside repo e.g. "src/auth/login.py"
    language: str  # "python", "javascript" etc.
    content: str  # raw source code
    repo_url: str  # original github url
    size_bytes: int  # file size


@dataclass
class IngestionResult:
    repo_url: str
    repo_name: str
    files: list[RawFile] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    error: Optional[str] = None


def _get_repo_name(repo_url: str) -> str:
    """Extract repo name from URL. e.g. https://github.com/user/myrepo -> myrepo"""
    return repo_url.rstrip("/").split("/")[-1].replace(".git", "")


def _should_exclude_dir(dir_name: str) -> str:
    return dir_name in EXCLUDED_DIRS or dir_name.startswith(".")


def ingest_repo(repo_url: str, clone_dir: Optional[str] = None) -> IngestionResult:
    """
    Clone a GitHub repo and extract all supported source files.

    Args:
        repo_url: Full GitHub URL e.g. https://github.com/user/repo
        clone_dir: Optional directory to clone into. Uses temp dir if None.

    Returns:
        IngestionResult with all extracted RawFile objects.

    """

    repo_name = _get_repo_name(repo_url)
    result = IngestionResult(repo_url=repo_url, repo_name=repo_name)

    use_temp = (
        clone_dir is None
    )  # True(no folder given) or False(folder already provided)
    if use_temp:
        clone_dir = tempfile.mkdtemp(prefix="repomind_")

    print(f"Cloning {repo_url} into {clone_dir}")

    try:
        git.Repo.clone_from(repo_url, clone_dir, depth=1)
        print(f"Clone complete. Walking files...")

        for root, dirs, files in os.walk(clone_dir):
            # Filter out excluded directories in-place
            dirs[:] = [d for d in dirs if not _should_exclude_dir(d)]

            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, clone_dir)
                # Normalize to forward slashes
                rel_path = rel_path.replace("\\", "/")

                size = os.path.getsize(abs_path)
                if size > MAX_FILE_SIZE_BYTES:
                    result.skipped_files.append(f"{rel_path} (too large: {size} bytes)")
                    continue

                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    if not content.strip():
                        result.skipped_files.append(f"{rel_path} (empty)")
                        continue

                    result.files.append(
                        RawFile(
                            file_path=rel_path,
                            language=SUPPORTED_EXTENSIONS[ext],
                            content=content,
                            repo_url=repo_url,
                            size_bytes=size,
                        )
                    )

                except Exception as e:
                    result.skipped_files.append(f"{rel_path} (read error: {e})")

        print(
            f"Done. {len(result.files)} files extracted, {len(result.skipped_files)} skipped."
        )

    except git.exc.GitCommandError as e:
        result.error = f"Git clone failed: {str(e)}"
        print(f"Error: {result.error}")

    finally:
        if use_temp and os.path.exists(clone_dir):
            # Windows sets .git files as read-only, need to force remove
            def force_remove(func, path, exc_info):
                import stat

                os.chmod(path, stat.S_IWRITE)
                func(path)

            shutil.rmtree(clone_dir, onexc=force_remove)
            print(f"Cleaned up temp dir.")

    return result
