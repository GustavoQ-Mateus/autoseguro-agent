import httpx
from app import quote_client


class _FakeResponse:
    def __init__(self, status_code, json_body):
        self.status_code = status_code
        self._json_body = json_body

    def json(self):
        return self._json_body


def test_sucesso_na_primeira_tentativa(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append(json)
        return _FakeResponse(200, {"premio_mensal": 100})

    monkeypatch.setattr(httpx, "post", fake_post)
    result = quote_client.call_quote({"idade": 35, "veiculo_ano": 2019, "plano_id": "essencial"})

    assert result.status == "sucesso"
    assert len(calls) == 1
    assert len(result.attempts) == 1


def test_retry_em_falha_tecnica_depois_sucesso(monkeypatch):
    respostas = [_FakeResponse(503, {}), _FakeResponse(200, {"premio_mensal": 100})]

    def fake_post(url, json, timeout):
        return respostas.pop(0)

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(quote_client.config, "QUOTE_BACKOFF_SECONDS", 0)
    result = quote_client.call_quote({"idade": 35, "veiculo_ano": 2019, "plano_id": "essencial"})

    assert result.status == "sucesso"
    assert len(result.attempts) == 2
    assert result.attempts[0].status == "falha_tecnica"
    assert result.attempts[1].status == "sucesso"


def test_esgota_tentativas_e_reporta_falha_tecnica(monkeypatch):
    def fake_post(url, json, timeout):
        return _FakeResponse(500, {})

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(quote_client.config, "QUOTE_BACKOFF_SECONDS", 0)
    result = quote_client.call_quote({"idade": 35, "veiculo_ano": 2019, "plano_id": "essencial"})

    assert result.status == "falha_tecnica"
    assert len(result.attempts) == quote_client.config.QUOTE_MAX_ATTEMPTS


def test_recusa_de_negocio_nao_tenta_de_novo(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append(1)
        return _FakeResponse(422, {"motivo": "Idade acima do limite de aceitacao."})

    monkeypatch.setattr(httpx, "post", fake_post)
    result = quote_client.call_quote({"idade": 90, "veiculo_ano": 2019, "plano_id": "essencial"})

    assert result.status == "recusada"
    assert result.motivo == "Idade acima do limite de aceitacao."
    assert len(calls) == 1


def test_payload_invalido_nao_tenta_de_novo(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append(1)
        return _FakeResponse(400, {"detalhe": "campo invalido"})

    monkeypatch.setattr(httpx, "post", fake_post)
    result = quote_client.call_quote({"idade": 35, "veiculo_ano": 2019, "plano_id": "essencial"})

    assert result.status == "recusada"
    assert len(calls) == 1


def test_timeout_esgota_orcamento(monkeypatch):
    def fake_post(url, json, timeout):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(quote_client.config, "QUOTE_BACKOFF_SECONDS", 0)
    result = quote_client.call_quote({"idade": 35, "veiculo_ano": 2019, "plano_id": "essencial"})

    assert result.status == "falha_tecnica"
    assert result.motivo == "timeout"
    assert len(result.attempts) == quote_client.config.QUOTE_MAX_ATTEMPTS
