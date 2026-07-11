#!/usr/bin/env python3
"""Metaphors kanban worker — picks next task, dispatches to agy, reports result.

Run by cron every 4 hours. One task per cycle to conserve usage.
"""
import json
import subprocess
import sys
import os
import time

WORKSPACE = "/home/pascal/workspace/Metaphors"
AGY_BIN = "/home/pascal/.local/bin/agy"
TIMEOUT = 600  # 10 min max per task

def run(cmd, **kwargs):
    """Run a shell command and return stdout."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=kwargs.get("timeout", 60), **{k:v for k,v in kwargs.items() if k != "timeout"})
    return result.stdout.strip(), result.returncode

def get_next_task():
    """Get the next ready task from kanban."""
    output, code = run("hermes kanban list --json 2>/dev/null")
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

def dispatch_to_agy(task):
    """Send task to agy for implementation."""
    title = task["title"]
    task_id = task["id"]
    body = task.get("body", "")

    prompt = f"""You are working in {WORKSPACE} — a new Python project called Metaphors.

TASK: {title}

DETAILS:
{body}

INSTRUCTIONS:
1. Read the existing code to understand context (ls the directory, check what exists)
2. Follow TDD: write tests first, verify they fail, implement, verify they pass
3. Run: cd {WORKSPACE} && python -m pytest tests/ -v to verify
4. Commit your changes with a descriptive message
5. Report what you did, what files changed, and test results

CONSTRAINTS:
- Do NOT modify files outside {WORKSPACE}
- Do NOT install new system packages (pip install in requirements.txt only)
- Do NOT start long-running processes
- Keep changes focused on this task only"""

    print(f"[worker] Dispatching to agy: {title}")
    cmd = f"cd {WORKSPACE} && {AGY_BIN} --print-timeout 10m --print {_shell_quote(prompt)}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=TIMEOUT)
    return result.stdout, result.stderr, result.returncode

def _shell_quote(s):
    """Quote a string for shell."""
    return "'" + s.replace("'", "'\\''") + "'"

def main():
    print(f"[worker] Metaphors kanban worker starting at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[worker] Workspace: {WORKSPACE}")

    task = get_next_task()
    if not task:
        print("[worker] No ready tasks. Nothing to do.")
        return

    task_id = task["id"]
    title = task["title"]
    print(f"[worker] Next task: {task_id} — {title}")

    # Mark as running
    subprocess.run(f"hermes kanban start {task_id}", shell=True, capture_output=True)

    # Dispatch to agy
    stdout, stderr, code = dispatch_to_agy(task)

    # Parse result
    summary = stdout[-2000:] if stdout else "No output"
    success = code == 0

    if success:
        # Mark as done
        metadata = json.dumps({"agent": "agy", "exit_code": code})
        subprocess.run(
            f"hermes kanban done {task_id} --summary {_shell_quote(summary)} --metadata '{metadata}'",
            shell=True, capture_output=True
        )
        print(f"[worker] Task completed: {title}")
        print(f"[worker] Summary: {summary[:200]}")
    else:
        # Block with error info
        error_info = f"agy failed (exit {code}):\n{stderr[-1000:]}" if stderr else f"agy failed (exit {code})"
        subprocess.run(
            f"hermes kanban block {task_id} {_shell_quote(error_info)}",
            shell=True, capture_output=True
        )
        print(f"[worker] Task blocked: {title}")
        print(f"[worker] Error: {error_info[:200]}")

if __name__ == "__main__":
    main()
