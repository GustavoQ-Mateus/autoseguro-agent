from __future__ import annotations
from dataclasses import dataclass, field
from . import config
from .models import ConversationState, QuoteResult, REQUIRED_SLOTS, SLOT_FIELDS


def merge_slots(known: dict, delta: dict) -> dict:
    merged = dict(known)
    for field_name in SLOT_FIELDS:
        if delta.get(field_name) is not None:
            merged[field_name] = delta[field_name]
    return merged


def missing_required(slots: dict) -> list[str]:
    return [f for f in REQUIRED_SLOTS if not slots.get(f)]


@dataclass
class PreDecision:
    action: str
    slots: dict
    stagnation_count: int
    motivo: str | None = None
    missing: list[str] = field(default_factory=list)


def pre_quote_decision(state: ConversationState, intent: str | None, slots_delta: dict) -> PreDecision:
    new_slots = merge_slots(state.slots, slots_delta)

    if intent == "pedindo_humano":
        return PreDecision(action="escalar", slots=new_slots, stagnation_count=state.stagnation_count,
                            motivo="pedido_explicito")

    missing_before = missing_required(state.slots)
    missing_after = missing_required(new_slots)

    if not missing_after:
        return PreDecision(action="cotar", slots=new_slots, stagnation_count=0)

    progress = len(missing_after) < len(missing_before)
    stagnation_count = 0 if progress else state.stagnation_count + 1

    if stagnation_count >= config.STAGNATION_LIMIT:
        return PreDecision(action="escalar", slots=new_slots, stagnation_count=stagnation_count,
                            motivo="estagnacao_coleta", missing=missing_after)

    return PreDecision(action="pedir_dado", slots=new_slots, stagnation_count=stagnation_count, missing=missing_after)


@dataclass
class PostDecision:
    action: str
    motivo: str | None = None


def post_quote_decision(result: QuoteResult) -> PostDecision:
    if result.status == "sucesso":
        return PostDecision(action="responder_cotacao")
    if result.status == "recusada":
        return PostDecision(action="responder_recusa", motivo=result.motivo)
    return PostDecision(action="escalar", motivo="falha_tecnica_persistente")


def build_quote_payload(slots: dict) -> dict:
    payload = {
        "plano_id": slots.get("plano_id") or "essencial",
        "idade": slots["idade"],
        "veiculo_ano": slots["veiculo_ano"],
    }
    if slots.get("cep"):
        payload["cep"] = slots["cep"]
    if slots.get("data_inicio"):
        payload["data_inicio"] = slots["data_inicio"]
    return payload
