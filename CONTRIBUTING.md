# Contribuindo com o MatexUnB

Obrigado pelo interesse em contribuir! Este guia explica como você pode ajudar.

## 🚀 Como Contribuir

### 1. Encontre ou Crie uma Issue

- Verifique as [Issues abertas](../../issues) para ver se alguém já reportou o problema
- Se não encontrar, abra uma nova Issue descrevendo o bug ou a feature desejada

### 2. Fork e Clone

```bash
git clone https://github.com/seu-usuario/matexunb.git
cd matexunb
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Crie uma Branch

```bash
git checkout -b feature/minha-feature
# ou
git checkout -b fix/correcao-do-bug
```

### 4. Faça suas Mudanças

- Siga os padrões de código existentes
- Adicione docstrings em todas as funções públicas
- Adicione testes para novas funcionalidades

### 5. Teste

```bash
python test_scraper.py
```

Certifique-se de que todos os 9 testes passam antes de abrir o PR.

### 6. Commit e Push

```bash
git add .
git commit -m "feat: descrição da mudança"
git push origin feature/minha-feature
```

### 7. Abra um Pull Request

- Descreva o que foi feito e por quê
- Inclua screenshots se houver mudanças visuais

## 📏 Padrões de Código

- **Python**: PEP 8, type hints, docstrings no formato Google
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/)
- **Branches**: `feature/nome`, `fix/nome`, `docs/nome`

## ⚠️ Regras

- Nunca comite credenciais ou dados sensíveis
- Nunca comite o diretório `secret/` ou `.venv/`
- Sempre teste com dados reais do SIGAA antes de abrir PR
