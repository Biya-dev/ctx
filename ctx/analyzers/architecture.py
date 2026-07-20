"""Architecture analyzer — infers project architecture from scan results."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ctx.scanner.filesystem import FilesystemResult
from ctx.scanner.packages import PackageResult


@dataclass
class ArchitectureResult:
    project_type: str = ""
    summary_points: list[str] = field(default_factory=list)
    entrypoints: list[str] = field(default_factory=list)
    architecture_layers: list[str] = field(default_factory=list)


# Map of directory names to architectural purposes
DIR_PURPOSES: dict[str, str] = {
    "app": "Application routes / pages",
    "pages": "Page components / routes",
    "src": "Source code",
    "lib": "Shared libraries / utilities",
    "utils": "Utility functions",
    "helpers": "Helper functions",
    "components": "UI components",
    "hooks": "Custom hooks",
    "services": "Service layer / business logic",
    "api": "API endpoints",
    "routes": "Route definitions",
    "controllers": "Request controllers",
    "models": "Data models",
    "schemas": "Data schemas / validation",
    "types": "Type definitions",
    "interfaces": "Interface definitions",
    "middleware": "Middleware functions",
    "auth": "Authentication",
    "prisma": "Prisma ORM / database schema",
    "db": "Database layer",
    "database": "Database layer",
    "migrations": "Database migrations",
    "config": "Configuration",
    "public": "Static / public assets",
    "static": "Static files",
    "assets": "Asset files",
    "styles": "Stylesheets",
    "css": "CSS files",
    "templates": "HTML templates",
    "views": "View layer",
    "tests": "Test files",
    "test": "Test files",
    "__tests__": "Test files",
    "spec": "Test specifications",
    "e2e": "End-to-end tests",
    "fixtures": "Test fixtures",
    "mocks": "Mock data / services",
    "scripts": "Build / utility scripts",
    "docs": "Documentation",
    "deploy": "Deployment configuration",
    "infra": "Infrastructure as code",
    "terraform": "Terraform IaC",
    "k8s": "Kubernetes manifests",
    "docker": "Docker configuration",
    ".github": "GitHub workflows / config",
    "ci": "CI/CD configuration",
    "plugins": "Plugin system",
    "extensions": "Extensions / addons",
    "workers": "Background workers",
    "jobs": "Background jobs",
    "queues": "Message queues",
    "events": "Event handlers",
    "providers": "Service providers",
    "stores": "State stores",
    "state": "State management",
    "context": "React context providers",
    "graphql": "GraphQL schema / resolvers",
    "proto": "Protocol buffer definitions",
    "grpc": "gRPC service definitions",
    "cmd": "CLI commands (Go convention)",
    "internal": "Internal packages (Go convention)",
    "pkg": "Public packages (Go convention)",
}

# Dependency-to-summary mapping
DEPENDENCY_INSIGHTS: dict[str, str] = {
    "next-auth": "Authentication uses NextAuth",
    "@auth/core": "Authentication uses Auth.js",
    "passport": "Authentication uses Passport.js",
    "jsonwebtoken": "JWT-based authentication",
    "prisma": "Database uses Prisma ORM",
    "@prisma/client": "Database uses Prisma ORM",
    "drizzle-orm": "Database uses Drizzle ORM",
    "typeorm": "Database uses TypeORM",
    "sequelize": "Database uses Sequelize ORM",
    "mongoose": "Database uses Mongoose (MongoDB)",
    "stripe": "Payments use Stripe",
    "@stripe/stripe-js": "Payments use Stripe",
    "tailwindcss": "Styling uses Tailwind CSS",
    "styled-components": "Styling uses styled-components",
    "@emotion/react": "Styling uses Emotion CSS-in-JS",
    "zustand": "State management uses Zustand",
    "redux": "State management uses Redux",
    "@reduxjs/toolkit": "State management uses Redux Toolkit",
    "jotai": "State management uses Jotai",
    "recoil": "State management uses Recoil",
    "socket.io": "Real-time communication via Socket.io",
    "ws": "WebSocket support",
    "bull": "Background jobs use Bull queue",
    "bullmq": "Background jobs use BullMQ",
    "redis": "Redis for caching / sessions",
    "ioredis": "Redis client (ioredis)",
    "aws-sdk": "AWS SDK integration",
    "@aws-sdk/client-s3": "AWS S3 file storage",
    "resend": "Email via Resend",
    "nodemailer": "Email via Nodemailer",
    "sentry": "Error tracking via Sentry",
    "@sentry/nextjs": "Error tracking via Sentry",
    "zod": "Schema validation uses Zod",
    "yup": "Schema validation uses Yup",
    "jest": "Testing uses Jest",
    "vitest": "Testing uses Vitest",
    "playwright": "E2E testing uses Playwright",
    "cypress": "E2E testing uses Cypress",
    # Python
    "django": "Web framework is Django",
    "flask": "Web framework is Flask",
    "fastapi": "Web framework is FastAPI",
    "sqlalchemy": "Database uses SQLAlchemy ORM",
    "alembic": "Database migrations use Alembic",
    "celery": "Background tasks use Celery",
    "pydantic": "Data validation uses Pydantic",
    "pytest": "Testing uses pytest",
    "httpx": "HTTP client uses httpx",
    "requests": "HTTP client uses requests",
    "boto3": "AWS SDK (boto3)",
    "torch": "Machine learning uses PyTorch",
    "tensorflow": "Machine learning uses TensorFlow",
    "scikit-learn": "ML uses scikit-learn",
    "pandas": "Data processing uses pandas",
    "numpy": "Numerical computing uses NumPy",
    "openai": "OpenAI API integration",
    "langchain": "LLM orchestration via LangChain",
    "anthropic": "Anthropic API integration",
}


def analyze_architecture(
    fs: FilesystemResult,
    pkg: PackageResult,
    root: Path,
) -> ArchitectureResult:
    """Analyze the project architecture from scan results."""
    result = ArchitectureResult()

    # Determine project type
    if pkg.framework:
        version_str = f" {pkg.framework_version}" if pkg.framework_version else ""
        type_parts = [pkg.framework + version_str]
    else:
        type_parts = [pkg.language or "Unknown"]

    # Detect project nature from directories and files
    has_api = any(
        d.relative.endswith("/api") or d.relative == "api"
        for d in fs.directories
    )
    has_frontend = any(
        d.relative in {"components", "pages", "app", "src/components", "src/pages"}
        for d in fs.directories
    )
    has_cli = any(
        f.relative in {"cli.py", "main.py", "__main__.py"}
        or "/cli/" in f.relative or "/commands/" in f.relative
        for f in fs.files
    )

    if has_frontend and has_api:
        type_parts.append("Full-Stack")
    elif has_api:
        type_parts.append("API")
    elif has_frontend:
        type_parts.append("Frontend")
    elif has_cli:
        type_parts.append("CLI")

    # Check for SaaS indicators
    all_deps = set(pkg.dependencies.keys()) | set(pkg.dev_dependencies.keys())
    saas_deps = {"stripe", "@stripe/stripe-js", "next-auth", "@auth/core", "prisma"}
    if saas_deps & all_deps:
        type_parts.append("SaaS")

    result.project_type = " ".join(type_parts)

    # Generate summary points from dependencies
    for dep_name, insight in DEPENDENCY_INSIGHTS.items():
        if dep_name in all_deps:
            result.summary_points.append(insight)

    # Add directory-based insights
    for d in fs.directories:
        dirname = d.relative.split("/")[-1]
        if dirname == "api" and has_frontend:
            result.summary_points.append("API routes colocated with frontend")

    # Detect entrypoints (only at root or shallow depth, skip test/docs/examples)
    entrypoint_names = {
        "main.py", "app.py", "manage.py", "wsgi.py", "asgi.py",
        "index.ts", "index.js", "main.ts", "main.js",
        "server.ts", "server.js", "main.go", "main.rs",
        "Main.java", "Program.cs", "__main__.py",
    }
    skip_prefixes = {"docs", "docs_src", "examples", "tests", "test", "spec", "e2e"}
    for f in fs.files:
        fname = f.relative.split("/")[-1]
        if fname in entrypoint_names:
            parts = f.relative.split("/")
            # Skip if file is inside a docs/test/example directory
            if parts[0] in skip_prefixes and len(parts) > 2:
                continue
            result.entrypoints.append(f.relative)
    # Cap entrypoints to keep output clean
    result.entrypoints = result.entrypoints[:10]

    # Build architecture layers
    layers = []
    layer_map = {
        "Frontend": {"components", "pages", "app", "views", "templates"},
        "API": {"api", "routes", "controllers", "endpoints"},
        "Services": {"services", "lib", "utils", "helpers"},
        "Models": {"models", "schemas", "types", "entities"},
        "Database": {"prisma", "db", "database", "migrations"},
        "Infrastructure": {"deploy", "infra", "terraform", "k8s", "docker"},
    }

    dir_names = set()
    for d in fs.directories:
        parts = d.relative.split("/")
        if len(parts) == 1:
            dir_names.add(parts[0])

    for layer, indicators in layer_map.items():
        if indicators & dir_names:
            layers.append(layer)

    result.architecture_layers = layers

    # Deduplicate summary points
    seen = set()
    unique = []
    for point in result.summary_points:
        if point not in seen:
            seen.add(point)
            unique.append(point)
    result.summary_points = unique

    return result


@dataclass
class DetailedArchitecture:
    """Extended architecture analysis for `ctx architecture` command."""
    project_name: str
    project_type: str
    language: str
    framework: str
    package_manager: str
    entrypoints: list[str]
    layers: dict[str, list[str]]  # Layer name -> matching directory/file paths
    database_tech: str
    auth_tech: str
    state_tech: str
    api_style: str  # REST, GraphQL, gRPC, CLI
    key_directories: list[tuple[str, str]]  # (dir, purpose)
    recommendations: list[str]


def analyze_detailed_architecture(
    fs: FilesystemResult,
    pkg: PackageResult,
    arch: ArchitectureResult,
    root: Path,
) -> DetailedArchitecture:
    """Build detailed architectural breakdown for `ctx architecture` command."""

    # Categorize directory paths into layers
    layers: dict[str, list[str]] = {
        "Entry & Routing": arch.entrypoints,
        "Presentation / UI": [],
        "Business Logic & Services": [],
        "Data & Storage": [],
        "Configuration & Infra": [],
    }

    key_dirs: list[tuple[str, str]] = []
    for d in fs.directories:
        rel = d.relative
        dirname = rel.split("/")[-1].lower()
        if dirname in DIR_PURPOSES:
            key_dirs.append((rel, DIR_PURPOSES[dirname]))

        if dirname in {"components", "pages", "views", "templates", "ui", "styles"}:
            layers["Presentation / UI"].append(rel)
        elif dirname in {"services", "lib", "utils", "helpers", "controllers", "hooks"}:
            layers["Business Logic & Services"].append(rel)
        elif dirname in {"models", "prisma", "db", "database", "migrations", "schemas"}:
            layers["Data & Storage"].append(rel)
        elif dirname in {"config", "deploy", "infra", ".github", "docker"}:
            layers["Configuration & Infra"].append(rel)

    # Detect technologies
    all_deps = {**pkg.dependencies, **pkg.dev_dependencies}
    db_tech = "None detected"
    for db_dep in ["prisma", "@prisma/client", "drizzle-orm", "sqlalchemy", "mongoose", "typeorm", "sequelize", "pg", "sqlite3"]:
        if db_dep in all_deps:
            db_tech = db_dep
            break

    auth_tech = "None detected"
    for auth_dep in ["next-auth", "@auth/core", "passport", "jsonwebtoken", "pyjwt", "clerk", "auth0"]:
        if auth_dep in all_deps:
            auth_tech = auth_dep
            break

    state_tech = "None detected"
    for state_dep in ["zustand", "redux", "@reduxjs/toolkit", "jotai", "recoil", "pinia", "pydantic"]:
        if state_dep in all_deps:
            state_tech = state_dep
            break

    api_style = "CLI" if "CLI" in arch.project_type else ("REST / Web" if "API" in arch.project_type or "Full-Stack" in arch.project_type else "Library / Package")
    if "graphql" in all_deps:
        api_style = "GraphQL"

    recs = []
    if not fs.important_files or not any("README" in f for f in fs.important_files):
        recs.append("Consider adding a README.md to document the project.")
    if not (root / ".env.example").exists() and (root / ".env").exists():
        recs.append("Create a .env.example file so team members know required environment variables.")

    return DetailedArchitecture(
        project_name=pkg.project_name or root.name,
        project_type=arch.project_type,
        language=pkg.language or "Unknown",
        framework=pkg.framework or "None",
        package_manager=pkg.package_manager or "None",
        entrypoints=arch.entrypoints,
        layers={k: v[:8] for k, v in layers.items() if v},
        database_tech=db_tech,
        auth_tech=auth_tech,
        state_tech=state_tech,
        api_style=api_style,
        key_directories=key_dirs[:10],
        recommendations=recs,
    )

