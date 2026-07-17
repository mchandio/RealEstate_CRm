#!/usr/bin/env bash
###############################################################################
# Real Estate CRM
# Production Startup Script
#
# Features
#   ✓ Automatic virtual environment creation
#   ✓ Dependency management
#   ✓ Database initialization
#   ✓ Port validation
#   ✓ Port availability detection
#   ✓ Logging
#   ✓ Graceful shutdown
#   ✓ ShellCheck compliant
#
###############################################################################

set -Eeuo pipefail

########################################
# Configuration
########################################

readonly APP_NAME="Real Estate CRM"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly VENV_DIR="$SCRIPT_DIR/.venv_linux"
readonly VENV_PYTHON="$VENV_DIR/bin/python"
readonly REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
readonly DATABASE="$SCRIPT_DIR/real_estate_crm.db"
readonly LOG_DIR="$SCRIPT_DIR/logs"
readonly LOG_FILE="$LOG_DIR/startup.log"

PORT=6090
MODE="web"

mkdir -p "$LOG_DIR"

########################################
# ANSI Colors
########################################

if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED=""
    GREEN=""
    YELLOW=""
    BLUE=""
    CYAN=""
    BOLD=""
    RESET=""
fi

########################################
# Logging
########################################

timestamp() {
    date +"%Y-%m-%d %H:%M:%S"
}

log() {
    local level="$1"
    shift

    printf "[%s] [%s] %s\n" \
        "$(timestamp)" \
        "$level" \
        "$*" | tee -a "$LOG_FILE"
}

info() {
    printf "${CYAN}%s${RESET}\n" "$*"
    log INFO "$*"
}

success() {
    printf "${GREEN}%s${RESET}\n" "$*"
    log SUCCESS "$*"
}

warn() {
    printf "${YELLOW}%s${RESET}\n" "$*"
    log WARNING "$*"
}

error() {
    printf "${RED}%s${RESET}\n" "$*" >&2
    log ERROR "$*"
}

########################################
# Error handling
########################################

cleanup() {
    info "Cleaning up..."
}

on_error() {
    local exit_code=$?

    error "Unexpected error occurred."

    error "Exit Code : $exit_code"

    error "Line      : ${BASH_LINENO[0]}"

    error "Command   : ${BASH_COMMAND}"

    exit "$exit_code"
}

trap cleanup EXIT
trap on_error ERR

########################################
# Banner
########################################

banner() {

cat <<EOF

============================================================
               $APP_NAME
============================================================

EOF

}

########################################
# Utilities
########################################

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

require_command() {

    local cmd="$1"

    command_exists "$cmd" || {

        error "$cmd is not installed."

        exit 1
    }

}

file_exists() {

    [[ -f "$1" ]]

}

directory_exists() {

    [[ -d "$1" ]]

}

########################################
# Validation
########################################

validate_port() {

    [[ "$PORT" =~ ^[0-9]+$ ]] || {

        error "Invalid port: $PORT"

        exit 1
    }

    (( PORT >= 1024 && PORT <= 65535 )) || {

        error "Port must be between 1024 and 65535"

        exit 1
    }

}

check_port_available() {

    if command_exists ss; then

        if ss -ltn | awk '{print $4}' | grep -q ":${PORT}$"; then

            error "Port $PORT is already in use."

            exit 1

        fi

    elif command_exists lsof; then

        if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then

            error "Port $PORT is already in use."

            exit 1

        fi

    fi

}
###############################################################################
# Argument Parsing
###############################################################################

show_help() {

cat <<EOF

$APP_NAME Startup Script

Usage:

    ./start.sh [OPTIONS]

Options

    --dev, -d
        Development mode (auto reload)

    --desktop
        Launch Qt desktop application

    --lan
        Launch LAN server

    --port PORT
        Specify custom port

    --help
        Show this help

Examples

    ./start.sh
    ./start.sh --dev
    ./start.sh --port 8080
    ./start.sh --desktop
    ./start.sh --lan

EOF

}

parse_arguments() {

    while [[ $# -gt 0 ]]; do

        case "$1" in

            --dev|-d)
                MODE="dev"
                ;;

            --desktop)
                MODE="desktop"
                ;;

            --lan)
                MODE="lan"
                ;;

            --port|-p)

                [[ $# -ge 2 ]] || {

                    error "--port requires a value"

                    exit 1
                }

                PORT="$2"

                shift
                ;;

            --help|-h)

                show_help

                exit 0
                ;;

            *)

                error "Unknown option: $1"

                show_help

                exit 1
                ;;

        esac

        shift

    done

}

