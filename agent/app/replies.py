from __future__ import annotations

_CAMPO_LABEL = {
    "idade": "sua idade",
    "veiculo_ano": "o ano do seu veículo",
}

ESCALONADA = (
    "Vou te transferir para um consultor humano, que continua seu atendimento a partir daqui."
)

INSTABILIDADE_ESCALONADA = (
    "Nosso sistema de cotação está instável no momento e não consegui gerar sua cotação. "
    "Vou te transferir para um consultor humano para continuar seu atendimento."
)

REPROCESSAR = (
    "Não consegui processar sua última mensagem agora. Pode reenviar essa informação, por favor?"
)


def ask_missing(missing: list[str]) -> str:
    campos = " e ".join(_CAMPO_LABEL.get(f, f) for f in missing)
    return f"Pra te passar uma cotação, preciso que me informe {campos}."


def quote_success(data: dict) -> str:
    coberturas = ", ".join(data.get("coberturas", []))
    linhas = [
        f"Sua cotação no plano {data['plano_nome']} ficou em R$ {data['premio_mensal']:.2f}/mês.",
        f"Franquia: R$ {data['franquia']}. Coberturas: {coberturas}.",
    ]
    pro_rata = data.get("primeiro_pagamento_pro_rata")
    if pro_rata:
        linhas.append(f"Primeiro pagamento proporcional: R$ {pro_rata['valor_primeiro_pagamento']:.2f}.")
    return " ".join(linhas)


def quote_refusal(motivo: str | None) -> str:
    base = motivo or "Não consegui aprovar essa cotação com os dados informados."
    return f"{base} Posso te transferir para um consultor humano revisar seu caso, se quiser."
