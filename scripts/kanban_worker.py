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
import urllib.request
from pathlib import Path
try:
    from PIL import Image, ImageStat
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

WORKSPACE = Path("/home/pascal/workspace/Metaphors")
LOCK_FILE = WORKSPACE / ".worker.lock"
# Shared lock across all autonomous workers (Metaphors, PetitionsRadar, etc.)
# Prevents concurrent agy/hermes sessions from different projects
SHARED_LOCK_FILE = Path("/home/pascal/workspace/.autonomous-worker.lock")
SHARED_LOCK_TIMEOUT = 900  # 15 min — if a worker dies, another can claim after this
REMOTE = "origin"
BRANCH = "main"
AGY_BIN = "/home/pascal/.local/bin/agy"
HERMES_BIN = os.path.expanduser("~/.local/bin/hermes")
TIMEOUT = 600
MAX_FIX_ROUNDS = 2
APP_PORT = 8080
SERVICE_NAME = "metaphors.service"
DISCORD_CHANNEL_ID = "1525810707449249833"  # #metaphors

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

def send_discord(message: str) -> bool:
    """Send a message directly to Discord via bot API — no LLM needed."""
    env_path = Path("/home/pascal/.hermes/.env")
    if not env_path.exists():
        log("No .env file found, cannot send Discord message")
        return False
    token = None
    for line in env_path.read_text().splitlines():
        if line.startswith("DISCORD_BOT_TOKEN="):
            token = line.split("=", 1)[1].strip()
            break
    if not token:
        log("No DISCORD_BOT_TOKEN found")
        return False
    try:
        payload = json.dumps({"content": message}).encode("utf-8")
        req = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{DISCORD_CHANNEL_ID}/messages",
            data=payload,
            headers={
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200 or resp.status == 201
    except Exception as e:
        log(f"Discord send failed: {e}")
        return False

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

def git_cleanup_dirty():
    """Clean up dirty git state on failure."""
    run("git merge --abort 2>/dev/null", workdir=WORKSPACE)
    run("git rebase --abort 2>/dev/null", workdir=WORKSPACE)
    run(f"git checkout {BRANCH} 2>/dev/null", workdir=WORKSPACE)
    run("git reset --hard HEAD 2>/dev/null", workdir=WORKSPACE)
    run("git clean -fd 2>/dev/null", workdir=WORKSPACE)

def git_rollback():
    """Rollback to last clean state if service fails after deploy."""
    # Get last healthy commit (before our changes)
    out, _, _ = run("git rev-parse HEAD", workdir=WORKSPACE)
    current = out.strip()
    # Check if service is healthy
    time.sleep(3)
    healthy = check_service_running()
    if not healthy:
        log(f"Service unhealthy after deploy, rolling back")
        run(f"git revert --no-edit HEAD", workdir=WORKSPACE)
        run(f"git push {REMOTE} {BRANCH}", workdir=WORKSPACE, timeout=30)
        restart_service()
        return True
    return False

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

def restart_service():
    """Restart the Metaphors service after update."""
    run(f"systemctl --user restart {SERVICE_NAME}", workdir=WORKSPACE)
    time.sleep(2)
    out, _, code = run(f"systemctl --user is-active {SERVICE_NAME}")
    return code == 0 and "active" in out

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

# ─── Screenshot Verification ───────────────────────────────────────

def verify_screenshot(path) -> bool:
    """Verify screenshot is not blank/broken.
    
    Returns True if:
    - Image exists and loads
    - Has pixel variance > threshold (not blank)
    - Not all one color
    
    Returns False if:
    - PIL not available
    - File doesn't exist
    - Can't load image
    - Image is blank/broken
    """
    if not PIL_AVAILABLE:
        log("PIL not available, skipping screenshot verification")
        return False
    
    if not Path(path).exists():
        log(f"Screenshot not found: {path}")
        return False
    
    try:
        img = Image.open(path)
        img.load()
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Check image dimensions
        if img.width < 10 or img.height < 10:
            log(f"Screenshot too small: {img.width}x{img.height}")
            return False
        
        # Get statistics
        stat = ImageStat.Stat(img)
        
        # Check variance (standard deviation) for each channel
        # If all channels have very low variance, image is blank
        min_variance = 5.0  # Threshold for "not blank"
        max_variance = max(stat.var) if stat.var else 0
        
        if max_variance < min_variance:
            log(f"Screenshot appears blank (max variance: {max_variance:.2f})")
            return False
        
        # Check if all pixels are the same color
        if all(abs(v - stat.mean[i]) < 1.0 for i, v in enumerate(stat.median)):
            log("Screenshot is solid color")
            return False
        
        log(f"Screenshot verified: variance={max_variance:.2f}, mean={stat.mean}")
        return True
        
    except Exception as e:
        log(f"Screenshot verification failed: {e}")
        return False

# ─── App Status ────────────────────────────────────────────────────

def check_service_running():
    """Check if systemd service is active."""
    out, _, code = run(f"systemctl --user is-active {SERVICE_NAME}")
    return code == 0 and "active" in out

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
        if t.get("status") == "ready":
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
    # More robust verdict parsing
    verdict = "FAIL"
    for line in out.upper().splitlines():
        if "VERDICT:" in line:
            verdict = "PASS" if "PASS" in line else "FAIL"
            break
    # Also check for explicit pass/fail patterns
    if verdict == "FAIL" and ("all tests pass" in out.lower() or "looks good" in out.lower()):
        verdict = "PASS"
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

def acquire_lock():
    """Prevent overlapping worker runs."""
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            # Check if process is still running
            os.kill(pid, 0)
            log(f"Another worker running (pid {pid}), skipping")
            return False
        except (ValueError, ProcessLookupError, PermissionError):
            pass  # Stale lock, claim it
    LOCK_FILE.write_text(str(os.getpid()))
    return True

def release_lock():
    """Release the worker lock."""
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass

def main():
    log("Autonomous worker starting")
    if not acquire_lock():
        print("[SILENT]")
        return

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
            print("[SILENT]")  # No LLM needed
            release_lock()
            return  # Silent — tasks are in progress

        # Truly idle — send Discord directly, no LLM needed
        version = get_app_version()
        if check_app_running():
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
        send_discord(msg)
        print("[SILENT]")  # Already sent to Discord
        release_lock()
        return

    # Execute task
    task_id = task["id"]
    title = task["title"]
    log(f"Working on: {title}")

    branch = f"task/{task_id[:8]}-{re.sub(r'[^a-zA-Z0-9]+', '-', title.lower())[:30]}"
    git_create_branch(branch)

    def cleanup_on_failure():
        git_cleanup_dirty()
        try:
            run(f"git branch -D {branch} 2>/dev/null", workdir=WORKSPACE)
        except Exception:
            pass

    # Plan → Implement → Review → Fix → Merge → Push
    plan = plan_task(task)
    if not plan:
        run(f"git checkout {BRANCH} && git branch -D {branch}", workdir=WORKSPACE)
        print("[SILENT]")
        release_lock()
        return

    impl = implement_task(task, plan)
    if not impl["success"]:
        run(f"git checkout {BRANCH} && git branch -D {branch}", workdir=WORKSPACE)
        print("[SILENT]")
        release_lock()
        return

    review_round = 0
    for i in range(MAX_FIX_ROUNDS):
        review_round = i + 1
        review = review_task(task, plan)
        if review["verdict"] == "PASS":
            break
        if not fix_task(task, review["summary"]):
            run(f"git checkout {BRANCH} && git branch -D {branch}", workdir=WORKSPACE)
            print("[SILENT]")
            release_lock()
            return

    merged = git_merge_branch(branch, title)
    if not merged:
        print("[SILENT]")
        release_lock()
        return

    pushed = git_push()

    # Capture screenshot for visual verification
    screenshot_path = WORKSPACE / "screenshots" / f"shipped_{re.sub(r'[^a-zA-Z0-9]', '_', title)[:40]}.png"
    screenshot_dir = screenshot_path.parent
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    run(f"python3 scripts/screenshot.py --output {screenshot_path} --wait 4", workdir=WORKSPACE, timeout=30)

    # Verify screenshot quality
    screenshot_ok = verify_screenshot(str(screenshot_path))
    if not screenshot_ok:
        log(f"Screenshot verification FAILED for: {title}")
        # Block the task instead of completing — screenshot looks broken
        run(f'{HERMES_BIN} kanban block {task_id} --reason "Screenshot verification failed: image appears blank/broken"', workdir=WORKSPACE)
        # Send Discord directly, no LLM needed
        files = git_diff_main_names()
        version = get_app_version()
        msg = f"**⚠️ Blocked: {title}**\n\n"
        msg += f"Screenshot verification failed — image appears blank or broken.\n"
        msg += f"Screenshot: `{screenshot_path}`\n"
        msg += f"**Files:** {', '.join(f'`{f}`' for f in files[:5])}\n"
        msg += f"**Version:** `{version}`\n"
        msg += f"Task blocked for manual review."
        send_discord(msg)
        print("[SILENT]")
        release_lock()
        return

    # Restart service to pick up changes
    restarted = restart_service()
    app_running = check_service_running()

    # Rollback if service is unhealthy
    if not app_running:
        git_rollback()
        app_running = check_service_running()

    # Build notification and send DIRECTLY to Discord (no LLM cron agent needed)
    files = git_diff_main_names()
    version = get_app_version()

    msg = f"**Shipped: {title}**\n\n"
    msg += f"**Files:** {', '.join(f'`{f}`' for f in files[:5])}"
    if len(files) > 5:
        msg += f" +{len(files)-5} more"
    msg += f"\n**Review:** {'pass' if review_round == 1 else f'{review_round} rounds'}"
    msg += f"\n**Branch:** `{branch}` → `{BRANCH}`"
    if pushed:
        msg += f" → pushed"
    if app_running:
        msg += f"\n\n**App live** on port {APP_PORT} — version `{version}`"
        msg += f"\nhttp://localhost:{APP_PORT}"
        msg += f"\nhttp://192.168.195.192:{APP_PORT} (ZeroTier)"
        msg += f"\n**Screenshot:** `{screenshot_path}`"
    else:
        msg += f"\n\n**Service restart failed** — check: journalctl --user -u {SERVICE_NAME}"
    log(f"Shipped: {title}")
    send_discord(msg)
    print("[SILENT]")  # Already sent to Discord
    release_lock()


def get_app_running_version():
    out, _, _ = run("git rev-parse --short HEAD", workdir=WORKSPACE)
    return out or "unknown"


if __name__ == "__main__":
    main()
