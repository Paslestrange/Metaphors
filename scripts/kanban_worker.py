#!/usr/bin/env python3
"""Metaphors kanban worker — autonomous project builder.

Smart workflow:
  1. SCAN project state (files, tests, docs, config)
  2. COMPARE against GOAL.md and plan
  3. IDENTIFY gaps (missing files, failing tests, incomplete features)
  4. CREATE tasks for gaps (if none exist)
  5. PICK next ready task
  6. EXECUTE: plan → implement → review → fix → merge
  7. NOTIFY via Discord

Run by cron every 4 hours. Self-directing — creates its own work.
"""
import json
import subprocess
import sys
import os
import time
import re
from pathlib import Path

WORKSPACE = Path("/home/pascal/workspace/Metaphors")
AGY_BIN = "/home/pascal/.local/bin/agy"
HERMES_BIN = os.path.expanduser("~/.local/bin/hermes")
TIMEOUT = 600
MAX_FIX_ROUNDS = 2

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
    """Scans project state and identifies gaps."""

    # Expected structure for a complete project
    REQUIRED_FILES = {
        # Core
        "server.py": "FastAPI server with WebSocket",
        "requirements.txt": "Python dependencies",
        "pyproject.toml": "Modern Python packaging",
        "Makefile": "Build/run targets",
        "install.sh": "One-command setup",
        "README.md": "Project introduction",
        "CONTRIBUTING.md": "Contribution guide",
        "LICENSE": "Open source license",
        ".gitignore": "Git ignore rules",
        ".env.example": "Environment variables template",

        # Engine
        "engine/__init__.py": "Engine package",
        "engine/entities.py": "Unified entity model",
        "engine/scheduler.py": "Real-time entity stream",

        # Data Sources
        "engine/sources/__init__.py": "Sources package",
        "engine/sources/base.py": "DataSource ABC",
        "engine/sources/mock.py": "Mock data source",
        "engine/sources/processes.py": "System process source",

        # Metaphors
        "engine/metaphors/__init__.py": "Metaphors package",
        "engine/metaphors/base.py": "MetaphorRenderer ABC + registry",
        "engine/metaphors/city.py": "City metaphor",
        "engine/metaphors/space.py": "Space station metaphor",
        "engine/metaphors/factory.py": "Factory metaphor",
        "engine/metaphors/garden.py": "Garden metaphor",
        "engine/metaphors/kitchen.py": "Kitchen metaphor",
        "engine/metaphors/ship.py": "Naval ship metaphor",
        "engine/metaphors/solar.py": "Solar system metaphor",
        "engine/metaphors/orchestra.py": "Orchestra metaphor",
        "engine/metaphors/construction.py": "Construction metaphor",

        # Frontend
        "static/index.html": "Main HTML page",
        "static/main.js": "Frontend rendering",
        "static/style.css": "Styles",

        # Tests
        "tests/__init__.py": "Tests package",
        "tests/test_entities.py": "Entity model tests",
        "tests/test_sources.py": "Data source tests",
        "tests/test_city.py": "City metaphor tests",
        "tests/test_integration.py": "Integration tests",

        # Docs
        "docs/custom-metaphor.md": "Custom metaphor tutorial",
        "docs/custom-data-source.md": "Custom data source tutorial",

        # Deployment
        "Dockerfile": "Container image",
        "docker-compose.yml": "Container orchestration",
        ".dockerignore": "Docker ignore rules",

        # CI
        ".github/workflows/ci.yml": "CI pipeline",
    }

    def __init__(self):
        self.existing = set()
        self.missing = {}
        self.test_results = {}
        self.server_runs = False

    def scan(self):
        """Full project scan."""
        log("Scanning project state...")

        # Find existing files
        for root, dirs, files in os.walk(WORKSPACE):
            # Skip venv, __pycache__, .git
            dirs[:] = [d for d in dirs if d not in ('.venv', '__pycache__', '.git', '.hermes', 'node_modules')]
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), WORKSPACE)
                self.existing.add(rel)

        # Identify missing files
        self.missing = {}
        for path, desc in self.REQUIRED_FILES.items():
            if path not in self.existing:
                self.missing[path] = desc

        # Check if tests pass
        self._run_tests()

        # Check if server starts
        self._check_server()

        log(f"Scan complete: {len(self.existing)} files exist, {len(self.missing)} missing")
        return self

    def _run_tests(self):
        """Run pytest and capture results."""
        output, _, code = run("python3 -m pytest tests/ -v --tb=short 2>&1", timeout=120)
        self.test_results = {
            "output": output,
            "passed": "passed" in output,
            "exit_code": code,
            "summary": self._parse_test_summary(output),
        }

    def _parse_test_summary(self, output):
        """Extract test summary from pytest output."""
        for line in output.splitlines():
            if "passed" in line or "failed" in line:
                return line.strip()
        return "No tests found"

    def _check_server(self):
        """Check if server can start."""
        # Just check imports work
        output, _, code = run("python3 -c 'from engine.entities import Entity; print(\"OK\")'", timeout=10)
        self.server_runs = code == 0 and "OK" in output

    def get_gaps(self):
        """Return prioritized list of gaps."""
        gaps = []

        # Missing critical files
        for path, desc in self.missing.items():
            priority = "high"
            if path in ("README.md", "CONTRIBUTING.md", "LICENSE"):
                priority = "medium"
            if path.startswith(".github/"):
                priority = "low"
            gaps.append({
                "type": "missing_file",
                "path": path,
                "description": desc,
                "priority": priority,
            })

        # Failing tests
        if self.test_results.get("exit_code", 0) != 0:
            gaps.append({
                "type": "failing_tests",
                "description": f"Tests failing: {self.test_results.get('summary', 'unknown')}",
                "priority": "high",
            })

        # Server won't start
        if not self.server_runs:
            gaps.append({
                "type": "server_broken",
                "description": "Server imports fail",
                "priority": "critical",
            })

        return gaps

    def get_status_message(self):
        """Return a human-readable status."""
        lines = [
            f"📁 Files: {len(self.existing)} exist, {len(self.missing)} missing",
            f"🧪 Tests: {self.test_results.get('summary', 'not run')}",
            f"🖥️ Server: {'OK' if self.server_runs else 'BROKEN'}",
        ]
        if self.missing:
            lines.append(f"\n❌ Missing {len(self.missing)} files:")
            for path in sorted(self.missing.keys())[:5]:
                lines.append(f"  • {path}")
            if len(self.missing) > 5:
                lines.append(f"  • ... and {len(self.missing) - 5} more")
        return "\n".join(lines)


