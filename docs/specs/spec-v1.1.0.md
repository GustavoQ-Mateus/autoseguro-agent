# Spec v1.1.0 — Falha técnica do LLM como categoria própria

Status: proposta, aguardando revisão.

## Contexto

Incremento sobre a [spec-v1.0.0](spec-v1.0.0.md), que permanece válida como
baseline; esta versão só adiciona e ajusta o que está descrito abaixo. Todo o
resto (RF1–RF11, RNFs, critérios da v1.0.0) continua em vigor sem alteração.

Uma revisão externa do repositório apontou um defeito de design: em
`agent/app/llm.py`, `extract_and_classify` trata qualquer falha técnica da
chamada ao LLM (timeout, erro de rede, 5xx da OpenRouter, chave inválida,
resposta inesperada) devolvendo os mesmos valores de uma extração vazia
legítima. A máquina de estados conta essa falha como estagnação na coleta e,
após 3 mensagens, escala com motivo `estagnacao_coleta` — mascarando uma
instabilidade de infraestrutura dentro de outra métrica. A decisão de
arquitetura está travada na [[0008-falha-tecnica-llm-categoria-propria]], que
adapta para o LLM o mesmo cuidado que a [[0003-resiliencia-quote-service]] já
dá ao `quote-service`.

## Escopo da fase (v1.1.0)

Distinguir, ponta a ponta, "a chamada ao LLM falhou tecnicamente" de "o lead
não respondeu nenhum dado útil", e escalar por um critério próprio e
auditável quando a falha técnica do LLM for persistente.

### Fora de escopo

- Retry inline (com backoff) da chamada ao LLM — rejeitado por ora na
  [[0008-falha-tecnica-llm-categoria-propria]]; se necessário, vira ADR e
  spec futuras.
- Qualquer mudança no papel do LLM: ele continua só extraindo slots e
  classificando intenção ([[0001-llm-orquestracao-tool-use]]); nenhuma
  decisão de ação migra para o LLM.
- Tudo que já estava fora de escopo na spec-v1.0.0.

## Requisitos funcionais (novos e alterados)

- **RF12 (novo)** — `extract_and_classify` reporta ao chamador, de forma
  explícita e distinta, três resultados possíveis: (a) **falha técnica do
  LLM** — a chamada HTTP à OpenRouter levantou exceção, retornou status
  não-2xx, ou a resposta não pôde ser parseada como tool call válido; (b)
  **extração com dado** — sucesso com um ou mais slots e/ou intenção útil;
  (c) **extração válida sem dado** — sucesso, porém sem slot novo. O caso (a)
  é sinalizado por um valor dedicado no retorno, nunca reaproveitando o campo
  de intenção (que é um conjunto fechado de rótulos de negócio). O
  `try/except` envolve apenas o trecho de rede/parsing; parsing bem-sucedido,
  mesmo com slots vazios, é caso (c), não (a).

- **RF8 (alterado)** — O critério de escalonamento passa a ter uma **quarta
  condição**, além das três da [[0004-criterio-escalonamento-humano]]:
  **falha técnica persistente do LLM** — após N falhas técnicas de LLM
  **consecutivas** (contador dedicado, default N=3, separado do de
  estagnação), o agente escala para humano com motivo próprio
  `falha_tecnica_llm`.

- **RF13 (novo)** — Reação da máquina de estados à falha técnica do LLM,
  conforme [[0008-falha-tecnica-llm-categoria-propria]]:
  - A cada mensagem com falha técnica do LLM, incrementa o contador dedicado
    de falhas técnicas de LLM; **não** toca em `stagnation_count`; **não**
    altera os slots conhecidos.
  - Uma extração bem-sucedida (mesmo sem dado novo) **zera** o contador de
    falhas técnicas de LLM — é contador de falhas consecutivas.
  - Abaixo do limite, o agente não escala: responde ao lead com uma mensagem
    neutra pedindo o reenvio da informação, sem expor detalhe de
    infraestrutura, mantendo a conversa em andamento.
  - No limite, escala com motivo `falha_tecnica_llm` e status `escalonada`.

- **RF9 (reforço)** — A escalação por `falha_tecnica_llm` é registrada no
  rastro como qualquer outra ([[0005-rastreabilidade-sqlite]]); o motivo no
  rastro passa a distinguir estagnação real do lead de instabilidade do LLM.

## Requisitos não funcionais

- **RNF7 (novo)** — A mensagem de reenvio enviada ao lead na falha técnica de
  LLM abaixo do limite não expõe detalhe de infraestrutura (provedor,
  timeout, chave, stack). Herda RNF5: nenhum artefato contém PII em texto
  puro.
- Demais RNFs da spec-v1.0.0 seguem válidos; nenhuma dependência nova entra
  (RNF3).

## Notas de implementação (não normativas)

Referência para a sessão de desenvolvimento; a fonte da verdade é a
[[0008-falha-tecnica-llm-categoria-propria]].

- `agent/app/llm.py`: retorno de `extract_and_classify` carrega o sinal de
  falha técnica (ex.: um terceiro valor booleano no retorno, ou um pequeno
  dataclass `Extraction(slots, intent, llm_failed)`); o `except` atual vira o
  caminho `llm_failed=True`, o caminho de sucesso vira `llm_failed=False`.
- `agent/app/models.py`: `ConversationState` ganha `llm_failure_count: int = 0`.
- `agent/data/schema.sql`: `conversation_state` ganha coluna
  `llm_failure_count INTEGER NOT NULL DEFAULT 0`.
- `agent/app/storage.py`: `load_state`/`save_state`/`get_conversation_full`
  passam a ler e gravar `llm_failure_count`.
- `agent/app/config.py`: novo `LLM_FAILURE_LIMIT = int(os.getenv("LLM_FAILURE_LIMIT", "3"))`.
- `agent/app/state_machine.py`: `pre_quote_decision` trata o sinal de falha
  técnica de LLM antes da lógica de estagnação — incrementa o contador
  dedicado, escala com `falha_tecnica_llm` no limite, ou devolve uma nova
  ação (ex.: `reprocessar`) abaixo do limite; sucesso zera o contador.
  `PreDecision` passa a propagar `llm_failure_count`.
- `agent/app/replies.py`: nova mensagem neutra de reenvio para a ação
  intermediária.
- `agent/app/main.py`: liga a nova ação a `_finish`, persistindo
  `llm_failure_count` em todos os `save_state`.

## Critério de sucesso

- Quando a chamada ao LLM falha tecnicamente, o contador de estagnação **não**
  é incrementado; o contador dedicado de falhas técnicas de LLM é.
- Uma falha técnica isolada de LLM não escala: o lead recebe uma mensagem
  neutra de reenvio; a conversa segue em andamento.
- Após N falhas técnicas de LLM consecutivas, a conversa escala com motivo
  `falha_tecnica_llm`, visível e distinto no rastro via
  `GET /conversations/{id}`.
- Uma extração bem-sucedida após falhas técnicas zera o contador de falhas
  técnicas de LLM.
- Nenhuma mensagem ao lead nem artefato persistido expõe detalhe de
  infraestrutura do LLM ou PII em texto puro.