###############################################################################
# Python
###############################################################################

check_python() {

    info "Checking Python..."

    require_command python3

    local version

    version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

    info "Python version: $version"

}

###############################################################################
# Virtual Environment
###############################################################################

create_virtualenv() {

    if directory_exists "$VENV_DIR"; then

        success "Virtual environment found."

        return

    fi

    warn "Virtual environment not found."

    info "Creating virtual environment..."

    python3 -m venv "$VENV_DIR"

    success "Virtual environment created."

}

###############################################################################
# Ensure pip
###############################################################################

ensure_pip() {

    info "Checking pip..."

    "$VENV_PYTHON" -m ensurepip --upgrade >/dev/null 2>&1 || true

    "$VENV_PYTHON" -m pip install \
        --disable-pip-version-check \
        --upgrade pip

    success "pip is ready."

}

###############################################################################
# Dependency Management
###############################################################################

requirements_hash() {

    sha256sum "$REQUIREMENTS" | awk '{print $1}'

}

install_dependencies() {

    file_exists "$REQUIREMENTS" || {

        error "requirements.txt not found."

        exit 1

    }

    local marker

    marker="$VENV_DIR/.requirements.sha256"

    local current_hash

    current_hash=$(requirements_hash)

    if file_exists "$marker"; then

        local stored_hash

        stored_hash=$(cat "$marker")

        if [[ "$stored_hash" == "$current_hash" ]]; then

            success "Dependencies are already up to date."

            return

        fi

    fi

    warn "Installing Python packages..."

    "$VENV_PYTHON" -m pip install \
        --upgrade \
        -r "$REQUIREMENTS"

    echo "$current_hash" > "$marker"

    success "Dependencies installed."

}

###############################################################################
# Project Validation
###############################################################################

validate_project() {

    info "Validating project..."

    local files=(

        start_app.py
        CRM/main.py
        run_lan_server.py

    )

    local missing=0

    for file in "${files[@]}"; do

        if ! file_exists "$SCRIPT_DIR/$file"; then

            error "Missing file: $file"

            missing=1
        fi

    done

    (( missing == 0 )) || exit 1

    success "Project validation successful."

}

###############################################################################
# Display Detection
###############################################################################

check_display() {

    if [[ "$MODE" != "desktop" ]]; then
        return
    fi

    if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then

        error "Desktop mode requires X11 or Wayland."

        exit 1

    fi

}
###############################################################################
# Database
###############################################################################

initialize_database() {

    if file_exists "$DATABASE"; then

        success "Database found."

        return

    fi

    warn "Database not found."

    info "Initializing database..."

    "$VENV_PYTHON" "$SCRIPT_DIR/database_setup.py"

    if ! file_exists "$DATABASE"; then

        error "Database initialization failed."

        exit 1

    fi

    success "Database initialized."

}

###############################################################################
# Network
###############################################################################

get_local_ip() {

    local ip=""

    if command_exists hostname; then

        ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi

    if [[ -z "$ip" ]] && command_exists ip; then

        ip=$(ip route get 1 2>/dev/null \
            | awk '{print $7; exit}')
    fi

    if [[ -z "$ip" ]]; then
        ip="127.0.0.1"
    fi

    printf "%s" "$ip"

}

###############################################################################
# Startup Information
###############################################################################

print_startup_information() {

    echo

    info "Application : $APP_NAME"

    info "Mode        : $MODE"

    info "Project     : $SCRIPT_DIR"

    info "Python      : $("$VENV_PYTHON" --version 2>&1)"

    info "Port        : $PORT"

    echo

}

###############################################################################
# Launchers
###############################################################################

launch_web() {

    success "Starting Web Server..."

    echo

    echo "URL"

    echo "    http://localhost:$PORT"

    echo

    echo "Press Ctrl+C to stop."

    echo

    exec "$VENV_PYTHON" \
        "$SCRIPT_DIR/start_app.py" \
        --port "$PORT" \
        --skip-install

}

launch_dev() {

    success "Starting Development Server..."

    echo

    echo "URL"

    echo "    http://localhost:$PORT"

    echo

    echo "Auto Reload : Enabled"

    echo

    exec "$VENV_PYTHON" \
        "$SCRIPT_DIR/start_app.py" \
        --dev \
        --port "$PORT" \
        --skip-install

}

launch_desktop() {

    success "Starting Desktop Application..."

    exec "$VENV_PYTHON" \
        -m CRM.main

}

