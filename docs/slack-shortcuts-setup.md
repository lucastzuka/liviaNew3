# Thinking Agent Tool - Agente o3-mini como Ferramenta

## Problema Resolvido
O slash command `/pensar` não funcionava em threads porque a Slack API não permite slash commands personalizados dentro de threads. Além disso, o bot estava entrando em loop infinito se mencionando.

## Solução: Agente o3-mini como Ferramenta
Implementamos um **Thinking Agent** usando o modelo o3-mini como ferramenta do agente principal:
- ✅ Funciona em qualquer lugar (threads, canais, DMs)
- ✅ Ativado por keywords simples: `+think`, `thinking`, `análise profunda`
- ✅ Usa modelo o3-mini especializado em análise profunda
- ✅ Integrado nativamente no OpenAI Agents SDK
- ✅ Sem loops infinitos ou auto-menções
- ✅ Rastreamento completo pelo Agents SDK

## Configuração (Nenhuma Necessária!)

**✅ PRONTO PARA USAR** - Não precisa configurar nada no Slack App Dashboard!

A ferramenta thinking está integrada diretamente no agente Livia e funciona automaticamente através de keywords.

## Como Usar

### Para Usuários
1. Em qualquer thread, canal ou DM, mencione o bot: `@livia`
2. Use uma das keywords para ativar o thinking:
   - `+think como posso melhorar esta campanha?`
   - `thinking sobre estratégia de marketing`
   - `análise profunda desta situação`
   - `me ajude a resolver este problema complexo`
3. O agente o3-mini será ativado automaticamente
4. Receba análise detalhada na mesma thread

### Keywords que Ativam o Thinking
- `+think` - Ativação explícita
- `thinking` - Palavra-chave principal
- `análise profunda` / `análise detalhada`
- `brainstorm` / `brainstorming`
- `resolução de problema`
- `estratégia` / `decisão` / `reflexão`
- `problema complexo` / `solução criativa`

## Permissões Necessárias
O shortcut requer os seguintes escopos OAuth:
- `commands` - Para registrar shortcuts
- `chat:write` - Para postar respostas
- `channels:history` - Para ler histórico de threads
- `groups:history` - Para canais privados
- `im:history` - Para DMs

## Vantagens sobre Slash Commands
1. **Funciona em qualquer lugar** - Threads, canais, DMs
2. **Interface rica** - Modal com formulário vs. linha de comando
3. **UX intuitiva** - Botão ⚡ familiar aos usuários
4. **Input estruturado** - Formulário limpo vs. texto livre
5. **Privacidade** - Resposta em DM vs. canal público
6. **Modelo especializado** - o3-mini para análise profunda

## Limitações
- Máximo de 5 shortcuts por app
- Não aceita parâmetros adicionais (mas isso não é problema para nosso caso)
- Requer cliques no menu (vs. digitação rápida de slash commands)

## Código Implementado
O handler está em `server.py` na função `handle_thinking_shortcut()` que:
1. Extrai a mensagem original e contexto
2. Cria um prompt de análise
3. Processa com streaming usando o agente Livia
4. Responde na mesma thread com insights

## Status da Implementação
✅ **CONCLUÍDO**: Thinking Agent implementado como ferramenta
✅ **CONCLUÍDO**: Slash command `/pensar` removido (não funciona em threads)
✅ **CONCLUÍDO**: Loop infinito corrigido (removidas auto-menções)
✅ **CONCLUÍDO**: Integração com OpenAI Agents SDK
✅ **CONCLUÍDO**: Keywords de ativação configuradas
✅ **CONCLUÍDO**: Tag `⛭ o3-mini` `Thinking` implementada
✅ **CONCLUÍDO**: Respostas completas (sem limitação de concisão)
✅ **CONCLUÍDO**: Suporte a reasoning traces em blocos de código
✅ **CONCLUÍDO**: Servidor testado e funcionando

## Exemplo de Uso
```
Usuário: @livia +think como posso melhorar a performance desta campanha?

Livia: ⛭ o3-mini Thinking

[Se houver reasoning trace:]
```
Analisando a questão da performance de campanha...
1. Identificando métricas-chave
2. Avaliando pontos de otimização
3. Considerando diferentes estratégias
```

[Análise completa e detalhada do o3-mini com insights profundos]
```

## Casos de Uso Ideais
- **Brainstorming**: `@livia thinking sobre ideias para campanha de natal`
- **Resolução de Problemas**: `@livia +think como resolver baixo engajamento`
- **Estratégia**: `@livia análise profunda da concorrência`
- **Decisões Complexas**: `@livia me ajude a decidir entre essas opções`
- **Criatividade**: `@livia brainstorm para conceito criativo`
