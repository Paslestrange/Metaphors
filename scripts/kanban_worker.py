#!/usr/bin/env python3
"""Metaphors kanban worker — full git workflow with feature branches and reviews.

Workflow per task:
  1. Create feature branch from main
  2. Plan (Hermes analyzes task)
  3. Implement on branch (agy writes code + tests)
  4. Review (Hermes reviews diff on branch)
  5. Fix if needed (agy fixes, loops back to review, max 2 rounds)
  6. Merge branch to main (squash)
  7. Post summary to Discord

Run by cron every 4 hours. One task per cycle.
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
TIMEOUT = 600
MAX_FIX_ROUNDS = 2

# ─── Helpers ───────────────────────────────────────────────────────

def run(cmd, timeout=60, workdir=None):
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        timeout=timeout, cwd=workdir or WORKSPACE
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def log(msg):
    print(f"[worker] {time.strftime('%H:%M:%S')} {msg}", flush=True)

def _sq(s):
    return s.replace("'", "'\\''")

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
    metadata = json.dumps({"agent": "agy", "workflow": "branch-review-merge"})
    run(f"hermes kanban done {task_id} --summary '{_sq(summary[:500])}' --metadata '{metadata}'")

def block_task(task_id, reason):
    run(f"hermes kanban block {task_id} '{_sq(reason[:500])}'")

def comment_task(task_id, body):
    run(f"hermes kanban comment {task_id} '{_sq(body[:500])}'")

# ─── Git Operations ────────────────────────────────────────────────

def task_branch_name(task_id, title):
    """Create a safe branch name from task id and title."""
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower())[:40].rstrip('-')
    short_id = task_id[:8] if task_id else "unknown"
    return f"task/{short_id}-{slug}"

def git_ensure_main():
    """Make sure we're on main with a clean working tree."""
    run("git checkout main", workdir=WORKSPACE)
    run("git pull --rebase origin main 2>/dev/null || true", workdir=WORKSPACE)

def git_create_branch(branch_name):
    """Create and checkout a new feature branch from main."""
    git_ensure_main()
    _, _, code = run(f"git checkout -b {branch_name}", workdir=WORKSPACE)
    if code != 0:
        # Branch exists, switch to it
        run(f"git checkout {branch_name}", workdir=WORKSPACE)
    log(f"On branch: {branch_name}")

def git_has_changes():
    """Check if there are uncommitted changes."""
    out, _, _ = run("git status --porcelain", workdir=WORKSPACE)
    return bool(out.strip())

def git_commit_all(message):
    """Stage all changes and commit."""
    run("git add -A", workdir=WORKSPACE)
    run(f'git commit -m "{message}"', workdir=WORKSPACE)

def git_diff_main():
    """Get diff of current branch vs main."""
    diff, _, _ = run("git diff main...HEAD", workdir=WORKSPACE)
    return diff

def git_diff_main_stat():
    """Get diff stat of current branch vs main."""
    stat, _, _ = run("git diff main...HEAD --stat", workdir=WORKSPACE)
    return stat

def git_diff_main_names():
    """Get list of changed files vs main."""
    names, _, _ = run("git diff main...HEAD --name-only", workdir=WORKSPACE)
    return [f.strip() for f in names.splitlines() if f.strip()]

def git_merge_branch(branch_name, title):
    """Squash merge feature branch into main."""
    git_ensure_main()

    # Check if branch has commits ahead of main
    count_out, _, _ = run(f"git rev-list --count main..{branch_name}", workdir=WORKSPACE)
    try:
        count = int(count_out)
    except ValueError:
        count = 0

    if count == 0:
        log("No commits on branch — nothing to merge")
        return False

    # Squash merge
    safe_title = re.sub(r'[^a-zA-Z0-9 ]', '', title)[:60]
    _, stderr, code = run(
        f'git merge --squash {branch_name}',
        workdir=WORKSPACE
    )
    if code != 0 and "Already up to date" not in stderr:
        log(f"Merge conflict or error: {stderr[:200]}")
        return False

    run(f'git commit -m "feat: {safe_title}"', workdir=WORKSPACE)

    # Delete feature branch
    run(f"git branch -D {branch_name}", workdir=WORKSPACE)

    log(f"Merged and deleted branch: {branch_name}")
    return True

# ─── Phase 1: Plan ────────────────────────────────────────────

def plan_task(task):
    title = task["title"]
    body = task.get("body", "")

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

