"""Dependency graph analyzer — maps package & module dependencies."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ctx.scanner.filesystem import FilesystemResult
from ctx.scanner.packages import PackageResult


@dataclass
class DependencyNode:
    """Node in dependency graph."""
    name: str
    category: str  # Framework, Database, Auth, Utility, Testing, Internal
    version: str = ""
    description: str = ""
    depends_on: list[str] = field(default_factory=list)


@dataclass
class LayerFlow:
    """Internal architecture layer flow."""
    from_layer: str
    to_layer: str
    description: str


@dataclass
class DependencyGraphResult:
    """Result of dependency analysis."""
    nodes: list[DependencyNode] = field(default_factory=list)
    flows: list[LayerFlow] = field(default_factory=list)
    categorized_deps: dict[str, list[str]] = field(default_factory=dict)
    chain_summary: list[str] = field(default_factory=list)


CATEGORY_RULES: dict[str, list[str]] = {
    "Framework": [
        "next", "react", "vue", "svelte", "angular", "express", "fastify", "hono",
        "remix", "astro", "django", "flask", "fastapi", "starlette", "typer", "click",
        "actix-web", "axum", "gin", "fiber"
    ],
    "Database / ORM": [
        "prisma", "@prisma/client", "drizzle-orm", "typeorm", "sequelize", "mongoose",
        "sqlalchemy", "alembic", "redis", "ioredis", "pg", "mysql2", "sqlite3",
        "psycopg2", "psycopg", "tortoise-orm", "peewee"
    ],
    "Authentication": [
        "next-auth", "@auth/core", "passport", "jsonwebtoken", "pyjwt", "auth0",
        "clerk", "lucia", "supabase-js", "@supabase/supabase-js", "firebase"
    ],
    "State & Validation": [
        "zod", "pydantic", "yup", "valibot", "zustand", "redux", "@reduxjs/toolkit",
        "jotai", "recoil", "pinia"
    ],
    "Utilities & Services": [
        "stripe", "axios", "httpx", "requests", "resend", "nodemailer", "boto3",
        "openai", "anthropic", "langchain", "celery", "bull", "bullmq", "winston",
        "pino", "sentry", "@sentry/nextjs", "gitpython", "rich", "pyyaml", "tomli"
    ],
    "Testing": [
        "pytest", "jest", "vitest", "playwright", "cypress", "mocha", "chai"
    ]
}


def analyze_dependencies(
    fs: FilesystemResult,
    pkg: PackageResult,
    root: Path,
) -> DependencyGraphResult:
    """Analyze codebase dependencies and build dependency graph."""
    result = DependencyGraphResult()

    all_deps = {**pkg.dependencies, **pkg.dev_dependencies}
    categorized: dict[str, list[str]] = {
        "Framework": [],
        "Database / ORM": [],
        "Authentication": [],
        "State & Validation": [],
        "Utilities & Services": [],
        "Testing": [],
        "Other": []
    }

    # Categorize external packages
    for dep, ver in all_deps.items():
        found_cat = False
        dep_lower = dep.lower()
        for cat, keywords in CATEGORY_RULES.items():
            if any(k == dep_lower or k in dep_lower for k in keywords):
                categorized[cat].append(dep)
                found_cat = True
                break
        if not found_cat:
            categorized["Other"].append(dep)

    # Clean empty categories
    result.categorized_deps = {k: v for k, v in categorized.items() if v}

    # Build primary dependency chains (e.g. Next -> React -> Prisma -> Postgres)
    chains: list[str] = []
    if pkg.language in ("TypeScript", "JavaScript"):
        if "next" in all_deps:
            chains.append("Browser -> Next.js (Router/SSR) -> React Components -> Node API")
        elif "react" in all_deps:
            chains.append("Browser -> React (SPA) -> REST/GraphQL API")
        elif "express" in all_deps or "fastify" in all_deps:
            chains.append("HTTP Request -> Middleware -> Router -> Controller -> Service")

    if pkg.language == "Python":
        if "fastapi" in all_deps:
            chains.append("Client -> FastAPI -> Starlette (Routing) -> Pydantic (Validation) -> Service/DB")
        elif "django" in all_deps:
            chains.append("HTTP Request -> Django WSGI/ASGI -> Middleware -> URL Conf -> Views -> ORM")
        elif "flask" in all_deps:
            chains.append("HTTP Request -> Flask App -> Blueprints -> Services")
        elif "typer" in all_deps or "click" in all_deps:
            chains.append("CLI Invocation -> Typer Routing -> Argument Parsing -> Action Handlers")

    # DB chain
    db_found = [d for d in all_deps if any(k in d for k in ["prisma", "sqlalchemy", "drizzle", "mongoose", "pg", "redis"])]
    if db_found:
        chains.append(f"Application Code -> {', '.join(db_found[:3])} -> Database Store")

    result.chain_summary = chains

    # Internal layer flows from directory structures
    dir_names = {d.relative.split("/")[0] for d in fs.directories}
    if {"app", "pages"} & dir_names and "components" in dir_names:
        result.flows.append(LayerFlow("Pages/Routes", "Components", "Renders UI components"))
    if {"app", "pages", "routes"} & dir_names and {"services", "lib", "controllers"} & dir_names:
        result.flows.append(LayerFlow("Routes/API", "Services/Lib", "Delegates business logic"))
    if {"services", "lib", "controllers"} & dir_names and {"models", "prisma", "db"} & dir_names:
        result.flows.append(LayerFlow("Services", "Data Models/DB", "Queries database / models"))

    return result