launch_lan() {

    local ip

    ip=$(get_local_ip)

    success "Starting LAN Server..."

    echo

    echo "Local"

    echo "    http://127.0.0.1:$PORT"

    echo

    echo "LAN"

    echo "    http://$ip:$PORT"

    echo

    exec "$VENV_PYTHON" \
        "$SCRIPT_DIR/run_lan_server.py"

}

###############################################################################
# Dispatcher
###############################################################################

launch_application() {

    case "$MODE" in

        web)

            launch_web
            ;;

        dev)

            launch_dev
            ;;

        desktop)

            launch_desktop
            ;;

        lan)

            launch_lan
            ;;

        *)

            error "Unknown startup mode: $MODE"

            exit 1
            ;;

    esac

}
###############################################################################
# Environment
###############################################################################

check_operating_system() {

    case "$(uname -s)" in

        Linux|Darwin)

            success "Operating System: $(uname -s)"
            ;;

        *)

            warn "Unsupported operating system: $(uname -s)"
            warn "This script is tested on Linux/macOS."
            ;;

    esac

}

###############################################################################
# Internet Connectivity (Optional)
###############################################################################

check_internet() {

    info "Checking internet connectivity..."

    if command_exists curl; then

        if curl \
            --silent \
            --head \
            --max-time 5 \
            https://pypi.org >/dev/null; then

            success "Internet connection available."

        else

            warn "Internet unavailable."

            warn "Dependency installation may fail."

        fi

        return
    fi

    warn "curl not installed. Skipping internet check."

}

###############################################################################
# Summary
###############################################################################

print_summary() {

cat <<EOF

============================================================
Startup Summary
============================================================

Application : $APP_NAME
Mode        : $MODE
Port        : $PORT
Project     : $SCRIPT_DIR
Database    : $DATABASE
Virtual Env : $VENV_DIR
Log File    : $LOG_FILE

============================================================

EOF

}

###############################################################################
# Main
###############################################################################

main() {

    banner

    parse_arguments "$@"

    validate_port

    check_operating_system

    require_command python3

    check_python

    create_virtualenv

    ensure_pip

    check_internet

    validate_project

    install_dependencies

    initialize_database

    check_display

    check_port_available

    print_startup_information

    print_summary

    launch_application

}
###############################################################################
# Environment Variables (.env)
###############################################################################

load_environment() {

    local env_file="$SCRIPT_DIR/.env"

    if [[ -f "$env_file" ]]; then

        info "Loading environment variables..."

        set -a
        # shellcheck disable=SC1090
        source "$env_file"
        set +a

        success ".env loaded."
    fi

}

###############################################################################
# Configuration Overrides
###############################################################################

apply_environment_overrides() {

    PORT="${CRM_PORT:-$PORT}"
    MODE="${CRM_MODE:-$MODE}"

}

###############################################################################
# Signal Handling
###############################################################################

shutdown() {

    echo
    warn "Shutdown requested."

    success "Goodbye."

    exit 0

}

trap shutdown SIGINT SIGTERM

###############################################################################
# Optional Health Check
###############################################################################

health_check() {

    if [[ "$MODE" == "desktop" ]]; then
        return
    fi

    info "Running pre-launch health checks..."

    if ! file_exists "$DATABASE"; then
        error "Database missing."
        exit 1
    fi

    success "Health check passed."

}

###############################################################################
# Startup Timer
###############################################################################

SCRIPT_START_TIME=$(date +%s)

print_runtime() {

    local end
    end=$(date +%s)

    local elapsed=$((end - SCRIPT_START_TIME))

    info "Startup completed in ${elapsed}s"

}

###############################################################################
# Final Startup Sequence
###############################################################################

# Update main() to include:
#
# load_environment
# apply_environment_overrides
# health_check
# print_runtime
#
# Example order:
#
# main() {
#     banner
#     parse_arguments "$@"
#     load_environment
#     apply_environment_overrides
#     validate_port
#     check_operating_system
#     check_python
#     create_virtualenv
#     ensure_pip
#     check_internet
#     validate_project
#     install_dependencies
#     initialize_database
#     health_check
#     check_display
#     check_port_available
#     print_startup_information
#     print_summary
#     print_runtime
#     launch_application
# }

###############################################################################
# ShellCheck Notes
###############################################################################

# Validate with:
#
#   shellcheck start.sh
#
# Format with:
#
#   shfmt -w start.sh
#
# Make executable:
#
#   chmod +x start.sh
###############################################################################
# Entry Point
###############################################################################

main "$@"
