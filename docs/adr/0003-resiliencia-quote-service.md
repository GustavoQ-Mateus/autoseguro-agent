# ADR-0003: Resiliência contra a instabilidade do quote-service

Status: aceita.

## Contexto

`POST /quote` falha ~20% das vezes (500/502/503) e é lenta ~10% das vezes
(até 8s), de propósito — simula um sistema legado real. O agente não pode
travar a conversa esperando indefinidamente, nem inventar ou aproximar um
preço quando a chamada falha.

## Decisão

- **Timeout de cliente por tentativa**: 5s — menor que o pior caso de
  lentidão simulada (8s), para nunca ficar bloqueado no cenário lento.
- **Retry limitado a falhas técnicas**: no máximo 2 tentativas adicionais
  (3 no total) apenas quando o resultado for timeout ou 500/502/503. Nunca
  há retry para `422 cotacao_recusada` ou `400 payload_invalido` — são
  respostas de negócio determinísticas, reenviar não muda o resultado.
- **Backoff curto fixo** entre tentativas (1s), para não segurar demais a
  resposta síncrona do webhook.
- **Nunca inventar valor**: se todas as tentativas dentro do orçamento
  falharem por motivo técnico, o agente não estima nem reaproveita um preço
  antigo — comunica instabilidade ao lead e aciona o critério de
  escalonamento ([[0004-criterio-escalonamento-humano]]).
- Toda tentativa (sucesso, falha técnica, recusa de negócio) é registrada no
  rastro da conversa ([[0005-rastreabilidade-sqlite]]), com o motivo.

## Alternativas consideradas

- **Retry ilimitado/exponencial até suceder**: rejeitada, pode travar a
  resposta ao lead por tempo indefinido — contradiz o requisito de não
  travar.
- **Cache da última cotação bem-sucedida como fallback aproximado**:
  rejeitada. Um preço de outro perfil ou desatualizado é, na prática,
  inventar um valor — exatamente o que o desafio pede para evitar.
- **Fila assíncrona com callback ao lead quando o serviço voltar**:
  rejeitada por complexidade desproporcional ao escopo (RNF4 da spec); o
  webhook responde de forma síncrona nesta versão.

## Consequências

- Pior caso de latência por mensagem é limitado e previsível (3 tentativas
  x 5s + 2 backoffs de 1s ≈ 17s no pior caso).
- Falhas de negócio (422) nunca são mascaradas por retry — o agente sempre
  responde o motivo real já na primeira tentativa.
