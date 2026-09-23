from __future__ import annotations

_CAMPO_LABEL = {
    "idade": "sua idade",
    "veiculo_ano": "o ano do seu veiculo",
}

ESCALONADA = (
    "Vou te transferir para um consultor humano, que continua seu atendimento a partir daqui."
)

INSTABILIDADE_ESCALONADA = (
    "Nosso sistema de cotacao esta instavel no momento e nao consegui gerar sua cotacao. "
    "Vou te transferir para um consultor humano para continuar seu atendimento."
)

REPROCESSAR = (
    "Nao consegui processar sua ultima mensagem agora. Pode reenviar essa informacao, por favor?"
)


def ask_missing(missing: list[str]) -> str:
    campos = " e ".join(_CAMPO_LABEL.get(f, f) for f in missing)
    return f"Pra te passar uma cotacao, preciso que me informe {campos}."


def quote_success(data: dict) -> str:
    coberturas = ", ".join(data.get("coberturas", []))
    linhas = [
        f"Sua cotacao no plano {data['plano_nome']} ficou em R$ {data['premio_mensal']:.2f}/mes.",
        f"Franquia: R$ {data['franquia']}. Coberturas: {coberturas}.",
    ]
    pro_rata = data.get("primeiro_pagamento_pro_rata")
    if pro_rata:
        linhas.append(f"Primeiro pagamento proporcional: R$ {pro_rata['valor_primeiro_pagamento']:.2f}.")
    return " ".join(linhas)


def quote_refusal(motivo: str | None) -> str:
    base = motivo or "Nao consegui aprovar essa cotacao com os dados informados."
    return f"{base} Posso te transferir para um consultor humano revisar seu caso, se quiser."
