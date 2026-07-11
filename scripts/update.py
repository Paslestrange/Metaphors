#!/usr/bin/env python3
"""
Self-update mechanism for Metaphors project.
Checks for updates, pulls latest changes, refreshes dependencies,
runs migrations, and displays changelog.
"""

import subprocess
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"


def run_cmd(cmd, cwd=None, check=True):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd or PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=check
        )
        return result.stdout.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stderr.strip(), e.returncode


def check_git_remote():
    """Check if git remote is configured."""
    output, code = run_cmd("git remote -v")
    if not output:
        print("⚠️  No git remote configured. Cannot check for updates.")
        print("   Add a remote with: git remote add origin <url>")
        return False
    return True


def get_current_commit():
    """Get current HEAD commit hash."""
    output, _ = run_cmd("git rev-parse HEAD")
    return output


def fetch_and_check_updates():
    """Fetch from remote and check if updates are available."""
    print("🔍 Checking for updates...")
    
    # Fetch latest from remote
    output, code = run_cmd("git fetch origin")
    if code != 0:
        print(f"❌ Failed to fetch from remote: {output}")
        return None, None
    
    # Get current and remote HEAD
    local_head, _ = run_cmd("git rev-parse HEAD")
    remote_head, _ = run_cmd("git rev-parse origin/HEAD")
    
    if local_head == remote_head:
        print("✅ Already up to date.")
        return None, None
    
    # Get commits between local and remote
    changelog, _ = run_cmd(f"git log --oneline {local_head}..{remote_head}")
    return remote_head, changelog


def pull_updates():
    """Pull latest changes from remote."""
    print("\n📥 Pulling latest changes...")
    output, code = run_cmd("git pull origin HEAD")
    if code != 0:
        print(f"❌ Failed to pull updates: {output}")
        return False
    print("✅ Updates pulled successfully.")
    return True


def check_requirements_changed(old_head, new_head):
    """Check if requirements.txt changed between commits."""
    if not old_head or not new_head:
        return False
    
    diff, _ = run_cmd(f"git diff {old_head} {new_head} -- requirements.txt")
    return bool(diff)


def reinstall_dependencies():
    """Reinstall Python dependencies."""
    print("\n📦 Reinstalling dependencies...")
    
    if not REQUIREMENTS_FILE.exists():
        print("⚠️  No requirements.txt found. Skipping dependency installation.")
        return
    
    # Check if venv exists
    venv_path = PROJECT_ROOT / ".venv"
    if venv_path.exists():
        pip_cmd = f"{venv_path}/bin/pip install -r requirements.txt"
    else:
        pip_cmd = "pip3 install -r requirements.txt"
    
    output, code = run_cmd(pip_cmd)
    if code != 0:
        print(f"❌ Failed to install dependencies: {output}")
        return
    
    print("✅ Dependencies updated.")


def run_migrations():
    """Run database migrations if they exist."""
    if not MIGRATIONS_DIR.exists():
        return
    
    migration_files = sorted(MIGRATIONS_DIR.glob("*.py"))
    if not migration_files:
        return
    
    print(f"\n🔄 Running {len(migration_files)} migration(s)...")
    for migration in migration_files:
        print(f"   Running {migration.name}...")
        output, code = run_cmd(f"python3 {migration}")
        if code != 0:
            print(f"   ❌ Migration failed: {output}")
            return
    print("✅ Migrations completed.")


def print_changelog(changelog):
    """Print the changelog."""
    if not changelog:
        return
    
    print("\n📋 Changelog:")
    print("-" * 50)
    for line in changelog.split('\n'):
        print(f"  {line}")
    print("-" * 50)


def main():
    """Main update workflow."""
    print("=" * 50)
    print("🚀 Metaphors Self-Update")
    print("=" * 50)
    
    # Check git remote
    if not check_git_remote():
        sys.exit(1)
    
    # Get current state
    old_head = get_current_commit()
    
    # Fetch and check for updates
    new_head, changelog = fetch_and_check_updates()
    if not new_head:
        sys.exit(0)
    
    # Show what will be updated
    print(f"\n📊 Updates available:")
    print_changelog(changelog)
    
    # Check if requirements will change
    req_changed = check_requirements_changed(old_head, new_head)
    if req_changed:
        print("\n⚠️  Dependencies will be updated.")
    
    # Pull updates
    if not pull_updates():
        sys.exit(1)
    
    # Reinstall dependencies if needed
    if req_changed:
        reinstall_dependencies()
    
    # Run migrations
    run_migrations()
    
    print("\n" + "=" * 50)
    print("✅ Update complete!")
    print("=" * 50)


if __name__ == "__main__":
    main()
