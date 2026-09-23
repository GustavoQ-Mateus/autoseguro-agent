import json
import httpx
from app import llm


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("erro", request=None, response=None)

    def json(self):
        return self._payload


def _tool_call(args):
    return {"choices": [{"message": {"tool_calls": [{"function": {"arguments": json.dumps(args)}}]}}]}


def test_falha_tecnica_de_rede_reporta_llm_failed(monkeypatch):
    def boom(*a, **k):
        raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(llm.httpx, "post", boom)
    extraction = llm.extract_and_classify([], "tenho 35 anos")
    assert extraction.llm_failed is True
    assert extraction.slots == {}
    assert extraction.intent is None


def test_status_nao_2xx_e_falha_tecnica(monkeypatch):
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: _FakeResponse({}, status_code=500))
    extraction = llm.extract_and_classify([], "tenho 35 anos")
    assert extraction.llm_failed is True


def test_extracao_com_dado_nao_e_falha_tecnica(monkeypatch):
    payload = _tool_call({"idade": 35, "intencao": "fornecendo_dado"})
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: _FakeResponse(payload))
    extraction = llm.extract_and_classify([], "tenho 35 anos")
    assert extraction.llm_failed is False
    assert extraction.slots == {"idade": 35}
    assert extraction.intent == "fornecendo_dado"


def test_extracao_vazia_legitima_nao_e_falha_tecnica(monkeypatch):
    payload = _tool_call({"intencao": "duvida_generica"})
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: _FakeResponse(payload))
    extraction = llm.extract_and_classify([], "e caro?")
    assert extraction.llm_failed is False
    assert extraction.slots == {}
    assert extraction.intent == "duvida_generica"
