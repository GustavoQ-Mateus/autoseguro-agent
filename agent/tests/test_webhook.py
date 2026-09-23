import pytest
from fastapi.testclient import TestClient
from app import config, llm, quote_client
from app.llm import Extraction
from app.main import app
from app.models import QuoteResult, AttemptLog


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "agent.db")
    with TestClient(app) as c:
        yield c


def _msg(conversation_id, body, timestamp="2026-01-01T10:00:00"):
    return {
        "conversation_id": conversation_id,
        "sender_role": "lead",
        "message_body": body,
        "message_type": "text",
        "timestamp": timestamp,
    }


def test_pede_dado_faltante_quando_incompleto(client, monkeypatch):
    monkeypatch.setattr(llm, "extract_and_classify",
                         lambda h, m: Extraction(slots={"idade": 35}, intent="fornecendo_dado"))
    resp = client.post("/webhook/message", json=_msg("conv_x", "tenho 35 anos"))
    assert resp.status_code == 200
    assert "veículo" in resp.json()["reply"].lower()


def test_fluxo_completo_ate_cotacao(client, monkeypatch):
    monkeypatch.setattr(llm, "extract_and_classify",
                         lambda h, m: Extraction(slots={"idade": 35, "veiculo_ano": 2019}, intent="fornecendo_dado"))
    monkeypatch.setattr(quote_client, "call_quote", lambda payload: QuoteResult(
        status="sucesso",
        data={"plano_nome": "Essencial", "premio_mensal": 119.9, "franquia": 4500, "coberturas": ["colisao"]},
        attempts=[AttemptLog(status="sucesso", http_status=200, motivo=None, latencia_ms=50)],
    ))

    resp = client.post("/webhook/message", json=_msg("conv_y", "tenho 35 anos, meu carro e um onix 2019"))
    assert resp.status_code == 200
    assert "119.9" in resp.json()["reply"]

    view = client.get("/conversations/conv_y").json()
    assert view["status"] == "cotado"
    assert len(view["quote_attempts"]) == 1


def test_falha_tecnica_persistente_escala(client, monkeypatch):
    monkeypatch.setattr(llm, "extract_and_classify",
                         lambda h, m: Extraction(slots={"idade": 35, "veiculo_ano": 2019}, intent="fornecendo_dado"))
    monkeypatch.setattr(quote_client, "call_quote", lambda payload: QuoteResult(
        status="falha_tecnica", motivo="timeout",
        attempts=[AttemptLog(status="falha_tecnica", http_status=None, motivo="timeout", latencia_ms=5000)] * 3,
    ))

    resp = client.post("/webhook/message", json=_msg("conv_z", "tenho 35 anos, meu carro e um onix 2019"))
    assert "instável" in resp.json()["reply"].lower()

    view = client.get("/conversations/conv_z").json()
    assert view["status"] == "escalonada"
    assert view["escalations"][0]["motivo"] == "falha_tecnica_persistente"


def test_falha_tecnica_isolada_de_llm_pede_reenvio_sem_escalar(client, monkeypatch):
    monkeypatch.setattr(llm, "extract_and_classify", lambda h, m: Extraction(llm_failed=True))
    resp = client.post("/webhook/message", json=_msg("conv_f", "tenho 35 anos"))

    reply = resp.json()["reply"].lower()
    assert "reenviar" in reply
    assert "timeout" not in reply and "provedor" not in reply and "instavel" not in reply

    view = client.get("/conversations/conv_f").json()
    assert view["status"] == "em_andamento"
    assert view["llm_failure_count"] == 1
    assert view["escalations"] == []


def test_falhas_tecnicas_de_llm_consecutivas_escalam(client, monkeypatch):
    monkeypatch.setattr(llm, "extract_and_classify", lambda h, m: Extraction(llm_failed=True))
    for i in range(config.LLM_FAILURE_LIMIT):
        client.post("/webhook/message", json=_msg("conv_g", "oi", timestamp=f"2026-01-01T10:0{i}:00"))

    view = client.get("/conversations/conv_g").json()
    assert view["status"] == "escalonada"
    assert view["llm_failure_count"] == config.LLM_FAILURE_LIMIT
    assert view["escalations"][0]["motivo"] == "falha_tecnica_llm"


def test_extracao_com_sucesso_zera_falha_tecnica_de_llm(client, monkeypatch):
    monkeypatch.setattr(llm, "extract_and_classify", lambda h, m: Extraction(llm_failed=True))
    client.post("/webhook/message", json=_msg("conv_r", "oi", timestamp="2026-01-01T10:00:00"))

    monkeypatch.setattr(llm, "extract_and_classify",
                        lambda h, m: Extraction(slots={"idade": 35}, intent="fornecendo_dado"))
    client.post("/webhook/message", json=_msg("conv_r", "tenho 35 anos", timestamp="2026-01-01T10:01:00"))

    view = client.get("/conversations/conv_r").json()
    assert view["llm_failure_count"] == 0
    assert view["status"] == "em_andamento"


def test_pedido_explicito_de_humano_escala(client, monkeypatch):
    monkeypatch.setattr(llm, "extract_and_classify", lambda h, m: Extraction(intent="pedindo_humano"))
    resp = client.post("/webhook/message", json=_msg("conv_h", "quero falar com um atendente humano"))
    assert "consultor humano" in resp.json()["reply"].lower()
    view = client.get("/conversations/conv_h").json()
    assert view["status"] == "escalonada"
    assert view["escalations"][0]["motivo"] == "pedido_explicito"


def test_reenvio_da_mesma_mensagem_e_idempotente(client, monkeypatch):
    calls = {"n": 0}

    def fake_extract(h, m):
        calls["n"] += 1
        return Extraction(slots={"idade": 35}, intent="fornecendo_dado")

    monkeypatch.setattr(llm, "extract_and_classify", fake_extract)
    payload = _msg("conv_dup", "tenho 35 anos")

    first = client.post("/webhook/message", json=payload)
    second = client.post("/webhook/message", json=payload)

    assert first.json() == second.json()
    assert calls["n"] == 1


def test_conversa_escalonada_nao_processa_mais(client, monkeypatch):
    monkeypatch.setattr(llm, "extract_and_classify", lambda h, m: Extraction(intent="pedindo_humano"))
    client.post("/webhook/message", json=_msg("conv_e", "quero um humano"))

    calls = {"n": 0}

    def fake_extract(h, m):
        calls["n"] += 1
        return Extraction(slots={"idade": 35, "veiculo_ano": 2019}, intent="fornecendo_dado")

    monkeypatch.setattr(llm, "extract_and_classify", fake_extract)
    resp = client.post("/webhook/message", json=_msg("conv_e", "tenho 35 anos, onix 2019", timestamp="2026-01-01T10:05:00"))

    assert calls["n"] == 0
    assert "consultor humano" in resp.json()["reply"].lower()


def test_mensagem_sem_dados_pii_em_texto_puro(client, monkeypatch):
    monkeypatch.setattr(llm, "extract_and_classify", lambda h, m: Extraction(intent="fornecendo_dado"))
    body = "meu cpf e 389.083.863-43 e meu email e ana@gmail.com"
    client.post("/webhook/message", json=_msg("conv_pii", body))

    view = client.get("/conversations/conv_pii").json()
    stored_body = view["messages"][0]["body"]
    assert "389.083.863-43" not in stored_body
    assert "ana@gmail.com" not in stored_body
