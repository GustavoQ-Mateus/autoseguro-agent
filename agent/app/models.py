from __future__ import annotations
from dataclasses import dataclass, field

REQUIRED_SLOTS = ("idade", "veiculo_ano")
SLOT_FIELDS = ("plano_id", "idade", "veiculo_ano", "cep", "data_inicio")

INTENCOES = (
    "fornecendo_dado",
    "pedindo_cotacao",
    "duvida_generica",
    "pedindo_humano",
    "outro",
)


@dataclass
class ConversationState:
    conversation_id: str
    slots: dict = field(default_factory=dict)
    stagnation_count: int = 0
    status: str = "em_andamento"
    llm_failure_count: int = 0


@dataclass
class AttemptLog:
    status: str
    http_status: int | None
    motivo: str | None
    latencia_ms: int


@dataclass
class QuoteResult:
    status: str
    data: dict | None = None
    motivo: str | None = None
    attempts: list[AttemptLog] = field(default_factory=list)
