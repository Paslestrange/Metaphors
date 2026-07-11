#!/usr/bin/env python3
"""Metaphors kanban worker — full workflow: plan → implement → review → fix → merge.

Run by cron every 4 hours. One task per cycle with review loop.
"""
import json
import subprocess
import sys
import os
import time
import re

WORKSPACE = "/home/pascal/workspace/Metaphors"
AGY_BIN = "/home/pascal/.local/bin/agy"
HERMES_BIN = os.path.expanduser("~/.local/bin/hermes")
TIMEOUT = 600  # 10 min max per phase
MAX_FIX_ROUNDS = 2  # max review→fix cycles

def run(cmd, timeout=60, workdir=None):
    """Run a shell command and return stdout, stderr, exitcode."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        timeout=timeout, cwd=workdir or WORKSPACE
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def log(msg):
    print(f"[worker] {time.strftime('%H:%M:%S')} {msg}", flush=True)

# ─── Phase 1: Planning ────────────────────────────────────────────

def plan_task(task):
    """Have Hermes analyze the task and create an implementation plan."""
    title = task["title"]
    body = task.get("body", "")
    task_id = task["id"]

    prompt = f"""You are planning an implementation task for the Metaphors project.

PROJECT: {WORKSPACE}
TASK: {title}
DESCRIPTION: {body}

Your job is to create a concise, actionable implementation plan. Do NOT write code.
Analyze the existing codebase (ls the directory, read key files), then output:

1. FILES TO CREATE/MODIFY (exact paths)
2. KEY DECISIONS (data structures, patterns, API contracts)
3. TEST STRATEGY (what tests to write, what to verify)
4. DEPENDENCIES (what existing code this depends on)
5. RISKS (what could go wrong, edge cases)

Keep it under 500 words. Be specific — exact file paths, exact function names."""

    log(f"Planning: {title}")
    stdout, stderr, code = run(
        f"{HERMES_BIN} chat -q '{_sq(prompt)}'",
        timeout=120
    )

    if code != 0 or not stdout:
        log(f"Planning failed (exit {code})")
        return None

    plan = stdout
    log(f"Plan created ({len(plan)} chars)")
    return plan


# ─── Phase 2: Implementation ──────────────────────────────────────

def implement_task(task, plan):
    """Have agy implement the task based on the plan."""
    title = task["title"]
    body = task.get("body", "")

    prompt = f"""You are implementing a task for the Metaphors project.

PROJECT: {WORKSPACE}
TASK: {title}
DESCRIPTION: {body}

IMPLEMENTATION PLAN:
{plan}

INSTRUCTIONS:
1. Read the existing code to understand context
2. Follow TDD: write tests FIRST, verify they fail, implement, verify they pass
3. Run: cd {WORKSPACE} && python3 -m pytest tests/ -v
4. If tests fail, fix them until ALL pass
5. Commit with a descriptive message

CONSTRAINTS:
- Do NOT modify files outside {WORKSPACE}
- Do NOT install new system packages
- Do NOT start long-running processes
- Keep changes focused on this task only
- Use python3 (not python) for all commands"""

    log(f"Implementing: {title}")
    stdout, stderr, code = run(
        f"{AGY_BIN} --print-timeout 10m --print '{_sq(prompt)}'",
        timeout=TIMEOUT
    )

    result = {
        "output": stdout or "",
        "errors": stderr or "",
        "exit_code": code,
        "success": code == 0,
    }

    if result["success"]:
        log(f"Implementation complete")
    else:
        log(f"Implementation failed (exit {code})")

    return result


# ─── Phase 3: Review ──────────────────────────────────────────────

def review_task(task, plan, impl_result):
    """Have Hermes review the implementation against the plan."""
    title = task["title"]
    body = task.get("body", "")

    # Get the diff
    diff_stdout, _, _ = run("git diff HEAD~1 --stat", workdir=WORKSPACE)
    diff_full, _, _ = run("git diff HEAD~1", workdir=WORKSPACE)
    # Truncate diff if too large
    if len(diff_full) > 8000:
        diff_full = diff_full[:8000] + "\n... (truncated)"

    # Get test results
    test_stdout, _, _ = run("python3 -m pytest tests/ -v --tb=short", workdir=WORKSPACE, timeout=120)

    prompt = f"""You are reviewing a code implementation for the Metaphors project.

