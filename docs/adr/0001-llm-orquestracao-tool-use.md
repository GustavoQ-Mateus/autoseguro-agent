# ADR-0001: Claude via tool-use só para extração/classificação, decisão de ação é código determinístico

Status: aceita.

## Contexto

O agente precisa extrair dados estruturados (idade, ano do veículo, plano,
CEP, data de início) de mensagens em português, texto livre e heterogêneo, e
entender a intenção do lead a cada mensagem. Ao mesmo tempo, o desafio exige
um "critério explícito e defensável" para as decisões-chave (quando cotar,
quando escalar) — ou seja, decisões auditáveis e testáveis, não uma
caixa-preta de modelo de linguagem.

Já está decidido usar Claude (Anthropic API) como o LLM de orquestração.

## Decisão

Claude é usado exclusivamente via tool-use/saída estruturada para duas
funções:

1. Extrair da mensagem (e do histórico) os slots de cotação:
   `plano_id`, `idade`, `veiculo_ano`, `cep`, `data_inicio`.
2. Classificar a mensagem atual dentro de um conjunto fechado de intenções
   (`fornecendo_dado`, `pedindo_cotacao`, `duvida_generica`, `pedindo_humano`,
   `outro`).

A decisão de qual ação tomar (pedir dado faltante, chamar `/quote`, responder
com a cotação, comunicar recusa, escalar) é sempre feita por uma máquina de
estados determinística em código Python, que consome a extração/classificação
do LLM como entrada — nunca como decisão final.

## Alternativas consideradas

- **LLM decide a ação diretamente** (loop agentic com tools de "responder",
  "cotar", "escalar"): rejeitada. Escalonamento e cotação precisam ser
  auditáveis e reprodutíveis, não sujeitos à variação de amostragem do
  modelo entre execuções.
- **Modelo local/open-source para extração**: rejeitada, fora do escopo já
  decidido (Claude via Anthropic API); extração de português não estruturado
  se beneficia de um modelo forte via tool-use.
- **Regras de regex/NLU leve sem LLM**: rejeitada. O texto do dataset é
  heterogêneo demais ("tenho 35 anos", "sou de 92", "meu carro é um Onix
  2019") para regex robusto cobrir com confiabilidade.

## Consequências

- Toda decisão de negócio é testável com testes unitários determinísticos,
  sem precisar mockar o LLM para validar a lógica de escalonamento/cotação.
- Extração vazia ou campo ausente na resposta do LLM é tratada pela máquina
  de estados como "dado não coletado ainda" — nunca derruba o fluxo.
- A chamada ao LLM tem custo e latência próprios; falha ou timeout do LLM é
  tratada pela mesma lógica de estagnação de coleta de dados (ver
  [[0004-criterio-escalonamento-humano]]), não como um caso especial à parte.
