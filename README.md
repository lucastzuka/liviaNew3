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

#### ⚡ Zapier Automation
Integração com Zapier Remote MCP para automação de workflows.

**Funcionalidades**:
- ✅ **Google Drive**: Buscar, listar, criar e gerenciar arquivos e pastas
- ✅ **Gmail**: Enviar emails e gerenciar mensagens
- ✅ **Notion**: Criar páginas e gerenciar conteúdo
- ✅ **Trello**: Adicionar cards e gerenciar boards

**Exemplos de Comandos**:
- "Buscar arquivo TargetGroupIndex_BR2024 no Google Drive"
- "Procurar pasta Marketing no drive"
- "Enviar email para equipe@empresa.com"
- "Criar página no Notion sobre reunião"

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

   **⚡ Zapier/Google Drive:**
   - "Buscar arquivo TargetGroupIndex_BR2024 no Google Drive"
   - "Procurar pasta Marketing no drive"
   - "Listar documentos recentes no Google Drive"

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
- **agent.py**: Define a Livia, MCPs (Slack, Asana) e processamento Zapier
- **server.py**: Servidor Socket Mode do Slack com proteção anti-loop
- **tools/**: Módulo de ferramentas (WebSearch, ImageProcessor)
- **OpenAI Agents SDK**: Orquestração de agentes inteligentes
- **MCP Servers**: Comunicação com APIs externas (Slack, Asana)
- **Zapier Remote MCP**: Automação via API Responses
- **API Responses**: Nova API da OpenAI para agentes e automação

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
