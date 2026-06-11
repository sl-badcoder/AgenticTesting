import asyncio
import html
import hmac
import json
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from src.app.storage import AppDatabase, User, UserPreferences
from src.core.agentic_testing import AgenticTestingConfig, AgenticTestingRunner
from src.core.project_profiles import PROJECT_PROFILES, get_project_profile
from src.frontend.llm.factory import create_llm_provider


@dataclass(frozen=True)
class DebugRunConfig:
    project_folder: str
    coverage_percentage: int


@dataclass(frozen=True)
class UiRunConfig:
    repo_path: str
    target_coverage: int
    project_profile: str
    test_framework: str
    provider: str
    model: str
    model_path: str
    model_id: str
    device: str
    api_key: str
    coverage_command: str
    max_iterations: int


def read_debug_config(form_data: dict[str, list[str]]) -> DebugRunConfig:
    project_folder = form_data.get("project_folder", [""])[0].strip()
    if not project_folder:
        raise ValueError("Project folder is required.")

    folder_path = Path(project_folder).expanduser()
    if not folder_path.exists() or not folder_path.is_dir():
        raise ValueError("Project folder must be an existing folder.")

    try:
        coverage_percentage = int(form_data.get("coverage_percentage", [""])[0])
    except ValueError as error:
        raise ValueError("Line coverage target must be a number.") from error

    if not 0 <= coverage_percentage <= 100:
        raise ValueError("Line coverage target must be between 0 and 100.")

    return DebugRunConfig(
        project_folder=str(folder_path),
        coverage_percentage=coverage_percentage,
    )


def read_ui_run_config(form_data: dict[str, list[str]]) -> UiRunConfig:
    repo_path = _form_value(form_data, "repo_path").strip()
    if not repo_path:
        raise ValueError("Repository path is required.")

    resolved_repo = Path(repo_path).expanduser()
    if not resolved_repo.exists() or not resolved_repo.is_dir():
        raise ValueError("Repository path must be an existing folder.")

    try:
        target_coverage = int(_form_value(form_data, "target_coverage"))
    except ValueError as error:
        raise ValueError("Line coverage target must be a number.") from error

    if not 0 <= target_coverage <= 100:
        raise ValueError("Line coverage target must be between 0 and 100.")

    try:
        max_iterations = int(_form_value(form_data, "max_iterations") or "5")
    except ValueError as error:
        raise ValueError("Max iterations must be a number.") from error

    if not 1 <= max_iterations <= 25:
        raise ValueError("Max iterations must be between 1 and 25.")

    provider = _form_value(form_data, "provider") or "fake"
    if provider not in {"fake", "llama.cpp", "huggingface", "openai", "anthropic"}:
        raise ValueError("Unsupported provider selected.")

    project_profile = _form_value(form_data, "project_profile") or "python-pytest"
    if project_profile not in PROJECT_PROFILES:
        raise ValueError("Unsupported project type selected.")

    profile = get_project_profile(project_profile)
    coverage_command = _form_value(form_data, "coverage_command") or profile.coverage_command

    return UiRunConfig(
        repo_path=str(resolved_repo),
        target_coverage=target_coverage,
        project_profile=project_profile,
        test_framework=_form_value(form_data, "test_framework") or profile.test_framework,
        provider=provider,
        model=_form_value(form_data, "model"),
        model_path=_form_value(form_data, "model_path"),
        model_id=_form_value(form_data, "model_id"),
        device=_form_value(form_data, "device"),
        api_key=_form_value(form_data, "api_key"),
        coverage_command=coverage_command,
        max_iterations=max_iterations,
    )


def preferences_from_run_config(config: UiRunConfig) -> UserPreferences:
    return UserPreferences(
        last_repo_path=config.repo_path,
        target_coverage=config.target_coverage,
        project_profile=config.project_profile,
        test_framework=config.test_framework,
        provider=config.provider,
        model=config.model,
        model_path=config.model_path,
        model_id=config.model_id,
        device=config.device,
        coverage_command=config.coverage_command,
        max_iterations=config.max_iterations,
    )


