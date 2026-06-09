#!/bin/bash
# ─────────────────────────────────────────────────────────────
# Turul Academy — local dev launcher
# Starts backend (port 8003) + frontend (port 5173) in separate
# Terminal tabs, then opens the app in the browser.
#
# Usage:  ./start.sh
# ─────────────────────────────────────────────────────────────

PROJECT="/Users/gabor/Documents/GitHub/turul-academy"

# Kill anything already holding the ports
echo "🔍 Clearing ports 8003 and 5173..."
lsof -ti :8003 | xargs kill -9 2>/dev/null
lsof -ti :5173 | xargs kill -9 2>/dev/null
sleep 1

# Open two new Terminal tabs — one per server
osascript <<EOF
tell application "Terminal"
  -- Backend tab
  do script "cd \"$PROJECT/backend\" && echo '🦅 Turul Academy — Backend (port 8003)' && .venv/bin/uvicorn main:app --port 8003 --reload"

  -- Frontend tab (new tab in same window)
  tell application "System Events" to keystroke "t" using command down
  delay 0.5
  do script "cd \"$PROJECT/frontend\" && echo '🦅 Turul Academy — Frontend (port 5173)' && npm run dev" in front window
end tell
EOF

# Wait for backend to be ready
echo "⏳ Waiting for backend..."
for i in $(seq 1 20); do
  if curl -s http://localhost:8003/api/curriculum/subjects > /dev/null 2>&1; then
    echo "✅ Backend ready"
    break
  fi
  sleep 1
done

# Wait for frontend to be ready
echo "⏳ Waiting for frontend..."
for i in $(seq 1 20); do
  if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "✅ Frontend ready"
    break
  fi
  sleep 1
done

# Open in browser
echo "🚀 Opening http://localhost:5173 ..."
open "http://localhost:5173"
