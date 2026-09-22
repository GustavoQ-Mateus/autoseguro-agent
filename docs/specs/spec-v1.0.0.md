# Spec v1.0.0 — Agente de atendimento e cotação AutoSeguro

Status: proposta, aguardando revisão.

## Contexto

Desafio técnico de FDE/AI Engineer (ver `docs/desafio/README_ORIGINAL.md`). O
agente atende um lead via canal que simula WhatsApp, qualifica os dados
necessários para cotar um seguro de veículo, chama o `quote-service` (que
simula um sistema legado instável) e decide, de forma determinística, entre
responder com a cotação, pedir mais informação, comunicar uma recusa de
negócio ou escalar para um humano.

Decisões já tomadas, tratadas como restrição desta spec (ver ADRs):

- LLM de orquestração: Claude via tool-use, só para extração de dados e
  classificação de intenção. A decisão de ação é sempre código determinístico
  ([[0001-llm-orquestracao-tool-use]]).
- Canal: webhook HTTP simulando WhatsApp, sem integração real
  ([[0002-canal-webhook-http]]).

## Escopo da fase 1 (v1.0.0)

Entregar o agente de ponta a ponta contra o `quote-service` local: conversa →
qualificação → cotação → decisão (responder, pedir dado, recusar, ou
escalar), com rastreabilidade completa e sem exposição de PII.

### Fora de escopo (não implementar nesta versão)

- Integração real com WhatsApp (Twilio/Meta Business API).
- Autenticação/autorização no webhook.
- Painel administrativo ou UI de qualquer tipo.
- Concorrência/carga em escala, múltiplos workers, filas assíncronas.
- Reengajamento proativo (mensagens enviadas sem o lead ter mandado nada).
- Pipeline de avaliação/fine-tuning usando `dataset/conversations.parquet`
  como treino — o dataset pode ser usado apenas como referência para
  calibrar prompts/exemplos, nunca como dependência de runtime do agente.
- Suporte a múltiplos idiomas.

Qualquer um destes itens, se necessário, vira uma nova versão de spec antes
de virar código.

## Requisitos funcionais

- **RF1** — `POST /webhook/message` recebe uma mensagem inbound simulando
  WhatsApp: `conversation_id`, `sender_role` (`lead`), `message_body`,
  `message_type` (`text`/`image`/`audio`/`document`), `timestamp`.
- **RF2** — Cada mensagem recebida gera um `message_id` único e é persistida
  com status inicial (`recebida`).
- **RF3** — O agente extrai, via LLM (tool-use), os slots necessários para
  cotar: `plano_id` (opcional, default `essencial`), `idade`, `veiculo_ano`
  (a partir do texto livre informado pelo lead), `cep` (opcional),
  `data_inicio` (opcional). A extração é incremental: acumula os slots já
  conhecidos ao longo da conversa, não descarta o que já foi entendido.
- **RF4** — O LLM também classifica a mensagem atual dentro de um conjunto
  fechado de intenções (ex.: `fornecendo_dado`, `pedindo_cotacao`,
  `duvida_generica`, `pedindo_humano`, `outro`). Esse rótulo é só um sinal de
  entrada para a máquina de estados determinística — o LLM nunca decide a
  ação a tomar.
- **RF5** — Se faltar `idade` ou `veiculo_ano` (obrigatórios), o agente
  responde pedindo o dado que falta e não chama `/quote`.
- **RF6** — Com os slots obrigatórios presentes, o agente chama `POST
  /quote` no `quote-service` com os dados coletados.
- **RF7** — Tratamento de instabilidade do `/quote` conforme
  [[0003-resiliencia-quote-service]]: timeout curto por tentativa, retry
  limitado só para falhas técnicas, nunca para recusa de negócio (422) ou
  payload inválido (400). Esgotado o orçamento de tentativas por motivo
  técnico, o agente nunca inventa ou aproxima um valor — comunica
  instabilidade e aciona o critério de escalonamento.
- **RF8** — Critério de escalonamento avaliado a cada mensagem conforme
  [[0004-criterio-escalonamento-humano]]: pedido explícito de humano, falha
  técnica persistente do `/quote`, ou estagnação na coleta de dados após N
  tentativas sem sucesso.
- **RF9** — Toda mensagem recebida, toda tentativa de cotação (sucesso,
  falha técnica, recusa de negócio) e toda decisão de escalonamento é
  registrada com id próprio, timestamp, status e vínculo ao
  `conversation_id`, conforme [[0005-rastreabilidade-sqlite]].
- **RF10** — O agente nunca solicita ativamente CPF, e-mail, telefone ou
  placa. Se o lead enviar esse dado espontaneamente em texto livre, o valor é
  mascarado antes de qualquer persistência ou log, conforme
  [[0006-tratamento-dados-sensiveis-pii]].
- **RF11** — Existe um endpoint de consulta (ex.: `GET
  /conversations/{conversation_id}`) que expõe o estado e o histórico de
  eventos de uma conversa, para inspeção e para produzir o "log de uma
  execução completa" exigido pelo desafio.

## Requisitos não funcionais

- **RNF1** — Nenhuma chamada ao `/quote` bloqueia a resposta do webhook
  indefinidamente: timeout de cliente obrigatório, menor que o pior caso de
  lentidão simulada (8s).
- **RNF2** — Reprocessar a mesma mensagem (mesmo `message_id`, reenvio
  duplicado do webhook) não deve gerar efeitos colaterais duplicados
  (nova cotação disparada, resposta duplicada).
- **RNF3** — Sem dependências novas além do necessário: cliente HTTP e SDK
  Anthropic são as adições esperadas; persistência via `sqlite3` da stdlib.
- **RNF4** — Persistência local em arquivo, sem exigir infraestrutura
  externa (sem Redis/Postgres) — proporcional ao escopo de um desafio de 3
  dias rodado localmente via `docker-compose`.
- **RNF5** — Nenhum artefato gerado pela aplicação (logs, respostas
  persistidas, banco local) contém PII em texto puro.
- **RNF6** — Código Python idiomático, FastAPI, sem comentários
  explicativos nem docstrings, seguindo o estilo já presente em
  `quote-service/`.

## Critério de sucesso

- Caminho feliz: uma conversa simulada via webhook, do primeiro contato até a
  entrega da cotação, funciona de ponta a ponta contra o `quote-service`
  local.
- Caminho de falha: quando `/quote` falha ou demora além do orçamento de
  retry, o agente não trava, não inventa preço, e escalona segundo o
  critério documentado em [[0004-criterio-escalonamento-humano]].
- Toda mensagem e toda tentativa de cotação de uma conversa de demonstração
  são rastreáveis (id + status) via `GET /conversations/{id}`.
- Nenhum CPF, e-mail, telefone ou placa em texto puro aparece em qualquer
  artefato do repositório (código, dados persistidos, exemplos, `ai-logs/`).