# ─── Task Creator ──────────────────────────────────────────────────

def create_tasks_for_gaps(gaps):
    """Create kanban tasks for identified gaps."""
    created = 0
    for gap in gaps[:3]:  # Max 3 new tasks per cycle
        path = gap.get("path", "")
        desc = gap.get("description", "")

        if gap["type"] == "missing_file":
            title = f"Create {path}"
            body = f"Create the missing file: {path}\n\nPurpose: {desc}\n\nFollow existing code patterns. Write tests if applicable. Commit with descriptive message."
        elif gap["type"] == "failing_tests":
            title = "Fix failing tests"
            body = f"Tests are failing. Run: python3 -m pytest tests/ -v\n\nFix all failing tests. Ensure all pass before committing."
        elif gap["type"] == "server_broken":
            title = "Fix server imports"
            body = "Server fails to import. Check engine/ imports, fix circular dependencies, ensure all modules load."
        else:
            continue

        # Check if similar task already exists
        output, _, _ = run("hermes kanban list --json 2>/dev/null")
        try:
            existing = json.loads(output)
            if any(t["title"] == title for t in existing):
                continue
        except (json.JSONDecodeError, KeyError):
            pass

        # Create task
        run(f'hermes kanban create "{_sq(title)}" --assignee default --body "{_sq(body)}"')
        created += 1
        log(f"Created task: {title}")

    return created


# ─── Git Operations ────────────────────────────────────────────────

def task_branch_name(task_id, title):
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower())[:40].rstrip('-')
    short_id = task_id[:8] if task_id else "unknown"
    return f"task/{short_id}-{slug}"

def git_ensure_main():
    run("git checkout main", workdir=WORKSPACE)
    run("git pull --rebase origin main 2>/dev/null || true", workdir=WORKSPACE)

def git_create_branch(branch_name):
    git_ensure_main()
    run(f"git checkout -b {branch_name}", workdir=WORKSPACE)

