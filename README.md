# RoomFlow

Sistema de gerenciamento e reserva de salas desenvolvido em **Python** com **Streamlit**.

## Tecnologias

* Python
* Streamlit
* SQLAlchemy e Alembic
* PostgreSQL (local ou Supabase)

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
```

No Linux:

```bash
source .venv/bin/activate
```

### 4. Instale as dependências

Na raiz do RoomFlow, com o ambiente virtual ativado, instale as dependências
da aplicação e do banco:

```bash
python -m pip install -r requirements.txt
```

## Executando a demonstração em memória

Com o ambiente virtual ativado, execute:

```bash
APP_ENV=development ROOMFLOW_PERSISTENCE=memory streamlit run main.py
```

O Streamlit iniciará o sistema e exibirá no terminal o endereço para acessar a aplicação pelo navegador.

Normalmente:

```text
http://localhost:8501
```

## Executando com PostgreSQL

### Supabase compartilhado do grupo

Todos os integrantes devem usar a URI do mesmo projeto PostgreSQL Supabase já
criado pelo grupo. Solicite ao responsável a URI do banco para o ambiente de
execução e confirme que o projeto é o ambiente acadêmico autorizado. Obtenha a
URI em **Supabase Dashboard → Connect**; copie a opção adequada ao tipo de rede
e use a string exatamente como fornecida. Para redes IPv4, o pooler compartilhado
em modo **Session** é uma opção compatível; use conexão direta quando a rede
suportar o endpoint. Consulte a [documentação de conexão do Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres)
para escolher o modo e ativar SSL.

No `.env` privado de cada computador, configure:

```dotenv
APP_ENV=production
ROOMFLOW_PERSISTENCE=postgres
DATABASE_URL=<URI PostgreSQL compartilhada fornecida pelo grupo>
```

Substitua o texto entre sinais pela URI privada do painel e codifique caracteres
reservados da senha. Se o responsável indicar SSL obrigatório e a URI não tiver
`sslmode`, configure também `DB_SSLMODE=require`. `DATABASE_URL` tem precedência
sobre os campos `DB_*`. Não envie a URI pelo Git, README, `.env.example` ou chat.

Depois de configurar a URI:

```powershell
streamlit run main.py
```

O Streamlit usa controllers e serviços locais; os repositórios abrem sessões no
PostgreSQL compartilhado. Os computadores configurados com a mesma URI, o mesmo
esquema e vínculos institucionais consultam os mesmos dados.

### Streamlit Community Cloud + Supabase

Em **App settings → Secrets** do Streamlit, configure as chaves na raiz do TOML:

```toml
APP_ENV = "production"
ROOMFLOW_PERSISTENCE = "postgres"
DATABASE_URL = "postgresql+psycopg://USUARIO:SENHA@HOST-DO-POOLER:5432/postgres"
```

Use a URI compartilhada do grupo nesse campo privado e codifique caracteres
reservados da senha na URL. Não publique o `.env` no Git. O `.env` local não é
enviado ao Community Cloud.

O Streamlit chama controllers locais e os serviços do runtime PostgreSQL no
mesmo processo. Não usa HTTP interno, ASGI, Uvicorn ou `ROOMFLOW_API_URL`.
O runtime valida a conexão e o esquema antes de exibir os formulários; uma falha
interrompe a operação com erro explícito, sem fallback para memória.

### Arquivos e imagens

Plantas de andares e posições de salas são persistidas no PostgreSQL; os bytes
das plantas ficam em `arquivos_planta`, portanto acompanham o banco compartilhado.
Logos e demais arquivos em `assets/` fazem parte do código implantado. A foto de
perfil ainda não está conectada a um armazenamento: o seletor atual não grava nem
exibe a imagem, e o modelo de usuário não tem campo de foto. Não há bucket ou
credencial do Supabase Storage configurado neste repositório. Antes de habilitar
fotos, confirme com o grupo se já existe um bucket autorizado e receba o nome,
políticas e credencial de servidor por um canal privado; se não existir, será
necessário aprovar a estratégia de armazenamento e a migration correspondente.

### Execução local

Configure `DATABASE_URL` com a URI privada do Supabase compartilhado, conforme
acima. O template não seleciona `localhost`; se a URI estiver ausente, a conexão
deve falhar explicitamente na inicialização. `DATABASE_URL` tem precedência sobre
os cinco campos `DB_*`; o carregamento não sobrescreve variáveis do ambiente.

Use `DB_*` somente em um ambiente separado de desenvolvimento local ou teste.
A demonstração em memória exige `APP_ENV=development` (ou `test`) e
`ROOMFLOW_PERSISTENCE=memory`; ela não compartilha dados.

Antes de iniciar com um banco compartilhado, confira o head local e a revisão
atual do banco:

```powershell
python -m alembic heads
python -m alembic current
```

Se houver revisão pendente no Supabase, combine a janela, backup e autorização
com o responsável antes de aplicar migrations. Use `upgrade head` apenas em um
banco local isolado ou após essa aprovação e a análise do impacto. Depois, inicie:

```powershell
streamlit run main.py
```

Abra `http://localhost:8501`. O script `python -m scripts.start_local`
é uma alternativa que inicia apenas o Streamlit; aceita `--streamlit-port`.

