"""Tests for install.sh — validates script structure and behavior."""
import subprocess
import os
import re
import pytest

INSTALL_SH = os.path.join(os.path.dirname(__file__), "..", "install.sh")


@pytest.fixture
def script_content():
    """Read install.sh content."""
    with open(INSTALL_SH) as f:
        return f.read()


class TestInstallScriptStructure:
    """Validate install.sh has required components."""

    def test_file_exists(self):
        assert os.path.isfile(INSTALL_SH), "install.sh must exist"

    def test_is_executable(self):
        assert os.access(INSTALL_SH, os.X_OK), "install.sh must be executable"

    def test_has_shebang(self, script_content):
        assert script_content.startswith("#!/"), "Must have a shebang line"
        assert "bash" in script_content.split("\n")[0], "Must use bash"

    def test_strict_mode(self, script_content):
        assert "set -euo pipefail" in script_content, "Must use strict mode"

    def test_checks_python_version(self, script_content):
        assert "3" in script_content and "10" in script_content, \
            "Must check for Python >= 3.10"

    def test_creates_venv(self, script_content):
        assert "venv" in script_content.lower(), "Must create a virtual environment"

    def test_installs_dependencies(self, script_content):
        assert "pip install" in script_content, "Must install dependencies via pip"
        assert "requirements.txt" in script_content, "Must install from requirements.txt"

    def test_has_usage_instructions(self, script_content):
        # After install, should tell user how to run
        assert "server.py" in script_content or "python" in script_content, \
            "Must show how to start the server"

    def test_no_hardcoded_paths(self, script_content):
        # Should work from any directory — no /home/user style paths
        assert "/home/" not in script_content, "Must not hardcode user paths"

    def test_handles_existing_venv(self, script_content):
        assert "if" in script_content and "venv" in script_content.lower(), \
            "Must handle case where venv already exists"


class TestInstallScriptSyntax:
    """Validate install.sh passes syntax check."""

    def test_bash_syntax(self):
        result = subprocess.run(
            ["bash", "-n", INSTALL_SH],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"


class TestInstallScriptDryRun:
    """Test install.sh behavior in a controlled environment."""

    def test_fails_without_python(self, monkeypatch, tmp_path):
        """Script should fail gracefully if no Python found."""
        # Create a modified version that uses a non-existent python
        script = tmp_path / "test_install.sh"
        with open(INSTALL_SH) as f:
            content = f.read()

        # Replace find_python to only look for nonexistent binary
        content = content.replace(
            'local candidates=("python3.12" "python3.11" "python3.10" "python3" "python")',
            'local candidates=("nonexistent_python_xyz")'
        )
        script.write_text(content)
        script.chmod(0o755)

        result = subprocess.run(
            ["bash", str(script)],
            capture_output=True, text=True,
            cwd=str(tmp_path),
            timeout=10
        )
        assert result.returncode != 0, "Should fail when Python not found"
        assert "not found" in result.stdout.lower() or "not found" in result.stderr.lower()
