"""Q&A analyzer — answers questions about the codebase using index matching or LLM APIs."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from ctx.analyzers.architecture import ArchitectureResult
from ctx.scanner.filesystem import FilesystemResult
from ctx.scanner.packages import PackageResult


@dataclass
class RelevantMatch:
    """A file snippet match relevant to the user query."""
    file_path: str
    line_number: int
    snippet: str
    relevance_score: float
    reason: str


@dataclass
class AskResult:
    """Result of ctx ask query."""
    query: str
    answer: str
    relevant_files: list[str] = field(default_factory=list)
    matches: list[RelevantMatch] = field(default_factory=list)
    used_ai: bool = False
    ai_provider: str = ""


# Common concept keywords to search target files
CONCEPT_KEYWORDS: dict[str, list[str]] = {
    "auth": ["auth", "login", "signup", "jwt", "session", "password", "token", "user", "middleware", "oauth"],
    "authentication": ["auth", "login", "signup", "jwt", "session", "password", "token", "user", "middleware", "oauth"],
    "database": ["db", "database", "query", "prisma", "sql", "model", "schema", "table", "migration", "connection"],
    "db": ["db", "database", "query", "prisma", "sql", "model", "schema", "table", "migration", "connection"],
    "api": ["api", "route", "endpoint", "fetch", "post", "get", "request", "response", "controller", "handler"],
    "routing": ["route", "router", "path", "page", "nav", "url", "dispatch"],
    "config": ["config", "env", "settings", "option", "flag"],
    "state": ["store", "state", "redux", "zustand", "context", "reducer"],
    "cli": ["cli", "typer", "click", "command", "arg", "flag", "parse", "option"],
    "entry": ["main", "app", "index", "server", "entry", "bootstrap"],
    "test": ["test", "spec", "mock", "assert", "fixture"],
}


def _extract_query_terms(query: str) -> set[str]:
    """Extract search terms and mapped concept keywords from a user query."""
    words = re.findall(r"\w+", query.lower())
    terms = set(words)

    # Add stemmed variants & sub-words (e.g., subcommands -> subcommand, command)
    for word in list(words):
        if len(word) > 4:
            if word.endswith("s"):
                terms.add(word[:-1])
            if word.endswith("ing"):
                terms.add(word[:-3])
            if word.endswith("ed"):
                terms.add(word[:-2])
            if "sub" in word and len(word) > 6:
                terms.add(word.replace("sub", ""))

        for concept_key, concept_terms in CONCEPT_KEYWORDS.items():
            if concept_key in word or word in concept_key:
                terms.update(concept_terms)

    return terms


def find_relevant_matches(
    query: str,
    fs: FilesystemResult,
    root: Path,
    max_matches: int = 8,
) -> tuple[list[str], list[RelevantMatch]]:
    """Scan codebase files and score lines relevant to query."""
    terms = _extract_query_terms(query)
    matches: list[RelevantMatch] = []
    file_scores: dict[str, float] = {}

    # Prioritize source code files
    for file_info in fs.files:
        if file_info.lines == 0 or file_info.size > 200_000:
            continue

        rel = file_info.relative
        # Bonus score for matching file path
        path_score = sum(3.0 for term in terms if term in rel.lower())

        try:
            full_path = root / rel
            if not full_path.exists():
                continue

            content = full_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()

            for i, line in enumerate(lines, 1):
                line_lower = line.lower()
                matched_terms = [t for t in terms if t in line_lower]
                if matched_terms:
                    score = len(matched_terms) * 1.5 + path_score
                    # Ignore pure import lines unless query specifically asks about imports
                    if line_lower.strip().startswith(("import ", "from ", "require(")) and "import" not in query.lower():
                        score *= 0.5

                    if score > 1.5:
                        reason = f"Matches terms: {', '.join(matched_terms[:3])}"
                        matches.append(RelevantMatch(
                            file_path=rel,
                            line_number=i,
                            snippet=line.strip(),
                            relevance_score=score,
                            reason=reason,
                        ))
                        file_scores[rel] = file_scores.get(rel, 0) + score
        except Exception:
            continue

    # Sort matches by score
    matches.sort(key=lambda m: m.relevance_score, reverse=True)

    # Dedup matches per file to keep top ones
    top_matches: list[RelevantMatch] = []
    seen_file_lines: set[tuple[str, int]] = set()

    for m in matches:
        key = (m.file_path, m.line_number)
        if key not in seen_file_lines and len(top_matches) < max_matches:
            seen_file_lines.add(key)
            top_matches.append(m)

    sorted_files = sorted(file_scores.keys(), key=lambda f: file_scores[f], reverse=True)
    return sorted_files[:5], top_matches


def _try_ai_answer(
    query: str,
    fs: FilesystemResult,
    pkg: PackageResult,
    arch: ArchitectureResult,
    matches: list[RelevantMatch],
) -> tuple[str, str] | None:
    """Attempt to answer query via configured LLM API keys if available."""

    # 1. OpenAI / OpenRouter / Groq / Gemini
    openai_key = os.getenv("OPENAI_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    groq_key = os.getenv("GROQ_API_KEY")

    context_snippets = "\n".join([
        f"File: {m.file_path}:{m.line_number}\n  {m.snippet}"
        for m in matches[:6]
    ])

    prompt = (
        f"Project: {pkg.project_name or 'Codebase'} ({arch.project_type})\n"
        f"Language: {pkg.language}, Framework: {pkg.framework}\n"
        f"Important Files: {', '.join(fs.important_files[:5])}\n\n"
        f"Relevant Code Snippets:\n{context_snippets}\n\n"
        f"User Question: {query}\n\n"
        "Provide a concise, direct answer (3-5 sentences) explaining where this logic lives, "
        "how it works in this project, and referencing relevant files."
    )

    if openrouter_key or openai_key or groq_key:
        api_url = "https://openrouter.ai/api/v1/chat/completions" if openrouter_key else (
            "https://api.groq.com/openai/v1/chat/completions" if groq_key else "https://api.openai.com/v1/chat/completions"
        )
        api_key = openrouter_key or groq_key or openai_key
        model = "anthropic/claude-3.5-haiku" if openrouter_key else ("llama-3.3-70b-versatile" if groq_key else "gpt-4o-mini")
        provider_name = "OpenRouter" if openrouter_key else ("Groq" if groq_key else "OpenAI")

        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 300,
            "temperature": 0.2,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        try:
            req = urllib.request.Request(api_url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["choices"][0]["message"]["content"].strip()
                return text, provider_name
        except Exception:
            pass

    return None


def ask_codebase(
    query: str,
    fs: FilesystemResult,
    pkg: PackageResult,
    arch: ArchitectureResult,
    root: Path,
) -> AskResult:
    """Perform codebase Q&A."""
    top_files, top_matches = find_relevant_matches(query, fs, root)

    result = AskResult(
        query=query,
        answer="",
        relevant_files=top_files,
        matches=top_matches,
    )

    # Check for AI API answer first
    ai_res = _try_ai_answer(query, fs, pkg, arch, top_matches)
    if ai_res:
        result.answer, result.ai_provider = ai_res
        result.used_ai = True
        return result

    # Offline Smart Fallback Answer
    lines = []
    if top_files:
        lines.append(f"Primary files related to '{query}':")
        for f in top_files[:3]:
            lines.append(f"  * {f}")
    else:
        lines.append(f"No exact file match found for '{query}'.")

    if arch.summary_points:
        lines.append("\nArchitecture Context:")
        for pt in arch.summary_points[:2]:
            lines.append(f"  * {pt}")

    lines.append("\nTip: Export full context with `ctx export . --claude` for complex AI reasoning.")
    result.answer = "\n".join(lines)
    return result
