# ADR-0005: Rastreabilidade e estado de conversa com SQLite local

Status: aceita.

## Contexto

O desafio exige que cada mensagem e cada cotação sejam rastreáveis, com id e
status. O webhook é stateless por natureza (cada POST é uma request/response
isolada), mas a conversa é multi-turno: o agente precisa lembrar, entre
chamadas, quais slots já foram coletados, quantas tentativas de coleta sem
sucesso já ocorreram, e o histórico de tentativas de cotação.

## Decisão

Persistir estado e rastro em um arquivo SQLite local (`sqlite3` da stdlib,
sem dependência nova), com ao menos estas entidades:

- **`messages`**: `id`, `conversation_id`, `sender_role`, `message_type`,
  `body` (já mascarado, ver [[0006-tratamento-dados-sensiveis-pii]]),
  `timestamp`, `status`.
- **`conversation_state`**: `conversation_id`, slots coletados (json),
  estágio atual, contador de tentativas de coleta sem sucesso, status geral
  (`em_andamento`, `cotado`, `recusado`, `escalonada`).
- **`quote_attempts`**: `id`, `conversation_id`, `timestamp`, payload
  enviado, status (`sucesso`, `falha_tecnica`, `recusada`), resposta ou
  motivo, latência.

O arquivo SQLite é artefato de runtime e não é commitado (entra no
`.gitignore`); o repositório versiona apenas o schema/migração inicial.

## Alternativas consideradas

- **JSONL append-only sem schema**: rejeitada. Dificulta consultar o estado
  atual de uma conversa (seria preciso reprocessar todo o log a cada
  request) e não dá suporte natural a status ponto-a-ponto por entidade.
- **Banco externo (Postgres/Redis)**: rejeitada por desproporcional ao
  escopo de um desafio de 3 dias rodado localmente via `docker-compose`
  (RNF4 da spec).
- **Estado só em memória do processo**: rejeitada. Perde-se tudo se o
  processo reiniciar, e não atende ao requisito de rastreabilidade
  persistente e consultável depois do fato.

## Consequências

- Fácil de inspecionar durante a demo (`sqlite3 arquivo.db "select * from
  quote_attempts"`), útil para produzir o "log de uma execução completa"
  exigido na entrega.
- SQLite não escala para concorrência pesada — aceitável, fora do escopo
  desta versão (não há requisito de carga).
