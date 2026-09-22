# RoomFlow

Sistema de gerenciamento e reserva de salas desenvolvido em **Python** com **Streamlit**.

## Tecnologias

* Python
* Streamlit

## Requisitos

Antes de executar o projeto, certifique-se de ter instalado:

* [Python](https://www.python.org/downloads/) 3.10 ou superior
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

Com o ambiente virtual ativado:

```bash
pip install -r requirements.txt
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

Instale as dependências e configure no `.env` o banco PostgreSQL que será usado
em produção, usando `.env.example` como referência. O nome em `DB_NAME` deve ser
exatamente o nome do banco existente. A porta usual do PostgreSQL é `5432`;
`8501` é a porta do Streamlit. O servidor precisa estar em execução e o usuário
configurado precisa ter acesso ao banco.

```bash
# Alembic cria as tabelas e registra a versão
.venv/bin/alembic upgrade head
```


Para alterações futuras nos modelos, use o Alembic:

```bash
.venv/bin/alembic revision --autogenerate -m "descreva a mudanca"
# Revise o arquivo gerado em migrations/versions antes de aplicar.
.venv/bin/alembic upgrade head
```

### Arquitetura
* **Views:** responsáveis pela interface da aplicação.
* **Controllers:** responsáveis pela lógica e controle das ações.
* **Models:** representam os dados e entidades do sistema.
* **Config:** contém as configurações da aplicação.
* **main.py:** ponto de entrada da aplicação.

## Desenvolvimento

Sempre que uma nova biblioteca for adicionada ao projeto, atualize o arquivo `requirements.txt` para que outros desenvolvedores possam instalar as mesmas dependências.

Para atualizar o arquivo com as dependências instaladas:

```bash
pip freeze > requirements.txt
```

## Status

🚧 Projeto em desenvolvimento.