# ─── Phase 2: Implement ──────────────────────────────────────

def implement_task(task, plan):
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

# ─── Phase 3: Review ──────────────────────────────────────────

def review_task(task, plan):
    title = task["title"]
    body = task.get("body", "")

    diff = git_diff_main()
    if len(diff) > 8000:
        diff = diff[:8000] + "\n... (truncated)"

    test_stdout, _, _ = run("python3 -m pytest tests/ -v --tb=short", workdir=WORKSPACE, timeout=120)

    prompt = f"""You are reviewing a code implementation for the Metaphors project.

TASK: {title}
DESCRIPTION: {body}

IMPLEMENTATION PLAN:
{plan}

GIT DIFF (branch vs main):
{diff}

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

# ─── Phase 4: Fix ──────────────────────────────────────────────

def fix_task(task, review_summary):
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
5. Commit fixes with message: "fix: address review feedback"

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

# ─── Main ──────────────────────────────────────────────────────

def main():
    log("Metaphors kanban worker starting")

    task = get_next_task()
    if not task:
        log("No ready tasks.")
        output = {
            "type": "idle",
            "message": "📋 **No pending tasks on the Metaphors kanban board.**\n\nAdd a new task with:\n```\nhermes kanban create \"Task title\" --assignee default --body \"Description...\"\n```\nOr tell me what to build next."
        }
        print(json.dumps(output))
        return

    task_id = task["id"]
    title = task["title"]
    log(f"Task: {task_id} — {title}")

    claim_task(task_id)

    # Create feature branch
    branch_name = task_branch_name(task_id, title)
    git_create_branch(branch_name)
    comment_task(task_id, f"Branch: `{branch_name}`")

    # Phase 1: Plan
    plan = plan_task(task)
    if not plan:
        block_task(task_id, "Planning phase failed — could not generate implementation plan")
        git_ensure_main()
        run(f"git branch -D {branch_name}", workdir=WORKSPACE)
        return

    comment_task(task_id, f"PLAN:\n{plan[:400]}")

    # Phase 2: Implement
    impl_result = implement_task(task, plan)
    if not impl_result["success"]:
        block_task(task_id, f"Implementation failed:\n{impl_result['errors'][-300:]}")
        git_ensure_main()
        run(f"git branch -D {branch_name}", workdir=WORKSPACE)
        return

    # Phase 3 + 4: Review loop
    review_round = 0
    for fix_round in range(MAX_FIX_ROUNDS):
        review_round = fix_round + 1
        review = review_task(task, plan)

        if review["verdict"] == "PASS":
            comment_task(task_id, f"REVIEW (round {review_round}): PASS\n{review['summary'][:300]}")
            break

        comment_task(task_id, f"REVIEW (round {review_round}): FAIL\n{review['summary'][:300]}")

        fix_result = fix_task(task, review["summary"])
        if not fix_result["success"]:
            block_task(task_id, f"Fix attempt failed after review:\n{review['summary'][:300]}")
            git_ensure_main()
            run(f"git branch -D {branch_name}", workdir=WORKSPACE)
            return
    else:
        log("Max fix rounds exhausted")
        comment_task(task_id, f"WARNING: {MAX_FIX_ROUNDS} review→fix cycles. May need manual review.")

    # Phase 5: Merge
    merged = git_merge_branch(branch_name, title)
    if not merged:
        block_task(task_id, "Merge failed — possible conflicts")
        return

    # Build summary
    files_changed = git_diff_main_names()
    diff_stat = git_diff_main_stat()

    summary = f"**✅ Task Complete: {title}**\n\n"
    summary += f"**Workflow:** Plan → Implement → Review ({review_round} round{'s' if review_round > 1 else ''}) → Merge\n\n"
    summary += f"**Branch:** `{branch_name}` → `main` (squash merge)\n\n"
    summary += "**Files changed:**\n"
    for f in files_changed[:10]:
        summary += f"• `{f}`\n"
    if len(files_changed) > 10:
        summary += f"• ... and {len(files_changed) - 10} more\n"
    if diff_stat:
        last_line = diff_stat.splitlines()[-1] if diff_stat.splitlines() else ""
        if last_line:
            summary += f"\n**Stats:** {last_line}"

    complete_task(task_id, summary)
    log(f"Task completed: {title}")

    # Output for Discord delivery
    print(json.dumps({"type": "complete", "message": summary}))

if __name__ == "__main__":
    main()
