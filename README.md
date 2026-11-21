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

## Executando o projeto

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

Preencha o `.env` local conforme `.env.example`. O banco deve existir. Para
aplicar as revisões somente ao banco de desenvolvimento escolhido, confirme
`DB_HOST` e `DB_NAME` antes de executar:

```powershell
python -m alembic upgrade head
```

Em um terminal, inicie a API:

```powershell
$env:ROOMFLOW_PERSISTENCE = "postgres"
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Em outro, aponte o Streamlit para essa API:

```powershell
$env:ROOMFLOW_API_URL = "http://127.0.0.1:8000"
python -m streamlit run main.py
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
Os fluxos operacionais de reservas, conflitos e notificações permanecem no modo
de demonstração. Com `ROOMFLOW_API_URL` configurado, o Streamlit usa a API para
os fluxos liberados. O modo em memória continua disponível sem as duas variáveis.

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
