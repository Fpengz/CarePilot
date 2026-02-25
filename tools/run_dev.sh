#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.." || exit 1

printf '[dev] Starting Streamlit with watchdog file watcher\n'
uv run streamlit run src/app.py --server.fileWatcherType watchdog --server.runOnSave true
