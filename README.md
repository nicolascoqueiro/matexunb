# 🎓 MatexUnB — Matrícula Extraordinária Automatizada

> **Sistema de automação para matrícula extraordinária na Universidade de Brasília (UnB)**
> com web scraping ao vivo do portal [SIGAA UnB](https://sigaa.unb.br/sigaa/public/turmas/listar.jsf).

![Python 3.12+](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-4.30-43B02A?logo=selenium&logoColor=white)
![License GNU General Public License v3.0](https://img.shields.io/badge/License-GPLv3-blue)

---

## 📋 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Funcionalidades](#-funcionalidades)
- [Arquitetura](#-arquitetura)
- [Tecnologias Utilizadas](#-tecnologias-utilizadas)
- [Instalação](#-instalação)
- [Uso](#-uso)
- [API REST](#-api-rest)
- [Web Scraping do SIGAA](#-web-scraping-do-sigaa)
- [Testes Automatizados](#-testes-automatizados)
- [Estrutura de Diretórios](#-estrutura-de-diretórios)
- [Modelos de Dados](#-modelos-de-dados)
- [Segurança](#-segurança)
- [Contribuição](#-contribuição)
- [Licença](#-licença)

---

## 📖 Sobre o Projeto

O **MatexUnB** é uma ferramenta desenvolvida para auxiliar estudantes da UnB durante o
período de **matrícula extraordinária**. O sistema:

1. **Consulta turmas em tempo real** diretamente do portal público do SIGAA UnB via web scraping
2. **Exibe uma interface web moderna** para visualizar, buscar e selecionar turmas
3. **Automatiza o processo de matrícula** usando Selenium para preencher formulários no SIGAA
4. **Gerencia credenciais de forma segura**, separando dados públicos de dados sensíveis

### Problema Resolvido

Durante a matrícula extraordinária na UnB, os estudantes enfrentam:
- Interface lenta e desatualizada do SIGAA
- Dificuldade em encontrar turmas com vagas disponíveis
- Processo manual e repetitivo de busca e tentativa de matrícula
- Risco de perder vagas por falta de agilidade

O MatexUnB resolve isso buscando **dados reais ao vivo** e automatizando todo o fluxo.

---

## ✨ Funcionalidades

| Funcionalidade | Descrição |
|---|---|
| 🔍 **Busca ao Vivo** | Consulta turmas diretamente do SIGAA UnB em tempo real via Selenium headless |
| 🏛️ **210 Departamentos** | Suporte a todos os departamentos e unidades acadêmicas da UnB |
| 📊 **Interface Web** | Dashboard moderno para visualizar turmas, vagas e horários |
| 🤖 **Automação** | Loop automático de tentativa de matrícula com Selenium |
| 🔐 **Dados Seguros** | Separação entre dados públicos (`public/db.json`) e sensíveis (`secret/db.json`) |
| 💾 **Cache Inteligente** | Cache em memória evita consultas repetidas ao SIGAA na mesma sessão |
| 🗑️ **Remoção Instantânea** | Turmas removidas com 1 clique, sem confirmação popup |
| 📡 **API REST** | Endpoints JSON para integração com outros sistemas |

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                     Navegador do Usuário                    │
│                   http://localhost:5050                      │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────────┐
│                  Flask Web Server (web_app.py)               │
│                    Porta 5050 (0.0.0.0)                     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │ Static Files │  │  API REST    │  │  Automação Thread │ │
│  │ (index.html) │  │ /api/*       │  │  (background)     │ │
│  └──────────────┘  └──────┬───────┘  └───────────────────┘ │
└────────────────────────────┼────────────────────────────────┘
                             │
              ┌──────────────▼──────────────┐
              │    sigaa_scraper.py          │
              │  (Web Scraping ao Vivo)      │
              │                             │
              │  Selenium Chrome Headless   │
              │         ↓                   │
              │  SIGAA UnB (listar.jsf)     │
              │         ↓                   │
              │  BeautifulSoup HTML Parser  │
              └──────────────┬──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │     Banco de Dados Local     │
              │                             │
              │  public/db.json  (turmas)   │
              │  secret/db.json  (senhas)   │
              └─────────────────────────────┘
```

---

## 🛠️ Tecnologias Utilizadas

| Tecnologia | Versão | Uso |
|---|---|---|
| **Python** | 3.12+ | Linguagem principal |
| **Flask** | 3.x | Servidor web e API REST |
| **Flask-CORS** | 5.x | Cross-Origin Resource Sharing |
| **Selenium** | 4.30 | Web scraping via Chrome headless |
| **BeautifulSoup4** | 4.x | Parsing de HTML do SIGAA |
| **Google Chrome** | 120+ | Navegador headless para scraping |
| **ChromeDriver** | Compatível | Driver do Selenium para Chrome |
| **HTML/CSS/JS** | - | Interface web frontend (SPA) |

---

## 📦 Instalação

### Pré-requisitos

- Python 3.12 ou superior
- Google Chrome instalado
- ChromeDriver compatível com a versão do Chrome

### Passo a Passo

```bash
# 1. Clone o repositório
git clone https://github.com/nicolascoqueiro/matexunb.git
cd matexunb

# 2. Crie e ative o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Inicie o servidor
python manager.py
```

O servidor estará disponível em:
- 👉 **http://localhost:5050**
- 👉 **http://127.0.0.1:5050**

---

## 🚀 Uso

### Interface Web

1. Acesse `http://localhost:5050` no navegador
2. Selecione o **departamento** desejado no dropdown (210 departamentos disponíveis)
3. Escolha o **ano** e **período** letivo
4. Clique em **Buscar** — o sistema faz scraping ao vivo no SIGAA
5. Visualize as turmas com vagas, horários, docentes e local
6. Adicione turmas à sua lista de matrícula
7. Configure suas credenciais (matrícula, CPF, senha do SIGAA)
8. Inicie a automação de matrícula

### Linha de Comando

```bash
# Iniciar o servidor web
python manager.py

# Executar testes automatizados
python test_scraper.py
```

---

## 📡 API REST

Todos os endpoints retornam JSON.

### Autenticação

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/auth/status` | Verifica se há um aluno autenticado |
| `POST` | `/api/auth/login` | Cadastra/autentica um aluno |
| `POST` | `/api/auth/logout` | Encerra a sessão e limpa credenciais |

### Departamentos

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/departments` | Lista todos os 210 departamentos da UnB |

### Turmas

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/data` | Retorna todas as turmas e alunos cadastrados |
| `POST` | `/api/classes` | Adiciona ou atualiza uma turma |
| `POST` | `/api/classes/delete` | Remove uma turma (JSON body: `{code, schedule}`) |
| `DELETE` | `/api/classes/<code>/<schedule>` | Remove uma turma por URL path |

### Web Scraper

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/scraper/search` | Busca turmas ao vivo no SIGAA e atualiza o banco local |

**Exemplo de requisição:**
```json
POST /api/scraper/search
{
  "depto_code": "508",
  "nivel": "G",
  "ano": "2026",
  "periodo": "2",
  "search": "COMPUTAÇÃO"
}
```

**Exemplo de resposta:**
```json
{
  "success": true,
  "source": "database_updated_live",
  "message": "Banco de Dados Local atualizado imediatamente (108 turmas registradas no db.json).",
  "classes": [
    {
      "code": "CIC0002",
      "turma": "01",
      "name": "FUNDAMENTOS TEÓRICOS DA COMPUTAÇÃO",
      "schedule": "24T45 (10/08/2026 - 14/12/2026)",
      "teacher": "MARIA EMILIA MACHADO TELLES WALTER (60h)",
      "vagas": "60",
      "matriculados": "0",
      "local": "PAT - AT-096/31",
      "ano": "2026",
      "periodo": "2"
    }
  ]
}
```

### Alunos

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/students` | Cadastra ou atualiza um aluno |
| `DELETE` | `/api/students/<registration>` | Remove um aluno por matrícula |

### Automação

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/automation/start` | Inicia o loop de automação de matrícula |
| `POST` | `/api/automation/stop` | Para a automação |
| `GET` | `/api/automation/status` | Status e logs da automação |

### OpenAPI Compatível

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/courses/?search=&year=&period=&depto_code=` | Busca disciplinas (formato OpenAPI) |
| `GET` | `/courses/year-period/` | Lista anos/períodos disponíveis |
| `POST` | `/courses/schedules/generate/` | Gera grades horárias |

---

## 🌐 Web Scraping do SIGAA

### Como Funciona

O scraper se conecta ao portal público do SIGAA UnB em:
```
https://sigaa.unb.br/sigaa/public/turmas/listar.jsf
```

#### Fluxo Completo (6 passos)

```
1. GET listar.jsf          → Carrega a página do formulário JSF
2. Click "Ciente"          → Aceita o modal de consentimento de cookies
3. GET listar.jsf          → Recarrega para obter javax.faces.ViewState fresco
4. Preenche formulário     → Nível, Departamento, Ano, Período
5. Injeta hidden input     → Simula o botão "Buscar" do JSF
6. form.submit()           → Submete e faz parsing da tabela de resultados
```

#### Por que Selenium e não HTTP puro?

O SIGAA da UnB usa **JavaServer Faces (JSF)**, que mantém estado no servidor.
Tentativas com `urllib`/`requests` falharam porque:

- O `javax.faces.ViewState` expira quando a sessão não é mantida corretamente
- O JSF requer que o nome do botão clicado seja enviado no POST
- O modal de cookies precisa ser aceito antes de interagir com o formulário
- Após aceitar cookies, a página precisa ser recarregada para um ViewState válido

#### Estrutura da Tabela HTML do SIGAA

```
div#turmasAbertas > table.listagem
├── thead: 7 colunas (Código, Ano-Período, Docente, Horário, Vagas Ofertadas, Vagas Ocupadas, Local)
├── tbody:
│   ├── tr.agrupador: "CIC0002 - FUNDAMENTOS TEÓRICOS DA COMPUTAÇÃO"
│   ├── tr (8 TDs):
│   │   ├── TD[0]: Turma ("01")
│   │   ├── TD[1]: Ano.Período ("2026.2")
│   │   ├── TD[2]: Docente ("MARIA EMILIA... (60h)")
│   │   ├── TD[3]: Horário ("24T45 (10/08/2026 - 14/12/2026)" + tooltip expandido)
│   │   ├── TD[4]: (vazio - separador)
│   │   ├── TD[5]: Vagas Ofertadas ("60")
│   │   ├── TD[6]: Vagas Ocupadas ("0")
│   │   └── TD[7]: Local ("PAT - AT-096/31")
│   └── ...
└── tfoot: "108 turmas encontrada(s)"
```

> **Nota:** O header mostra 7 colunas, mas cada linha de dados tem **8 TDs**.
> O TD[4] é um separador vazio que não aparece no header.

#### Cache

O sistema mantém um cache em memória (`_scrape_cache`) para evitar consultas repetidas
ao SIGAA durante a mesma execução do servidor. O cache é indexado por
`{depto_code}_{nivel}_{ano}_{periodo}`.

---

## 🧪 Testes Automatizados

### Executar Testes

```bash
# Ativar ambiente virtual
source .venv/bin/activate

# Executar todos os testes
python test_scraper.py

# Executar com verbosidade
python -m unittest test_scraper -v
```

### Suíte de Testes

| Teste | Descrição | Validação |
|---|---|---|
| `test_01` | Scraping ao vivo CDS (640) | Retorna turmas reais com códigos CDS* |
| `test_02` | Scraping ao vivo CIC (508) | Retorna turmas com todos os campos obrigatórios |
| `test_03` | Scraping ao vivo COM (345) | Retorna turmas reais de Comunicação |
| `test_04` | Filtro de busca por nome | Busca por "COMPUTAÇÃO" filtra corretamente |
| `test_05` | Parsing de schedule | Horários limpos sem "Terça-feira 20:50..." expandido |
| `test_06` | Parsing de vagas/local | Vagas=número, Local=texto (não invertidos) |
| `test_07` | Parser HTML direto | Parser funciona com HTML fornecido manualmente |
| `test_08` | API REST /api/scraper/search | Endpoint retorna 200 com turmas ao vivo |
| `test_09` | Cache de memória | Evita requisições duplicadas ao SIGAA |

### Resultado Esperado

```
Ran 9 tests in ~50s

OK
```

> **Nota:** Os testes levam ~50 segundos porque cada um abre um Chrome headless
> e faz scraping ao vivo no SIGAA. Isso é intencional — garante que os dados
> retornados são **sempre reais**.

---

## 📁 Estrutura de Diretórios

```
matexunb/
├── manager.py              # Ponto de entrada — inicia o Flask na porta 5050
├── web_app.py              # Servidor Flask com todas as rotas da API REST
├── sigaa_scraper.py        # Web scraper ao vivo do SIGAA UnB via Selenium
├── config.py               # Integração entre bancos de dados público e secreto
├── departments.py          # Lista dos 210 departamentos/unidades da UnB
├── get_enrollment_manager.py  # Gerenciador de matrícula via Selenium
├── list_classes.py         # Lógica de listagem e processamento de turmas
├── test_scraper.py         # Suíte de 9 testes automatizados
├── requirements.txt        # Dependências Python
├── .gitignore              # Arquivos ignorados pelo Git
├── LICENSE                 # Licença MIT
├── README.md               # Este arquivo
│
├── models/                 # Modelos de dados (ORM-like)
│   ├── __init__.py
│   ├── school_class.py     # Modelo SchoolClass (turma disciplinar)
│   ├── students.py         # Modelo Student (aluno)
│   ├── db.py               # Persistência JSON pública (public/db.json)
│   ├── secret_db.py        # Persistência JSON secreta (secret/db.json)
│   └── offered_db.py       # Persistência de turmas ofertadas
│
├── static/                 # Arquivos estáticos servidos pelo Flask
│   ├── index.html          # SPA (Single Page Application) principal
│   └── favicon.ico         # Ícone do site
│
├── public/                 # Dados públicos
│   └── db.json             # Banco de dados de turmas e alunos (dados não sensíveis)
│
├── secret/                 # Dados sensíveis (NÃO comitado no Git)
│   └── db.json             # Credenciais dos alunos (CPF, senha, data de nascimento)
│
└── .venv/                  # Ambiente virtual Python (NÃO comitado no Git)
```

---

## 📐 Modelos de Dados

### SchoolClass (`models/school_class.py`)

Representa uma turma ofertada no SIGAA.

```python
SchoolClass(
    code="CIC0002",                              # Código da disciplina
    schedule_class="24T45 (10/08/2026 - 14/12/2026)",  # Horário
    teacher="MARIA EMILIA MACHADO TELLES WALTER (60h)", # Docente
    depto_code="508",                            # Código do departamento
    nivel="G",                                   # Nível (G=Graduação)
    ano="2026",                                  # Ano letivo
    periodo="2",                                 # Período/Semestre
    students=[...]                               # Lista de Student
)
```

### Student (`models/students.py`)

Representa um aluno cadastrado no sistema.

```python
Student(
    name="João Silva",           # Nome completo
    cpf="12345678901",           # CPF (dado sensível)
    registration="231012345",    # Matrícula acadêmica
    date_of_birth="01011999",    # Data de nascimento (dado sensível)
    password="senha123",         # Senha do SIGAA (dado sensível)
    get_enrolled=False,          # Matrícula realizada?
    error=""                     # Mensagem de erro (se houver)
)
```

### Separação Público/Secreto

| Arquivo | Contém | Comitado no Git? |
|---|---|---|
| `public/db.json` | Turmas, nomes, matrículas, status | ✅ Sim |
| `secret/db.json` | CPF, data nascimento, senhas | ❌ **Não** |

---

## 🔐 Segurança

- **Dados sensíveis nunca são comitados** — o `.gitignore` exclui `secret/db.json`
- **Separação de responsabilidades** — `config.py` mescla dados públicos e sensíveis apenas em memória
- **Selenium headless** — o Chrome roda sem interface gráfica, sem expor dados na tela
- **Acesso local apenas** — o servidor Flask roda em `localhost:5050` por padrão

### ⚠️ Aviso Importante

> Este software é uma ferramenta de **apoio estudantil**. O uso é de
> responsabilidade exclusiva do usuário. Certifique-se de que o uso está
> em conformidade com as normas da UnB e do SIGAA.

---

## 🤝 Contribuição

1. Faça um Fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'feat: adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

### Padrão de Commits

Este projeto segue o [Conventional Commits](https://www.conventionalcommits.org/):

```
feat:     Nova funcionalidade
fix:      Correção de bug
docs:     Apenas documentação
refactor: Refatoração de código
test:     Adição ou modificação de testes
chore:    Tarefas de manutenção
```

---

## 📄 Licença

Distribuído sob a **Licença GNU General Public License v3.0**. Veja [LICENSE](LICENSE) para mais informações.

---

## 🏫 Departamentos Suportados

O sistema suporta todos os **210 departamentos** cadastrados no SIGAA UnB, incluindo:

<details>
<summary>Ver lista completa de departamentos</summary>

| Código | Departamento |
|---|---|
| 672 | Campus UnB Ceilândia (FCTS) |
| 673 | Campus UnB Gama (FGA) |
| 640 | Centro de Desenvolvimento Sustentável (CDS) |
| 508 | Depto Ciências da Computação (CIC) |
| 518 | Depto Matemática (MAT) |
| 524 | Depto Física (FIS) |
| 345 | Depto Comunicação Organizacional (COM) |
| 327 | Depto Administração |
| 548 | Depto Economia |
| 437 | Depto Engenharia Civil e Ambiental |
| 443 | Depto Engenharia Elétrica |
| 449 | Depto Engenharia Mecânica |
| 422 | Depto Enfermagem |
| 424 | Depto Nutrição |
| 592 | Depto Psicologia Clínica |
| 483 | Depto Sociologia |
| 559 | Depto História |
| 555 | Depto Geografia |
| ... | _e mais 192 departamentos_ |

</details>

---

<p align="center">
  Feito com ❤️ para os estudantes da <strong>Universidade de Brasília</strong>
</p>
