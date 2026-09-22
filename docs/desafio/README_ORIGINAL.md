# Desafio Técnico — FDE / AI Engineer (Namastex)

Bem-vindo(a)! Este é um teste **take-home** que espelha o trabalho real de um FDE
(Forward Deployed Engineer) na Namastex: subir um **agente de verdade**, conectado a
sistemas que nem sempre colaboram, em cima de **dados bagunçados do mundo real**.

> ⏱️ **Tempo:** ~3 dias de relógio. **Espera-se que você use AI coding tools**
> (Claude Code, Cursor, ChatGPT, etc.) — isso é a régua aqui, não trapaça. A gente quer ver
> você orquestrando IA pra entregar com qualidade e velocidade.
>
> 📎 Por isso mesmo: **as conversas que você teve com as IAs fazem parte da entrega.**
> Veja [Transparência de uso de IA](#transparência-de-uso-de-ia-obrigatório) — é obrigatório.

---

## O cenário

Você é o engenheiro responsável por uma seguradora fictícia, a **AutoSeguro**. O time
de vendas atende leads por **WhatsApp** e fecha seguro de **veículo**. Sua missão é
construir um **agente** que:

1. **Conversa** com o lead, qualifica e **cota um plano** usando a nossa API de cotação.
2. **Decide** quando consegue resolver sozinho e quando precisa **passar pra um humano**.
3. Não trava nem inventa preço quando a infraestrutura falha.

Te entregamos três coisas (tudo neste repo):

| Insumo | Onde | O que é |
|---|---|---|
| **API de cotação** | `quote-service/` | Serviço HTTP `POST /quote` que você sobe local com Docker |
| **Histórico de conversas** | `dataset/conversations.parquet` | ~2.500 conversas reais* lead↔vendedor (*sintéticas, ver dicionário) |
| **Dicionário de dados** | `dataset/DICIONARIO.md` | Esquema do dataset |

---

## Subindo a API de cotação

```bash
docker compose up --build
# API em http://localhost:8000
```

Sem Docker? Dá pra rodar direto:

```bash
cd quote-service && uv run uvicorn app.main:app --port 8000
```

Endpoints:

- `GET  /health` — health check
- `GET  /planos` — tabela de planos **e as regras de cotação** (leia com atenção)
- `POST /quote` — calcula a cotação

Exemplo:

```bash
curl -X POST localhost:8000/quote -H 'content-type: application/json' \
  -d '{"plano_id":"completo","idade":35,"veiculo_ano":2022,"cep":"01310-100","data_inicio":"2026-07-15"}'
```

> ⚠️ **Aviso de operação:** a `/quote` simula um sistema legado real — ela **não responde
> de primeira toda vez** (falhas e lentidão acontecem). Seu agente precisa lidar com isso
> de forma elegante. Tratar bem a instabilidade é parte central do desafio.

---

## O que entregar

1. **Um agente** que atende um lead de ponta a ponta: conversa → qualifica → cota → decide
   (resolve ou encaminha pro humano, com critério claro).
2. **Repositório público no GitHub** com o código.
3. **README** explicando como rodar e **as decisões que você tomou** (e por quê).
4. **Log de uma execução completa** (uma conversa do início ao fim, com a cotação saindo).
5. **As suas conversas com as IAs**, exportadas dentro do repo — ver a seção abaixo.

Você pode usar o dataset de conversas como bem entender (ex.: few-shot, avaliação,
entender padrões de objeção, testar seu agente). Use o que fizer sentido pra sua solução.

---

## Transparência de uso de IA (obrigatório)

A gente **quer** que você use IA — e faz parte da entrega mostrar o processo, não só o
resultado final. Esses logs **entram na avaliação** junto com o código.

**Exporte todas as conversas que você teve com IAs durante o desafio** — ChatGPT,
Claude Code, Cursor, Copilot Chat, Gemini, o que tiver usado — e **inclua no repo**,
numa pasta `ai-logs/`.

Como exportar, por ferramenta:

| Ferramenta | Como |
|---|---|
| **ChatGPT** | Menu da conversa → *Share* (link público) ou *Export*. Cole o link ou salve o arquivo |
| **Claude.ai** | Menu da conversa → *Share* ou *Export* |
| **Claude Code** | As sessões ficam em `~/.claude/projects/<slug-do-projeto>/*.jsonl` — copie os arquivos |
| **Codex CLI** | Sessões em `~/.codex/sessions/` |
| **Cursor / Windsurf** | Exporte ou copie o histórico do painel de chat pra um `.md` |
| **Copilot Chat / outros** | Copie e cole num `.md` mesmo — serve |

Não precisa ser bonito. Um `.jsonl` cru, um `.md` com copy-paste ou uma lista de links
públicos resolve — pode mandar o histórico como ele saiu.

> ⚠️ **Tire os seus segredos antes de commitar** (API keys, tokens, dados pessoais seus).
> Isso vai pra um repo público.

Se a exportação não for viável na sua ferramenta, **avise antes de entregar** — a gente
combina uma sessão de tela compartilhada pra você mostrar o passo a passo, e está tudo certo.

---

## Como a gente vai olhar

Sem pegadinha escondida na avaliação — o que importa:

- **Funciona de ponta a ponta?** O agente cota certo e não quebra no caminho feliz.
- **O que ele faz quando a `/quote` falha?** (esse é o ponto que mais separa.)
- **O critério de passar pro humano é explícito e defensável?**
- **Dá pra rastrear o que aconteceu?** (cada mensagem/cotação, com id e status.)
- **Cuidado com dados sensíveis.** O histórico tem informação pessoal — pense nisso.
- **Qualidade:** outro engenheiro consegue pegar seu código e entender as decisões?
- **Como você usou a IA.** Os `ai-logs/` entram na avaliação junto com o código.

> 💡 Não existe "formato de saída certo" definido de propósito. Queremos ver **a sua decisão** de engenharia.

---

## Entrega

Mande o link do repo público — com o código **e** a pasta `ai-logs/`.
Qualquer dúvida, fale com quem te enviou o desafio.
Quando começar, **avise** — a gente marca a conversa de feedback logo depois da entrega.

Boa! 🚀
