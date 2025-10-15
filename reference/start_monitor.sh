#!/bin/bash
# Start the monitoring proxy server
# This runs the proxy with integrated monitoring dashboard

cd "$(dirname "$0")"

echo "========================================================================"
echo "  Starting Codex Monitor + Proxy Server"
echo "========================================================================"
echo ""
echo "  Dashboard: http://localhost:8888"
echo "  Proxy: http://localhost:8889"
echo ""
echo "  The dashboard will show:"
echo "    - All API requests/responses from Codex"
echo "    - OAuth token status"
echo "    - Wrapper activity"
echo ""
echo "  Keep this running while using Codex"
echo "========================================================================"
echo ""

# Start proxy server (which includes monitoring)
python3 proxy_server.py
