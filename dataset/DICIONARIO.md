# Dicionário de dados — `conversations.parquet`

> ⚠️ **Dados 100% sintéticos.** Conversas, nomes, CPF, e-mails, telefones, placas e CEPs
> foram **gerados proceduralmente** (`scripts/generate_dataset.py`). Os formatos são
> plausíveis, mas **nenhum dado é de pessoa real**. Ainda assim, trate-os como se fossem
> sensíveis — é parte do desafio.

Cada **linha = uma mensagem**. Conversas se reconstroem agrupando por `conversation_id`
e ordenando por `message_index`.

| Coluna | Tipo | Descrição |
|---|---|---|
| `conversation_id` | string | Identificador da conversa (`conv_00001`, ...) |
| `message_index` | int | Ordem da mensagem dentro da conversa (0 = primeira) |
| `timestamp` | string (ISO 8601) | Horário da mensagem |
| `sender_role` | string | `lead` ou `vendedor` |
| `sender_name` | string | Nome exibido do remetente |
| `message_type` | string | `text`, `image`, `audio` ou `document` |
| `message_body` | string | Conteúdo. Para mídia, vem um marcador (ex.: `[documento] CNH_frente.pdf`) |
| `channel` | string | Sempre `whatsapp` |
| `conversation_outcome` | string | Desfecho: `ganho`, `perdido`, `em_negociacao`, `sem_resposta` |
| `lead_idade_informada` | int | Idade que o lead informou (quando aplicável) |
| `veiculo_texto` | string | Marca/modelo/ano em texto livre, como o lead falou |

## Notas

- O conteúdo das mensagens é **não estruturado** — dados como CPF, e-mail, telefone e placa
  aparecem soltos no meio do texto, em formatos variados.
- Algumas mensagens são de **mídia** (`image`/`audio`/`document`): não há transcrição, só o marcador.
- `veiculo_texto` é texto livre ("e um Sandero 2022", "Toyota Corolla, ano 2008") — não vem normalizado.
- Regenerar (reprodutível): `uv run scripts/generate_dataset.py --n 2500 --seed 42`.
