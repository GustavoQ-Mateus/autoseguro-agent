# Log de execucao completa

Conversa real, ponta a ponta, capturada via `POST /webhook/message` contra o
agente rodando localmente (`docker compose up --build`), terminando com uma
cotacao entregue pelo lead. `conversation_id`: `conv_demo_completo`.

## Passo 1: mensagem inicial pedindo cotacao (sem dados ainda)

Request:

```bash
curl -X POST localhost:8001/webhook/message -H 'content-type: application/json' -d '{
  "conversation_id": "conv_demo_completo",
  "sender_role": "lead",
  "message_body": "Oi, tudo bem? Queria fazer uma cotacao de seguro pro meu carro",
  "message_type": "text",
  "timestamp": "2026-09-22T10:00:00"
}'
```

Response:

```json
{
  "message_id": "msg_871a80b9375c3a0f1c2d61aeb099b391",
  "reply": "Pra te passar uma cotacao, preciso que me informe sua idade e o ano do seu veiculo."
}
```

## Passo 2: lead fornece os dados faltantes em texto livre

Request:

```bash
curl -X POST localhost:8001/webhook/message -H 'content-type: application/json' -d '{
  "conversation_id": "conv_demo_completo",
  "sender_role": "lead",
  "message_body": "Claro! Tenho 32 anos e meu carro e um Onix 2020",
  "message_type": "text",
  "timestamp": "2026-09-22T10:01:00"
}'
```

Response:

```json
{
  "message_id": "msg_ff08aa9876396b0b9eee18cf040431a2",
  "reply": "Sua cotacao no plano Essencial ficou em R$ 137.88/mes. Franquia: R$ 4500. Coberturas: colisao, roubo, furto."
}
```

## Passo 3: estado final da conversa

Request:

```bash
curl localhost:8001/conversations/conv_demo_completo
```

Response:

```json
{
  "conversation_id": "conv_demo_completo",
  "status": "cotado",
  "slots": {
    "idade": 32,
    "veiculo_ano": 2020
  },
  "stagnation_count": 0,
  "messages": [
    {
      "message_id": "msg_871a80b9375c3a0f1c2d61aeb099b391",
      "sender_role": "lead",
      "message_type": "text",
      "body": "Oi, tudo bem? Queria fazer uma cotacao de seguro pro meu carro",
      "response_body": "Pra te passar uma cotacao, preciso que me informe sua idade e o ano do seu veiculo.",
      "timestamp": "2026-09-22T10:00:00",
      "status": "processada"
    },
    {
      "message_id": "msg_ff08aa9876396b0b9eee18cf040431a2",
      "sender_role": "lead",
      "message_type": "text",
      "body": "Claro! Tenho 32 anos e meu carro e um Onix 2020",
      "response_body": "Sua cotacao no plano Essencial ficou em R$ 137.88/mes. Franquia: R$ 4500. Coberturas: colisao, roubo, furto.",
      "timestamp": "2026-09-22T10:01:00",
      "status": "processada"
    }
  ],
  "quote_attempts": [
    {
      "id": "5c9be846-e823-454a-9e4a-f41664b18b69",
      "timestamp": "2026-09-22T19:28:26.779682+00:00",
      "payload": {
        "plano_id": "essencial",
        "idade": 32,
        "veiculo_ano": 2020
      },
      "status": "falha_tecnica",
      "motivo": "upstream_unavailable",
      "http_status": 500,
      "latencia_ms": 22
    },
    {
      "id": "04fe0700-989d-4c25-85b2-c2da3e958ea5",
      "timestamp": "2026-09-22T19:28:26.814013+00:00",
      "payload": {
        "plano_id": "essencial",
        "idade": 32,
        "veiculo_ano": 2020
      },
      "status": "sucesso",
      "motivo": null,
      "http_status": 200,
      "latencia_ms": 10
    }
  ],
  "escalations": []
}
```