def build_provider_config(
    config: UiRunConfig,
    database: AppDatabase,
    user_id: int,
) -> dict[str, object]:
    if config.provider == "llama.cpp":
        if not config.model_path:
            raise ValueError("A GGUF model path is required for llama.cpp.")
        return {
            "type": "llama.cpp",
            "model_path": config.model_path,
        }

    if config.provider == "huggingface":
        if not config.model_id:
            raise ValueError("A Hugging Face model id is required.")
        return {
            "type": "huggingface",
            "model_id": config.model_id,
            "device": config.device or None,
        }

    if config.provider in {"openai", "anthropic"}:
        if config.api_key:
            database.save_api_key(user_id, config.provider, config.api_key)
        api_key = database.get_api_key(user_id, config.provider)
        if not api_key:
            raise ValueError(f"An API key is required for {config.provider}.")
        return {
            "type": config.provider,
            "model": config.model or _default_api_model(config.provider),
            "api_key": api_key,
        }

    return {
        "type": "fake",
        "responses": [
            "Fake analyzer summary.",
            "Fake test improvement plan.",
            '{"actions": [], "final": "Fake implementer made no changes."}',
            "Fake reviewer feedback.",
        ],
    }


class AppRequestHandler(BaseHTTPRequestHandler):
    database: AppDatabase

    def do_GET(self) -> None:
        user = self._current_user()
        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)

        if parsed_url.path == "/browse-native":
            self._handle_native_browse(query)
            return

        if not self.database.has_users():
            self._send_html(render_signup_page())
            return

        if user is None:
            self._send_html(render_login_page())
            return

        selected_repo = _form_value(query, "selected_repo")
        browse_path = _form_value(query, "browse_path")
        self._send_html(
            render_dashboard(
                self.database,
                user,
                selected_repo=selected_repo or None,
                browse_path=browse_path or None,
            )
        )

    def _handle_native_browse(self, query: dict[str, list[str]]) -> None:
        user = self._current_user()
        if user is None:
            self._redirect("/")
            return

        start_path = _form_value(query, "start") or str(Path.home())
        try:
            selected_path = open_native_folder_dialog(start_path)
        except ValueError as error:
            self._send_html(
                render_dashboard(
                    self.database,
                    user,
                    error=f"{error} Use the folder fallback panel instead.",
                    browse_path=start_path,
                ),
                status=400,
            )
            return

        if selected_path:
            self._redirect(f"/?selected_repo={_url_quote(selected_path)}")
            return

        self._redirect(f"/?browse_path={_url_quote(start_path)}")

    def do_POST(self) -> None:
        form_data = self._read_form_data()
        action = _form_value(form_data, "action")

        try:
            if action == "signup":
                self._handle_signup(form_data)
            elif action == "login":
                self._handle_login(form_data)
            elif action == "logout":
                self._handle_logout()
            elif action == "run":
                self._handle_run(form_data)
            else:
                self._send_html(render_login_page(error="Unknown action."), status=400)
        except ValueError as error:
            user = self._current_user()
            if user:
                self._send_html(
                    render_dashboard(self.database, user, error=str(error)),
                    status=400,
                )
            elif self.database.has_users():
                self._send_html(render_login_page(error=str(error)), status=400)
            else:
                self._send_html(render_signup_page(error=str(error)), status=400)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _handle_signup(self, form_data: dict[str, list[str]]) -> None:
        if self.database.has_users():
            raise ValueError("A user already exists. Please sign in.")
        user = self.database.create_user(
            username=_form_value(form_data, "username"),
            password=_form_value(form_data, "password"),
        )
        self._send_html(
            render_dashboard(self.database, user, message="User created."),
            cookie=self._session_cookie(user.id),
        )

    def _handle_login(self, form_data: dict[str, list[str]]) -> None:
        user = self.database.authenticate_user(
            username=_form_value(form_data, "username"),
            password=_form_value(form_data, "password"),
        )
        if user is None:
            raise ValueError("Invalid username or password.")
        self._send_html(
            render_dashboard(self.database, user, message="Signed in."),
            cookie=self._session_cookie(user.id),
        )

    def _handle_logout(self) -> None:
        self._send_html(render_login_page(message="Signed out."), cookie="session=; Max-Age=0; Path=/; HttpOnly")

    def _handle_run(self, form_data: dict[str, list[str]]) -> None:
        user = self._current_user()
        if user is None:
            raise ValueError("Please sign in first.")

        run_config = read_ui_run_config(form_data)
        self.database.save_preferences(user.id, preferences_from_run_config(run_config))
        provider = create_llm_provider(
            build_provider_config(run_config, self.database, user.id)
        )
        runner = AgenticTestingRunner(
            config=AgenticTestingConfig(
                repository_path=run_config.repo_path,
                target_line_coverage=run_config.target_coverage,
                max_iterations=run_config.max_iterations,
                coverage_command=run_config.coverage_command,
                allowed_commands=_allowed_commands_for_run(run_config),
                project_profile=run_config.project_profile,
                test_framework=run_config.test_framework,
            ),
            provider=provider,
        )
        result = asyncio.run(runner.run())
        self.database.add_run_history(
            user_id=user.id,
            repo_path=run_config.repo_path,
            target_coverage=run_config.target_coverage,
            final_coverage=result.final_line_coverage,
            provider=run_config.provider,
            reached_target=result.reached_target,
        )
        self._send_html(
            render_dashboard(
                self.database,
                user,
                result={
                    "final_line_coverage": result.final_line_coverage,
                    "target_line_coverage": result.target_line_coverage,
                    "reached_target": result.reached_target,
                    "iterations": len(result.iterations),
                },
                message="Run completed.",
            )
        )

    def _current_user(self) -> User | None:
        raw_cookie = self.headers.get("Cookie")
        if not raw_cookie:
            return None

        parsed = cookies.SimpleCookie(raw_cookie)
        morsel = parsed.get("session")
        if morsel is None:
            return None

        user_id = self._verify_session(morsel.value)
        if user_id is None:
            return None

        user = self.database.get_first_user()
        if user and user.id == user_id:
            return user
        return None

    def _session_cookie(self, user_id: int) -> str:
        key = self.database.secret_box._load_or_create_key()
        payload = str(user_id)
        signature = hmac.new(key, payload.encode("utf-8"), "sha256").hexdigest()
        return f"session={payload}:{signature}; Path=/; HttpOnly; SameSite=Lax"

    def _verify_session(self, value: str) -> int | None:
        try:
            payload, signature = value.split(":", 1)
            user_id = int(payload)
        except ValueError:
            return None

        key = self.database.secret_box._load_or_create_key()
        expected = hmac.new(key, payload.encode("utf-8"), "sha256").hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        return user_id

    def _read_form_data(self) -> dict[str, list[str]]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        return parse_qs(raw_body)

    def _send_html(
        self,
        body: str,
        status: int = 200,
        cookie: str | None = None,
    ) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(encoded)

    def _redirect(self, location: str) -> None:
        self.send_response(303)
        self.send_header("Location", location)
        self.end_headers()


