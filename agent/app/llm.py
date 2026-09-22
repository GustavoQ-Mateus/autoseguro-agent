from __future__ import annotations
import json
import httpx
from . import config
from .models import INTENCOES

_TOOL_NAME = "extrair_dados_cotacao"

_TOOL = {
    "type": "function",
    "function": {
        "name": _TOOL_NAME,
        "description": "Extrai os dados de cotacao de seguro auto e classifica a intencao da mensagem atual do lead.",
        "parameters": {
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
    },
}

_SYSTEM = (
    "Voce extrai dados estruturados de conversas de um lead com uma seguradora de veiculos "
    "e classifica a intencao da ultima mensagem do lead. Use so o que estiver explicito no "
    "historico e na mensagem atual, nunca invente valores. Se um dado nao foi informado, "
    "omita o campo. Idade e ano do veiculo devem ser numeros inteiros."
)

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def _build_prompt(history: list[dict], current_message: str) -> str:
    linhas = [f"{m['sender_role']}: {m['body']}" for m in history]
    linhas.append(f"lead: {current_message}")
    return "Historico da conversa:\n" + "\n".join(linhas)


def extract_and_classify(history: list[dict], current_message: str) -> tuple[dict, str | None]:
    try:
        resp = httpx.post(
            _OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": _build_prompt(history, current_message)},
                ],
                "tools": [_TOOL],
                "tool_choice": {"type": "function", "function": {"name": _TOOL_NAME}},
            },
            timeout=config.OPENROUTER_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        tool_calls = resp.json()["choices"][0]["message"]["tool_calls"]
        data = json.loads(tool_calls[0]["function"]["arguments"])
    except Exception:
        return {}, None

    intencao = data.pop("intencao", None)
    slots = {k: v for k, v in data.items() if v is not None}
    return slots, intencao
