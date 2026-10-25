"""Start the authenticated dashboard on loopback, reusing Clipforge if present."""
import argparse
import getpass
import os
from pathlib import Path
import sys
import webbrowser

project = Path(__file__).resolve().parent
os.chdir(project)
# Codex's shared dependencies are optional; a normal venv remains supported.
for shared in (project.parent / "dashboard-deps", project.parent.parent / "work" / "dashboard-deps"):
    if shared.is_dir():
        sys.path.insert(0, str(shared))
try:
    import uvicorn
except ImportError:
    raise SystemExit("Install dependencies first: python -m pip install -e .")
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=4185)
parser.add_argument("--no-browser", action="store_true")
args = parser.parse_args()
if not os.getenv("ADMIN_TOKEN"):
    token = getpass.getpass("Choose a private dashboard password (not saved): ")
    if not token.strip():
        raise SystemExit("A non-empty private password is required.")
    os.environ["ADMIN_TOKEN"] = token
candidate = project.parent.parent / "outputs" / "Clipforge"
if not os.getenv("CLIPFORGE_ROOT") and (candidate / "data").is_dir():
    os.environ["CLIPFORGE_ROOT"] = str(candidate)
os.environ.setdefault("DATABASE_PATH", str(project / "data" / "jobs.sqlite3"))
url = f"http://127.0.0.1:{args.port}/"
print(f"Mission Control: {url}")
print("Sign in as admin using the private password. Keep this window open.")
print("Existing Clipforge services keep their own credentials; no key is copied.")
if not args.no_browser:
    webbrowser.open(url)
uvicorn.run("backend.api:app", host="127.0.0.1", port=args.port)