def render_signup_page(error: str | None = None) -> str:
    return render_shell(
        title="Create User",
        content=f"""
        <section class="auth-shell">
          <div class="brand-panel">
            <p class="eyebrow">AgenticTesting</p>
            <h1>Set up your local testing workspace.</h1>
            <p>Create one local user to keep provider credentials, repository defaults, and run history on this machine.</p>
          </div>
          <form class="auth-card" method="post">
            <input type="hidden" name="action" value="signup">
            {_notice(error, "error")}
            <label>Username<input name="username" autocomplete="username" required></label>
            <label>Password<input name="password" type="password" autocomplete="new-password" minlength="8" required></label>
            <button type="submit">Create user</button>
          </form>
        </section>
        """,
    )


def render_login_page(
    error: str | None = None,
    message: str | None = None,
) -> str:
    return render_shell(
        title="Sign In",
        content=f"""
        <section class="auth-shell">
          <div class="brand-panel">
            <p class="eyebrow">AgenticTesting</p>
            <h1>Welcome back.</h1>
            <p>Sign in to continue with your saved provider settings and recent repositories.</p>
          </div>
          <form class="auth-card" method="post">
            <input type="hidden" name="action" value="login">
            {_notice(error, "error")}
            {_notice(message, "success")}
            <label>Username<input name="username" autocomplete="username" required></label>
            <label>Password<input name="password" type="password" autocomplete="current-password" required></label>
            <button type="submit">Sign in</button>
          </form>
        </section>
        """,
    )


