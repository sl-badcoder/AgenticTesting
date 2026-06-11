<h1 align="center">AgenticTesting</h1>

<p align="center">
  <strong>Choose a repo. Set a coverage target. Let agents grow the test suite.</strong>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
  <img alt="Status" src="https://img.shields.io/badge/status-experimental-orange">
</p>

---

## ✨ What It Does

AgenticTesting is a local-first framework for AI-assisted test generation. It measures a repository's current line coverage, asks agents to reason about the gaps, lets them add or improve tests through constrained repo tools, and repeats until the requested target is reached.

The core loop is intentionally simple:

| Step | Agent / System | Job |
| --- | --- | --- |
| 1 | Coverage runner | Measures current line coverage |
| 2 | Analyzer | Finds useful test gaps |
| 3 | Planner | Chooses the next focused test task |
| 4 | Implementer | Edits tests through safe repo tools |
| 5 | Reviewer | Reviews the result and guides the next loop |

The loop stops when the requested line coverage is reached or the iteration limit is exhausted.

## 🚀 Quick Start

```bash
git clone [<repository-url>](https://github.com/sl-badcoder/AgenticTesting.git)
cd PythonProject2

python -m venv .venv
source .venv/bin/activate

pip install pytest pytest-cov cryptography
python -m src.frontend.debug_ui
```

Open:

```text
http://127.0.0.1:8765
```

On first launch, create a local user. Then select a repository, target coverage, project type, provider, and model.

## 🧭 Highlights

The UI is the primary workflow. It is designed for repeated local use: pick a project, tune the target, choose a model, run the agents, inspect the result, and come back later with your settings still saved.

| Area | Support |
| --- | --- |
| UI | Local browser dashboard with saved settings |
| Repo picker | macOS Finder dialog via `osascript`, plus in-page fallback |
| Local models | llama.cpp GGUF, Hugging Face Transformers |
| API models | OpenAI, Anthropic |
| Project profiles | Python, .NET, C++ GoogleTest, Jest, Custom |
| Credential storage | SQLite + encrypted API keys |
| Password storage | Salted PBKDF2-HMAC-SHA256 hashes |
| Repo safety | Relative file tools and command allowlists |

## 🖥️ Web UI

Start the UI:

```bash
python -m src.frontend.debug_ui
```

The dashboard stores useful local state:

| Stored item | Purpose |
| --- | --- |
| Last repo | Pre-fills the next run |
| Target coverage | Reuses your preferred threshold |
| Provider/model | Keeps your LLM setup |
| API keys | Encrypted locally for OpenAI/Anthropic |
| Run history | Shows recent results |

Local files are created under:

```text
.agentic_testing/
├── app.db
└── secret.key
```

Keep this folder private. It is ignored by Git.

## 🧪 Project Profiles

The selected profile controls the default coverage command and the test style guidance sent to the agents.

| Profile | Test style | Coverage command |
| --- | --- | --- |
| Python / pytest | `pytest` tests | `pytest --cov=. --cov-report=term-missing` |
| .NET | xUnit, NUnit, or MSTest | `dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=opencover` |
| C++ / GoogleTest | `TEST` / `TEST_F` cases | `gcovr --txt` |
| JS/TS / Jest | Jest tests | `npm test -- --coverage` |
| Custom | Existing repo conventions | Editable command |

The command is still editable in the UI for custom build systems.

## 🤖 Providers

Use a hosted model when you want stronger reasoning, or a local model when you want everything to stay on your laptop.

| Provider | Install | Notes |
| --- | --- | --- |
| Fake | Built in | Dry runs and tests |
| OpenAI | `pip install openai` | API key saved encrypted in UI |
| Anthropic | `pip install anthropic` | API key saved encrypted in UI |
| llama.cpp | `pip install llama-cpp-python` | Uses local GGUF model paths |
| Hugging Face | `pip install transformers torch accelerate` | Uses model ids and local cache |

## ⚙️ CLI

The UI is the main workflow, but a CLI exists for automation:

```bash
python -m src.agentic_testing_cli /path/to/repo 80 --provider fake
```

Examples:

```bash
python -m src.agentic_testing_cli /path/to/repo 85 \
  --provider openai \
  --model gpt-4.1-mini

python -m src.agentic_testing_cli /path/to/repo 80 \
  --provider llama.cpp \
  --model-path /path/to/model.gguf
```

## 🧱 Architecture

The code is split between the app shell, the agentic testing loop, provider integrations, and reusable database/cache infrastructure.

```text
src/
├── app/                  # Local user, credentials, preferences
├── core/                 # Coverage loop, workspace tools, project profiles
├── database/             # Database adapters and cache layer
├── frontend/             # Web UI, agents, LLM providers
├── agentic_testing_cli.py
└── local_agent_cli.py
```

Core modules:

| Module | Responsibility |
| --- | --- |
| `src/core/agentic_testing.py` | Main analyzer/planner/implementer/reviewer loop |
| `src/core/coverage.py` | Coverage command runner and parser |
| `src/core/workspace.py` | Safe file and command operations |
| `src/core/project_profiles.py` | Project profile presets |
| `src/app/storage.py` | SQLite app state |
| `src/app/security.py` | Password hashing and API-key encryption |

## ✅ Testing

```bash
pytest
```

Current coverage includes:

| Area | Covered |
| --- | --- |
| UI parsing/rendering | Yes |
| User/password storage | Yes |
| Encrypted API keys | Yes |
| Provider factory | Yes |
| Coverage parsing | Yes |
| Workspace safety | Yes |
| Database/cache adapters | Yes |

## 🔐 Security Notes

The UI stores secrets locally because API-backed providers need reusable credentials. Passwords use a different model: they are never encrypted for later recovery, only hashed for verification.

| Data | Storage |
| --- | --- |
| Passwords | Salted PBKDF2-HMAC-SHA256 hash |
| API keys | Fernet-encrypted ciphertext |
| App DB | `.agentic_testing/app.db` |
| Encryption key | `.agentic_testing/secret.key` |

API keys must be decryptable so the selected provider can use them. Passwords are never decrypted because they are not stored reversibly.

## 📄 License

Released under the [MIT License](LICENSE).
