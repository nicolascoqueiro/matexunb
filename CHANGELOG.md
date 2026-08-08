# Changelog — MatexUnB

Todas as mudanças notáveis neste projeto serão documentadas aqui.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [2.1.0] - 2026-08-08

### 🚀 Adicionado
- **Detecção e renovação automática de sessão SIGAA** — ao detectar expiração (timeout de 8 min), o sistema faz re-login sem fechar o navegador e retoma a tentativa de matrícula
- **Log de confirmação com data e hora exatas** — ao confirmar matrícula, exibe `✅ MATRÍCULA CONFIRMADA em DD/MM/AAAA às HH:MM:SS` no painel de logs
- **Parada automática da automação** — o loop encerra sozinho quando todos os alunos estiverem inscritos (status `"Concluído"`)
- **Recarregamento de dados a cada ciclo** — o `db.json` é relido no início de cada iteração, capturando mudanças feitas pela interface sem reiniciar o servidor

### 🔧 Corrigido
- **Erros temporários não bloqueiam mais o aluno** — "vaga não encontrada" e "sessão expirada" não são mais gravados em `student.error`; apenas erros definitivos (credenciais inválidas) bloqueiam futuras tentativas
- **Sessão expira silenciosamente** — após ~60 F5s (~8 min), o SIGAA redirecionava para o login sem ser detectado; agora `_is_session_expired()` verifica a URL e o DOM a cada refresh

### 🗑️ Removido
- **`gui.py`** — interface gráfica desktop (Tkinter) removida; o projeto agora utiliza exclusivamente a interface web (`static/index.html` + Flask)

---

## [2.0.0] - 2026-07-25

### 🚀 Adicionado
- **Web scraping ao vivo via Selenium** no portal público do SIGAA UnB (`listar.jsf`)
- **Suporte a todos os 210 departamentos** da UnB
- **Cache em memória** para evitar consultas repetidas ao SIGAA na mesma sessão
- **Parser HTML** com mapeamento correto das 8 colunas da tabela do SIGAA
- **Limpeza automática de horários** — remove texto expandido ("Terça-feira 20:50 às 22:30")
- **9 testes automatizados** validando scraping ao vivo, parsing, API e cache
- **Endpoint `/api/scraper/search`** com atualização imediata do banco de dados local
- **Endpoints OpenAPI** compatíveis (`/courses/`, `/courses/year-period/`)
- **Remoção instantânea de turmas** com 1 clique (sem confirmação popup)
- **Documentação completa** — README.md, CONTRIBUTING.md, CHANGELOG.md

### 🔧 Corrigido
- **HTTP 405 Method Not Allowed** ao remover turmas com `/` no horário (ex: `10/08/2026`)
- **Mapeamento de colunas** — TD[4] é vazio (separador), TD[5]=vagas, TD[6]=ocupadas, TD[7]=local
- **ViewState JSF** — recarrega a página após aceitar cookies para obter ViewState fresco
- **Modal de cookies** — aceita clicando no botão "Ciente" (não removendo o elemento DOM)

### 🗑️ Removido
- **9.540 linhas de catálogos fictícios** — substituídos por scraping ao vivo
- **Geração de dados inventados** — o sistema agora retorna 0 turmas se não houver dados reais
- **Confirmação popup ao remover turmas** — remoção instantânea com 1 clique

## [1.0.0] - 2025-XX-XX

### Adicionado
- Versão inicial do sistema com interface GUI (Tkinter)
- Automação de matrícula via Selenium
- Modelos de dados (SchoolClass, Student)
- Separação de dados públicos e sensíveis
- Servidor Flask básico
