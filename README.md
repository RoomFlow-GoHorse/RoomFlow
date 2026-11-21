# RoomFlow

Sistema de gerenciamento e reserva de salas desenvolvido em **Python** com **Streamlit**.

## Tecnologias

* Python
* Streamlit

## Requisitos

Antes de executar o projeto, certifique-se de ter instalado:

* [Python](https://www.python.org/downloads/) 3.11 ou superior
* Git

## Instalação

### 1. Clone o repositório

```bash
git clone <URL_DO_REPOSITORIO>
```

Entre na pasta do projeto:

```bash
cd reserva_salas_GoHorse
cd RoomFlow
```

### 2. Crie o ambiente virtual

No Windows:

```powershell
python -m venv .venv
```

### 3. Ative o ambiente virtual

No PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

No Prompt de Comando (CMD):

```cmd
.venv\Scripts\activate

No linux 
source .venv/bin/activate
```

### 4. Instale as dependências

Na raiz do RoomFlow, com o ambiente virtual ativado, instale as dependências
do frontend, da API, do banco e dos testes:

```bash
python -m pip install -r requirements.txt
```

## Executando a demonstração em memória

Com o ambiente virtual ativado, execute:

```bash
streamlit run main.py
```

O Streamlit iniciará o sistema e exibirá no terminal o endereço para acessar a aplicação pelo navegador.

Normalmente:

```text
http://localhost:8501
```

## Executando com PostgreSQL

Preencha o `.env` local conforme `.env.example`. Configure os cinco campos
`DB_*` ou uma `DATABASE_URL` PostgreSQL. Se as duas formas estiverem presentes,
`DATABASE_URL` tem precedência. Em uma URL, codifique caracteres especiais da
senha. O banco deve existir. Para
aplicar as revisões somente ao banco de desenvolvimento escolhido, confirme
`DB_HOST` e `DB_NAME` antes de executar:

```powershell
python -m alembic upgrade head
```

No Windows, na pasta `RoomFlow`, inicie ambos os processos com o Python do
ambiente virtual. O comando aguarda a API confirmar a conexão e o esquema
PostgreSQL em `/ready` antes de iniciar o Streamlit. Ele usa as portas 8000
e 8501 e não aplica migrations.

```powershell
.\.venv\Scripts\python.exe -m scripts.start_local
```

Abra `http://127.0.0.1:8501`. Use `--api-port` e `--streamlit-port` para
escolher portas livres se já houver outro processo usando as padrões.

Para iniciar separadamente, mantenha a API rodando no primeiro terminal:

```powershell
$env:ROOMFLOW_PERSISTENCE = "postgres"
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Em outro, confirme que `Invoke-RestMethod http://127.0.0.1:8000/ready` retorna
`ready` e `postgres`. Depois aponte o Streamlit para essa API:

```powershell
$env:ROOMFLOW_API_URL = "http://127.0.0.1:8000"
.\.venv\Scripts\python.exe -m streamlit run main.py
```

Use **Criar conta → Cadastrar instituição** para criar a primeira instituição e
o administrador. O cadastro registra o perfil necessário no catálogo, junto com
a conta e o vínculo. Os scripts `seed_perfis` e `seed_demo` continuam opcionais.

Confirmação de e-mail e recuperação de senha usam SMTP com TLS implícito.
Configure `ROOMFLOW_SMTP_HOST`, `ROOMFLOW_SMTP_PORT` (padrão 465),
`ROOMFLOW_SMTP_FROM` e, se exigidos pelo servidor, `ROOMFLOW_SMTP_USERNAME` e
`ROOMFLOW_SMTP_PASSWORD` somente no ambiente da API ou no `.env` local.

O modo PostgreSQL inclui autenticação, usuários, instituições, convites,
matrículas, estrutura física, recursos, plantas, painel e histórico administrativos.
Com `ROOMFLOW_API_URL` configurado, solicitantes podem criar, acompanhar, alterar
e cancelar suas reservas. Gerentes podem consultar e avaliar as solicitações da
própria instituição. A disponibilidade considera salas ativas e desbloqueadas
e reservas aprovadas no PostgreSQL. Solicitações abertas com horários
sobrepostos aparecem sinalizadas na lista do gerente.

Em **Conflitos**, o gerente consulta pares de reservas da própria instituição,
mantém uma reserva e rejeita a outra, ou move uma para uma sala compatível.
O botão **Detectar sobreposições** também verifica reservas anteriores à integração.

O painel do gerente e a tela de ocupação consultam as reservas no fuso da
instituição. A taxa divide o tempo coberto por reservas aprovadas pelo tempo
utilizável das salas ativas no horário institucional, descontando bloqueios
registrados. O filtro de status restringe a linha do tempo. A disponibilidade
continua considerando todas as aprovações do período selecionado.

As telas de agenda e notificações continuam no modo de
demonstração. O modo em memória continua disponível sem as duas variáveis.

### Arquitetura
* **Views:** responsáveis pela interface da aplicação.
* **Controllers:** responsáveis pela lógica e controle das ações.
* **Models:** representam os dados e entidades do sistema.
* **Config:** contém as configurações da aplicação.
* **main.py:** ponto de entrada da aplicação.

## Desenvolvimento

Mantenha as dependências diretas em `requirements.txt`. Para executar a suíte:

```bash
python -m unittest discover -s tests -v
```

Para incluir os testes PostgreSQL, prepare um banco local descartável com nome
iniciado por `roomflow_test_`, aplique nele as revisões e rode a mesma suíte com
`ROOMFLOW_TEST_DATABASE` apontando para esse banco. Os testes usam as credenciais
locais do `.env` e criam dados próprios.

## Status

🚧 Projeto em desenvolvimento.
