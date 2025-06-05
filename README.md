# 🤖 Livia - Slack Chatbot Agent

Livia é um chatbot inteligente para Slack que usa **OpenAI Agents SDK** e **API Responses**. Ela responde apenas em threads que mencionam o bot na primeira mensagem e inclui ferramentas avançadas como busca na web, visão de imagens e automação via Zapier.

## ✨ Características

- **🎯 Resposta Inteligente**: Responde apenas em threads que começam com uma menção ao bot
- **🛠️ Ferramentas Avançadas**:
  - 🔍 **Web Search Tool** - Busca informações atuais na internet, notícias e fatos
  - 👁️ **Image Vision** - Análise de imagens enviadas via Slack ou URLs
  - 📋 **Asana Integration** - Gerenciamento de projetos e tarefas via MCP
  - ⚡ **Zapier Automation** - Integração com Google Drive, Gmail e outras ferramentas
  - 🔧 **Slack MCP Tools** - Ferramentas nativas do Slack via Model Context Protocol
- **🚀 OpenAI Agents SDK**: Usa a mais recente tecnologia de agentes da OpenAI
- **🔄 API Responses**: Utiliza a nova API Responses da OpenAI para automação
- **🛡️ Proteção Anti-Loop**: Sistema robusto contra respostas infinitas

## Configuração

### 1. Pré-requisitos

- Python 3.8+
- Node.js (para npx)
- Conta OpenAI com acesso à API
- Workspace do Slack com permissões de administrador

### 2. Instalação

```bash
# Clone o repositório
git clone <repository-url>
cd liviaNEW3

# Crie um ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instale as dependências
pip install -r requirements.txt

# Instale npx (se não tiver)
npm install -g npx
```

### 3. Configuração do Slack

