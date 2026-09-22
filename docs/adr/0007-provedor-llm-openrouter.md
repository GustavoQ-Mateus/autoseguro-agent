# ADR-0007: Provedor de LLM passa de Anthropic direto para OpenRouter

Status: aceita.

## Contexto

A [[0001-llm-orquestracao-tool-use]] decidiu usar Claude via a API direta da
Anthropic para extração de dados e classificação de intenção, com a API
sendo chamada pelo SDK `anthropic` (`agent/app/llm.py`, `agent/app/config.py`,
dependência `anthropic>=0.40` em `agent/pyproject.toml`).

O que mudou: o usuário já tem crédito de API disponível na OpenRouter, e não
na Anthropic diretamente. Isso é uma restrição prática de custo/acesso, não
uma reavaliação da decisão de arquitetura em si — o contrato definido pela
ADR-0001 (LLM só extrai dado e classifica intenção; a decisão de ação
continua sempre na máquina de estados determinística em
`agent/app/state_machine.py`) não muda.

## Decisão

O acesso ao LLM passa a ser feito via OpenRouter (`https://openrouter.ai/api/v1`,
API REST compatível com o formato de chat completions da OpenAI, incluindo
function calling), mantendo o mesmo modelo Claude usado até aqui — agora
roteado pela OpenRouter como `anthropic/claude-sonnet-5`.

- O papel do LLM na arquitetura não muda: só extrai `plano_id`, `idade`,
  `veiculo_ano`, `cep`, `data_inicio` e classifica a intenção da mensagem
  atual. Nenhuma decisão de ação migra para o LLM.
- A chamada é feita via `httpx` (dependência já existente no projeto, usada
  para chamar o `quote-service`), contra o endpoint de chat completions da
  OpenRouter — sem adicionar um SDK novo.
- O formato de tool/function-calling muda do estilo nativo da Anthropic
  (`tools: [{name, description, input_schema}]`,
  `tool_choice: {type: "tool", name}`, resposta em `content[].type ==
  "tool_use"`) para o formato compatível com OpenAI que a OpenRouter espera
  (`tools: [{type: "function", function: {name, description, parameters}}]`,
  `tool_choice: {type: "function", function: {name}}`, resposta em
  `choices[0].message.tool_calls[].function.arguments`, uma string JSON).
- O slug exato do modelo (`anthropic/claude-sonnet-5`) deve ser conferido no
  catálogo de modelos da OpenRouter no momento da implementação, já que
  provedores às vezes versionam o nome do slug de forma diferente do nome
  comercial do modelo.

## Alternativas consideradas

- **Manter Anthropic direto**: rejeitada. O usuário não tem crédito
  disponível nesse provedor agora; é uma restrição prática, não uma
  reavaliação de qualidade do modelo.
- **Adicionar o SDK `openai` (compatível com a OpenRouter) em vez de usar
  `httpx` cru**: rejeitada. A API da OpenRouter é uma REST simples
  compatível com OpenAI; usar o `httpx` que já é dependência do projeto
  evita uma dependência nova sem necessidade real (regra do projeto).
- **Trocar também de modelo para algo mais barato (ex.: `gpt-4o-mini`,
  `gemini-2.0-flash`), já que o provedor está mudando mesmo**: rejeitada por
  ora. O usuário optou por manter a família Claude (Sonnet 5) via
  OpenRouter, priorizando a qualidade de extração já validada sobre o custo
  mínimo. Pode ser revisitado numa ADR futura se o custo por chamada virar
  um problema real.

## Consequências

- Variáveis de ambiente mudam: `ANTHROPIC_API_KEY` → `OPENROUTER_API_KEY`,
  `ANTHROPIC_MODEL` → `OPENROUTER_MODEL` (default `anthropic/claude-sonnet-5`),
  `ANTHROPIC_TIMEOUT_SECONDS` → `OPENROUTER_TIMEOUT_SECONDS` (mantém default
  de 15s).
- A dependência `anthropic` sai de `agent/pyproject.toml`; nenhuma
  dependência nova entra no lugar.
- `agent/app/llm.py` é reescrito para montar a request HTTP no formato
  OpenAI-compatible e fazer o parsing da resposta nesse novo formato, mas a
  assinatura pública `extract_and_classify(history, current_message) ->
  tuple[dict, str | None]` não muda — quem chama essa função
  (`agent/app/state_machine.py` ou equivalente) não precisa mudar.
- Testes que mockam o client Anthropic precisam ser reescritos para mockar a
  chamada HTTP/resposta da OpenRouter.
- `docker-compose.yml` e `README.md` precisam trocar as variáveis de
  ambiente documentadas de Anthropic para OpenRouter.
- A ADR-0001 permanece válida como registro histórico da decisão original
  (LLM só extrai/classifica) e não é editada; esta ADR só substitui o
  provedor e o transporte usados para cumprir aquele contrato.
