#!/bin/bash

# Start Livia Chatbot with Concurrency Improvements
# -------------------------------------------------
# Installs dependencies and starts the chatbot with enhanced concurrency support

echo "🚀 Starting Livia Chatbot with Concurrency Improvements..."
echo "=" * 60

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create .env file with required environment variables:"
    echo "  - SLACK_BOT_TOKEN"
    echo "  - SLACK_APP_TOKEN"
    echo "  - SLACK_TEAM_ID"
    echo "  - OPENAI_API_KEY"
    exit 1
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
python -c "import tenacity" 2>/dev/null || {
    echo "📦 Installing tenacity for concurrency management..."
    pip install tenacity>=8.2.0
}

# Run concurrency test first
echo "🧪 Running concurrency tests..."
python test_concurrency.py

if [ $? -eq 0 ]; then
    echo "✅ Concurrency tests passed!"
else
    echo "❌ Concurrency tests failed!"
    exit 1
fi

echo ""
echo "🎯 CONCURRENCY CONFIGURATION:"
echo "  - OpenAI API: Max 8 concurrent requests"
echo "  - Zapier MCP: Max 3 concurrent requests"
echo "  - Automatic retry with exponential backoff"
echo "  - Rate limiting protection"
echo "  - Real-time performance monitoring"
echo ""

# Start the chatbot
echo "🤖 Starting Livia Chatbot..."
echo "📊 Monitor concurrency stats in logs"
echo "🔄 Multiple users can now be processed simultaneously!"
echo ""

python server.py
