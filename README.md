# AgenticTesting

<p align="center">
  <strong>An agentic testing framework that improves a target repository's tests until a requested line coverage percentage is reached.</strong>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
  <img alt="Status" src="https://img.shields.io/badge/status-experimental-orange">
</p>

---

## Overview

AgenticTesting takes two primary inputs:

- a path to a repository
- a target line coverage percentage

It then runs an agent pipeline that measures coverage, plans the next test improvement, edits the target repository, reviews the result, and repeats until the target coverage is reached or the iteration limit is exhausted.

The project provides a small but extensible foundation for:

- assigning specialized agent roles such as planners, reviewers, and validators
- measuring line coverage with `pytest-cov`
- running a modern local web UI for test-run configuration
- running small local LLMs through llama.cpp or Hugging Face Transformers
- using API-backed providers such as OpenAI and Anthropic
- giving agents constrained tools to inspect, edit, and test a repository
- storing local user preferences and encrypted provider credentials in SQLite
- connecting to SQL databases through a shared adapter interface
- caching database query results with in-memory or Redis-backed caches
- testing agent workflows without live model calls through a deterministic fake agent

The goal is to build a practical layer around AI-assisted test generation and review while keeping the supporting infrastructure testable, replaceable, and easy to reason about.

## Features

### Agentic coverage loop

The main framework loop is:

1. **Analyzer** runs coverage and summarizes the current test gap.
2. **Planner** chooses the next focused test-improvement task.
3. **Implementer** edits the target repository through constrained tools.
4. **Reviewer** inspects the result and gives feedback for the next iteration.
5. **Coverage runner** measures line coverage again.

The loop stops when the target percentage is reached.

### Model providers

The LLM provider layer separates model execution from agent behavior. The same pipeline can run with local models or remote APIs.

Supported providers:

- `llama.cpp` through `llama-cpp-python` for local GGUF models
- Hugging Face Transformers for local or cached model ids
- OpenAI through the official `openai` package
- Anthropic through the official `anthropic` package
- fake provider for deterministic tests and dry runs

Provider packages are optional because local model stacks are large and API integrations require separate credentials. If a provider is selected without its dependency installed, AgenticTesting raises a clear setup error.

### Local application storage

The browser UI stores local application state in SQLite:

- one local user account
- last repository path
- last selected coverage target
- selected provider and model fields
- encrypted OpenAI and Anthropic API keys
- recent run history

Passwords are salted and hashed with PBKDF2-HMAC-SHA256. API keys are encrypted at rest with Fernet and decrypted only when constructing the selected provider.

### Constrained coding agent

The implementer agent interacts with the target repository through a controlled tool protocol. The model can request actions, but the Python workspace layer decides whether they are allowed.

Available tools:

- list repository files
- read a relative file path
- replace exact text in a file
- write a file
- run explicitly allowed commands, such as `pytest`

The agent rejects paths that escape the configured repository root and blocks commands outside the allowlist.

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

### Local Web UI

The project includes a local web UI for configuring and starting agentic coverage runs. It validates:

- repository path selected through the native folder picker or the built-in fallback browser
- target line coverage percentage
- project type and test framework profile
- provider-specific model fields
- API-key availability for OpenAI and Anthropic

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
│   ├── frontend/              # Debug UI, agent implementations, and LLM providers
│   ├── info/                  # Agent instruction prompts
│   ├── agentic_testing_cli.py # Coverage-improvement CLI
│   ├── local_agent_cli.py     # CLI for local model repository editing
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
- `pytest-cov` in target repositories you want AgenticTesting to improve

Optional packages depend on which integrations you use:

| Integration | Package |
| --- | --- |
| OpenAI provider | `openai` |
| Anthropic provider | `anthropic` |
| llama.cpp local models | `llama-cpp-python` |
| Hugging Face local models | `transformers`, `torch`, `accelerate` |
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

Install the development dependencies:

```bash
pip install pytest pytest-cov
```

Install optional dependencies as needed:

```bash
pip install openai anthropic llama-cpp-python transformers torch accelerate
```

Run the test suite:

```bash
pytest
```

## Running AgenticTesting

### Web UI

Start the local application:

```bash
python -m src.frontend.debug_ui
```

Then open:

```text
http://127.0.0.1:8765
```

On first launch, create a local user. After that, the dashboard remembers your last repository, target line coverage, selected provider, model fields, encrypted API keys, and recent runs.

The UI supports:

- selecting a repository through a native folder picker on macOS
- falling back to the in-page folder browser when a native picker is unavailable
- project profiles for Python, .NET, C++ GoogleTest, JavaScript/TypeScript Jest, and custom setups
- fake dry runs
- llama.cpp GGUF model paths
- Hugging Face model ids
- OpenAI models and encrypted API key storage
- Anthropic models and encrypted API key storage