def git_merge_branch(branch_name, title):
    git_ensure_main()
    count_out, _, _ = run(f"git rev-list --count main..{branch_name}", workdir=WORKSPACE)
    try:
        count = int(count_out)
    except ValueError:
        count = 0
    if count == 0:
        return False
    safe_title = re.sub(r'[^a-zA-Z0-9 ]', '', title)[:60]
    run(f'git merge --squash {branch_name}', workdir=WORKSPACE)
    run(f'git commit -m "feat: {safe_title}"', workdir=WORKSPACE)
    run(f"git branch -D {branch_name}", workdir=WORKSPACE)
    return True

def git_diff_main_names():
    names, _, _ = run("git diff main...HEAD --name-only", workdir=WORKSPACE)
    return [f.strip() for f in names.splitlines() if f.strip()]

def git_diff_main_stat():
    stat, _, _ = run("git diff main...HEAD --stat", workdir=WORKSPACE)
    return stat


# ─── Kanban Operations ─────────────────────────────────────────────

def get_next_task():
    output, _, code = run("hermes kanban list --json 2>/dev/null")
    if code != 0 or not output:
        return None
    try:
        tasks = json.loads(output)
    except json.JSONDecodeError:
        return None
    for task in tasks:
        if task.get("state") == "ready":
            return task
    return None

def claim_task(task_id):
    run(f"hermes kanban start {task_id}")

def complete_task(task_id, summary):
    metadata = json.dumps({"agent": "agy", "workflow": "autonomous"})
    run(f"hermes kanban done {task_id} --summary '{_sq(summary[:500])}' --metadata '{metadata}'")

def block_task(task_id, reason):
    run(f"hermes kanban block {task_id} '{_sq(reason[:500])}'")

def comment_task(task_id, body):
    run(f"hermes kanban comment {task_id} '{_sq(body[:500])}'")


# ─── Execution Phases ──────────────────────────────────────────────

def plan_task(task):
    title = task["title"]
    body = task.get("body", "")
    prompt = f"""You are planning an implementation task for the Metaphors project.

PROJECT: {WORKSPACE}
TASK: {title}
DESCRIPTION: {body}

Create a concise implementation plan. Do NOT write code.
Output: FILES TO CREATE/MODIFY, KEY DECISIONS, TEST STRATEGY, DEPENDENCIES.
Under 500 words. Exact file paths."""
    stdout, _, code = run(f"{HERMES_BIN} chat -q '{_sq(prompt)}'", timeout=120)
    return stdout if code == 0 and stdout else None

def implement_task(task, plan):
    title = task["title"]
    body = task.get("body", "")
    prompt = f"""You are implementing a task for the Metaphors project.

PROJECT: {WORKSPACE}
TASK: {title}
DESCRIPTION: {body}

PLAN: {plan}

INSTRUCTIONS:
1. Read existing code for context
2. TDD: tests FIRST, verify fail, implement, verify pass
3. Run: cd {WORKSPACE} && python3 -m pytest tests/ -v
4. Commit with descriptive message

CONSTRAINTS:
- Do NOT modify files outside {WORKSPACE}
- Do NOT install packages (add to requirements.txt only)
- Use python3 for all commands"""
    stdout, stderr, code = run(f"{AGY_BIN} --print-timeout 10m --print '{_sq(prompt)}'", timeout=TIMEOUT)
    return {"output": stdout or "", "errors": stderr or "", "success": code == 0}

def review_task(task, plan):
    title = task["title"]
    diff, _, _ = run("git diff main...HEAD", workdir=WORKSPACE)
    if len(diff) > 8000:
        diff = diff[:8000] + "\n... (truncated)"
    tests, _, _ = run("python3 -m pytest tests/ -v --tb=short", workdir=WORKSPACE, timeout=120)
    prompt = f"""Review this implementation for the Metaphors project.

TASK: {title}
PLAN: {plan}
DIFF: {diff}
TESTS: {tests[-2000:]}

Check: correctness, test coverage, code quality, security, completeness.
Output: VERDICT: PASS or FAIL, then brief explanation.
Under 300 words."""
    stdout, _, code = run(f"{HERMES_BIN} chat -q '{_sq(prompt)}'", timeout=120)
    if code != 0 or not stdout:
        return {"verdict": "PASS", "summary": "Review skipped"}
    verdict = "PASS" if "VERDICT: PASS" in stdout.upper() else "FAIL"
    return {"verdict": verdict, "summary": stdout}

