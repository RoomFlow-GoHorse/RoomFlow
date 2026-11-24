# Banco centralizado e população de dados

## Diagnóstico

- A API já separa a interface Streamlit do PostgreSQL e mantém credenciais somente no backend.
- `DATABASE_URL` aceita PostgreSQL remoto; a configuração por campos `DB_*` precisa documentar SSL e pool para provedores gerenciados.
- Plantas persistidas usam `arquivos_planta` no PostgreSQL, portanto ficam disponíveis para todas as instâncias da API conectadas ao mesmo banco.
- Não há imagens `1.png` a `6.png` no repositório. Elas não serão recriadas nem substituídas.
- As seeds existentes são demonstrativas e não são adequadas para popular uma instituição real compartilhada de forma idempotente.
- A migration `c8d15a6e2f91` permanece pendente de validação em banco isolado: `ROOMFLOW_TEST_DATABASE` não está configurado.

## Plano de execução

1. Fortalecer a configuração documentada de PostgreSQL remoto, SSL, timeout e pool sem credenciais fixas.
2. Validar a cadeia de migrations e registrar os comandos seguros para banco vazio, teste isolado e produção.
3. Criar seeds modulares e idempotentes, sem sobrescrever dados administrativos existentes.
4. Receber as seis plantas originais antes de cadastrar os arquivos e suas posições.
5. Substituir as fontes locais restantes por consultas da API e concluir testes de participantes.

## Limitações e decisões

- Nenhuma migration será aplicada enquanto o destino, backup e autorização não forem confirmados.
- Dados institucionais oficiais da UniSAPIENS só serão inseridos quando fornecidos ou verificados; o mecanismo de seed tratará dados acadêmicos de apresentação como opcionais.
- O banco compartilhado deve ser acessado somente pela API; clientes Streamlit recebem `ROOMFLOW_API_URL`, não credenciais PostgreSQL.

## Próxima tarefa

Auditar migrations e preparar testes PostgreSQL isolados.

## Concluído

- A conexão aceita `DATABASE_URL` remota ou `DB_*`, com `DB_SSLMODE`, timeout e pool configuráveis sem credenciais fixas.
- Testes de regressão da API e mapeamento: 13 aprovados.
- A cadeia Alembic é linear, com `c8d15a6e2f91` como única revisão head e `reserva_participantes` no topo.

## Validação de migrations e testes isolados

- O serviço PostgreSQL local está disponível, mas `ROOMFLOW_TEST_DATABASE` não foi informado.
- Para impedir alteração de um banco principal ou compartilhado, a validação de migrations e os testes PostgreSQL continuam bloqueados até que um banco cujo nome comece por `roomflow_test_` seja explicitamente configurado.
- Com esse banco criado e as mesmas credenciais locais autorizadas, execute:

```powershell
$env:ROOMFLOW_TEST_DATABASE = "roomflow_test_roomflow"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m unittest tests.test_postgres_integration -v
```
