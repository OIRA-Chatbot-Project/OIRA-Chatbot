#!/bin/bash
# Quick start script for OIRA Chatbot Frontend

echo "🚀 OIRA Chatbot Frontend Setup"
echo "================================"
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

echo "✅ Node.js version: $(node --version)"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Dependencies installed successfully!"
    echo ""
    echo "🎉 Setup complete! You can now:"
    echo ""
    echo "   Start development server:"
    echo "   npm run dev"
    echo ""
    echo "   Build for production:"
    echo "   npm run build"
    echo "   npm start"
    echo ""
    echo "📝 Make sure your backend is running on http://localhost:8000"
    echo ""
else
    echo ""
    echo "❌ Installation failed. Please check the errors above."
    exit 1
fi