### Project Profiles

The coverage command is the command AgenticTesting runs inside the selected repository to measure whether the target line coverage has been reached. Different ecosystems need different commands and different test styles, so the UI now asks for a project profile instead of making you type the command first.

Built-in profiles:

| Project profile | Test style guidance | Default coverage command |
| --- | --- | --- |
| Python / pytest | Creates pytest-style tests | `pytest --cov=. --cov-report=term-missing` |
| .NET | Follows existing xUnit, NUnit, or MSTest projects | `dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=opencover` |
| C++ / GoogleTest | Creates `TEST` / `TEST_F` GoogleTest cases | `gcovr --txt` |
| JavaScript or TypeScript / Jest | Creates Jest tests | `npm test -- --coverage` |
| Custom | Uses your override command and existing repo conventions | `pytest --cov=. --cov-report=term-missing` |

The selected profile also changes the instructions sent to the planner and implementer agents, so a .NET repository gets .NET test guidance and a C++ repository gets GoogleTest guidance.

The advanced coverage command field remains editable for repositories with custom build or coverage tooling.

### Folder Selection

The UI runs as a local Python server, so it can help select a repository folder on the same machine.

On macOS, the **Browse** button opens the native Finder folder picker through `osascript`. If the native picker is unavailable or fails, the dashboard keeps working and shows the built-in folder browser fallback instead.

### CLI

### Dry run with the fake provider

The CLI is still available for automation. Start with the fake provider to verify coverage measurement. This does not make useful code changes, but it confirms the framework can run against a repository:

```bash
python -m src.agentic_testing_cli \
  /path/to/project \
  80 \
  --provider fake \
  --max-iterations 1
```

### llama.cpp with a GGUF model

Install the Python bindings:

```bash
pip install llama-cpp-python
```

Then run a local GGUF model:

```bash
python -m src.agentic_testing_cli \
  /path/to/project \
  80 \
  --provider llama.cpp \
  --model-path /path/to/model.gguf \
  --max-iterations 5 \
  --implementer-max-steps 8
```

Useful laptop-friendly GGUF models include small instruct-tuned models such as TinyLlama, Qwen2.5 Coder 1.5B, or Phi-family coding models in quantized GGUF form.

### Hugging Face Transformers

Install the local model stack:

```bash
pip install transformers torch accelerate
```

Run a small model by id:

```bash
python -m src.agentic_testing_cli \
  /path/to/project \
  80 \
  --provider huggingface \
  --model-id TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --device cpu
```

On Apple Silicon, try `--device mps` if your installed PyTorch build supports it. On CUDA machines, use the device configuration supported by your local Transformers setup.

### OpenAI

Install the provider:

```bash
pip install openai
```

In the web UI, paste the API key once. It is encrypted in the local SQLite database and reused for later runs.

CLI runs can still use the `OPENAI_API_KEY` environment variable:

```bash
python -m src.agentic_testing_cli \
  /path/to/project \
  85 \
  --provider openai \
  --model gpt-4.1-mini
```

### Anthropic

Install the provider:

```bash
pip install anthropic
```

In the web UI, paste the API key once. It is encrypted in the local SQLite database and reused for later runs.

CLI runs can still use the `ANTHROPIC_API_KEY` environment variable:

```bash
python -m src.agentic_testing_cli \
  /path/to/project \
  85 \
  --provider anthropic \
  --model claude-3-5-haiku-latest
```

### Command safety

By default, the implementer may only run commands whose executable is:

```text
pytest
```

You can allow additional command executables explicitly:

```bash
python -m src.agentic_testing_cli \
  /path/to/project \
  80 \
  --provider llama.cpp \
  --model-path /path/to/model.gguf \
  --allow-command pytest \
  --allow-command ruff
```

The command allowlist checks the executable name only. The agent still cannot access files outside the configured repository path through workspace file tools.

### Custom coverage command

The default coverage command is:

```bash
pytest --cov=. --cov-report=term-missing
```

Override it when the target repository needs a different command:

```bash
python -m src.agentic_testing_cli \
  /path/to/project \
  90 \
  --provider openai \
  --coverage-command "pytest tests --cov=src --cov-report=term-missing"
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

## Local Data And Credentials

The UI creates local application files under:

```text
.agentic_testing/
├── app.db
└── secret.key
```

`app.db` stores users, preferences, encrypted API keys, and run history. `secret.key` encrypts and decrypts provider API keys. Keep both files private and do not commit them.

Passwords are not stored in plain text. They are stored as salted PBKDF2-HMAC-SHA256 hashes.

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

- local app user storage and password hashing
- encrypted API-key storage
- UI form parsing and provider config loading
- local LLM provider selection
- constrained repository workspace behavior
- fake local coding-agent edit runs
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
