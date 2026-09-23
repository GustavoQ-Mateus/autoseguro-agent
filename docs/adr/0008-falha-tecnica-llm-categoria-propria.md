# ADR-0008: Falha técnica do LLM como categoria própria de escalonamento

Status: aceita.

## Contexto

`extract_and_classify` (`agent/app/llm.py`) envolve a chamada ao LLM via
OpenRouter ([[0007-provedor-llm-openrouter]]) num `try/except` amplo. Quando a
chamada falha por qualquer motivo técnico (timeout, erro de rede, 5xx da
OpenRouter, chave inválida, resposta em formato inesperado), o `except`
devolve `({}, None)` — os mesmos valores que uma chamada bem-sucedida
produziria quando o lead simplesmente não informou nenhum dado útil.

A máquina de estados (`agent/app/state_machine.py`, `pre_quote_decision`) não
tem como distinguir os dois casos: recebe `intent=None` e `slots_delta={}`,
conclui que não houve progresso na qualificação e incrementa
`stagnation_count`. Depois de N=3 mensagens assim, escala com motivo
`estagnacao_coleta` ([[0004-criterio-escalonamento-humano]]). O motivo
registrado no rastro passa a mentir: a conversa pode ter sido escalada porque
a OpenRouter esteve fora do ar, não porque o lead ignorou as perguntas.

Isso é a mesma classe de instabilidade de infraestrutura que a
[[0003-resiliencia-quote-service]] trata com cuidado para o `quote-service` —
falha técnica é uma categoria distinta de resposta de negócio e não pode ser
mascarada dentro de outra métrica. Para o LLM essa distinção não existia; a
falha ficava escondida dentro do contador de estagnação.

## Decisão

Falha técnica da chamada ao LLM passa a ser uma categoria própria, separada
de "resposta válida sem dado extraído", tanto na extração quanto no
escalonamento.

### Reporte na extração

`extract_and_classify` deixa de sinalizar falha com o mesmo valor que uma
extração vazia legítima. Ela passa a distinguir explicitamente:

- **Falha técnica de infra** — a chamada HTTP à OpenRouter levantou exceção,
  retornou status não-2xx, ou a resposta não pôde ser parseada como um
  tool call válido. É exatamente o que hoje cai no `except`.
- **Resposta válida sem dado** — a chamada teve sucesso, o modelo respondeu
  com o tool call, mas nenhum slot foi extraído e/ou a intenção classificada
  não trouxe dado obrigatório novo. Continua sendo tratada como falta de
  progresso na coleta (alimenta `stagnation_count`, como hoje).

O sinal de falha técnica é carregado de forma explícita para o chamador (um
valor dedicado no retorno, não um `None` sobrecarregado). O `try/except`
envolve apenas o trecho de rede/parsing: se o parsing tiver sucesso, mesmo
com slots vazios, isso **não** é falha técnica.

Rejeitado sinalizar a falha reaproveitando o campo de intenção (ex.: uma
intenção sentinel `erro_tecnico_llm`): a intenção é um conjunto fechado de
rótulos de negócio ([[0001-llm-orquestracao-tool-use]]); misturar um sinal de
infraestrutura nesse conjunto contamina esse contrato e obriga todo consumidor
da intenção a conhecer o caso especial.

### Reação da máquina de estados

Adapta-se o mesmo raciocínio da [[0004-criterio-escalonamento-humano]] para
estagnação: um contador dedicado de falhas técnicas **consecutivas** do LLM,
separado de `stagnation_count`, avaliado a cada mensagem.

- A cada mensagem em que a extração reporta falha técnica do LLM, o contador
  de falhas técnicas de LLM é incrementado; `stagnation_count` **não** é
  tocado, e os slots conhecidos **não** mudam (não houve delta confiável).
- Uma extração bem-sucedida (mesmo sem dado novo) **zera** o contador de
  falhas técnicas de LLM — é um contador de falhas consecutivas, igual ao de
  estagnação.
- Enquanto o contador estiver abaixo do limite, o agente não escala: responde
  ao lead com uma mensagem neutra pedindo que reenvie a informação, sem expor
  detalhe de infraestrutura, e mantém o estado da conversa em andamento.
