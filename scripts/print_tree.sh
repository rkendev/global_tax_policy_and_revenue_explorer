#!/usr/bin/env bash
set -e
command -v tree >/dev/null 2>&1 && tree -a -I ".git|__pycache__|.venv|.pytest_cache|data" ||   find . -maxdepth 3 -type d -print
