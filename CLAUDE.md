# autoseguro-agent, regras do projeto

Projeto spec-driven. A fonte da verdade é `docs/specs/spec-vX.Y.Z.md` mais as ADRs em `docs/adr/`. Só implemente o que está na spec da fase atual; escopo novo vira nova versão de spec antes de virar código.

Antes de implementar qualquer fase, leia a spec da versão e as ADRs relevantes. Elas não são carregadas automaticamente, só este CLAUDE.md é. Cada ADR trava uma decisão de arquitetura; respeite-a e, se precisar mudar, escreva uma nova ADR registrando o porquê.

## Contexto do projeto
Agente de atendimento e cotação de seguro auto. `quote-service/` é um mock do serviço de cotação, `dataset/` e `scripts/` trazem conversas sintéticas entre lead e vendedor, e o `docker-compose.yml` sobe os dois serviços.

Fluxo de trabalho deste repositório: uma sessão orquestradora escreve specs e ADRs em `docs/`, sem tocar em código de implementação; uma sessão de desenvolvimento separada lê essas specs/ADRs e implementa. As duas sessões commitam e pusham no mesmo repositório, cada uma na sua etapa.

## Código
- Simplicidade proporcional ao problema. Aplique KISS e YAGNI. Não adicione camadas de abstração, padrões de projeto, generalizações ou configurações que a spec da fase não pede. Resolva o problema atual, nunca o hipotético.
- Sem código documentado. Não escreva comentários explicativos nem docstrings. O código se explica por nomes claros de variáveis, funções e tipos. Comentário só em caso raro e genuinamente não óbvio, e curto.
- Idiomático por stack: Python em todo o projeto (FastAPI no `quote-service` e no agente). Siga o estilo já presente no `quote-service`.
- Nada de dependência nova sem necessidade real.
- Nunca use travessão em nada gerado.

## Dados sensíveis
`dataset/conversations.parquet` tem CPF, e-mail, telefone e placa embutidos em texto livre (sintéticos, mas tratados como sensíveis por decisão do projeto). Nenhum desses dados em texto puro pode chegar a logs, exemplos ou artefatos commitados neste repositório público.

## Commits
- Curtos, no padrão Conventional Commits: `tipo(escopo): descrição`.
- Tipos: feat, fix, refactor, test, docs, chore, build, ci.
- Descrição no imperativo, minúscula, sem ponto final, até cerca de 50 caracteres.
- Exemplos: `feat(agent): adiciona endpoint de webhook`, `fix(quote-client): trata timeout com retry`, `docs(adr): registra criterio de escalacao`.
- Um commit por unidade lógica de mudança.
- NUNCA incluir "Co-Authored-By: Claude" nem qualquer referência à Anthropic.
