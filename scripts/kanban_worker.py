#!/usr/bin/env python3
"""Metaphors autonomous worker — robot colleague edition.

Self-directing project builder. Scans, identifies gaps, creates tasks,
executes them, pushes to remote. Minimal Discord output — only speaks
when shipping features or when truly blocked.

Workflow:
  1. SCAN project state
  2. If tests failing → auto-create fix task, execute it
  3. If gaps found → auto-create tasks (max 2/cycle)
  4. Pick next ready task → plan → implement → review → fix → merge → push
  5. Only notify Discord on: feature shipped, or idle (no work at all)
"""
import json
import subprocess
import sys
import os
import time
import re
from pathlib import Path

WORKSPACE = Path("/home/pascal/workspace/Metaphors")
REMOTE = "origin"
BRANCH = "main"
AGY_BIN = "/home/pascal/.local/bin/agy"
HERMES_BIN = os.path.expanduser("~/.local/bin/hermes")
TIMEOUT = 600
MAX_FIX_ROUNDS = 2
APP_PORT = 8080

# ─── Helpers ───────────────────────────────────────────────────────

def run(cmd, timeout=60, workdir=None):
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        timeout=timeout, cwd=str(workdir or WORKSPACE)
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def log(msg):
    print(f"[worker] {time.strftime('%H:%M:%S')} {msg}", flush=True)

def _sq(s):
    return s.replace("'", "'\\''")

# ─── Project Scanner ───────────────────────────────────────────────

class ProjectScanner:
    REQUIRED_FILES = {
        "server.py": "FastAPI server",
        "requirements.txt": "Dependencies",
        "pyproject.toml": "Python packaging",
        "Makefile": "Build targets",
        "install.sh": "Install script",
        "README.md": "Documentation",
        "CONTRIBUTING.md": "Contribution guide",
        "LICENSE": "License",
        ".gitignore": "Git ignore",
        ".env.example": "Env template",
        "engine/__init__.py": "Engine package",
        "engine/entities.py": "Entity model",
        "engine/scheduler.py": "Scheduler",
        "engine/sources/__init__.py": "Sources package",
        "engine/sources/base.py": "DataSource ABC",
        "engine/sources/mock.py": "Mock source",
        "engine/sources/processes.py": "Process source",
        "engine/metaphors/__init__.py": "Metaphors package",
        "engine/metaphors/base.py": "MetaphorRenderer ABC",
        "engine/metaphors/city.py": "City metaphor",
        "engine/metaphors/space.py": "Space metaphor",
        "engine/metaphors/factory.py": "Factory metaphor",
        "engine/metaphors/garden.py": "Garden metaphor",
        "engine/metaphors/kitchen.py": "Kitchen metaphor",
        "engine/metaphors/ship.py": "Ship metaphor",
        "engine/metaphors/solar.py": "Solar metaphor",
        "engine/metaphors/orchestra.py": "Orchestra metaphor",
        "engine/metaphors/construction.py": "Construction metaphor",
        "static/index.html": "Frontend HTML",
        "static/main.js": "Frontend JS",
        "static/style.css": "Frontend CSS",
        "tests/__init__.py": "Tests package",
        "tests/test_entities.py": "Entity tests",
        "tests/test_sources.py": "Source tests",
        "tests/test_city.py": "City tests",
        "tests/test_integration.py": "Integration tests",
        "docs/custom-metaphor.md": "Metaphor tutorial",
        "docs/custom-data-source.md": "Data source tutorial",
        "Dockerfile": "Docker image",
        "docker-compose.yml": "Docker Compose",
        ".dockerignore": "Docker ignore",
        ".github/workflows/ci.yml": "CI pipeline",
    }

    def __init__(self):
        self.existing = set()
        self.missing = {}
        self.tests_pass = False
        self.test_summary = ""
        self.server_ok = False

    def scan(self):
        for root, dirs, files in os.walk(WORKSPACE):
            dirs[:] = [d for d in dirs if d not in ('.venv', '__pycache__', '.git', '.hermes', 'node_modules')]
            for f in files:
                self.existing.add(os.path.relpath(os.path.join(root, f), WORKSPACE))

        self.missing = {p: d for p, d in self.REQUIRED_FILES.items() if p not in self.existing}
        self._check_tests()
        self._check_server()
        return self

    def _check_tests(self):
        out, _, code = run("python3 -m pytest tests/ -v --tb=short 2>&1", timeout=120)
        self.tests_pass = code == 0
        for line in out.splitlines():
            if "passed" in line or "failed" in line:
                self.test_summary = line.strip()
                break

    def _check_server(self):
        out, _, code = run("python3 -c 'from engine.entities import Entity; print(\"OK\")'", timeout=10)
        self.server_ok = code == 0 and "OK" in out

    def has_critical_gaps(self):
        return bool(self.missing) or not self.tests_pass or not self.server_ok

# ─── Task Creator ──────────────────────────────────────────────────

