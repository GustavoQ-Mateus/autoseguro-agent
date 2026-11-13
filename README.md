# autoseguro-agent

Agente de IA que atende leads de seguro auto num canal de mensagens no formato do WhatsApp. O LLM extrai os dados do lead e classifica a intenção, uma máquina de estados determinística decide a próxima ação, o agente chama o serviço de cotação com timeout e retentativa e passa a conversa para um humano por critérios auditáveis. CPF, e-mail, telefone e placa são mascarados antes de qualquer log, persistência ou chamada ao modelo.

O serviço de cotação é um mock com planos fixos e o dataset de conversas é sintético, gerado por script.

- Regras do projeto e fluxo spec-driven: [CLAUDE.md](CLAUDE.md)
- Specs por versão: `docs/specs/`
- Decisões de arquitetura: `docs/adr/`

## Como rodar

Via Docker Compose (`quote-service` na porta 8000, agente na porta 8001):

```bash
export OPENROUTER_API_KEY=sk-or-...
docker compose up --build
```

Sem Docker:

```bash
cd quote-service && python -m uvicorn app.main:app --port 8000 &
cd agent && OPENROUTER_API_KEY=sk-or-... QUOTE_SERVICE_URL=http://localhost:8000 \
  python -m uvicorn app.main:app --port 8001
```

Testes do agente:

```bash
cd agent && python -m pytest
```

Exemplo de mensagem:

```bash
curl -X POST localhost:8001/webhook/message -H 'content-type: application/json' -d '{
  "conversation_id": "conv_demo",
  "sender_role": "lead",
  "message_body": "Oi, queria fazer um seguro pro meu carro",
  "message_type": "text",
  "timestamp": "2026-09-22T10:00:00"
}'

curl localhost:8001/conversations/conv_demo
```

## Log de execução completa

Conversa real, ponta a ponta, com o agente rodando via Docker Compose e a
OpenRouter, terminando com uma cotação entregue ao lead: [docs/demo/conversa-completa.md](docs/demo/conversa-completa.md).

## Decisões tomadas

O projeto é spec-driven: a fonte da verdade é `docs/specs/spec-v1.1.0.md`, com
cada decisão de arquitetura registrada em `docs/adr/`. Resumo:

- LLM só extrai dados e classifica intenção; a decisão de ação é sempre a
  máquina de estados determinística em `agent/app/state_machine.py`
  ([ADR-0001](docs/adr/0001-llm-orquestracao-tool-use.md)). O transporte hoje é via
  OpenRouter, não a API direta da Anthropic
  ([ADR-0007](docs/adr/0007-provedor-llm-openrouter.md)).
- Canal é um webhook HTTP simulando WhatsApp, sem integração real
  ([ADR-0002](docs/adr/0002-canal-webhook-http.md)).
- `/quote`: timeout de 5s por tentativa, até 3 tentativas só para falha técnica,
  nunca para recusa de negócio ([ADR-0003](docs/adr/0003-resiliencia-quote-service.md)).
- Escalonamento para humano por quatro critérios auditáveis: pedido explícito,
  falha técnica persistente do `/quote`, estagnação após 3 mensagens sem
  extrair um dado obrigatório, ou falha técnica persistente do próprio LLM
  ([ADR-0004](docs/adr/0004-criterio-escalonamento-humano.md)). Falha de LLM é
  contada separada da estagnação do lead, para o motivo registrado não mentir
  sobre a causa real ([ADR-0008](docs/adr/0008-falha-tecnica-llm-categoria-propria.md)).
- Estado e rastro em SQLite local, versionando só o schema
  ([ADR-0005](docs/adr/0005-rastreabilidade-sqlite.md)).
- PII (CPF, e-mail, telefone, placa) nunca é solicitada e é mascarada antes de
  qualquer persistência, log ou chamada ao LLM
  ([ADR-0006](docs/adr/0006-tratamento-dados-sensiveis-pii.md)).

`message_id` é derivado deterministicamente de
`conversation_id + sender_role + message_type + timestamp + corpo mascarado`,
para que o reenvio idêntico do mesmo webhook devolva a mesma resposta já
registrada em vez de reprocessar (RNF2).
