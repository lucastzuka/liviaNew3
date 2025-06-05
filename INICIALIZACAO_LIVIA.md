# 🚀 **Guia de Inicialização da Livia - NUNCA MAIS ERRE!**

## ⚠️ **PROBLEMA COMUM:**
Quando você fecha o terminal e abre novamente, as variáveis de ambiente são perdidas, causando o erro:
```
Illegal header value b'Bearer '
OPENAI_API_KEY is not set
```

## ✅ **SOLUÇÃO DEFINITIVA - SIGA ESTES PASSOS:**

### **1. 📁 Navegue para o diretório correto**
```bash
cd /Users/lucasvieira/Desktop/liviaNEW3
```

### **2. 🔑 Configure as variáveis de ambiente (SEMPRE FAZER ISSO!)**
```bash
# Carregue o arquivo .env
export $(cat .env | xargs)

# OU configure manualmente (se preferir):
export OPENAI_API_KEY="sua_chave_aqui"
export SLACK_BOT_TOKEN="xoxb-sua_chave_aqui"
export SLACK_APP_TOKEN="xapp-sua_chave_aqui"
export SLACK_TEAM_ID="T046LTU4TT5"
```

### **3. ✅ Verifique se as variáveis foram carregadas**
```bash
echo $OPENAI_API_KEY
echo $SLACK_BOT_TOKEN
```
**Deve mostrar as chaves, não vazio!**

### **4. 🚀 Execute o servidor**
```bash
python server.py
```

---

## 🎯 **COMANDO ÚNICO PARA COPIAR E COLAR:**

```bash
cd /Users/lucasvieira/Desktop/liviaNEW3 && export $(cat .env | xargs) && python server.py
```

**Este comando faz tudo de uma vez:**
1. Vai para o diretório correto
2. Carrega todas as variáveis do .env
3. Executa o servidor

---

## 🔧 **ALTERNATIVA: Script de Inicialização Automática**

Vou criar um script que faz tudo automaticamente:

### **Arquivo: `start_livia.sh`**
```bash
#!/bin/bash
echo "🚀 Iniciando Livia Chatbot..."
cd /Users/lucasvieira/Desktop/liviaNEW3
echo "📁 Diretório: $(pwd)"
echo "🔑 Carregando variáveis de ambiente..."
export $(cat .env | xargs)
echo "✅ OPENAI_API_KEY carregada: ${OPENAI_API_KEY:0:10}..."
echo "✅ SLACK_BOT_TOKEN carregada: ${SLACK_BOT_TOKEN:0:10}..."
echo "🚀 Executando servidor..."
python server.py
```

### **Para usar o script:**
```bash
# Torne executável (só precisa fazer uma vez)
chmod +x start_livia.sh

# Execute sempre que quiser iniciar
./start_livia.sh
```

---

## 📋 **CHECKLIST DE INICIALIZAÇÃO:**

- [ ] 📁 Estou no diretório `/Users/lucasvieira/Desktop/liviaNEW3`?
- [ ] 🔑 Carreguei as variáveis com `export $(cat .env | xargs)`?
- [ ] ✅ Verifiquei se `echo $OPENAI_API_KEY` mostra a chave?
- [ ] 🚀 Executei `python server.py`?

---

## 🆘 **SE DER ERRO:**

### **Erro: "OPENAI_API_KEY is not set"**
```bash
# Solução:
export $(cat .env | xargs)
echo $OPENAI_API_KEY  # Deve mostrar a chave
```

### **Erro: "No such file or directory: .env"**
```bash
# Solução:
cd /Users/lucasvieira/Desktop/liviaNEW3
ls -la .env  # Deve mostrar o arquivo
```

### **Erro: "Illegal header value b'Bearer '"**
```bash
# Solução:
export OPENAI_API_KEY="sk-proj-sua_chave_completa_aqui"
```

---

## 🎯 **RESUMO - COMANDO MÁGICO:**

**SEMPRE use este comando quando abrir um novo terminal:**

```bash
cd /Users/lucasvieira/Desktop/liviaNEW3 && export $(cat .env | xargs) && python server.py
```

**OU use o script:**
```bash
./start_livia.sh
```

---

## 🔥 **DICA PRO:**

Adicione um alias no seu `.zshrc` ou `.bashrc`:

```bash
echo 'alias livia="cd /Users/lucasvieira/Desktop/liviaNEW3 && export \$(cat .env | xargs) && python server.py"' >> ~/.zshrc
```

Depois disso, você só precisa digitar:
```bash
livia
```

E pronto! 🚀
