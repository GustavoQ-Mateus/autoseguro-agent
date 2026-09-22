# ADR-0004: Critério de escalonamento para humano

Status: aceita.

## Contexto

O desafio exige um critério "explícito e defensável" de quando o agente
passa a conversa para um humano em vez de resolver sozinho. O critério
precisa ser auditável (dá pra dizer, depois do fato, exatamente por que uma
conversa foi escalonada) e não depender de sinais subjetivos.

## Decisão

O agente escalona para humano quando qualquer uma destas condições,
avaliadas deterministicamente a cada mensagem, for verdadeira:

1. **Pedido explícito do lead por atendimento humano** — a mensagem é
   classificada pelo LLM como intenção `pedindo_humano`
   ([[0001-llm-orquestracao-tool-use]]).
2. **Falha técnica persistente do `/quote`** — todas as tentativas dentro do
   orçamento de retry ([[0003-resiliencia-quote-service]]) falharam por
   motivo técnico (timeout ou 5xx) para a cotação em andamento.
3. **Estagnação na coleta de dados** — após N=3 mensagens consecutivas do
   lead sem que o agente consiga extrair o dado obrigatório que ainda falta
   (`idade` ou `veiculo_ano`), o agente para de insistir e escalona.

**Recusa de negócio não escalona automaticamente.** Quando `/quote` retorna
`422 cotacao_recusada` (ex.: idade ou veículo fora da política de aceitação),
essa é uma resposta determinística e válida — o motivo já vem pronto da
regra de negócio. O agente comunica o motivo ao lead e oferece a opção de
falar com um humano; só escalona de fato se o lead responder afirmativamente
(o que cai na condição 1).

Ao escalonar, o agente marca a conversa com status `escalonada` no rastro
([[0005-rastreabilidade-sqlite]]), registrando qual das três condições foi
acionada, envia uma mensagem padrão avisando que um consultor humano vai
continuar o atendimento, e para de agir automaticamente naquela conversa.

## Alternativas consideradas

- **Escalonar também em toda recusa de negócio**: rejeitada. Infla o volume
  de escalonamento para casos que o agente já responde corretamente e de
  forma clara — a regra de recusa é determinística, não precisa de humano.
- **Usar confiança/sentimento do LLM como sinal contínuo de escalonamento**:
  rejeitada. Adiciona uma superfície subjetiva e não determinística a um
  critério que precisa ser auditável; contadores e categorias fechadas são
  mais defensáveis.
- **Escalonar após 1 única falha técnica do `/quote`**: rejeitada. Uma falha
  isolada é esperada dado que a taxa de falha simulada é de 20%; escalonar
  na primeira falha geraria uma taxa de escalonamento alta demais para o
  agente ser útil (perto de 1 em cada 5 tentativas de cotação).

## Consequências

- Critério 100% auditável: cada escalonamento no rastro carrega qual das
  três condições foi acionada.
- N=3 é um parâmetro explícito e documentado, ajustável sem mudar a
  arquitetura.
- Recusa de negócio bem tratada evita escalonamentos desnecessários, mas
  ainda dá ao lead um caminho para insistir com um humano se quiser.
