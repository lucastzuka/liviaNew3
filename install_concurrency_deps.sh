#!/bin/bash

# Install Concurrency Dependencies for Livia Chatbot
# --------------------------------------------------
# Installs tenacity for retry logic and exponential backoff

echo "🚀 Installing concurrency dependencies for Livia Chatbot..."

# Install tenacity for retry logic
echo "📦 Installing tenacity for retry and exponential backoff..."
pip install tenacity>=8.2.0

# Verify installation
echo "✅ Verifying installation..."
python -c "import tenacity; print(f'✅ tenacity {tenacity.__version__} installed successfully')"

echo "🎯 Concurrency dependencies installed successfully!"
echo ""
echo "📊 Next steps:"
echo "1. Run the chatbot: python server.py"
echo "2. Test with multiple users simultaneously"
echo "3. Monitor concurrency stats with concurrency_manager.get_stats()"
echo ""
echo "🔧 Configuration:"
echo "- OpenAI: Max 8 concurrent requests"
echo "- Zapier: Max 3 concurrent requests"
echo "- Automatic retry with exponential backoff"
echo "- Rate limiting protection"
