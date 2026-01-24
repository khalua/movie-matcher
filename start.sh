#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo -e "${GREEN}Starting Movie Matcher...${NC}\n"

# Setup and start backend
echo -e "${BLUE}Starting backend server...${NC}"

# Check if venv exists, create if not
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    python3 -m venv "$BACKEND_DIR/venv"
    source "$BACKEND_DIR/venv/bin/activate"
    echo -e "${BLUE}Installing dependencies...${NC}"
    pip install -r "$BACKEND_DIR/requirements.txt"
else
    source "$BACKEND_DIR/venv/bin/activate"
fi

# Start Flask (using port 5001 to avoid macOS AirPlay conflict on 5000)
export FLASK_APP="$BACKEND_DIR/app.py"
flask run --host=0.0.0.0 --port=5001 &
BACKEND_PID=$!

# Give backend a moment to start
sleep 2

# Check if backend started
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Backend failed to start!${NC}"
    exit 1
fi

# Start frontend
echo -e "${BLUE}Starting frontend server...${NC}"
cd "$FRONTEND_DIR"
REACT_APP_API_URL=http://localhost:5001 npm start &
FRONTEND_PID=$!

echo -e "\n${GREEN}Both servers started!${NC}"
echo -e "Backend PID: $BACKEND_PID"
echo -e "Frontend PID: $FRONTEND_PID"
echo -e "\nBackend: http://localhost:5001"
echo -e "Frontend: http://localhost:3000"
echo -e "\nPress Ctrl+C to stop both servers..."

# Cleanup function
cleanup() {
    echo -e "\n${BLUE}Stopping servers...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    # Also kill any child processes
    pkill -P $$ 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Keep script running
wait
