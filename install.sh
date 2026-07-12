#!/usr/bin/env bash
# install.sh — One-command setup for Metaphors
# Usage: curl ... | bash  or  bash install.sh
set -euo pipefail

# --- Configuration ---
MIN_PYTHON_MAJOR=3
MIN_PYTHON_MINOR=10
VENV_DIR=".venv"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}▸${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
fail()  { echo -e "${RED}✗${NC} $*"; exit 1; }

# --- Pre-flight: find a suitable Python ---
find_python() {
    local candidates=("python3.12" "python3.11" "python3.10" "python3" "python")
    for cmd in "${candidates[@]}"; do
        if command -v "$cmd" &>/dev/null; then
            echo "$cmd"
            return
        fi
    done
    return 1
}

check_python_version() {
    local python="$1"
    local version
    version=$("$python" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local major minor
    major=$(echo "$version" | cut -d. -f1)
    minor=$(echo "$version" | cut -d. -f2)

    if (( major < MIN_PYTHON_MAJOR )) || { (( major == MIN_PYTHON_MAJOR )) && (( minor < MIN_PYTHON_MINOR )); }; then
        return 1
    fi
    echo "$version"
    return 0
}

# --- Main ---
main() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     Metaphors — Setup                ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
    echo ""

    # Step 1: Find Python
    info "Checking Python version..."
    local python
    python=$(find_python) || fail "Python not found. Install Python >= ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}."

    local version
    version=$(check_python_version "$python") || fail "Python ${MIN_PYTHON_MAJOR}.${MIN_PYTHON_MINOR}+ required (found $("$python" --version 2>&1))."
    ok "Python $version ($python)"

    # Step 2: Create virtual environment
    if [[ ! -d "$VENV_DIR" ]]; then
        info "Creating virtual environment in ${VENV_DIR}/..."
        "$python" -m venv "$VENV_DIR"
        ok "Virtual environment created"
    else
        ok "Virtual environment already exists"
    fi

    # Activate
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"

    # Step 3: Upgrade pip
    info "Upgrading pip..."
    python -m pip install --upgrade pip --quiet
    ok "pip upgraded"

    # Step 4: Install project dependencies
    info "Installing dependencies..."
    pip install --quiet -r requirements.txt
    ok "Dependencies installed"

    # Step 5: Environment file
    if [[ -f ".env.example" && ! -f ".env" ]]; then
        cp .env.example .env
        ok "Created .env from .env.example"
    elif [[ -f ".env" ]]; then
        ok ".env already exists"
    fi

    # Done
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║     Setup complete!                  ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
    echo ""
    echo "  Next steps:"
    echo ""
    echo "    source ${VENV_DIR}/bin/activate"
    echo "    python server.py"
    echo ""
    echo "  Then open http://localhost:8080"
    echo ""
    echo "  Run tests:  make test"
    echo "  Run lint:   make lint"
    echo ""
}

main "$@"
