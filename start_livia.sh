#!/bin/bash

# 🚀 Script de Inicialização da Livia
# Use: ./start_livia.sh

echo "🤖 Iniciando Livia Slack Chatbot..."

# Verificar se está no diretório correto
if [ ! -f "server.py" ]; then
    echo "❌ Erro: server.py não encontrado. Certifique-se de estar no diretório correto."
    exit 1
fi

# Verificar Python disponível
echo "🔧 Verificando Python..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python não encontrado!"
    exit 1
fi
echo "✅ Usando: $PYTHON_CMD"

# Verificar se aiohttp está instalado
echo "📦 Verificando dependências..."
$PYTHON_CMD -c "import aiohttp" 2>/dev/null || {
    echo "📦 Instalando aiohttp..."
    pip3 install aiohttp
}

# Verificar variáveis de ambiente
echo "🔐 Verificando variáveis de ambiente..."
if [ -z "$SLACK_BOT_TOKEN" ] || [ -z "$SLACK_APP_TOKEN" ] || [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Carregando variáveis de ambiente do .env..."
    if [ -f ".env" ]; then
        export $(cat .env | grep -v '^#' | xargs)
        echo "✅ Variáveis carregadas do .env"
    else
        echo "❌ Arquivo .env não encontrado!"
        exit 1
    fi
fi

# Iniciar servidor
echo "🚀 Iniciando servidor Livia..."
echo "📱 Slack Bot Token: ${SLACK_BOT_TOKEN:0:20}..."
echo "🔑 OpenAI API Key: ${OPENAI_API_KEY:0:20}..."
echo ""
echo "✅ Para parar o servidor, pressione Ctrl+C"
echo "🔗 Logs serão exibidos abaixo:"
echo "----------------------------------------"

$PYTHON_CMD server.py
