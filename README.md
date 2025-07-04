# 🤖 Livia - Slack Chatbot Agent

**Livia é um chatbot inteligente para Slack com integração completa da API do Slack usando Bolt for Python.** Ela usa **OpenAI Agents SDK** para fornecer uma experiência de IA avançada diretamente no Slack, respondendo apenas quando mencionada na primeira mensagem de threads.

## ✨ Características Principais

### 🎯 **Integração Slack Completa**
- **✅ Slack Socket Mode**: Conexão em tempo real usando Bolt for Python (framework oficial)
- **✅ Thread Detection**: Responde apenas dentro de threads que começam com menção ao bot (a primeira msg da thread menciona o bot)
- **✅ Multi-Channel Support**: Funciona em canais públicos, privados, grupos e DMs (mas durante o desenvolvimento só envia msg no canal de testes C059NNLU3E1)
- **✅ Security Whitelist**: Sistema de segurança para desenvolvimento com canais/usuários permitidos
- **Anti-Loop Protection**: Proteção robusta contra respostas infinitas, respostas em canal ou usuario errado, respostas duplicadas, etc.

### ⚡ **Performance e Streaming**
- **🚀 STREAMING EM TEMPO REAL**: Respostas aparecem progressivamente como no ChatGPT
- **⚡ SUPER OTIMIZADO**: streaming rápido.
- **🔄 Rate Limiting Inteligente**: Atualizações otimizadas (10 chars ou 0.5s)
- **📱 Experiência ChatGPT no Slack**: Interface de conversação fluida e responsiva.
- **🧠 Gestão Inteligente de Memória**: Avisa automaticamente quando a conversa atinge o limite de contexto.

### 🛠️ **Ferramentas Avançadas**
- **🔍 Web Search Tool** - Busca informações atuais na internet.
- **📄 File Search Tool** - Busca semântica em documentos ja carregados na vector store da openai.
- **🎵 Audio Transcription** - Transcrição de áudios (mp3, wav, m4a, ogg, flac, webm) de audios enviados pelo usuario para o bot no slack.
- **👁️ Image Vision** - Análise de imagens com IA (PNG, JPEG, WEBP, GIF)
- **🎨 Image Generation** - Geração de imagens usando gpt-image-1 sem streaming
- **⚡ 9 MCPs Zapier** - Asana, Google Drive, Everhour, Gmail, Calendar, Google Docs, etc.
- **✨ Formatação Slack Perfeita** - Conversão automática markdown → Slack
  - `**negrito**` → `*negrito*`
  - `[texto](url)` → `<url|texto>` clicável
  - URLs longas viram títulos descritivos

### 🏗️ **Arquitetura Avançada**
- **🚀 OpenAI Agents SDK**: Tecnologia de agentes mais recente da OpenAI
- **🔄 OpenAI Responses API**: Pode ser usado
- **📋 Structured Outputs**: Garantia de aderência a schemas JSON com validação automática
- **🏗️ Arquitetura Híbrida**: Combina Agents SDK + Structured Outputs
- **🔧 Sistema Modular**: Organizado e facilmente extensíveis.

## Limite de Concorrência (Atendimentos Simultâneos)

Livia suporta atendimento simultâneo de múltiplos usuários/requisições, limitado por um semáforo global configurável via variável de ambiente:

- **LIVIA_MAX_CONCURRENCY**: número máximo de atendimentos/processamentos paralelos da Livia.  
  Exemplo no `.env`:
  ```
  LIVIA_MAX_CONCURRENCY=5
  ```
  O valor padrão é 5 se não especificado. Recomendado: ajuste entre 3 e 10 conforme recursos e limites de API.

Esse mecanismo garante escalabilidade sem risco de respostas misturadas ou sobrecarga de custos/rate limits.

## 📋 Structured Outputs (Opcional)

Livia suporta **OpenAI Structured Outputs** para garantir que as respostas sigam schemas JSON específicos, eliminando a necessidade de validação manual e reduzindo erros de formato.

### ✨ **Benefícios**
- **🔒 Confiabilidade**: Garantia de que respostas seguem estruturas específicas
- **✅ Validação Automática**: Elimina necessidade de validação manual de JSON
- **📊 Consistência**: Respostas padronizadas para diferentes tipos de operações
- **🐛 Debugging**: Melhor rastreamento de erros estruturais

### ⚙️ **Configuração**
```bash
# No arquivo .env
LIVIA_USE_STRUCTURED_OUTPUTS=true
```

### 🎯 **Casos de Uso**
- **Everhour**: Estrutura de time tracking com validação de IDs e formatos
- **Asana**: Operações de projeto/tarefa com metadados estruturados
- **Gmail**: Resultados de busca e operações de email organizados
- **Web Search**: Resultados de busca com citações e resumos estruturados
- **File Search**: Metadados de arquivos e citações organizadas

**Nota**: Requer modelos `gpt-4o-2024-08-06` ou posteriores.


### ⚡ **Comando Único (Recomendado)**

```bash
./start-livia.sh
```

### 🔧 **Componentes Principais**

#### 🏗️ **Core Architecture**
- **agent.py**: Agente OpenAI com sistema modular de MCPs + **STREAMING** + **FILE SEARCH**
- **server.py**: Servidor Slack Socket Mode com Bolt for Python + **STREAMING** + **THREAD DETECTION**
- **slack_formatter.py**: Conversão inteligente markdown → Slack format

#### 🛠️ **Tools & Integrations**
- **tools/**: Módulo de ferramentas (WebSearch, ImageProcessor, ImageGeneration)
- **OpenAI Agents SDK**: Orquestração de agentes com **streaming nativo** + **FileSearchTool**
- **OpenAI Responses API**: Para MCPs remotos com **streaming**
- **Zapier Remote MCPs**: Sistema modular de automação

```

## Security

### Secret Management

- **No secrets in code**: All sensitive API keys (e.g., Zapier MCP integrations) are now loaded from environment variables only.  
- **Setup**: Copy `.env.example` to `.env` and fill in each required `ZAPIER_*_API_KEY` variable for every integration you use.
- **Never commit `.env` or real keys**: Only placeholders should exist in `.env.example`.

### Logging Redaction

- All log output is automatically filtered to redact secrets using patterns for OpenAI (`sk-...`) and Zapier/base64 keys.
- The filter is applied globally at startup (see `security_utils.py` and usage in both `server.py` and `agent.py`).
- If a secret appears in any log message, it is replaced by `***REDACTED***`.

### Pre-commit Secret Scanning

- This project ships with a [gitleaks](https://github.com/gitleaks/gitleaks) config (`.gitleaks.toml`) to prevent accidental commits of API keys or secrets.
- **Recommended**: Add gitleaks as a pre-commit hook in your workflow:
  ```
  pre-commit install
  ```
  or run manually before committing:
  ```
  gitleaks detect --source .
  ```

### Updating Secrets

- To rotate or update any secret, simply change it in your environment or `.env` file. No code changes are needed.
- If you add new MCPs, add corresponding `ZAPIER_<SERVICE>_API_KEY` variables and update `.env.example`.
- **OpenAI Agents SDK**: Orquestração de agentes com **streaming nativo** + **FileSearchTool**
- **OpenAI Responses API**: Para MCPs remotos com **streaming**
- **Zapier Remote MCPs**: Sistema modular de automação