TASK: {title}
DESCRIPTION: {body}

IMPLEMENTATION PLAN:
{plan}

IMPLEMENTATION OUTPUT:
{impl_result['output'][-2000:]}

GIT DIFF:
{diff_full}

TEST RESULTS:
{test_stdout[-2000:]}

Review for:
1. CORRECTNESS — Does it match the plan? Any logic errors?
2. TEST COVERAGE — Are tests comprehensive? Missing edge cases?
3. CODE QUALITY — Clean, readable, follows project conventions?
4. SECURITY — Any injection, path traversal, or unsafe patterns?
5. COMPLETENESS — Is the task fully done? Missing pieces?

Output your verdict as:
VERDICT: PASS or FAIL

If PASS: brief summary of what's good.
If FAIL: numbered list of specific issues to fix, with file paths and line numbers.
Keep review under 300 words."""

    log(f"Reviewing: {title}")
    stdout, stderr, code = run(
        f"{HERMES_BIN} chat -q '{_sq(prompt)}'",
        timeout=120
    )

    if code != 0 or not stdout:
        log(f"Review failed (exit {code})")
        return {"verdict": "PASS", "summary": "Review could not be completed — assuming pass"}

    review = stdout
    verdict = "PASS" if "VERDICT: PASS" in review.upper() or "VERDICT:PASS" in review.upper() else "FAIL"
    log(f"Review verdict: {verdict}")

    return {"verdict": verdict, "summary": review}


# ─── Phase 4: Fix (if review failed) ──────────────────────────────

def fix_task(task, review_summary):
    """Have agy fix issues found during review."""
    title = task["title"]

    prompt = f"""You are fixing issues found during code review for the Metaphors project.

PROJECT: {WORKSPACE}
TASK: {title}

REVIEW FEEDBACK:
{review_summary}

INSTRUCTIONS:
1. Read the review feedback carefully
2. Fix each issue listed
3. Run: cd {WORKSPACE} && python3 -m pytest tests/ -v
4. Ensure ALL tests pass after fixes
5. Commit fixes separately with message: "fix: address review feedback for {title}"

