#!/bin/bash

# Script para inicializar Livia sem erro
echo "🚀 Iniciando Livia..."

# Vai para o diretório correto
cd /Users/lucasvieira/Desktop/liviaNEW3

# Carrega variáveis de ambiente
export $(cat .env | xargs)

# Executa o servidor
python server.py
