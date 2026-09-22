from __future__ import annotations
import anthropic
from . import config
from .models import INTENCOES

_TOOL_NAME = "extrair_dados_cotacao"

_TOOL = {
    "name": _TOOL_NAME,
    "description": "Extrai os dados de cotacao de seguro auto e classifica a intencao da mensagem atual do lead.",
    "input_schema": {
        "type": "object",
        "properties": {
            "plano_id": {"type": ["string", "null"], "enum": ["essencial", "completo", "premium", None]},
            "idade": {"type": ["integer", "null"]},
            "veiculo_ano": {"type": ["integer", "null"]},
            "cep": {"type": ["string", "null"]},
            "data_inicio": {"type": ["string", "null"], "description": "formato YYYY-MM-DD"},
            "intencao": {"type": "string", "enum": list(INTENCOES)},
        },
        "required": ["intencao"],
    },
}

_SYSTEM = (
    "Voce extrai dados estruturados de conversas de um lead com uma seguradora de veiculos "
    "e classifica a intencao da ultima mensagem do lead. Use so o que estiver explicito no "
    "historico e na mensagem atual, nunca invente valores. Se um dado nao foi informado, "
    "omita o campo. Idade e ano do veiculo devem ser numeros inteiros."
)

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=config.ANTHROPIC_TIMEOUT_SECONDS)
    return _client


def _build_prompt(history: list[dict], current_message: str) -> str:
    linhas = [f"{m['sender_role']}: {m['body']}" for m in history]
    linhas.append(f"lead: {current_message}")
    return "Historico da conversa:\n" + "\n".join(linhas)


def extract_and_classify(history: list[dict], current_message: str) -> tuple[dict, str | None]:
    try:
        resp = _get_client().messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=300,
            system=_SYSTEM,
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": _TOOL_NAME},
            messages=[{"role": "user", "content": _build_prompt(history, current_message)}],
        )
    except Exception:
        return {}, None

    tool_use = next((b for b in resp.content if b.type == "tool_use"), None)
    if tool_use is None:
        return {}, None

    data = dict(tool_use.input)
    intencao = data.pop("intencao", None)
    slots = {k: v for k, v in data.items() if v is not None}
    return slots, intencao
