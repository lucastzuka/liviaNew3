# Funcionalidades do Chatbot Livia

A seguir, uma lista de todas as funcionalidades disponíveis no chatbot Livia, com uma breve descrição e um exemplo de prompt para teste.

## Funções Principais

### 1. Responder a Menções e Mensagens Diretas

- **Descrição:** O bot responde quando é mencionado diretamente em um canal (`@Livia`) ou quando recebe uma mensagem direta.
- **Prompt de Teste:** Mencione o bot em um canal com uma pergunta simples, como: `@Livia qual a previsão do tempo para amanhã?`

### 2. Análise de Imagens (Visão)

- **Descrição:** O bot pode analisar o conteúdo de imagens enviadas em uma conversa.
- **Prompt de Teste:** Envie uma imagem para o bot e pergunte: `@Livia o que você vê nesta imagem?`

### 3. Transcrição de Áudio

- **Descrição:** O bot pode transcrever o conteúdo de arquivos de áudio enviados na conversa.
- **Prompt de Teste:** Envie um arquivo de áudio (MP3, WAV, etc.) e diga: `@Livia transcreva este áudio para mim.`

### 4. Geração de Imagens

- **Descrição:** Cria uma imagem a partir de uma descrição textual usando o comando `+img`.
- **Prompt de Teste:** Envie a mensagem: `+img um astronauta surfando em um anel de saturno, estilo aquarela`

### 5. Análise Profunda (Thinking)

- **Descrição:** Utiliza o comando `+think` para abrir uma interface de análise profunda, ideal para questões complexas que exigem uma resposta mais elaborada.
- **Prompt de Teste:** Envie a mensagem: `+think` e, na janela que abrir, descreva um problema complexo para o bot analisar.

### 6. Lista de Comandos

- **Descrição:** Exibe uma lista de todos os comandos `+` disponíveis.
- **Prompt de Teste:** Envie a mensagem: `+comandos`

## Integrações (via Zapier)

O bot pode interagir com diversas ferramentas externas. Aqui estão alguns exemplos de como testá-las:

### 7. Interação com Gmail

- **Descrição:** Pode buscar, ler e redigir e-mails na sua conta do Gmail.
- **Prompt de Teste:** `@Livia busque por e-mails de "lucas.vieira@live.com" sobre o projeto "Livia" e me dê um resumo.`

### 8. Interação com Google Calendar

- **Descrição:** Pode verificar sua agenda, criar e encontrar eventos no Google Calendar.
- **Prompt de Teste:** `@Livia quais são meus próximos 3 eventos na agenda?`

### 9. Interação com Asana

- **Descrição:** Pode criar, encontrar e atualizar tarefas no Asana.
- **Prompt de Teste:** `@Livia crie uma tarefa no Asana chamada "Revisar apresentação para cliente" para amanhã.`

### 10. Interação com Slack

- **Descrição:** Pode enviar mensagens para outros canais ou usuários no Slack.
- **Prompt de Teste:** `@Livia envie uma mensagem para o canal #general dizendo "Olá a todos, o almoço será servido em 10 minutos."`