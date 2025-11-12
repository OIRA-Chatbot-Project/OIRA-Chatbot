#!/bin/bash
# Helper script for common backend tasks

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}OIRA Chatbot Backend Helper${NC}"
echo ""

# Function to show menu
show_menu() {
    echo "Available commands:"
    echo "  1) Install dependencies"
    echo "  2) Run setup tests"
    echo "  3) Ingest PDFs (create/update vector database)"
    echo "  4) Start development server"
    echo "  5) Start production server"
    echo "  6) Run Gradio demo"
    echo "  7) Exit"
    echo ""
}

# Function to install dependencies
install_deps() {
    echo -e "${BLUE}Installing dependencies...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}Done!${NC}"
}

# Function to run tests
run_tests() {
    echo -e "${BLUE}Running setup tests...${NC}"
    python test_setup.py
}

# Function to ingest PDFs
ingest_pdfs() {
    echo -e "${BLUE}Ingesting PDFs from data/ folder...${NC}"
    python ingest_database.py
    echo -e "${GREEN}Done!${NC}"
}

# Function to start dev server
start_dev() {
    echo -e "${BLUE}Starting development server...${NC}"
    echo -e "Server will be available at: ${GREEN}http://localhost:8000${NC}"
    echo -e "API docs at: ${GREEN}http://localhost:8000/docs${NC}"
    echo ""
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

# Function to start production server
start_prod() {
    echo -e "${BLUE}Starting production server...${NC}"
    echo -e "Server will be available at: ${GREEN}http://localhost:8000${NC}"
    echo ""
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
}

# Function to run Gradio demo
run_gradio() {
    echo -e "${BLUE}Starting Gradio demo...${NC}"
    python chatbot.py
}

# Main menu loop
while true; do
    show_menu
    read -p "Select an option (1-7): " choice
    echo ""
    
    case $choice in
        1)
            install_deps
            ;;
        2)
            run_tests
            ;;
        3)
            ingest_pdfs
            ;;
        4)
            start_dev
            ;;
        5)
            start_prod
            ;;
        6)
            run_gradio
            ;;
        7)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option. Please select 1-7.${NC}"
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    clear
done