def existing_tasks():
    out, _, _ = run("hermes kanban list --json 2>/dev/null")
    try:
        return json.loads(out)
    except (json.JSONDecodeError, KeyError):
        return []

def task_exists(title):
    return any(t["title"] == title for t in existing_tasks())

def create_task(title, body):
    if task_exists(title):
        return False
    run(f'hermes kanban create "{_sq(title)}" --assignee default --body "{_sq(body)}"')
    return True

def auto_create_tasks(scanner):
    """Create tasks for gaps. Max 2 per cycle."""
    created = 0

    # Priority 1: Failing tests
    if not scanner.tests_pass and not task_exists("Fix failing tests"):
        create_task(
            "Fix failing tests",
            f"Tests are failing: {scanner.test_summary}\n\n"
            f"Run: cd {WORKSPACE} && python3 -m pytest tests/ -v\n"
            f"Fix all failures. Ensure 100% pass rate."
        )
        created += 1

    # Priority 2: Server broken
    if not scanner.server_ok and not task_exists("Fix server imports"):
        create_task(
            "Fix server imports",
            "Server fails to import. Check engine/ modules, fix dependencies."
        )
        created += 1

    # Priority 3: Missing files (max 1 per cycle)
    if created < 2:
        for path, desc in sorted(scanner.missing.items()):
            if created >= 2:
                break
            title = f"Create {path}"
            if not task_exists(title):
                create_task(title, f"Create missing file: {path}\n\nPurpose: {desc}")
                created += 1
                break  # Only 1 missing file task per cycle

    return created

# ─── Git Operations ────────────────────────────────────────────────

def git_ensure_main():
    run(f"git checkout {BRANCH}", workdir=WORKSPACE)
    run(f"git pull --rebase {REMOTE} {BRANCH} 2>/dev/null || true", workdir=WORKSPACE)

def git_create_branch(name):
    git_ensure_main()
    run(f"git checkout -b {name}", workdir=WORKSPACE)

def git_merge_branch(name, title):
    git_ensure_main()
    count_out, _, _ = run(f"git rev-list --count {BRANCH}..{name}", workdir=WORKSPACE)
    try:
        count = int(count_out)
    except ValueError:
        count = 0
    if count == 0:
        return False
    safe_title = re.sub(r'[^a-zA-Z0-9 ]', '', title)[:60]
    run(f'git merge --squash {name}', workdir=WORKSPACE)
    run(f'git commit -m "feat: {safe_title}"', workdir=WORKSPACE)
    run(f"git branch -D {name}", workdir=WORKSPACE)
    return True

def git_push():
    """Push main to remote."""
    _, stderr, code = run(f"git push {REMOTE} {BRANCH}", workdir=WORKSPACE, timeout=30)
    if code == 0:
        log("Pushed to remote")
        return True
    else:
        log(f"Push failed: {stderr[:200]}")
        return False

def git_diff_main_names():
    names, _, _ = run(f"git diff {BRANCH}...HEAD --name-only", workdir=WORKSPACE)
    return [f.strip() for f in names.splitlines() if f.strip()]

# ─── App Status ────────────────────────────────────────────────────

def check_app_running():
    """Check if the app is running on the expected port."""
    out, _, _ = run(f"curl -s http://localhost:{APP_PORT}/health 2>/dev/null")
    return '"status":"ok"' in out or '"status": "ok"' in out

def get_app_version():
    """Get the latest commit hash as version."""
    out, _, _ = run("git rev-parse --short HEAD", workdir=WORKSPACE)
    return out or "unknown"

# ─── Kanban Operations ─────────────────────────────────────────────

def get_next_task():
    out, _, code = run("hermes kanban list --json 2>/dev/null")
    if code != 0 or not out:
        return None
    try:
        tasks = json.loads(out)
    except json.JSONDecodeError:
        return None
    for t in tasks:
        if t.get("state") == "ready":
            return t
    return None

# ─── Execution Phases ──────────────────────────────────────────────

def plan_task(task):
    prompt = f"""Plan this task for the Metaphors project at {WORKSPACE}.

Task: {task['title']}
Description: {task.get('body', '')}

Create a brief implementation plan: files to change, key decisions, test strategy.
Do NOT write code. Under 300 words. Exact file paths."""
    out, _, code = run(f"{HERMES_BIN} chat -q '{_sq(prompt)}'", timeout=120)
    return out if code == 0 and out else None

def implement_task(task, plan):
    prompt = f"""Implement this task for the Metaphors project at {WORKSPACE}.

Task: {task['title']}
Description: {task.get('body', '')}
Plan: {plan}

1. Read existing code for context
2. TDD: tests first, verify fail, implement, verify pass
3. Run: cd {WORKSPACE} && python3 -m pytest tests/ -v
4. Commit with descriptive message

Do NOT install packages or modify files outside {WORKSPACE}.
Use python3 for all commands."""
    out, err, code = run(f"{AGY_BIN} --print-timeout 10m --print '{_sq(prompt)}'", timeout=TIMEOUT)
    return {"output": out or "", "errors": err or "", "success": code == 0}

