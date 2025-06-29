#!/bin/bash

# 🤖 Livia Slack Chatbot - Startup Script
# =======================================
# Inicializa o chatbot com todas as verificações necessárias

echo "🚀 Iniciando Livia Slack Chatbot..."
echo "=================================="

# Verifica se o arquivo .env existe
if [ ! -f ".env" ]; then
    echo "❌ Erro: Arquivo .env não encontrado!"
    echo "📝 Crie o arquivo .env com as variáveis necessárias:"
    echo "   - SLACK_BOT_TOKEN"
    echo "   - SLACK_APP_TOKEN"
    echo "   - SLACK_TEAM_ID"
    echo "   - OPENAI_API_KEY"
    exit 1
fi

# Carrega variáveis de ambiente
echo "📋 Carregando variáveis de ambiente..."
export $(cat .env | grep -v '^#' | xargs)

# Verifica se as variáveis essenciais estão definidas
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ Erro: OPENAI_API_KEY não definida no .env"
    exit 1
fi

if [ -z "$SLACK_BOT_TOKEN" ]; then
    echo "❌ Erro: SLACK_BOT_TOKEN não definida no .env"
    exit 1
fi

echo "✅ Variáveis de ambiente carregadas"
echo "🎯 Funcionalidades ativas:"
echo "   - 🔍 Web Search Tool"
echo "   - 📄 File Search Tool"
echo "   - 👁️ Image Vision"
echo "   - 🎨 Image Generation (gpt-image-1)"
echo "   - 🎵 Audio Transcription"
echo "   - ⚡ Streaming em Tempo Real"
echo "   - 📋 9 MCPs Zapier (Asana, Google Drive, etc.)"
echo ""

# Ativa ambiente conda livia-chatbot (Python 3.11+)
echo "🔧 Ativando ambiente conda livia-chatbot (Python 3.11+)..."
source /opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh
conda activate livia-chatbot

# Verifica versão do Python
PYTHON_VERSION=$(python --version 2>&1)
echo "🐍 Usando Python: $PYTHON_VERSION"

# Verifica se temos Python 3.11+
if python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "✅ Versão do Python compatível com MCPServerStdio"
else
    echo "❌ Erro: Python 3.11+ necessário para MCPServerStdio"
    exit 1
fi

# Executa o servidor
echo "🤖 Iniciando servidor..."
python -m server.slack_server