1. Acesse [https://api.slack.com/apps](https://api.slack.com/apps)
2. Clique em "Create New App" → "From an app manifest"
3. Use o seguinte manifest JSON:

```json
{
    "display_information": {
        "name": "Livia"
    },
    "features": {
        "bot_user": {
            "display_name": "Livia",
            "always_online": true
        }
    },
    "oauth_config": {
        "scopes": {
            "bot": [
                "app_mentions:read",
                "channels:history",
                "channels:read",
                "chat:write",
                "reactions:write",
                "users:read",
                "conversations:history",
                "files:read"
            ]
        }
    },
    "settings": {
        "event_subscriptions": {
            "bot_events": [
                "app_mention",
                "message.im",
                "message.groups",
                "message.channels"
            ]
        },
        "interactivity": {
            "is_enabled": true
        },
        "org_deploy_enabled": false,
        "socket_mode_enabled": true,
        "token_rotation_enabled": false
    }
}
```

4. Instale o app no workspace
5. Copie os tokens necessários

### 4. Configuração de Ambiente

```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite o arquivo .env com seus tokens
nano .env
```

Preencha com:
- `SLACK_BOT_TOKEN`: Token do bot (xoxb-...)
- `SLACK_APP_TOKEN`: Token do app (xapp-...)
- `SLACK_TEAM_ID`: ID do workspace (T...)
- `OPENAI_API_KEY`: Sua chave da API OpenAI

### 5. Integrações Disponíveis

#### 📋 Asana Integration
A Livia vem com integração ao Asana via MCP (Model Context Protocol).

**Funcionalidades**:
- ✅ Criar e gerenciar tarefas
- ✅ Listar projetos e workspaces
- ✅ Atualizar status de tarefas
- ✅ Buscar tarefas e projetos
- ✅ Gerenciar colaboração em equipe

#### ⚡ Zapier Automation (Modular)
Sistema modular de integração com Zapier Remote MCP para automação de workflows.

**🔧 Integrações Ativas**:
- ✅ **Asana**: Gerenciar projetos, tarefas e workspaces
- ✅ **Google Drive**: Buscar, listar, criar e gerenciar arquivos e pastas
- ✅ **Everhour**: Controle de tempo, timesheet e rastreamento de horas
- ✅ **Google Docs**: Criar, editar e gerenciar documentos de texto
- ✅ **Slack Externo**: Enviar mensagens para outros workspaces
- ✅ **Google Calendar**: Criar e gerenciar eventos, reuniões e compromissos
- ✅ **Gmail**: Enviar, ler e gerenciar emails
- ✅ **Google Analytics**: Acessar métricas, relatórios e dados de tráfego
- ✅ **Google Slides**: Criar e gerenciar apresentações e slides

**🚀 Fácil Expansão**:
- Sistema modular permite adicionar novas integrações facilmente
- Roteamento automático baseado em palavras-chave
- Configuração centralizada em `ZAPIER_MCPS`

**📝 Exemplos de Comandos**:
- **Asana**: "Busque as últimas 3 tarefas do projeto Pauta Inovação"
- **Google Drive**: "Buscar arquivo TargetGroupIndex_BR2024 no Google Drive"
- **Everhour**: "Registrar 2 horas de trabalho no projeto X"
- **Google Docs**: "Criar documento sobre reunião de planejamento"
- **Gmail**: "Enviar email para equipe@empresa.com sobre o projeto"
- **Google Calendar**: "Agendar reunião para amanhã às 14h"
- **Google Analytics**: "Mostrar métricas de tráfego do último mês"
- **Google Slides**: "Criar apresentação sobre resultados Q4"

**➕ Como Adicionar Novas Integrações**:
1. Configure o MCP no Zapier (mcp.zapier.com)
2. Adicione a configuração em `ZAPIER_MCPS` no `agent.py`
3. Defina palavras-chave para roteamento automático
4. Pronto! O sistema detecta e roteia automaticamente

## Uso

### Executar o Bot

```bash
python server.py
```

### Como Usar no Slack

1. **Mencione a Livia** em um canal para iniciar uma conversa:
   ```
   @Livia Olá! Como você pode me ajudar?
   ```

2. **Continue a conversa na thread** - Livia responderá apenas em threads que começaram com uma menção

3. **Envie imagens** para análise:
   - **Upload direto**: Faça upload de uma imagem no Slack
   - **Link de imagem**: Cole um link de imagem na conversa
   - **Formatos suportados**: PNG, JPEG, WEBP, GIF (não animado)
   - Livia analisará automaticamente e descreverá o conteúdo

4. **Use comandos naturais**:

   **🔍 Busca na Web:**
   - "Pesquise informações sobre IA na internet"
   - "Qual é a cotação do dólar hoje?"
   - "Busque notícias recentes sobre tecnologia"

   **👁️ Análise de Imagens:**
   - "Analise esta imagem" (com upload de imagem)
   - "O que você vê nesta foto?" (com link de imagem)

   **📋 Asana:**
   - "Crie uma tarefa no Asana: Revisar documentação"
   - "Liste meus projetos no Asana"
   - "Qual o status das tarefas do projeto X?"

   **⚡ Zapier Integrations:**
   - **Google Drive**: "Buscar arquivo TargetGroupIndex_BR2024 no Google Drive"
   - **Gmail**: "Enviar email para cliente@empresa.com sobre proposta"
   - **Google Calendar**: "Agendar reunião com equipe para sexta-feira às 15h"
   - **Google Docs**: "Criar documento de especificações do projeto"
   - **Everhour**: "Registrar 3 horas de desenvolvimento no projeto Alpha"
   - **Google Analytics**: "Mostrar dados de tráfego da última semana"
   - **Google Slides**: "Criar apresentação sobre resultados do trimestre"

### 6. Análise de Imagens com IA

A Livia possui capacidades avançadas de visão computacional usando o modelo **gpt-4.1-mini** para análise de imagens:

#### **Como Usar:**

1. **Upload de Imagem**:
   - Faça upload de uma imagem diretamente no Slack
   - Mencione @Livia ou continue uma conversa existente
   - Livia analisará automaticamente a imagem

2. **Link de Imagem**:
   - Cole um link de imagem na conversa
   - Formatos suportados: `https://exemplo.com/imagem.jpg`
   - Livia detectará e analisará automaticamente

#### **Formatos Suportados:**
- ✅ PNG (.png)
- ✅ JPEG (.jpg, .jpeg)
- ✅ WEBP (.webp)
- ✅ GIF não animado (.gif)

#### **Exemplos de Análise:**
- **Objetos e Pessoas**: "Vejo uma pessoa usando óculos de sol..."
- **Texto em Imagens**: "A imagem contém o texto 'Bem-vindos'..."
- **Cores e Composição**: "A imagem tem tons predominantemente azuis..."
- **Contexto e Situação**: "Esta parece ser uma foto de um escritório..."

#### **Limitações:**
- Tamanho máximo: 50MB por imagem
- Não processa GIFs animados
- Melhor qualidade com imagens claras e bem iluminadas

## 🏗️ Arquitetura

### 📁 Estrutura do Projeto
```
liviaNEW3/
├── agent.py              # 🤖 Agente principal + MCPs
├── server.py             # 🌐 Servidor Slack Socket Mode
├── tools/                # 🛠️ Ferramentas modulares
│   ├── __init__.py       # Exportações
│   ├── web_search.py     # 🔍 WebSearchTool
│   └── image_vision.py   # 👁️ Processamento de imagens
├── requirements.txt      # 📦 Dependências
└── README.md            # 📖 Documentação
```

### 🔧 Componentes Principais
- **agent.py**: Define a Livia com sistema modular de MCPs do Zapier
- **server.py**: Servidor Socket Mode do Slack com proteção anti-loop
- **tools/**: Módulo de ferramentas (WebSearch, ImageProcessor)
- **OpenAI Agents SDK**: Orquestração de agentes inteligentes
- **MCP Local**: Comunicação com APIs locais (Slack)
- **Zapier Remote MCPs**: Sistema modular de automação via API Responses
- **API Responses**: Nova API da OpenAI para agentes e automação

### 🏗️ Arquitetura Modular dos MCPs

```python
# Configuração centralizada em agent.py
ZAPIER_MCPS = {
    "asana": {
        "name": "Zapier Asana MCP",
        "url": "https://mcp.zapier.com/api/mcp/s/...",
        "keywords": ["asana", "projeto", "tarefa"],
        "description": "📋 **Asana**: gerenciar projetos e tarefas"
    },
    "google_drive": {
        "name": "Zapier Google Drive MCP",
        "url": "https://mcp.zapier.com/api/mcp/s/...",
        "keywords": ["drive", "arquivo", "pasta"],
        "description": "📁 **Google Drive**: gerenciar arquivos"
    }
    # 🚀 Adicione novos MCPs aqui facilmente!
}
```

**🔄 Fluxo de Roteamento**:
1. **Detecção**: Sistema analisa palavras-chave na mensagem
2. **Roteamento**: Direciona para o MCP apropriado automaticamente
3. **Processamento**: OpenAI Responses API processa via MCP específico
4. **Fallback**: Se falhar, usa agente local com Slack MCP

## 🚀 Adicionando Novos MCPs do Zapier

### Passo a Passo Completo

#### 1. **Configure o MCP no Zapier**
1. Acesse [mcp.zapier.com](https://mcp.zapier.com)
2. Crie um novo servidor MCP
3. Adicione as ferramentas/apps desejadas (Gmail, Calendar, etc.)
4. Copie a URL do servidor e o token Bearer

#### 2. **Adicione a Configuração no Código**
Edite o arquivo `agent.py` e adicione sua nova integração em `ZAPIER_MCPS`:

```python
ZAPIER_MCPS = {
    # ... integrações existentes ...

    "gmail": {
        "name": "Zapier Gmail MCP",
        "server_label": "zapier-gmail",
        "url": "https://mcp.zapier.com/api/mcp/s/SEU-SERVER-ID/mcp",
        "token": "SEU-TOKEN-BEARER",
        "keywords": ["gmail", "email", "enviar email", "caixa de entrada"],
        "description": "📧 **Gmail**: enviar, ler e gerenciar emails"
    }
}
```

#### 3. **Teste a Integração**
```bash
# Reinicie o servidor
python server.py

# Teste no Slack
@Livia enviar email para teste@exemplo.com
```

#### 4. **Exemplos de Integrações Populares**

**📧 Gmail**:
```python
"gmail": {
    "keywords": ["gmail", "email", "enviar email", "ler email"],
    "description": "📧 **Gmail**: enviar, ler e gerenciar emails"
}
```

**📅 Google Calendar**:
```python
"calendar": {
    "keywords": ["calendario", "agenda", "reuniao", "evento"],
    "description": "📅 **Calendar**: criar e gerenciar eventos"
}
```

**💬 Slack Externo**:
```python
"slack_external": {
    "keywords": ["slack externo", "enviar slack", "outro workspace"],
    "description": "💬 **Slack**: enviar mensagens para outros workspaces"
}
```

### ✅ Vantagens do Sistema Modular
- **🔧 Plug & Play**: Adicione integrações sem modificar código existente
- **🎯 Roteamento Automático**: Sistema detecta intenção baseado em palavras-chave
- **🛡️ Isolamento**: Falhas em um MCP não afetam outros
- **📈 Escalável**: Suporta quantas integrações precisar

## Desenvolvimento

Para contribuir ou modificar:

1. Faça fork do repositório
2. Crie uma branch para sua feature
3. Implemente as mudanças
4. Teste thoroughly
5. Submeta um pull request

## 🔧 Troubleshooting

### ❗ Problemas Comuns

1. **"Agent not ready"**:
   - ✅ Verifique se todas as variáveis de ambiente estão configuradas
   - ✅ Confirme se o OPENAI_API_KEY é válido

2. **SSL errors**:
   - ✅ Certifique-se de que o `certifi` está instalado
   - ✅ Execute: `pip install --upgrade certifi`

3. **MCP server fails**:
   - ✅ Verifique se o npx está instalado: `npx --version`
   - ✅ Teste: `npx -y @modelcontextprotocol/server-slack`

4. **Respostas duplicadas/infinitas**:
   - ✅ Sistema de proteção anti-loop implementado
   - ✅ Bot ignora suas próprias mensagens automaticamente

5. **Google Drive não encontra arquivos**:
   - ✅ Use "buscar arquivo" em vez de "buscar pasta"
   - ✅ Tente nomes parciais: "TargetGroup" para "TargetGroupIndex_BR2024"

### 📊 Logs e Debug

O sistema gera logs detalhados. Para debug mais verboso:

```python
# Em agent.py, descomente:
logging.getLogger("openai.agents").setLevel(logging.DEBUG)
```

### 🆘 Comandos de Teste

```bash
# Testar conectividade Slack
python -c "from server import SlackSocketModeServer; print('Slack OK')"

# Testar OpenAI
python -c "from openai import OpenAI; OpenAI().models.list(); print('OpenAI OK')"

# Testar MCP Servers
npx -y @modelcontextprotocol/server-slack
npx -y @roychri/mcp-server-asana
```

## Licença

[Especificar licença]

## Suporte

Para suporte, abra uma issue no repositório ou entre em contato.
