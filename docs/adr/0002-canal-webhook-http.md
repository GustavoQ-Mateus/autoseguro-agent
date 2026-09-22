# ADR-0002: Canal via webhook HTTP simulando WhatsApp

Status: aceita.

## Contexto

O cenário do desafio é atendimento por WhatsApp, mas já está decidido que não
haverá integração real com nenhuma API de mensageria (Twilio, Meta Business
API) — isso não é o que o desafio avalia.

## Decisão

O agente expõe `POST /webhook/message`, recebendo um payload que simula uma
mensagem inbound de WhatsApp: `conversation_id`, `sender_role`,
`message_body`, `message_type`, `timestamp`. A resposta do agente ao lead é
devolvida de forma síncrona no corpo da resposta HTTP desse mesmo POST, sem
chamar nenhuma API externa de mensageria.

## Alternativas consideradas

- **Integração real com Twilio/Meta WhatsApp Business API**: rejeitada,
  exigiria conta e credenciais externas e não é avaliada pelo desafio.
- **CLI/REPL interativo**: rejeitada. Um webhook HTTP é mais fiel ao formato
  real de integração de mensageria e permite reproduzir facilmente, via
  `curl` ou script, o "log de uma execução completa" exigido na entrega.

## Consequências

- A resposta ao lead é sempre o retorno síncrono do POST — simplifica a
  demo, mas deixa fora do escopo v1.0.0 qualquer envio assíncrono/proativo
  (ex.: reengajar o lead depois de X horas de silêncio).
- O formato de payload de entrada/saída do webhook não segue um padrão
  externo (Twilio/Meta) — é definido e documentado nesta spec
  ([[spec-v1.0.0]], RF1).
