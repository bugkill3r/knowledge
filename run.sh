#!/usr/bin/env bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  printf "\nStopping backend and frontend...\n"
  [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  exit 0
}

trap cleanup INT TERM

# Free ports 8000 and 3000 if in use (e.g. from a previous run)
for port in 8000 3000; do
  for pid in $(lsof -ti:"$port" 2>/dev/null); do
    kill -9 "$pid" 2>/dev/null && echo "Killed process $pid on port $port" || true
  done
done
sleep 1

cd "$ROOT/backend"
if [ -d "venv" ]; then
  source venv/bin/activate
fi
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Prefer Node 18+ for Next.js 14
export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  . "$NVM_DIR/nvm.sh"
  nvm use 18 2>/dev/null || nvm use 20 2>/dev/null || nvm use 22 2>/dev/null || nvm use 2>/dev/null || true
fi

cd "$ROOT/frontend"
npm run dev &
FRONTEND_PID=$!

sleep 2
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both."
echo ""

wait
