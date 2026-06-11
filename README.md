# AgenticTesting

<p align="center">
  <strong>An experimental agentic testing framework for planning, reviewing, validating, and debugging software test coverage.</strong>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
  <img alt="Status" src="https://img.shields.io/badge/status-experimental-orange">
</p>

---

## Overview

AgenticTesting is a Python framework that explores how AI agents can support automated testing workflows. The project provides a small but extensible foundation for:

- assigning specialized agent roles such as planners, reviewers, and validators
- running a lightweight debug UI for test-run configuration
- connecting to SQL databases through a shared adapter interface
- caching database query results with in-memory or Redis-backed caches
- testing agent workflows without live model calls through a deterministic fake agent

The goal is to build a practical layer around AI-assisted test generation and review while keeping the supporting infrastructure testable, replaceable, and easy to reason about.

## Features

### Agent workflow primitives

- `BaseAgent` defines the shared interface for model-backed agents.
- `OpenAIAgent` and `ClaudeAgent` provide integration points for external AI providers.
- `FakeAgent` makes agent behavior deterministic in tests.
- `Plan`, `Reviewer`, and `Validation` wrap agents into dedicated testing roles.

### Database adapter layer

AgenticTesting includes a database abstraction with support for:

- SQLite
- PostgreSQL / Postgres
- MySQL / MariaDB

All database vendors expose the same core operations:

- `connect`
- `close`
- `execute`
- `fetch_one`
- `fetch_all`
- `begin_transaction`
- `commit`
- `rollback`

### Query caching

The cache layer can be used independently or wrapped around a database connection with `CachedDatabaseConnection`.

Supported cache backends:

- in-memory cache for local development and tests
- Redis cache for shared or persistent cache use cases

Read queries are cached by query text, parameters, and database name. Mutating operations and transaction boundaries clear the cache so stale query results are not reused.

### Debug UI

The project includes a minimal local web UI for configuring debug runs. It validates:

- project folder path
- desired line coverage percentage

Run it with:

```bash
python -m src.frontend.debug_ui
```

Then open:

```text
http://127.0.0.1:8765
```

## Project Structure

```text
.
├── src/
│   ├── core/                  # Planner, reviewer, analyzer, and validation roles
│   ├── database/              # Database adapters, factories, cache wrappers
│   ├── frontend/              # Debug UI and agent implementations
│   ├── info/                  # Agent instruction prompts
│   └── main.py                # Early project entry point
├── test/
│   ├── database/              # Database and cache tests
│   └── frontend/              # Debug UI and agent tests
├── LICENSE
└── README.md
```

## Requirements

- Python 3.10 or newer
- `pytest` for running the test suite

Optional packages depend on which integrations you use:

| Integration | Package |
| --- | --- |
| OpenAI agent integration | `openai-agents` |
| Claude agent integration | `anthropic` |
| PostgreSQL | `psycopg` |
| MySQL / MariaDB | `mysql-connector-python` |
| Redis cache | `redis` |

## Quick Start

Clone the repository:

```bash
git clone <repository-url>
cd PythonProject2
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the development dependency:

```bash
pip install pytest
```

Install optional dependencies as needed:

```bash
pip install anthropic openai-agents psycopg mysql-connector-python redis
```

Run the test suite:

```bash
pytest
```

## Usage Examples

### Create a SQLite connection

```python
from src.database.base import DatabaseConfig
from src.database.factory import create_database_connection

config = DatabaseConfig(vendor="sqlite", database=":memory:")

with create_database_connection(config) as database:
    database.execute("create table checks (id integer primary key, name text)")
    database.execute("insert into checks (name) values (?)", ("coverage",))

    row = database.fetch_one("select * from checks where name = ?", ("coverage",))
    print(row)
```

### Add an in-memory query cache

```python
from src.database.base import DatabaseConfig
from src.database.cache import CacheConfig
from src.database.cache.cached_database import CachedDatabaseConnection
from src.database.cache.factory import create_cache_connection
from src.database.factory import create_database_connection

database = create_database_connection(
    DatabaseConfig(vendor="sqlite", database=":memory:")
)

cache = create_cache_connection(
    CacheConfig(vendor="memory", namespace="agentic_testing")
)

cached_database = CachedDatabaseConnection(
    database=database,
    cache=cache,
    ttl_seconds=60,
)
```

### Test an agent workflow without model calls

```python
import asyncio

from src.frontend.agents.FakeAgent import FakeAgent

agent = FakeAgent(responses=["Create unit tests for the database factory."])

result = asyncio.run(agent.run("Plan the next test task."))
print(result)
```

## Environment Variables

Provider-backed agents expect the relevant API keys to be available in the environment.

```bash
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."
```

## Testing

Run all tests:

```bash
pytest
```

Run a focused test group:

```bash
pytest test/database
pytest test/frontend
```

The current tests cover:

- database connection factories
- SQLite, PostgreSQL, and MySQL adapter behavior
- in-memory and Redis cache behavior
- cached database invalidation
- debug UI form parsing and rendering
- deterministic fake-agent responses

## Roadmap

- Complete the main orchestration flow for planning, reviewing, validating, and applying test improvements.
- Add a formal package configuration with pinned development dependencies.
- Expand provider integrations and normalize async behavior across agents.
- Add richer debug-run persistence and reporting.
- Document end-to-end examples once the agent pipeline stabilizes.

## Contributing

Contributions are welcome. For now, the most useful improvements are:

- focused tests for existing behavior
- clearer agent orchestration boundaries
- adapter fixes for real database and cache backends
- documentation updates as workflows become stable

Before opening a pull request, run:

```bash
pytest
```

## License

This project is released under the [MIT License](LICENSE).
