# Livia - Slack Chatbot Agent

Livia é um chatbot inteligente para Slack que usa OpenAI Agents SDK e API Responses. Ela responde apenas em threads que mencionam o bot na primeira mensagem e inclui ferramentas avançadas como busca na web, busca em arquivos e visão de imagens.

## Características

- **Resposta Inteligente**: Responde apenas em threads que começam com uma menção ao bot
- **Ferramentas Avançadas**:
  - 🔍 Web Search - Busca informações na internet
  - 📁 File Search - Busca e análise de arquivos
  - 👁️ Image Vision - Análise de imagens enviadas via Slack ou URLs
  - 🔧 MCP Tools - Ferramentas do Model Context Protocol para Slack
- **OpenAI Agents SDK**: Usa a mais recente tecnologia de agentes da OpenAI
- **API Responses**: Utiliza a nova API Responses da OpenAI (não Chat Completions)

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
   - Faça upload de uma imagem
   - Ou envie um link de imagem
   - Livia analisará automaticamente

4. **Use comandos naturais**:
   - "Pesquise informações sobre IA"
   - "Analise esta imagem"
   - "Busque arquivos sobre vendas"

## Arquitetura

- **agent.py**: Define a Livia e suas capacidades
- **server.py**: Servidor Socket Mode do Slack
- **OpenAI Agents SDK**: Orquestração de agentes
- **MCP Server**: Comunicação com APIs do Slack
- **API Responses**: Nova API da OpenAI para agentes

## Desenvolvimento

Para contribuir ou modificar:

1. Faça fork do repositório
2. Crie uma branch para sua feature
3. Implemente as mudanças
4. Teste thoroughly
5. Submeta um pull request

## Troubleshooting

### Problemas Comuns

1. **"Agent not ready"**: Verifique se todas as variáveis de ambiente estão configuradas
2. **SSL errors**: Certifique-se de que o `certifi` está instalado
3. **MCP server fails**: Verifique se o npx está instalado e acessível

### Logs

O sistema gera logs detalhados. Para debug mais verboso:

```python
# Em agent.py, descomente:
logging.getLogger("openai.agents").setLevel(logging.DEBUG)
```

## Licença

[Especificar licença]

## Suporte

Para suporte, abra uma issue no repositório ou entre em contato.
