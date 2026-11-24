# Implementação: solicitante e participante

## Diagnóstico inicial

- Branch: `fix/integração_SolicitanteParticipante`.
- A API seleciona persistência PostgreSQL somente com `ROOMFLOW_PERSISTENCE=postgres`.
- Reservas já possuem CRUD, histórico, validações de período, capacidade e conflitos.
- Não existe vínculo persistido entre uma reserva e seus participantes: a quantidade atual é apenas um número previsto.
- O participante não dispõe de consulta de reservas vinculadas; dashboard e agenda usam dados locais de demonstração.
- Notificações de reserva alcançam solicitante e revisores, não participantes vinculados.
- `requirements.txt` declarava `httpx2`, embora o cliente importe `httpx`; a dependência foi corrigida antes deste plano.

## Plano

1. Corrigir os mocks de disponibilidade para `httpx` e registrar a linha de base de testes.
2. Adicionar persistência N:N reserva–participante, migração e contratos de domínio.
3. Integrar criação, edição, leitura e cancelamento de reservas aos vínculos, de forma atômica.
4. Expor consultas e respostas de participação autenticadas e restritas ao vínculo.
5. Entregar notificações aos participantes e substituir dados demonstrativos das telas participantes/agenda por API.
6. Cobrir os fluxos em testes; validar PostgreSQL somente em banco isolado configurado por `ROOMFLOW_TEST_DATABASE`.

## Limitações conhecidas

- `ROOMFLOW_TEST_DATABASE` não está configurado neste ambiente; migrations e testes PostgreSQL destrutivos não serão executados contra o banco local.
- Cada alteração será testada e registrada abaixo antes do próximo item.

## Registro de execução

| Etapa | Resultado | Testes | Commit |
| --- | --- | --- | --- |
| Diagnóstico | Concluído | `127` executados: `124` aprovados, `27` ignorados, `2` erros e `1` falha nos mocks `httpx2` | — |
| Compatibilidade `httpx` | Concluída | `tests.test_api_availability`: 3 aprovados | Pendente |
