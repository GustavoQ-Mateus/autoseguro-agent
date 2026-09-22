# ADR-0006: Tratamento de dados sensíveis (PII)

Status: aceita.

## Contexto

`dataset/conversations.parquet` tem CPF, e-mail, telefone e placa embutidos
em texto livre (sintéticos, mas tratados como sensíveis por exigência do
desafio). As mensagens reais recebidas pelo webhook em runtime podem conter
os mesmos tipos de dado, espontaneamente digitados pelo lead. O repositório
é público — nenhum desses dados pode chegar em texto puro a logs, exemplos
ou artefatos commitados.

## Decisão

- **Não coletar o que não precisa**: o schema de extração usado pelo LLM
  ([[0001-llm-orquestracao-tool-use]]) só define os campos que o `/quote`
  de fato exige — `plano_id`, `idade`, `veiculo_ano`, `cep`, `data_inicio`.
  O agente nunca pergunta ativamente CPF, e-mail, telefone ou placa.
- **Mascarar o que não dá pra evitar receber**: antes de qualquer
  persistência ([[0005-rastreabilidade-sqlite]]) ou log, todo `message_body`
  passa por uma função de mascaramento por regex que substitui por
  marcadores (`[CPF]`, `[EMAIL]`, `[TELEFONE]`, `[PLACA]`) os padrões:
  - CPF: `\d{3}\.\d{3}\.\d{3}-\d{2}`
  - e-mail: padrão usual `usuario@dominio`
  - telefone: `+55 \d{2} 9?\d{4}-\d{4}` e variações sem separador
  - placa: padrão antigo (`[A-Z]{3}\d{4}`) e Mercosul (`[A-Z]{3}\d[A-Z]\d{2}`)
- Se `dataset/conversations.parquet` for usado para calibrar prompts ou
  montar exemplos, qualquer trecho salvo em arquivo versionado passa pela
  mesma função de mascaramento antes de tocar disco. Nenhum script de
  exploração deve escrever amostras cruas do dataset em arquivo commitado.
- `ai-logs/` e qualquer log de execução incluído no repositório são
  revisados antes do commit final para garantir ausência de PII em texto
  puro — responsabilidade humana de quem commita, não só da função de
  mascaramento.

## Alternativas consideradas

- **Confiar que o LLM "não repete" PII nas respostas**: rejeitada, não é uma
  garantia técnica, é comportamento probabilístico do modelo.
- **Tokenização/criptografia reversível de PII**: rejeitada, desproporcional
  ao escopo — o agente nunca precisa recuperar o valor original desses
  campos para cotar.
- **Bloquear a mensagem inteira quando PII for detectado**: rejeitada,
  quebraria a conversa; mascarar preserva o contexto conversacional sem
  expor o dado.

## Consequências

- A função de mascaramento é testável isoladamente com os formatos gerados
  por `scripts/generate_dataset.py` (CPF, e-mail, telefone, placa).
- Reduzir a coleta na origem (não perguntar o que não precisa) é mais
  robusto do que só mascarar depois — há menos PII circulando no sistema
  desde o início.
- Mascaramento por regex cobre os formatos conhecidos do dataset e do
  gerador, mas não é infalível para todo formato imaginável — risco residual
  aceito e documentado.