### Implantação

Instale `requirements.txt`, configure `DATABASE_URL` nos Secrets/variáveis
privadas e execute as migrations em uma etapa de implantação controlada.
Configure SMTP para confirmação de e-mail e recuperação de senha. Inicie
`streamlit run main.py` (ou selecione `main.py` no Community Cloud) e reinicie o
app após atualizar a configuração. Não é preciso publicar uma API ou abrir a
porta 8000. Verifique login e leitura dos dados após o reinício.

### API opcional preservada

`api/`, `controllers/http/`, os clientes `controllers/*_api.py` e
`controllers/embedded_api.py` não participam do runtime Streamlit. Foram
preservados para compatibilidade e cobertura HTTP; o transporte embutido ficou
obsoleto. Se houver consumidores externos, instale `requirements-api.txt` e
inicie a API separadamente com `uvicorn api.main:app`. O Streamlit continua
acessando os serviços diretamente, mesmo se `ROOMFLOW_API_URL` estiver definida.
FastAPI, Starlette, Uvicorn, python-multipart, httpx2 e anyio foram retirados das
dependências diretas do monólito e mantidos nesse arquivo opcional.

Use **Criar conta → Cadastrar instituição** para criar a primeira instituição e
o administrador. O cadastro registra o perfil necessário no catálogo, junto com
a conta e o vínculo. Para inserir os perfis manualmente, execute
`python -m db.seeds`; para criar também a instituição e os dados de
demonstração, execute `python -m db.seeds --demo` somente em um banco acadêmico
autorizado. A senha legada é `123456789`; para senhas separadas, configure
`ROOMFLOW_DEMO_PASSWORD_ADMIN`, `ROOMFLOW_DEMO_PASSWORD_GERENTE`,
`ROOMFLOW_DEMO_PASSWORD_SOLICITANTE` e
`ROOMFLOW_DEMO_PASSWORD_PARTICIPANTE` no ambiente do processo. A seed só altera
contas identificadas como demos exclusivas; ela interrompe a transação ao
encontrar um e-mail que pertença a uma conta não reconhecida como demo. Revise o
destino antes de executá-la e nunca use senhas previsíveis em produção pública.

Confirmação de e-mail e recuperação de senha usam SMTP com TLS implícito.
Configure `ROOMFLOW_SMTP_HOST`, `ROOMFLOW_SMTP_PORT` (padrão 465),
`ROOMFLOW_SMTP_FROM` e, se exigidos pelo servidor, `ROOMFLOW_SMTP_USERNAME` e
`ROOMFLOW_SMTP_PASSWORD` no ambiente do Streamlit ou no `.env` local.

O modo PostgreSQL inclui autenticação, usuários, instituições, convites,
matrículas, estrutura física, recursos, plantas, painel e histórico administrativos.
Solicitantes podem criar, acompanhar, alterar
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

As notificações operacionais são gravadas no PostgreSQL com a reserva e seu
histórico. Novas solicitações chegam aos gerentes ativos com permissão de
análise.
Conforme as preferências, aprovação e rejeição avisam o solicitante,
cancelamentos avisam solicitante e gerência, e alterações operacionais avisam
as demais partes envolvidas.
A leitura é individual por vínculo, e o solicitante pode consultar o histórico
em **Minhas reservas**.

A tela de agenda continua no modo de demonstração e não integra as rotas do modo
persistente. O modo em memória exige um ambiente explícito de desenvolvimento ou teste.

### Arquitetura

`Views (Streamlit) → Controllers locais → Application Services → Repositories
→ Models SQLAlchemy → PostgreSQL`

* `views/`: apresentação e interação.
* `controllers/local_runtime.py`: coordenação, identidade e adaptação para as telas.
* `application/services/`: casos de uso, autorização e transações existentes.
* `infrastructure/persistence/`: repositórios PostgreSQL e runtime compartilhado.
* `models/`: entidades, políticas e mapeamento SQLAlchemy.
* `config/database.py`: único engine e SessionLocal; `config/runtime.py`: seleção explícita de persistência.

O cache compartilha serviços e pool, nunca uma sessão SQLAlchemy ou o usuário
atual. `PostgresTransaction` abre/fecha sessões por operação e mantém transações
aninhadas no contexto da execução. Cada ação autenticada resolve o token da
`st.session_state` atual; sessões de autenticação e vínculos ficam no banco.
As correções `from __future__ import annotations` dos repositórios de reservas
foram preservadas para compatibilidade com Python 3.12.

## Desenvolvimento

Mantenha as dependências diretas em `requirements.txt`. Para executar a suíte:

```bash
python -m pip install -r requirements-api.txt
python -m unittest discover -s tests -t . -v
```

Para incluir os testes PostgreSQL, prepare um banco local descartável com nome
iniciado por `roomflow_test_`, aplique nele as revisões e rode a mesma suíte com
`ROOMFLOW_TEST_DATABASE` apontando para esse banco. Os testes usam `DB_*` do ambiente (com fallback ao `.env`) e criam dados próprios.
Nunca aponte os testes de escrita para o Supabase real. As telas são testadas
com controllers locais, inclusive em processos Streamlit distintos, sem Uvicorn.

## Status

🚧 Projeto em desenvolvimento.
