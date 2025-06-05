#!/bin/bash

# 🚀 Configurar alias para iniciar Livia facilmente

echo "🔧 Configurando alias 'start-livia'..."

# Adicionar alias ao .zshrc (ou .bash_profile) - SEM CONDA
ALIAS_COMMAND="alias start-livia='cd /Users/lucasvieira/Desktop/liviaNEW3 && python3 server.py'"

# Verificar qual shell está sendo usado
if [ -f ~/.zshrc ]; then
    SHELL_CONFIG=~/.zshrc
elif [ -f ~/.bash_profile ]; then
    SHELL_CONFIG=~/.bash_profile
else
    SHELL_CONFIG=~/.bashrc
fi

# Verificar se alias já existe
if grep -q "start-livia" "$SHELL_CONFIG" 2>/dev/null; then
    echo "✅ Alias 'start-livia' já existe em $SHELL_CONFIG"
else
    echo "$ALIAS_COMMAND" >> "$SHELL_CONFIG"
    echo "✅ Alias 'start-livia' adicionado a $SHELL_CONFIG"
fi

echo ""
echo "🎉 Configuração completa!"
echo ""
echo "📋 Para usar:"
echo "1. Feche e reabra o terminal (ou execute: source $SHELL_CONFIG)"
echo "2. Digite: start-livia"
echo "3. A Livia será iniciada automaticamente!"
echo ""
echo "🛑 Para parar: Ctrl+C"
