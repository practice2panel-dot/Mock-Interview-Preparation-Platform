#!/bin/bash

echo "========================================"
echo "  Interview Project - Starting Services"
echo "========================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo -e "${BLUE}[1/4] Checking if Python is installed...${NC}"
if command_exists python3; then
    echo -e "${GREEN}✅ Python3 found${NC}"
    PYTHON_CMD="python3"
elif command_exists python; then
    echo -e "${GREEN}✅ Python found${NC}"
    PYTHON_CMD="python"
else
    echo -e "${RED}❌ Python is not installed or not in PATH${NC}"
    echo "Please install Python and try again"
    exit 1
fi

echo
echo -e "${BLUE}[2/4] Checking if Node.js is installed...${NC}"
if command_exists node; then
    echo -e "${GREEN}✅ Node.js found${NC}"
else
    echo -e "${RED}❌ Node.js is not installed or not in PATH${NC}"
    echo "Please install Node.js and try again"
    exit 1
fi

echo
echo -e "${BLUE}[3/4] Starting Backend Server...${NC}"
cd Backend

echo "Installing Python dependencies..."
$PYTHON_CMD -m pip install -r requirements.txt > /dev/null 2>&1

echo "Creating sample database tables..."
$PYTHON_CMD create_sample_tables.py

echo "Starting Flask API server on http://localhost:5000..."
gnome-terminal --title="Backend Server" -- bash -c "$PYTHON_CMD start_server.py; exec bash" 2>/dev/null || \
xterm -title "Backend Server" -e "$PYTHON_CMD start_server.py" 2>/dev/null || \
osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && '"$PYTHON_CMD"' start_server.py"' 2>/dev/null || \
echo "Please start the backend manually: cd Backend && $PYTHON_CMD start_server.py"

cd ..

echo
echo -e "${BLUE}[4/4] Starting Frontend Server...${NC}"
cd frontend

echo "Installing Node.js dependencies..."
npm install > /dev/null 2>&1

echo "Starting React development server on http://localhost:3000..."
gnome-terminal --title="Frontend Server" -- bash -c "npm start; exec bash" 2>/dev/null || \
xterm -title "Frontend Server" -e "npm start" 2>/dev/null || \
osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && npm start"' 2>/dev/null || \
echo "Please start the frontend manually: cd frontend && npm start"

cd ..

echo
echo "========================================"
echo -e "${GREEN}  🚀 Both services are starting!${NC}"
echo "========================================"
echo
echo -e "${YELLOW}Backend API:  http://localhost:5000${NC}"
echo -e "${YELLOW}Frontend App: http://localhost:3000${NC}"
echo
echo "Press Enter to exit this launcher..."
read
