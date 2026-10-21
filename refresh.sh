#!/usr/bin/env bash
# Refresh the tool tracker: re-probe everything, rebuild the page, optionally publish to Pages.
#   bash refresh.sh            # probe + rebuild (local only)
#   PUBLISH=1 bash refresh.sh  # probe + rebuild + push to GitHub Pages
#   bash refresh.sh --fast     # keep last MCP handshake results, refresh everything else
set -euo pipefail
cd /opt/data/studio/tool-tracker
/opt/hermes/.venv/bin/python collect.py "$@"
/opt/hermes/.venv/bin/python build.py
if [[ "${PUBLISH:-0}" == "1" ]]; then
  bash /opt/data/scripts/publish-pages.sh /opt/data/studio/tool-tracker tool-tracker
fi