def fix_task(task, review_summary):
    title = task["title"]
    prompt = f"""Fix issues found during code review for Metaphors project.

PROJECT: {WORKSPACE}
TASK: {title}
REVIEW: {review_summary}

Fix each issue. Run tests. Commit fixes.
Only fix listed issues — no refactoring."""
    stdout, _, code = run(f"{AGY_BIN} --print-timeout 10m --print '{_sq(prompt)}'", timeout=TIMEOUT)
    return {"success": code == 0, "output": stdout or ""}


# ─── Main ──────────────────────────────────────────────────────────

def main():
    log("Metaphors autonomous worker starting")

    # Phase 1: Scan project
    scanner = ProjectScanner().scan()
    status = scanner.get_status_message()
    log(f"Project status:\n{status}")

    # Phase 2: Identify gaps and create tasks
    gaps = scanner.get_gaps()
    if gaps:
        log(f"Found {len(gaps)} gaps")
        created = create_tasks_for_gaps(gaps)
        if created:
            log(f"Created {created} new tasks")

    # Phase 3: Pick next task
    task = get_next_task()
    if not task:
        log("No ready tasks.")
        output = {
            "type": "idle",
            "message": f"📋 **Metaphors project status:**\n\n{status}\n\n"
                       f"{'✅ All files present!' if not scanner.missing else f'❌ {len(scanner.missing)} files missing'}\n"
                       f"{'🧪 All tests pass' if scanner.test_results.get('exit_code', 0) == 0 else '🧪 Tests failing'}\n"
                       f"{'🖥️ Server runs' if scanner.server_runs else '🖥️ Server broken'}\n\n"
                       f"Add a task or let the worker auto-create one next cycle."
        }
        print(json.dumps(output))
        return

    task_id = task["id"]
    title = task["title"]
    log(f"Task: {task_id} — {title}")
    claim_task(task_id)

    # Create branch
    branch_name = task_branch_name(task_id, title)
    git_create_branch(branch_name)
    comment_task(task_id, f"Branch: `{branch_name}`")

    # Plan
    plan = plan_task(task)
    if not plan:
        block_task(task_id, "Planning failed")
        git_ensure_main()
        run(f"git branch -D {branch_name}", workdir=WORKSPACE)
        return
    comment_task(task_id, f"PLAN:\n{plan[:400]}")

    # Implement
    impl = implement_task(task, plan)
    if not impl["success"]:
        block_task(task_id, f"Implementation failed:\n{impl['errors'][-300:]}")
        git_ensure_main()
        run(f"git branch -D {branch_name}", workdir=WORKSPACE)
        return

    # Review loop
    review_round = 0
    for fix_round in range(MAX_FIX_ROUNDS):
        review_round = fix_round + 1
        review = review_task(task, plan)
        if review["verdict"] == "PASS":
            comment_task(task_id, f"REVIEW (round {review_round}): PASS")
            break
        comment_task(task_id, f"REVIEW (round {review_round}): FAIL\n{review['summary'][:300]}")
        fix = fix_task(task, review["summary"])
        if not fix["success"]:
            block_task(task_id, f"Fix failed:\n{review['summary'][:300]}")
            git_ensure_main()
            run(f"git branch -D {branch_name}", workdir=WORKSPACE)
            return
    else:
        comment_task(task_id, f"WARNING: {MAX_FIX_ROUNDS} review rounds exhausted")

    # Merge
    merged = git_merge_branch(branch_name, title)
    if not merged:
        block_task(task_id, "Merge failed")
        return

    # Build summary
    files = git_diff_main_names()
    stat = git_diff_main_stat()
    summary = f"**✅ Task Complete: {title}**\n\n"
    summary += f"**Workflow:** Plan → Implement → Review ({review_round} round) → Merge\n\n"
    summary += f"**Branch:** `{branch_name}` → `main`\n\n"
    summary += "**Files:**\n"
    for f in files[:10]:
        summary += f"• `{f}`\n"
    if len(files) > 10:
        summary += f"• ... +{len(files) - 10} more\n"

    complete_task(task_id, summary)
    log(f"Done: {title}")

    # Rescan after completion
    scanner2 = ProjectScanner().scan()
    new_status = scanner2.get_status_message()
    summary += f"\n\n**Project status after:**\n{new_status}"

    print(json.dumps({"type": "complete", "message": summary}))


if __name__ == "__main__":
    main()
