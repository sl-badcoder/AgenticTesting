import json
from dataclasses import asdict, dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs


@dataclass(frozen=True)
class DebugRunConfig:
    project_folder: str
    coverage_percentage: int


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


class DebugRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._send_html(render_page())

    def do_POST(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        form_data = parse_qs(raw_body)

        try:
            config = read_debug_config(form_data)
        except ValueError as error:
            self._send_html(render_page(error=str(error)), status=400)
            return

        self._send_html(render_page(config=config))

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_html(self, html: str, status: int = 200) -> None:
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def render_page(
    config: DebugRunConfig | None = None,
    error: str | None = None,
) -> str:
    config_json = json.dumps(asdict(config), indent=2) if config else ""
    escaped_config_json = (
        config_json.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    escaped_error = (
        error.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if error
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agentic Testing Debug</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, sans-serif;
      line-height: 1.45;
      color: #1f2933;
      background: #f6f8fa;
    }}
    body {{
      margin: 0;
      padding: 32px;
    }}
    main {{
      max-width: 760px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #d8dee4;
      border-radius: 8px;
      padding: 24px;
    }}
    h1 {{
      font-size: 22px;
      margin: 0 0 20px;
    }}
    label {{
      display: block;
      font-weight: 700;
      margin: 16px 0 6px;
    }}
    input {{
      width: 100%;
      box-sizing: border-box;
      border: 1px solid #b8c0cc;
      border-radius: 6px;
      font: inherit;
      padding: 10px 12px;
    }}
    input[type="number"] {{
      max-width: 160px;
    }}
    button {{
      margin-top: 18px;
      border: 0;
      border-radius: 6px;
      background: #2563eb;
      color: white;
      font: inherit;
      font-weight: 700;
      padding: 10px 14px;
      cursor: pointer;
    }}
    pre {{
      background: #111827;
      color: #e5e7eb;
      border-radius: 6px;
      padding: 14px;
      overflow: auto;
      min-height: 92px;
    }}
    .error {{
      border: 1px solid #dc2626;
      background: #fef2f2;
      color: #991b1b;
      border-radius: 6px;
      padding: 10px 12px;
      margin-bottom: 16px;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Agentic Testing Debug</h1>
    {f'<div class="error">{escaped_error}</div>' if escaped_error else ''}
    <form method="post">
      <label for="project_folder">Project folder</label>
      <input id="project_folder" name="project_folder" value="{Path.cwd()}" required>

      <label for="coverage_percentage">Line coverage target</label>
      <input id="coverage_percentage" name="coverage_percentage" type="number" min="0" max="100" value="80" required>

      <button type="submit">Create debug run</button>
    </form>

    <h2>Debug output</h2>
    <pre>{escaped_config_json}</pre>
  </main>
</body>
</html>"""


def main() -> None:
    host = "127.0.0.1"
    port = 8765
    server = ThreadingHTTPServer((host, port), DebugRequestHandler)
    print(f"Debug UI running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