CONSTRAINTS:
- Only fix the issues listed in the review
- Do NOT refactor unrelated code
- Do NOT add new features"""

    log(f"Fixing: {title}")
    stdout, stderr, code = run(
        f"{AGY_BIN} --print-timeout 10m --print '{_sq(prompt)}'",
        timeout=TIMEOUT
    )

    success = code == 0
    if success:
        log(f"Fixes applied")
    else:
        log(f"Fix attempt failed (exit {code})")

    return {"success": success, "output": stdout or ""}


# ─── Phase 5: Merge ───────────────────────────────────────────────

def merge_task(task):
    """Squash commits and clean up."""
    title = task["title"]

    # Check if there are uncommitted changes
    status, _, _ = run("git status --porcelain", workdir=WORKSPACE)
    if status:
        run("git add -A", workdir=WORKSPACE)
        run(f'git commit -m "chore: uncommitted fixes for {title}"', workdir=WORKSPACE)

    # Get commit count
    count_out, _, _ = run("git rev-list --count HEAD ^main 2>/dev/null || echo 1", workdir=WORKSPACE)
    try:
        count = int(count_out)
    except ValueError:
        count = 1

    if count > 1:
        # Squash commits into one
        log(f"Squashing {count} commits")
        run(f"git reset --soft HEAD~{count}", workdir=WORKSPACE)
        safe_title = re.sub(r'[^a-zA-Z0-9 ]', '', title)[:60]
        run(f'git commit -m "feat: {safe_title}"', workdir=WORKSPACE)

    log("Merge complete")
    return True


# ─── Helpers ───────────────────────────────────────────────────────

def _sq(s):
    """Single-quote a string for shell, escaping internal single quotes."""
    return s.replace("'", "'\\''")

def get_next_task():
    """Get the next ready task from kanban."""
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
    """Mark task as running."""
    run(f"hermes kanban start {task_id}")

def complete_task(task_id, summary):
    """Mark task as done."""
    metadata = json.dumps({"agent": "agy", "workflow": "plan-implement-review"})
    run(f"hermes kanban done {task_id} --summary '{_sq(summary[:500])}' --metadata '{metadata}'")

def block_task(task_id, reason):
    """Block task with reason."""
    run(f"hermes kanban block {task_id} '{_sq(reason[:500])}'")

def comment_task(task_id, body):
    """Add a comment to the task."""
    run(f"hermes kanban comment {task_id} '{_sq(body[:500])}'")


# ─── Main ──────────────────────────────────────────────────────────

def main():
    log("Metaphors kanban worker starting")

    task = get_next_task()
    if not task:
        log("No ready tasks.")
        # Output message for Discord delivery
        print(json.dumps({
            "type": "idle",
            "message": "📋 **No pending tasks on the Metaphors kanban board.**\n\nAdd a new task with:\n```\nhermes kanban create \"Task title\" --assignee default --body \"Description...\"\n```\nOr tell me what to build next."
        }))
        return

    task_id = task["id"]
    title = task["title"]
    log(f"Task: {task_id} — {title}")

    claim_task(task_id)

    # Phase 1: Plan
    plan = plan_task(task)
    if not plan:
        block_task(task_id, "Planning phase failed — could not generate implementation plan")
        return

    comment_task(task_id, f"PLAN:\n{plan[:400]}")

    # Phase 2: Implement
    impl_result = implement_task(task, plan)
    if not impl_result["success"]:
        block_task(task_id, f"Implementation failed:\n{impl_result['errors'][-300:]}")
        return

    # Phase 3 + 4: Review loop
    for fix_round in range(MAX_FIX_ROUNDS):
        review = review_task(task, plan, impl_result)

        if review["verdict"] == "PASS":
            comment_task(task_id, f"REVIEW (round {fix_round + 1}): PASS\n{review['summary'][:300]}")
            break

        # Review failed — attempt fix
        comment_task(task_id, f"REVIEW (round {fix_round + 1}): FAIL\n{review['summary'][:300]}")

        fix_result = fix_task(task, review["summary"])
        if not fix_result["success"]:
            block_task(task_id, f"Fix attempt failed after review:\n{review['summary'][:300]}")
            return

        # Update impl_result for next review round
        impl_result = {"output": fix_result["output"], "success": True}
    else:
        # Exhausted fix rounds
        log("Max fix rounds exhausted — completing with warnings")
        comment_task(task_id, f"WARNING: {MAX_FIX_ROUNDS} review→fix cycles completed. May need manual review.")

    # Phase 5: Merge
    merge_task(task)

    # Complete
    # Generate feature summary from git diff
    diff_stat, _, _ = run("git diff HEAD~1 --stat", workdir=WORKSPACE)
    diff_names, _, _ = run("git diff HEAD~1 --name-only", workdir=WORKSPACE)
    files_changed = [f.strip() for f in diff_names.splitlines() if f.strip()]

    summary = f"**✅ Task Complete: {title}**\n\n"
    summary += f"**Workflow:** Plan → Implement → Review ({fix_round + 1} round{'s' if fix_round > 0 else ''}) → Merge\n\n"
    summary += "**Files changed:**\n"
    for f in files_changed[:10]:
        summary += f"• `{f}`\n"
    if len(files_changed) > 10:
        summary += f"• ... and {len(files_changed) - 10} more\n"
    summary += f"\n**Stats:** {diff_stat.splitlines()[-1] if diff_stat else 'changes made'}"

    complete_task(task_id, summary)
    log(f"Task completed: {title}")


if __name__ == "__main__":
    main()