- Ao atingir o limite de N falhas técnicas de LLM consecutivas, o agente
  escala para humano com motivo próprio **`falha_tecnica_llm`**, distinto de
  `estagnacao_coleta`, `pedido_explicito` e `falha_tecnica_persistente`.

O limite é um parâmetro explícito e próprio (`LLM_FAILURE_LIMIT`, default 3),
independente de `STAGNATION_LIMIT`. Mantém-se 3 por consistência e por ser
defensável pela mesma razão da [[0004-criterio-escalonamento-humano]]: uma
falha isolada é transiente e não deve escalar, mas uma indisponibilidade
persistente do LLM cega o agente por completo e precisa de humano. O valor
pode ser ajustado sem mudar a arquitetura.

Não se adiciona retry inline dentro de `extract_and_classify` (ao contrário do
`quote-service`, que tem retry síncrono na mesma mensagem). Ver alternativas.

## Alternativas consideradas

- **Sinalizar a falha com uma intenção sentinel (`erro_tecnico_llm`)**:
  rejeitada. Polui o conjunto fechado de intenções de negócio da
  [[0001-llm-orquestracao-tool-use]] e força todo consumidor da intenção a
  tratar um caso de infraestrutura. Um valor de retorno dedicado é mais
  honesto e localizado.
- **Levantar exceção e tratar no `main.py`**: rejeitada. A decisão sobre a
  falha é graduada (contar, escalar depois de N) e pertence à máquina de
  estados determinística; carregá-la como dado no retorno flui naturalmente
  por `pre_quote_decision`, coerente com o modo como `QuoteResult` já carrega
  as tentativas para a decisão pós-cotação.
- **Contar falha técnica de LLM dentro do mesmo `stagnation_count`**:
  rejeitada — é exatamente o defeito que esta ADR corrige. O rastro precisa
  dizer, depois do fato, se a conversa escalou por estagnação real do lead ou
  por instabilidade do LLM.
- **Escalar na primeira falha técnica de LLM**: rejeitada, mesma lógica da
  [[0004-criterio-escalonamento-humano]] para o `/quote`: uma falha isolada é
  transiente e escalar de imediato geraria escalonamento excessivo.
- **Adicionar retry inline (backoff) na chamada ao LLM, espelhando a
  [[0003-resiliencia-quote-service]]**: rejeitada por ora. O retry inline do
  `/quote` se justifica por uma taxa de falha simulada de ~20% e por bloquear
  a única resposta que o lead aguarda naquele instante. O contador
  entre-mensagens é a adaptação mais simples e simétrica do critério de
  estagnação, não adiciona latência nem complexidade a `llm.py`, e o timeout
  de cliente já limita o pior caso por chamada. Pode ser revisitado numa ADR
  futura se a taxa real de falha do LLM justificar.

## Consequências

- Escopo novo além da spec v1.0.0: sobe para `docs/specs/spec-v1.1.0.md`
  antes de qualquer código, conforme a regra do projeto.
- `extract_and_classify` muda a forma do retorno para carregar o sinal de
  falha técnica. Isso supera o ponto específico da
  [[0007-provedor-llm-openrouter]] que previa a assinatura pública
  `tuple[dict, str | None]` estável; aquela ADR permanece válida quanto ao
  provedor e ao transporte, só a forma do retorno evolui aqui.
- `ConversationState` ganha um contador dedicado de falhas técnicas de LLM,
  persistido junto do estado da conversa ([[0005-rastreabilidade-sqlite]]);
  `conversation_state` ganha a coluna correspondente no schema.
- Surge um quarto motivo de escalonamento auditável, `falha_tecnica_llm`, no
  rastro de escalações — o critério continua 100% auditável: cada
  escalonamento diz qual condição o acionou.
- O agente ganha uma ação intermediária (pedir reenvio) para falha técnica de
  LLM abaixo do limite, sem vazar detalhe de infraestrutura ao lead.
- A [[0004-criterio-escalonamento-humano]] passa a ter uma quarta condição de
  escalonamento; esta ADR a estende, não a substitui.