def render_dashboard(
    database: AppDatabase,
    user: User,
    error: str | None = None,
    message: str | None = None,
    result: dict[str, object] | None = None,
    selected_repo: str | None = None,
    browse_path: str | None = None,
) -> str:
    preferences = database.get_preferences(user.id)
    repo_value = selected_repo or preferences.last_repo_path
    profile = get_project_profile(preferences.project_profile)
    coverage_command = preferences.coverage_command or profile.coverage_command
    history = database.list_run_history(user.id)
    openai_saved = database.has_api_key(user.id, "openai")
    anthropic_saved = database.has_api_key(user.id, "anthropic")
    result_json = json.dumps(result, indent=2) if result else ""

    history_rows = "".join(
        f"""
        <tr>
          <td>{_escape(entry.repo_path)}</td>
          <td>{entry.target_coverage}%</td>
          <td>{entry.final_coverage}%</td>
          <td>{_escape(entry.provider)}</td>
          <td>{'Reached' if entry.reached_target else 'Open'}</td>
        </tr>
        """
        for entry in history
    ) or '<tr><td colspan="5">No runs yet.</td></tr>'

    return render_shell(
        title="Dashboard",
        content=f"""
        <header class="topbar">
          <div>
            <p class="eyebrow">AgenticTesting</p>
            <h1>Coverage workspace</h1>
          </div>
          <form method="post">
            <input type="hidden" name="action" value="logout">
            <button class="secondary" type="submit">Sign out</button>
          </form>
        </header>

        {_notice(error, "error")}
        {_notice(message, "success")}

        <main class="dashboard-grid">
          <form class="run-panel" method="post">
            <input type="hidden" name="action" value="run">
            <div class="section-heading">
              <h2>Test target</h2>
              <span>Signed in as {_escape(user.username)}</span>
            </div>

            <label>Repository path
              <div class="path-picker-row">
                <input name="repo_path" value="{_escape(repo_value)}" placeholder="/Users/me/project" required>
                <a class="browse-button" href="/browse-native?start={_url_quote(repo_value or str(Path.home()))}">Browse</a>
              </div>
            </label>

            <div class="inline-grid">
              <label>Line coverage
                <input name="target_coverage" type="number" min="0" max="100" value="{preferences.target_coverage}" required>
              </label>
              <label>Max iterations
                <input name="max_iterations" type="number" min="1" max="25" value="{preferences.max_iterations}" required>
              </label>
            </div>

            <div class="section-heading compact">
              <h2>Project type</h2>
              <span>drives test style and coverage command</span>
            </div>

            <label>Project and test stack
              <select name="project_profile">
                {_profile_options(preferences.project_profile)}
              </select>
            </label>

            <label>Test framework preference
              <input name="test_framework" value="{_escape(preferences.test_framework or profile.test_framework)}" placeholder="pytest, xUnit, GoogleTest, Jest">
            </label>

            <label>Coverage command override
              <input name="coverage_command" value="{_escape(coverage_command)}">
            </label>

            <div class="section-heading compact">
              <h2>Provider</h2>
              <span>API keys are encrypted locally</span>
            </div>

            <label>LLM provider
              <select name="provider">
                {_option("fake", "Fake dry run", preferences.provider)}
                {_option("llama.cpp", "llama.cpp", preferences.provider)}
                {_option("huggingface", "Hugging Face", preferences.provider)}
                {_option("openai", "OpenAI", preferences.provider)}
                {_option("anthropic", "Anthropic", preferences.provider)}
              </select>
            </label>

            <div class="inline-grid">
              <label>API model
                <input name="model" value="{_escape(preferences.model)}" placeholder="gpt-4.1-mini or claude-3-5-haiku-latest">
              </label>
              <label>Device
                <input name="device" value="{_escape(preferences.device)}" placeholder="cpu, mps, cuda">
              </label>
            </div>

            <label>llama.cpp GGUF model path
              <input name="model_path" value="{_escape(preferences.model_path)}" placeholder="/Users/me/models/model.gguf">
            </label>

            <label>Hugging Face model id
              <input name="model_id" value="{_escape(preferences.model_id)}" placeholder="TinyLlama/TinyLlama-1.1B-Chat-v1.0">
            </label>

            <label>OpenAI or Anthropic API key
              <input name="api_key" type="password" placeholder="{_credential_placeholder(openai_saved, anthropic_saved)}">
            </label>

            <button type="submit">Start agentic run</button>
          </form>

          <aside class="side-panel">
            {render_folder_browser(repo_value, browse_path)}
            <section>
              <h2>Latest result</h2>
              <pre>{_escape(result_json) if result_json else "Run output will appear here."}</pre>
            </section>
            <section>
              <h2>Recent runs</h2>
              <table>
                <thead><tr><th>Repo</th><th>Target</th><th>Final</th><th>Provider</th><th>Status</th></tr></thead>
                <tbody>{history_rows}</tbody>
              </table>
            </section>
          </aside>
        </main>
        """,
    )