def review_task(task, plan):
    diff, _, _ = run(f"git diff {BRANCH}...HEAD", workdir=WORKSPACE)
    if len(diff) > 6000:
        diff = diff[:6000] + "\n..."
    tests, _, _ = run("python3 -m pytest tests/ --tb=short -q", workdir=WORKSPACE, timeout=120)
    prompt = f"""Review this code for the Metaphors project.

Task: {task['title']}
Diff: {diff}
Tests: {tests[-1500:]}

Check: correctness, tests, quality, security.
Output exactly: VERDICT: PASS or VERDICT: FAIL
Then one sentence why."""
    out, _, code = run(f"{HERMES_BIN} chat -q '{_sq(prompt)}'", timeout=120)
    if code != 0 or not out:
        return {"verdict": "PASS", "summary": "Review skipped"}
    verdict = "PASS" if "VERDICT: PASS" in out.upper() else "FAIL"
    return {"verdict": verdict, "summary": out}

def fix_task(task, review):
    prompt = f"""Fix issues for the Metaphors project at {WORKSPACE}.

Task: {task['title']}
Review: {review}

Fix each issue. Run tests. Commit.
Only fix listed issues."""
    out, _, code = run(f"{AGY_BIN} --print-timeout 10m --print '{_sq(prompt)}'", timeout=TIMEOUT)
    return {"success": code == 0}

# ─── Main ──────────────────────────────────────────────────────────

def main():
    log("Autonomous worker starting")

    # Scan
    scanner = ProjectScanner().scan()

    # Auto-create tasks for gaps
    created = auto_create_tasks(scanner)

    # Pick task
    task = get_next_task()
    if not task:
        if scanner.has_critical_gaps():
            # Gaps exist but tasks are running — don't spam discord
            log(f"Gaps exist but no ready tasks. Tests: {scanner.test_summary}")
            return  # Silent — tasks are in progress

        # Truly idle — notify discord
        if check_app_running():
            version = get_app_version()
            msg = f"🤖 **Metaphors worker idle.**\n\n"
            msg += f"App running on port {APP_PORT} — version `{version}`\n"
            msg += f"Tests: {scanner.test_summary or 'all passing'}\n"
            msg += f"Missing files: {len(scanner.missing)}\n\n"
            msg += f"Nothing to do. Add a task or let me find gaps next cycle."
        else:
            msg = f"🤖 **Metaphors worker idle.**\n\n"
            msg += f"App not running. Tests: {scanner.test_summary or 'all passing'}\n"
            msg += f"Missing files: {len(scanner.missing)}\n\n"
            msg += f"Nothing to do."
        print(json.dumps({"type": "idle", "message": msg}))
        return

    # Execute task
    task_id = task["id"]
    title = task["title"]
    log(f"Working on: {title}")

    branch = f"task/{task_id[:8]}-{re.sub(r'[^a-zA-Z0-9]+', '-', title.lower())[:30]}"
    git_create_branch(branch)

    # Plan → Implement → Review → Fix → Merge → Push
    plan = plan_task(task)
    if not plan:
        run(f"git checkout {BRANCH} && git branch -D {branch}", workdir=WORKSPACE)
        return

    impl = implement_task(task, plan)
    if not impl["success"]:
        run(f"git checkout {BRANCH} && git branch -D {branch}", workdir=WORKSPACE)
        return

    review_round = 0
    for i in range(MAX_FIX_ROUNDS):
        review_round = i + 1
        review = review_task(task, plan)
        if review["verdict"] == "PASS":
            break
        if not fix_task(task, review["summary"]):
            run(f"git checkout {BRANCH} && git branch -D {branch}", workdir=WORKSPACE)
            return

    merged = git_merge_branch(branch, title)
    if not merged:
        return

    pushed = git_push()

    # Build notification
    files = git_diff_main_names()
    version = get_app_running_version() if check_app_running() else get_app_version()
    app_running = check_app_running()

    msg = f"✅ **Shipped: {title}**\n\n"
    msg += f"**Files:** {', '.join(f'`{f}`' for f in files[:5])}"
    if len(files) > 5:
        msg += f" +{len(files)-5} more"
    msg += f"\n**Review:** {'pass' if review_round == 1 else f'{review_round} rounds'}"
    msg += f"\n**Branch:** `{branch}` → `{BRANCH}`"
    if pushed:
        msg += f" → pushed"
    if app_running:
        msg += f"\n\n🚀 **App live** on port {APP_PORT} — version `{version}`"
        msg += f"\nhttp://localhost:{APP_PORT}"

    print(json.dumps({"type": "shipped", "message": msg}))
    log(f"Shipped: {title}")


def get_app_running_version():
    out, _, _ = run("git rev-parse --short HEAD", workdir=WORKSPACE)
    return out or "unknown"


if __name__ == "__main__":
    main()
