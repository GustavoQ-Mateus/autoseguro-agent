"""Logica de cotacao. Le plans.json e aplica as regras (faixa etaria, idade do
veiculo, regiao, carencia, pro-rata de entrada no meio do mes)."""
from __future__ import annotations
import json, datetime as dt
from pathlib import Path
from calendar import monthrange

_PLANS_PATH = Path(__file__).resolve().parent.parent / "data" / "plans.json"


def load_plans() -> dict:
    return json.loads(_PLANS_PATH.read_text(encoding="utf-8"))


class CotacaoRecusada(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


def _faixa_etaria_mult(regras: dict, idade: int) -> float:
    for f in regras["faixa_etaria"]:
        if f["idade_min"] <= idade <= f["idade_max"]:
            if f.get("recusar"):
                raise CotacaoRecusada(f["motivo"])
            return f["multiplicador"]
    raise CotacaoRecusada("Idade fora das faixas aceitas.")


def _idade_veiculo_mult(regras: dict, ano_veiculo: int, hoje: dt.date) -> float:
    anos = hoje.year - ano_veiculo
    for f in regras["idade_veiculo"]:
        if f["anos_min"] <= anos <= f["anos_max"]:
            if f.get("recusar"):
                raise CotacaoRecusada(f["motivo"])
            return f["multiplicador"]
    raise CotacaoRecusada("Idade do veiculo fora das faixas aceitas.")


def _regiao_mult(regras: dict, cep: str | None) -> float:
    if not cep:
        return 1.0
    pref = cep.replace("-", "").strip()[:2]
    r = regras["regiao_cep"]
    return r["multiplicador"] if pref in r["prefixos_alto_risco"] else 1.0


def _pro_rata_primeiro_mes(base_mensal: float, inicio: dt.date) -> dict:
    """Primeiro mes proporcional aos dias restantes (inclui o dia de inicio)."""
    dias_mes = monthrange(inicio.year, inicio.month)[1]
    dias_restantes = dias_mes - inicio.day + 1
    valor = round(base_mensal * dias_restantes / dias_mes, 2)
    return {"dias_no_mes": dias_mes, "dias_cobrados": dias_restantes, "valor_primeiro_pagamento": valor}


def cotar(payload: dict) -> dict:
    """Recebe dados do lead/veiculo e devolve a cotacao calculada.
    Campos esperados: plano_id, idade (int), veiculo_ano (int),
    cep (str, opcional), data_inicio (YYYY-MM-DD, opcional)."""
    plans = load_plans()
    regras = plans["regras"]
    hoje = dt.date.today()

    plano_id = (payload.get("plano_id") or "essencial").lower()
    plano = next((p for p in plans["planos"] if p["id"] == plano_id), None)
    if plano is None:
        raise CotacaoRecusada(f"Plano '{plano_id}' inexistente. Opcoes: "
                              + ", ".join(p["id"] for p in plans["planos"]))

    idade = int(payload["idade"])
    ano = int(payload["veiculo_ano"])
    cep = payload.get("cep")

    m_idade = _faixa_etaria_mult(regras, idade)
    m_veic = _idade_veiculo_mult(regras, ano, hoje)
    m_regiao = _regiao_mult(regras, cep)

    premio = round(plano["base_mensal"] * m_idade * m_veic * m_regiao, 2)

    car = regras["carencia"]
    resp = {
        "plano_id": plano["id"],
        "plano_nome": plano["nome"],
        "premio_mensal": premio,
        "franquia": plano["franquia"],
        "coberturas": plano["coberturas"],
        "multiplicadores": {"faixa_etaria": m_idade, "idade_veiculo": m_veic, "regiao": m_regiao},
        "carencia": {
            "coberturas": [c for c in plano["coberturas"] if c in car["coberturas_com_carencia"]],
            "dias": car["dias"],
            "observacao": car["_obs"],
        },
        "moeda": plans["moeda"],
    }

    di = payload.get("data_inicio")
    if di:
        inicio = dt.date.fromisoformat(di)
        if inicio.day != 1:
            resp["primeiro_pagamento_pro_rata"] = _pro_rata_primeiro_mes(premio, inicio)
    return resp
