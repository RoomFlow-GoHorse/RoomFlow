# Auditoria de desempenho do RoomFlow

24 de novembro de 2026

## Diagnóstico

Três rotas do participante abortaram localmente com `PermissionDenied`. Isso é um defeito funcional reproduzível nas permissões atuais e deve entrar na triagem de incidentes junto com os sintomas de lentidão.

O código amplifica o custo de cada interação autenticada. Antes de renderizar a página, ele valida a sessão e carrega uma caixa de notificações completa para exibir apenas o contador. Depois, controllers repetem a validação em cada chamada. O dashboard do participante, a localização de espaços e a planta administrativa acrescentam consultas proporcionais ao número de reservas ou prédios. Essa combinação explica a sensibilidade a latência de rede e volume de dados. O ensaio local confirmou a quantidade de operações, a repetição e o custo no processo de teste. A causa dos travamentos em produção continua sem confirmação por falta de uma série de métricas do deploy e do banco remoto.

## Navegação e trabalho síncrono

- [main.py](../main.py) usa um roteador próprio com `session_state.page` e `st.query_params`. Cada execução passa por configuração, boot, CSS, sincronização, autenticação, sidebar e despacho da rota. Os imports dos módulos já se beneficiam do cache de importação do Python após a inicialização. O CSS e os logos têm cache de leitura ou codificação em [ui_components.py](../views/components/ui_components.py), embora o HTML ainda seja emitido a cada renderização.
- [app_state_service.py:46](../controllers/app_state_service.py#L46) chama `st.rerun()` depois de escrever a rota. No clique de sidebar, o primeiro ciclo já chegou à autenticação e à consulta de notificações antes de mudar de página. Usar callbacks `on_click` para gravar destino, URL e limpar diálogos antes do fluxo principal elimina esse ciclo intermediário. Validar links diretos, botão voltar, redirecionamento por perfil e limpeza de estado. Considerar `st.navigation` apenas se simplificar o roteamento após essa correção.
- Vários `st.rerun()` seguem mutações e existem para atualizar listas e indicadores. Manter onde a recarga é necessária. Priorizar ações locais que apenas alteram seleção, filtros ou diálogos. Usar formulários para filtros que podem ser aplicados juntos e fragmentos para regiões independentes. Um fragmento que lê dados protegidos deve resolver a identidade e aplicar as permissões no próprio ciclo. [Fluxo de execução do Streamlit](https://docs.streamlit.io/develop/api-reference/execution-flow)
- [sidebar.py:82](../views/components/sidebar.py#L82) busca `inbox(unread_only=True, limit=1)` antes de processar os botões. São cinco statements para o inbox, incluindo `SET TRANSACTION`, consulta à instituição, contagem, seleção e contagem de não lidas, além de dois para autenticar. O caminho existente `notifications.unread_count()` mantém a política do serviço e reduz os cinco statements do inbox a um. A tela de notificações ainda pode reutilizar o resultado dentro do mesmo ciclo, se a ordem de renderização permitir.
- [authentication_service.py:117](../application/services/authentication_service.py#L117) faz duas leituras por validação, em dois checkouts. O serviço usa um lock quando recebe essa dependência. O runtime PostgreSQL não injeta um lock de processo nessa leitura. [main.py](../main.py), [streamlit_runtime.py](../controllers/streamlit_runtime.py) e [local_runtime.py](../controllers/local_runtime.py) repetem trabalho. Alguns handlers chamam `get_streamlit_actor` e passam o ator a um proxy que resolve de novo. Primeiro eliminar a duplicação dentro de uma mesma ação e avaliar um lookup único de sessão, usuário e vínculo, com equivalência de expiração, revogação, perfis e estados. Manter verificações de autorização e revalidações atuais de escrita. Evitar TTL para a identidade autenticada.
- [streamlit_runtime.py:56](../controllers/streamlit_runtime.py#L56) cria um `LocalRuntime` e suas fachadas a cada acesso. Os serviços ficam em `st.cache_resource`; o caminho persistente da UI chama serviços Python diretamente. Reutilizar a fachada por execução se o perfil de CPU apontar ganho. A criação dos wrappers é secundária frente às consultas que eles disparam.
- A planta administrativa busca metadados, posições e bytes, codifica a imagem em Base64 e a envia como HTML. A configuração de estrutura e recursos também renderiza conteúdo em expanders, inclusive fechados no fluxo atual. Adiar leituras e renderização dessas seções e medir tamanho da planta, payload e RSS com arquivos representativos. Base64 acrescenta cerca de um terço ao tamanho bruto antes do HTML. Ações de cadastro e recuperação podem aguardar SMTP síncrono com timeout de socket de 10 s. Separar essa métrica da navegação e do SQL. As chamadas de envio ficam fora dos trechos transacionais inspecionados. [Planta](../views/pages/admin/floor_plan_page.py) · [Storage PostgreSQL](../infrastructure/persistence/plant_repository.py) · [SMTP](../infrastructure/email/smtp_email_sender.py)
- Em [main.py](../main.py), a primeira execução de qualquer rota pública aguarda a validação do esquema, incluindo listagem de tabelas e revisão Alembic. Após sucesso, o cache de recurso evita repetir a inspeção. Falhas de inicialização voltam a ser tentadas em novas execuções. A recuperação visível via botão também faz rerun. Preservar a verificação antes de operações que dependem do banco e medir separadamente retomada do processo, bootstrap e reconexão.

## Consultas e transações

| Caminho | Evidência e mudança recomendada |
|---|---|
| Dashboard do participante | `list_participating()` seguido de `participating_detail()` para cada reserva. Cada detalhe adiciona duas consultas de autenticação, uma releitura da reserva e uma consulta ao status do vínculo. Selecionar o status na listagem existente, que já faz join de `reserva_participantes` por usuário e instituição. Preservar a consulta de detalhe para ações explícitas. [View](../views/pages/participant/participant_dashboard_page.py#L368) · [Repository](../infrastructure/persistence/reservation_repository.py#L60) |
| Localizar e planta | As views iteram pelos prédios. Cada chamada de andares autentica, valida o prédio no serviço e lista seus andares, quatro statements por prédio. Carregar só o prédio selecionado quando a UI permitir ou carregar todos os andares em uma consulta institucional e agrupar por prédio. Buscar espaços do contexto selecionado sempre que a UI dispensar o catálogo inteiro. [Localizar](../views/pages/participant/find_space_page.py#L179) · [Planta](../views/pages/admin/floor_plan_page.py#L67) · [Serviço](../application/services/space_service.py#L116) |
| Dashboard administrativo | Lista todos os usuários, espaços e recursos para contar e faz uma consulta de andares por prédio. Usar agregações no SQL por status e perfil e uma consulta limitada para cadastros recentes, com a mesma ordenação e os mesmos critérios atuais. [Serviço](../application/services/admin_dashboard_service.py#L38) |
| Dashboard gerencial e ocupação | `context()` e `report()` reconstroem instituição, prédios, espaços e recursos em snapshots distintos. O relatório mantém o snapshot durante agrupamento, construção de janelas e cálculo de ocupação por sala, com período permitido de até 366 dias. Eliminar a carga duplicada mantendo consistência dentro do relatório. Encerrar o snapshot após materializar os dados e executar os cálculos puros fora dele. [Serviço](../application/services/manager_operations_service.py#L98) |
| Reservas e agenda | Listagens de reservas institucionais, próprias e participações sem limite. A agenda carrega a lista e separa eventos no Python. Aplicar janela visível no SQL com critério de sobreposição e paginação de listas com ordenação estável. Listagens de reservas buscam o catálogo de salas para ler só o timezone, e o formulário de nova reserva chama catálogo duas vezes. Extrair leitura de configurações no serviço e buscar disponibilidade apenas para o período aplicado. Em `detail_own`, a consulta de participantes passa novamente pelo detalhe, incluindo histórico e nova autenticação. [Agenda](../views/pages/shared/agenda_page.py) · [Reservas](../infrastructure/persistence/reservation_repository.py) · [Controller](../controllers/local_runtime.py) |
| Espaços, usuários e matrículas | Espaços e recursos já têm carga em lote para associações, porém parte do filtro de status, recurso e busca roda após materializar o resultado. Usuários trazem entidades inteiras, incluindo dados necessários só a login, com vínculo e instituição completos. As abas de usuários e acesso executam ambas as seções no fluxo atual. Usar projeções por tela, filtros e paginação no repository e carregamento sob demanda, testando equivalência de busca Unicode. [Estrutura](../infrastructure/persistence/structure_repository.py#L126) · [Usuários](../infrastructure/persistence/users.py#L18) · [Abas](../views/pages/admin/users_page.py#L190) |
| Escritas de reserva e conflitos | Validação de participantes faz uma leitura por ID dentro da transação e a audiência de revisão pode listar todos os usuários. Fazer lookup em lote por instituição e projetar apenas destinatários elegíveis. A sincronização de conflitos usa self-join de intervalos e pode ficar cara com ocupação densa. Medir planos para sincronização global e por reserva. [Reservas](../application/services/reservation_service.py#L207) · [Conflitos](../infrastructure/persistence/conflict_repository.py#L45) · [Notificações](../application/services/notification_service.py) |

Os N+1 acima ocorrem por chamadas explícitas entre camadas. Os caminhos inspecionados usam joins, projeções e entidades de domínio materializadas antes de fechar a sessão. O repository de estrutura resolve recursos em uma segunda consulta em lote. `joinedload` ou `selectinload` agregariam valor apenas onde efetivamente houver navegação por relações ORM. Evitar ativar eager loading indiscriminadamente.

A listagem de reservas usa `EXISTS` correlacionado para sobreposição, sem gerar uma nova viagem por linha, mas pode repetir trabalho no servidor. As migrations já incluem índices de sala/período, solicitante/status, participação por instituição/usuário, histórico por reserva e destinatários por usuário/leitura. Validar com `EXPLAIN (ANALYZE, BUFFERS)` em staging representativo antes de migrar. Candidatos incluem índices por instituição e ordenação temporal para as listagens, por prédio para andares, índice parcial para não lidas conforme seletividade e índice funcional compatível com `lower(btrim(email))` caso o login faça scan relevante. Analisar estratégia de intervalos para reservas se o plano mostrar custo no predicado de sobreposição. [Migrations](../migrations/versions) · [Query Performance do Supabase](https://supabase.com/docs/guides/database/extensions/pg_stat_statements)

`PostgresTransaction.session()` usa `sessionmaker.begin()`, que fecha a sessão e devolve a conexão mesmo em exceções. Snapshots e escritas aninhadas compartilham a sessão só dentro do contexto, com `ContextVar` restaurado em `finally`. Todas as amostras terminaram com zero conexões emprestadas. Isso cobre os fluxos ensaiados. `atomic()` usa o mesmo advisory lock transacional para o processo de escrita de diferentes instituições e serviços, criando fila transversal quando alguma operação demora. Medir tempo de aquisição do lock e duração da transação. Preservar as garantias de concorrência antes de considerar chaves mais específicas. [Transações](../infrastructure/persistence/transaction.py)

## Engine, Supavisor e timeouts

[config/database.py](../config/database.py) cria uma engine e uma fábrica de sessões por processo no import. O cache persistente reutiliza a mesma infraestrutura durante os reruns. A configuração local apontava para Supavisor em modo sessão na porta 5432, com `sslmode=require` e `DATABASE_URL` como origem. A configuração de secrets e o endpoint implantado permanecem por confirmar.

| Parâmetro | Configuração observada | Ação |
|---|---|---|
| `pool_size` e `max_overflow` | Padrões 5 e 10, até 15 conexões concorrentes por processo. O parser atual rejeita zero em `DB_MAX_OVERFLOW`. | Definir orçamento com base em processos, concorrência, limites do Supavisor e reserva para outros consumidores. Como ponto de partida em staging com baixa concorrência, testar 2–3 permanentes e 0–2 extras, permitindo zero no parser se necessário. |
| `pool_pre_ping` | Ligado. Reutilizações saudáveis podem incluir ping adicional antes de cada sessão. | Manter inicialmente e medir checkout com ping. Reduzir checkouts desnecessários antes de avaliar desligá-lo. |
| `pool_timeout` | Padrão SQLAlchemy de 30 s. | Tornar configurável e testar 3–5 s em staging. Registrar esgotamento separadamente de falhas SQL e de conexão. |
| `pool_recycle` | Padrão SQLAlchemy de -1. | Ajustar só com evidência de conexões encerradas por idade ou inatividade na infraestrutura. Reciclagem é avaliada no checkout. |
| `connect_timeout` | Padrão 5 s em `connect_args`. | Medir DNS, abertura e TLS. Esse limite cobre conexão, enquanto fila local, execução SQL e espera por locks têm limites próprios. |
| SQL e locks | Nenhum `statement_timeout` ou `lock_timeout` é definido pelo aplicativo. Configuração do papel remoto desconhecida. | Inspecionar valores efetivos e testar limites por categoria em staging. Separar falhas de checkout, desconexão, timeout SQL e lock nos logs. Evitar repetição automática de escrita após falha de conexão com resultado de commit desconhecido. |

O modo sessão suporta prepared statements do Psycopg e tende a reter a conexão de backend enquanto o cliente do pool local estiver conectado. O Supavisor transacional na porta 6543 exigiria testar com `prepare_threshold=None` e revisar dependências de estado entre transações. O snapshot usa `SET TRANSACTION` e o lock é transacional. Testar ambos explicitamente antes de mudar endpoint. Dimensionar também as conexões de ferramentas administrativas e Alembic. A conexão direta para migrations depende da conectividade IPv6 ou do IPv4 contratado. [SQLAlchemy Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html) · [Supabase Connect](https://supabase.com/docs/guides/database/connecting-to-postgres) · [Prepared statements](https://supabase.com/kb/troubleshooting/disabling-prepared-statements-qL8lEL)

A URL recebe precedência sobre `DB_HOST` e demais campos, mas `DB_SSLMODE`, se definido, entra em `connect_args` e pode sobrepor a URL. Conferir que o deploy entrega a configuração como variáveis de ambiente lidas pelo código e que a política TLS é coerente. `require` exige TLS. Para autenticação do hostname, testar `verify-full` com a CA indicada pelo Supabase. [SSL no Supabase](https://supabase.com/docs/guides/platform/ssl-enforcement)

## Cache, estado e invalidação

- Conservar engine, fábrica e serviços thread-safe em cache de recurso. Manter `Session` limitada à unidade de trabalho. Evitar guardar sessão ORM, token ou ator resolvido em cache compartilhado. Usar estado de sessão para navegação e preferências de UI. Limpar dados protegidos de estado no logout e em troca de instituição ou identidade. A planta tem dados derivados em estado e deve repovoá-los a partir do escopo autorizado antes de reutilizar.
- Reduzir consultas antes de acrescentar TTL. Se o catálogo estrutural continuar caro, testar `st.cache_data` para projeções leves, com 30–60 s e `max_entries`, após autorização. A chave inclui instituição, filtros normalizados e escopo de visibilidade quando os dados diferirem entre perfis. Retornar DTOs, evitando ORM, credenciais e conteúdo de planta grande. Contadores de notificações devem começar com consulta dedicada. Se precisarem de cache, usar por sessão ou por usuário e instituição, com TTL curto de 5–15 s e atualização imediata após marcação de leitura.
- Invalidar dados afetados **após commit bem-sucedido**, cobrindo criação, atualização e exclusão, inclusive alterações indiretas de recursos, estrutura e planta. Uma chave com versão por instituição e domínio permite atingir só o escopo afetado. Para múltiplos processos, usar versão persistida e atualizada junto à mutação ou assumir explicitamente a janela de obsolescência do TTL. Listas de reservas, conflitos e disponibilidade devem inicialmente permanecer frescas. Validar qualquer ação contra o banco, como hoje. [Cache do Streamlit](https://docs.streamlit.io/develop/concepts/architecture/caching)

## Medição local

Ensaio em PostgreSQL 16.15 temporário via socket Unix, com migrations até `c8d15a6e2f91`, Streamlit 1.63.0, SQLAlchemy 2.0.54 e Psycopg 3.3.6. A instituição medida tinha quatro perfis, três prédios, três andares, seis salas e seis reservas vinculadas ao participante. A planta foi medida sem imagem cadastrada. A execução foi sequencial por `AppTest`, com URL e sessão de cada perfil. Houve uma primeira execução por rota e três repetições. A tabela contém a mediana das três repetições por rota. Os três cliques foram medidos uma vez cada. O processo e o cache de recursos foram reutilizados. A primeira abertura da landing, incluindo o bootstrap e duas consultas de prontidão, levou **1.226 ms**.

A duração é medida no servidor de teste e inclui o custo do `AppTest`. CPU é tempo de CPU do processo na mesma janela. O tempo SQL soma as execuções observadas via eventos de cursor, incluindo `SET TRANSACTION` e excluindo fetch/mapeamento, ping do driver e controle implícito de transação. Checkout é o número de aquisições da pool e o tempo total de aquisição, que pode incluir ping. Ciclos contam entradas no fluxo principal em `load_css()`. O ensaio não mede pintura no navegador, WebSocket ou ida ao Supabase.

| Perfil | Rota | Tempo (ms) | CPU (ms) | SQL | SQL (ms) | Checkouts | Checkout (ms) | Ciclos |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| publico | landing | 275 | 278 | 0 | 0.00 | 0 | 0.00 | 1 |
| publico | login | 291 | 295 | 0 | 0.00 | 0 | 0.00 | 1 |
| publico | signup_choice | 239 | 243 | 0 | 0.00 | 0 | 0.00 | 1 |
| publico | signup_institution | 264 | 268 | 0 | 0.00 | 0 | 0.00 | 1 |
| publico | signup_member | 256 | 259 | 0 | 0.00 | 0 | 0.00 | 1 |
| publico | forgot_password | 258 | 261 | 0 | 0.00 | 0 | 0.00 | 1 |
| admin | admin_dashboard | 282 | 281 | 22 | 6.99 | 16 | 2.26 | 1 |
| admin | historico_admin | 270 | 271 | 23 | 4.47 | 17 | 2.19 | 1 |
| admin | usuarios | 285 | 282 | 21 | 5.69 | 16 | 3.17 | 1 |
| admin | permissoes | 259 | 260 | 12 | 3.09 | 7 | 1.50 | 1 |
| admin | planta_instituicao | 327 | 319 | 44 | 10.43 | 38 | 5.36 | 1 |
| admin | configuracoes_instituicao | 284 | 285 | 16 | 2.92 | 10 | 1.72 | 1 |
| admin | notificacoes | 251 | 252 | 18 | 3.39 | 8 | 1.37 | 1 |
| admin | conta | 272 | 275 | 10 | 2.11 | 5 | 0.90 | 1 |
| gerente | gerente_dashboard | 289 | 288 | 30 | 8.31 | 11 | 2.08 | 1 |
| gerente | gerente_reservas | 289 | 289 | 22 | 6.21 | 15 | 3.01 | 1 |
| gerente | espacos | 285 | 285 | 19 | 4.82 | 13 | 2.61 | 1 |
| gerente | ocupacao | 275 | 274 | 30 | 7.82 | 11 | 1.80 | 1 |
| gerente | gerente_conflitos | 263 | 266 | 15 | 2.87 | 9 | 1.45 | 1 |
| gerente | notificacoes | 279 | 282 | 18 | 3.67 | 8 | 1.47 | 1 |
| gerente | conta | 252 | 254 | 10 | 2.53 | 5 | 1.11 | 1 |
| solicitante | agenda | 262 | 264 | 13 | 3.07 | 8 | 1.37 | 1 |
| solicitante | nova_reserva | 269 | 267 | 28 | 5.70 | 18 | 2.55 | 1 |
| solicitante | minhas_reservas | 284 | 285 | 19 | 4.35 | 12 | 1.66 | 1 |
| solicitante | notificacoes | 282 | 281 | 18 | 4.51 | 8 | 1.67 | 1 |
| solicitante | conta | 259 | 259 | 10 | 1.58 | 5 | 0.79 | 1 |
| participante | participante_dashboard † | 269 | 269 | 12 | 2.54 | 7 | 1.37 | 1 |
| participante | agenda † | 285 | 288 | 12 | 2.47 | 7 | 1.04 | 1 |
| participante | localizar † | 285 | 287 | 12 | 2.45 | 7 | 1.18 | 1 |
| participante | notificacoes | 286 | 288 | 18 | 3.05 | 8 | 1.37 | 1 |
| participante | conta | 279 | 282 | 10 | 2.17 | 5 | 0.85 | 1 |
| admin | Alterar período do dashboard para 90 dias | 293 | 290 | 22 | 8.60 | 16 | 2.41 | 1 |
| admin | Clique do dashboard para Permissões | 503 | 504 | 22 | 7.91 | 12 | 2.56 | 2 |
| participante | click_localizar † | 508 | 513 | 22 | 3.42 | 12 | 1.79 | 2 |

† A execução registrou `PermissionDenied`, então o tempo mede o caminho interrompido. Dashboard e agenda do participante chamam `list_participating()`, que exige `VIEW_PARTICIPANT_DASHBOARD`, ausente na política efetiva do perfil. Localizar chama `list_buildings()`, que exige `MANAGE_FLOOR_PLAN`. A rota permite a entrada, mas essas views tratam somente `RuntimeUnavailable` nesse trecho. O N+1 do painel e o custo por prédio em Localizar foram identificados no código. As medições dessas rotas não incluem os loops. O click `click_localizar` parte do painel e inclui os dois ciclos. [Política efetiva](../models/domain/policies/permission_policy.py) · [Navegação por perfil](../config/constants.py)

O maior checkout individual da rodada foi 2,27 ms. O pico de RSS foi **272,7 MiB** para o processo do ensaio inteiro, incluindo fixtures, bibliotecas e infraestrutura de teste. O RSS máximo é cumulativo. O ensaio não atribui memória por página nem comprova vazamento de memória. As durações locais próximas ao tempo de CPU indicam que o PostgreSQL via socket foi uma parcela pequena do tempo medido. Com um banco remoto, a sequência de SQL, checkouts, pings e encerramentos de transação tende a amplificar a latência. O custo por rodada em produção exige medição do próprio deploy.

## Produção e critérios de aceite

1. **P0 — Triar a falha do participante.** Comparar o commit implantado com o código auditado e correlacionar `PermissionDenied` com logs das três rotas. Qualquer ajuste de acesso é uma decisão funcional separada. Para Localizar, avaliar uma leitura de catálogo com escopo institucional e permissão própria em vez de reutilizar gestão de planta.
2. **P1 — Eliminar trabalho fixo da navegação.** Usar contador dedicado na sidebar e callback nos botões de rota. Comparar as mesmas ações pelo navegador e pelo ensaio. Esperar quatro statements a menos por render autenticado na sidebar e um ciclo completo por clique de navegação. Confirmar a atualização do contador após leitura e os redirecionamentos de sessão inválida.
3. **P1 — Reduzir trabalho proporcional a dados.** Após resolver o acesso às rotas afetadas, validar que mais reservas no painel e mais prédios em catálogos não elevem linearmente a quantidade de statements. Limitar calendário e listagens a janelas e páginas. Repetir com volumes de staging e checar ordenação, recortes de datas, instituição e equivalência dos filtros.
4. **P1 — Instrumentar antes de alterar pool ou índices.** No Streamlit, registrar por rota, ação e ciclo o tempo de servidor, CPU e RSS. No SQLAlchemy, coletar contagem e duração de SQL, duração do checkout desde antes da aquisição, eventos de novas conexões, invalidações, retornos, falhas e tempo de transação. Medir espera pelo advisory lock. Usar apenas tipo de operação, rótulo de rota e ID efêmero de correlação. Suprimir SQL com parâmetros, identidade, tokens e DSN. Relatar p50 e p95, número de amostras e falhas, com abertura a frio, navegação aquecida, uma sessão e sessões simultâneas.
5. **P2 — Isolar infraestrutura e SQL.** Medir do worker implantado abertura de conexão, TLS, checkout aquecido e `SELECT 1` repetido. Comparar com tempo de execução de statements no Supabase, espera em `pg_stat_activity`, locks, ocupação do pool e CPU do banco. Conferir região do projeto e localização efetiva do worker quando disponível. Checkout alto com SQL baixo aponta para fila ou abertura de conexão. SQL alto no Supabase pede plano e análise de volume ou locks. RSS crescente durante sessões e plantas representativas pede perfil de memória, e picos de CPU com SQL baixo pedem perfil de renderização e processamento Python. Usar logs da Community Cloud para reinícios, suspensão e erros de recursos. [Gerenciamento na Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app) · [Limites de recursos da Community Cloud](https://docs.streamlit.io/knowledge-base/deploy/resource-limits) · [Observabilidade no Supabase](https://supabase.com/docs/guides/observability/inspect)
6. **P2 — Validar decisões de cache e limites.** Exercitar carga concorrente com duas instituições, dois usuários com notificações diferentes, revogação de sessão, escrita seguida de leitura e falha antes do commit. Testar expiração, mutações e isolamento. Verificar se toda conexão retorna e se a espera sob saturação é limitada. Adotar metas de p95 com base na primeira série de produção.

A auditoria inspecionou a configuração local sem reproduzir segredos. O PostgreSQL temporário foi usado para as medições. Permanecem sem medição os endpoints remotos, os logs da Community Cloud, o volume real, a concorrência real, a latência entre os serviços e os planos do Supabase. A rodada inicial foi diagnóstica. As alterações e os resultados posteriores estão registrados abaixo.

## Reteste após as correções

A navegação da sidebar e dos atalhos administrativos e gerenciais passou a usar callbacks. A sidebar chama a contagem dedicada. A autenticação PostgreSQL reúne sessão, conta e vínculo em uma consulta, validando expiração, revogação e estado do usuário a cada ação. A planta administrativa e a localização carregam andares em lote. O painel do participante lê o status do vínculo na própria listagem, e o catálogo de localização exige a permissão de leitura específica e restringe as consultas à instituição autenticada. As telas de reservas carregam apenas as configurações quando precisam de fuso horário ou da exigência de justificativa. O relatório de ocupação libera o snapshot antes dos cálculos em Python.

| Cenário | SQL antes | SQL depois | Checkouts antes | Checkouts depois |
|---|---:|---:|---:|---:|
| Clique do dashboard administrativo para Permissões | 22 | 4 | 12 | 4 |
| Dashboard administrativo | 22 | 11 | 16 | 10 |
| Planta administrativa | 44 | 20 | 38 | 19 |
| Painel do participante | interrompido | 12 | interrompido | 7 |
| Agenda do participante | interrompida | 5 | interrompida | 5 |
| Localizar | interrompida | 8 | interrompida | 7 |

O clique para Permissões passou de dois ciclos e 503 ms para um ciclo e 253 ms, em uma amostra por versão. As demais linhas comparam medianas locais. O reteste usou PostgreSQL em loopback TCP com fixtures equivalentes. O ensaio inicial usou socket Unix, portanto os números de SQL, checkout e ciclos são os mais diretamente comparáveis. Todas as rotas listadas no reteste terminaram sem erro e com zero conexões emprestadas. Um teste de integração cobre a navegação do participante, o isolamento do catálogo entre instituições e a visibilidade da participação por usuário.

O deploy, a instrumentação remota e a avaliação de paginação, índices, cache e limites do pool continuam pendentes. Essas alterações dependem da série de produção e de validação com volume representativo.
