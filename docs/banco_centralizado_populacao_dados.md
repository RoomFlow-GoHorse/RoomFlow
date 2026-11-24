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

Configurar parâmetros opcionais de conexão PostgreSQL e atualizar a documentação de implantação.
