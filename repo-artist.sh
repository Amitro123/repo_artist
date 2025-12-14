#!/usr/bin/env bash
# Repo-Artist CLI Wrapper for Unix/Linux/Mac
# Sets PYTHONPATH and runs the CLI

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH="$SCRIPT_DIR"
python "$SCRIPT_DIR/scripts/cli.py" "$@"
