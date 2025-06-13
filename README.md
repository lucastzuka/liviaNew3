# 🤖 Livia - Slack Chatbot Agent

**Livia é um chatbot inteligente para Slack com integração completa da API do Slack usando Bolt for Python.** Ela usa **OpenAI Agents SDK** e **API Responses** para fornecer uma experiência de IA avançada diretamente no Slack, respondendo apenas quando mencionada na primeira mensagem de threads.

## ✨ Características Principais

### 🎯 **Integração Slack Completa**
- **✅ Slack Socket Mode**: Conexão em tempo real usando Bolt for Python (framework oficial)
- **✅ Thread Detection**: Responde apenas em threads que começam com menção ao bot (a primeira msg da thread menciona o bot)
- **✅ Multi-Channel Support**: Funciona em canais públicos, privados, grupos e DMs (mas durante o desenvolvimento só envia msg no canal de testes C059NNLU3E1)
- **✅ Security Whitelist**: Sistema de segurança para desenvolvimento com canais/usuários permitidos
- **Anti-Loop Protection**: Proteção robusta contra respostas infinitas, respostas em canal ou usuario errado, respostas duplicadas, etc.

### ⚡ **Performance e Streaming**
- **🚀 STREAMING EM TEMPO REAL**: Respostas aparecem progressivamente como no ChatGPT
- **⚡ SUPER OTIMIZADO**: 85-93% redução de latência + streaming rápido.
- **🔄 Rate Limiting Inteligente**: Atualizações otimizadas (10 chars ou 0.5s)
- **📱 Experiência ChatGPT no Slack**: Interface de conversação fluida e responsiva.

### 🛠️ **Ferramentas Avançadas**
- **🔍 Web Search Tool** - Busca informações atuais na internet.
- **📄 File Search Tool** - Busca semântica em documentos ja carregados na vector store da openai.
- **🎵 Audio Transcription** - Transcrição de áudios (mp3, wav, m4a, ogg, flac, webm) de audios enviados pelo usuario para o bot no slack.
- **👁️ Image Vision** - Análise de imagens com IA (PNG, JPEG, WEBP, GIF)
- **🎨 Image Generation** - Geração de imagens usando gpt-image-1 sem streaming
- **⚡ 9 MCPs Zapier** - Asana, Google Drive, Everhour, Gmail, Calendar, Docs, Analytics, etc.
- **✨ Formatação Slack Perfeita** - Conversão automática markdown → Slack
  - `**negrito**` → `*negrito*`
  - `[texto](url)` → `<url|texto>` clicável
  - URLs longas viram títulos descritivos

### 🏗️ **Arquitetura Avançada**
- **🚀 OpenAI Agents SDK**: Tecnologia de agentes mais recente da OpenAI
- **🔄 OpenAI Responses API**: Pode ser usado para MCPs remotos com streaming
- **🏗️ Arquitetura Híbrida**: Combina Agents SDK + Responses API.
- **🔧 Sistema Modular**: Organizado e facilmente extensíveis.

## 🚀 Configuração e Instalação
**🎯 Descoberta Importante**: Os agentes e MCPs funcionam muito bem com **JSON Mode** para respostas estruturadas!

## 🚀 Inicialização e Execução

### ⚡ **Comando Único (Recomendado)**

```bash
./start-livia.sh
```

## 🏗️ Arquitetura

### 📁 **Estrutura do Projeto**
```
liviaNEW3/
├── 🤖 agent.py              # Agente principal OpenAI
├── 🌐 server.py             # Servidor Slack Socket Mode 
├── 🛠️ tools/                # Ferramentas modulares
│   ├── __init__.py         # ImageProcessor + exportações
│   ├── web_search.py       # 🔍 WebSearchTool
│   ├── image_generation.py # 🎨 ImageGenerationTool
│   └── mcp/               # MCPs Zapier organizados
│       ├── __init__.py
│       └── zapier_mcps.py  # Configurações centralizadas
├── 📋 slack_formatter.py    # Formatação Slack (markdown → Slack)
├── 📦 requirements.txt      # Dependências Python
├── 🚀 start-livia.sh        # Script de inicialização automática
├── 📖 README.md            # Documentação completa
└── 🔒 .env                 # Variáveis de ambiente (não versionado)
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

---

### 🧠 Concorrência (Concurrency): 
O bot agora suporta verdadeira concorrência: cada thread do Slack (ou DM) recebe seu próprio lock assíncrono, permitindo que várias conversas sejam processadas em paralelo. Não existe mais travamento global (`agent_lock` removido). Mensagens na MESMA thread/DM continuam protegidas por lock sequencial (para evitar respostas embaralhadas), mas mensagens em threads ou DMs diferentes executam ao mesmo tempo, liberando todo o potencial de throughput multiusuário do Livia.

#### 🏗️ **Core Architecture**
- **agent.py**: Agente OpenAI com sistema modular de MCPs + **STREAMING** + **FILE SEARCH**
- **server.py**: Servidor Slack Socket Mode com Bolt for Python + **STREAMING** + **THREAD DETECTION**
- **slack_formatter.py**: Conversão inteligente markdown → Slack format

#### 🛠️ **Tools & Integrations**
- **tools/**: Módulo de ferramentas (WebSearch, ImageProcessor, ImageGeneration)
- **OpenAI Agents SDK**: Orquestração de agentes com **streaming nativo** + **FileSearchTool**
- **OpenAI Responses API**: Para MCPs remotos com **streaming**
- **Zapier Remote MCPs**: Sistema modular de automação
