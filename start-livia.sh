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
export $(cat .env | xargs)

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

# Executa o servidor
echo "🤖 Iniciando servidor..."
python server.py