def render_page(
    config: DebugRunConfig | None = None,
    error: str | None = None,
) -> str:
    config_json = json.dumps(asdict(config), indent=2) if config else ""
    return render_shell(
        title="Debug",
        content=f"""
        <main class="legacy-debug">
          <h1>Agentic Testing Debug</h1>
          {_notice(error, "error")}
          <pre>{_escape(config_json)}</pre>
        </main>
        """,
    )


def render_shell(title: str, content: str) -> str:
    profile_json = json.dumps(
        {
            key: {
                "coverage_command": profile.coverage_command,
                "test_framework": profile.test_framework,
            }
            for key, profile in PROJECT_PROFILES.items()
        }
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(title)} · AgenticTesting</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #172026;
      background: #eef2f3;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        linear-gradient(135deg, rgba(20, 83, 116, .10), transparent 34%),
        linear-gradient(315deg, rgba(124, 58, 237, .08), transparent 30%),
        #eef2f3;
    }}
    body, input, select, button {{ font: inherit; }}
    h1, h2, p {{ margin: 0; }}
    label {{
      display: grid;
      gap: 7px;
      color: #34424c;
      font-size: 13px;
      font-weight: 700;
    }}
    .path-picker-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
    }}
    .browse-button {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 92px;
      border: 1px solid #c7d0d8;
      border-radius: 8px;
      background: #ffffff;
      color: #172026;
      font-weight: 800;
      text-decoration: none;
      padding: 0 14px;
    }}
    input, select {{
      width: 100%;
      border: 1px solid #c7d0d8;
      border-radius: 8px;
      background: #ffffff;
      color: #172026;
      padding: 11px 12px;
      outline: none;
    }}
    input:focus, select:focus {{
      border-color: #2563eb;
      box-shadow: 0 0 0 3px rgba(37, 99, 235, .16);
    }}
    button {{
      border: 0;
      border-radius: 8px;
      background: #172026;
      color: #ffffff;
      font-weight: 800;
      padding: 12px 16px;
      cursor: pointer;
    }}
    button.secondary {{
      background: #ffffff;
      color: #172026;
      border: 1px solid #c7d0d8;
    }}
    .auth-shell {{
      width: min(960px, calc(100vw - 32px));
      min-height: 100vh;
      margin: 0 auto;
      display: grid;
      grid-template-columns: 1fr 360px;
      gap: 24px;
      align-items: center;
    }}
    .brand-panel h1 {{
      max-width: 620px;
      font-size: clamp(40px, 7vw, 72px);
      line-height: .95;
      letter-spacing: 0;
    }}
    .brand-panel p:last-child {{
      max-width: 560px;
      margin-top: 18px;
      color: #52616b;
      font-size: 18px;
    }}
    .eyebrow {{
      margin-bottom: 12px;
      color: #2563eb;
      font-size: 12px;
      font-weight: 900;
      letter-spacing: .12em;
      text-transform: uppercase;
    }}
    .auth-card, .run-panel, .side-panel section, .legacy-debug {{
      border: 1px solid rgba(139, 152, 164, .32);
      border-radius: 8px;
      background: rgba(255, 255, 255, .86);
      box-shadow: 0 24px 70px rgba(23, 32, 38, .12);
      backdrop-filter: blur(18px);
    }}
    .auth-card {{
      display: grid;
      gap: 16px;
      padding: 24px;
    }}
    .topbar {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 28px 0 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
    }}
    .topbar h1 {{ font-size: 34px; letter-spacing: 0; }}
    .dashboard-grid {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto 40px;
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(360px, .85fr);
      gap: 20px;
      align-items: start;
    }}
    .run-panel {{
      padding: 22px;
      display: grid;
      gap: 16px;
    }}
    .side-panel {{
      display: grid;
      gap: 20px;
    }}
    .side-panel section {{
      padding: 20px;
      overflow: auto;
    }}
    .folder-browser {{
      display: grid;
      gap: 12px;
    }}
    .folder-browser .folder-path {{
      color: #52616b;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    .folder-list {{
      display: grid;
      gap: 6px;
      max-height: 310px;
      overflow: auto;
    }}
    .folder-row {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      align-items: center;
      border: 1px solid #d9e0e6;
      border-radius: 8px;
      background: #ffffff;
      padding: 8px;
    }}
    .folder-row a {{
      color: #172026;
      font-weight: 700;
      text-decoration: none;
      overflow-wrap: anywhere;
    }}
    .folder-row .select-link {{
      color: #2563eb;
      font-size: 12px;
      font-weight: 900;
      text-transform: uppercase;
    }}
    .section-heading {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
    }}
    .section-heading.compact {{ margin-top: 8px; }}
    .section-heading h2, .side-panel h2 {{ font-size: 17px; }}
    .section-heading span {{
      color: #60717d;
      font-size: 12px;
      font-weight: 700;
    }}
    .inline-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }}
    pre {{
      min-height: 128px;
      margin: 14px 0 0;
      border-radius: 8px;
      background: #101820;
      color: #d7e1ea;
      overflow: auto;
      padding: 14px;
      white-space: pre-wrap;
    }}
    table {{
      width: 100%;
      margin-top: 14px;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      border-bottom: 1px solid #d9e0e6;
      padding: 9px 7px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: #52616b; font-size: 12px; }}
    .notice {{
      width: min(1180px, calc(100vw - 32px));
      margin: 0 auto 14px;
      border-radius: 8px;
      padding: 12px 14px;
      font-weight: 700;
    }}
    .auth-card .notice {{ width: 100%; margin: 0; }}
    .error {{ background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }}
    .success {{ background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }}
    .legacy-debug {{
      width: min(780px, calc(100vw - 32px));
      margin: 40px auto;
      padding: 24px;
    }}
    @media (max-width: 860px) {{
      .auth-shell, .dashboard-grid, .inline-grid {{
        grid-template-columns: 1fr;
      }}
      .auth-shell {{
        align-content: center;
        padding: 24px 0;
      }}
      .topbar {{
        align-items: flex-start;
        flex-direction: column;
      }}
    }}
  </style>
</head>
<body>
  {content}
  <script>
    const projectProfiles = {profile_json};
    const profileSelect = document.querySelector('select[name="project_profile"]');
    const coverageInput = document.querySelector('input[name="coverage_command"]');
    const frameworkInput = document.querySelector('input[name="test_framework"]');
    if (profileSelect && coverageInput && frameworkInput) {{
      profileSelect.addEventListener('change', () => {{
        const profile = projectProfiles[profileSelect.value];
        if (!profile) return;
        coverageInput.value = profile.coverage_command;
        frameworkInput.value = profile.test_framework;
      }});
    }}
  </script>
</body>
</html>"""


def main() -> None:
    host = "127.0.0.1"
    port = 8765
    AppRequestHandler.database = AppDatabase()
    server = ThreadingHTTPServer((host, port), AppRequestHandler)
    print(f"AgenticTesting UI running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


def _form_value(form_data: dict[str, list[str]], key: str) -> str:
    return form_data.get(key, [""])[0].strip()


def _default_api_model(provider: str) -> str:
    if provider == "anthropic":
        return "claude-3-5-haiku-latest"
    return "gpt-4.1-mini"


def _allowed_commands_for_run(config: UiRunConfig) -> tuple[str, ...]:
    commands = set(get_project_profile(config.project_profile).allowed_commands)
    try:
        first = shlex.split(config.coverage_command)[0]
    except (IndexError, ValueError):
        first = ""
    if first:
        commands.add(first)
    return tuple(sorted(commands))


def _credential_placeholder(openai_saved: bool, anthropic_saved: bool) -> str:
    saved = []
    if openai_saved:
        saved.append("OpenAI")
    if anthropic_saved:
        saved.append("Anthropic")
    return f"Saved for {', '.join(saved)}. Leave blank to keep." if saved else "Stored encrypted when provided"


def render_folder_browser(
    selected_repo: str,
    browse_path: str | None,
) -> str:
    current_path = Path(unquote(browse_path or selected_repo or str(Path.home()))).expanduser()
    if not current_path.exists() or not current_path.is_dir():
        current_path = Path.home()
    current_path = current_path.resolve()

    rows = []
    parent = current_path.parent
    if parent != current_path:
        rows.append(_folder_row(parent, ".."))

    try:
        directories = sorted(
            [path for path in current_path.iterdir() if path.is_dir()],
            key=lambda path: path.name.lower(),
        )
    except OSError:
        directories = []

    for path in directories[:100]:
        if path.name.startswith("."):
            continue
        rows.append(_folder_row(path, path.name))

    folder_rows = "".join(rows) or '<div class="folder-row">No readable folders.</div>'
    return f"""
    <section class="folder-browser">
      <div class="section-heading">
        <h2>Folder fallback</h2>
        <a class="browse-button" href="/?selected_repo={_url_quote(str(current_path))}">Use this</a>
      </div>
      <div class="folder-path">{_escape(current_path)}</div>
      <div class="folder-list">{folder_rows}</div>
    </section>
    """


def _folder_row(path: Path, label: str) -> str:
    return f"""
    <div class="folder-row">
      <a href="/?browse_path={_url_quote(str(path))}">{_escape(label)}</a>
      <a class="select-link" href="/?selected_repo={_url_quote(str(path))}">Select</a>
    </div>
    """


def open_native_folder_dialog(start_path: str) -> str:
    start = Path(start_path).expanduser()
    if not start.exists() or not start.is_dir():
        start = Path.home()

    if sys.platform == "darwin":
        return _open_macos_folder_dialog(start)

    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as error:
        raise ValueError("Native folder picker is not available on this system.") from error

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        selected = filedialog.askdirectory(
            initialdir=str(start),
            title="Select repository folder",
            mustexist=True,
        )
    finally:
        root.destroy()

    return selected or ""


def _open_macos_folder_dialog(start: Path) -> str:
    script = """
    on run argv
      set startPath to POSIX file (item 1 of argv)
      set selectedFolder to choose folder with prompt "Select repository folder" default location startPath
      return POSIX path of selectedFolder
    end run
    """
    try:
        completed = subprocess.run(
            ["osascript", "-e", script, str(start)],
            text=True,
            capture_output=True,
            check=False,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError("Native macOS folder picker could not be opened.") from error

    if completed.returncode != 0:
        if "User canceled" in completed.stderr:
            return ""
        raise ValueError("Native macOS folder picker could not be opened.")

    return completed.stdout.strip()


def _profile_options(selected: str) -> str:
    return "".join(
        _option(profile.key, profile.label, selected)
        for profile in PROJECT_PROFILES.values()
    )


def _option(value: str, label: str, selected: str) -> str:
    selected_attr = " selected" if value == selected else ""
    return f'<option value="{_escape(value)}"{selected_attr}>{_escape(label)}</option>'


def _notice(message: str | None, kind: str) -> str:
    if not message:
        return ""
    return f'<div class="notice {kind}">{_escape(message)}</div>'


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _url_quote(value: str) -> str:
    return quote(value, safe="")


if __name__ == "__main__":
    main()
