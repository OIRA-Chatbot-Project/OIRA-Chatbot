#!/bin/bash
# OIRA Chatbot - Main startup script
# Runs both backend and frontend servers concurrently

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}   OIRA Chatbot Startup${NC}"
echo -e "${BLUE}================================${NC}\n"

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo -e "${RED}❌ Backend directory not found${NC}"
    exit 1
fi

# Check if frontend directory exists
if [ ! -d "frontend" ]; then
    echo -e "${RED}❌ Frontend directory not found${NC}"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    kill 0  # Kill all processes in the current process group
    exit
}

trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${BLUE}Starting Backend Server...${NC}"
cd backend

# Check if Python virtual environment exists
if [ -d ".venv" ]; then
    echo -e "${GREEN}✓ Found Python virtual environment${NC}"
    source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null
else
    echo -e "${YELLOW}⚠ No virtual environment found. Using system Python.${NC}"
fi

# Check if Python dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip install -r requirements.txt
fi

# Start backend server in background
echo -e "${GREEN}✓ Starting FastAPI backend on http://localhost:8000${NC}"
python main.py > ../backend.log 2>&1 &
BACKEND_PID=$!

cd ..

# Give backend time to start
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}❌ Backend failed to start. Check backend.log for details.${NC}"
    cat backend.log
    exit 1
fi

# Start frontend
echo -e "\n${BLUE}Starting Frontend Server...${NC}"
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
    npm install
fi

# Start frontend server in background
echo -e "${GREEN}✓ Starting Next.js frontend on http://localhost:3000${NC}"
npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!

cd ..

# Give frontend time to start
sleep 5

echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}   🎉 Both servers are running!${NC}"
echo -e "${GREEN}================================${NC}\n"
echo -e "📡 Backend API:  ${BLUE}http://localhost:8000${NC}"
echo -e "🌐 Frontend UI:  ${BLUE}http://localhost:3000${NC}"
echo -e "📚 API Docs:     ${BLUE}http://localhost:8000/docs${NC}\n"
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}\n"
echo -e "Logs are being written to:"
echo -e "  - backend.log"
echo -e "  - frontend.log\n"

# Wait for both processes
wait
