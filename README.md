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

## Tabelas no PostgreSQL

O Streamlit e o FastAPI usam os repositórios em memória. A configuração do
PostgreSQL atende às migrations e aos scripts de seed. Consulte o
[estado da integração com o banco](docs/institutional-enrollment-data-model.md).

Para preparar um banco de desenvolvimento, use o `.env.example` como referência
e informe no `DB_NAME` o nome de um banco existente. A porta padrão do PostgreSQL
é `5432`. Com o ambiente virtual ativo:

```bash
python -m alembic upgrade head
python -m scripts.seed_perfis
```

O seed opcional de demonstração usa `python -m scripts.seed_demo` e pede a
senha das quatro contas de demonstração.

Para mudanças futuras no modelo SQLAlchemy, revise a migration gerada antes
de aplicá-la:

```bash
python -m alembic revision --autogenerate -m "descreva a mudança"
```

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

## Status

🚧 Projeto em desenvolvimento.
