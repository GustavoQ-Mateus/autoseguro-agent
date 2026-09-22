from __future__ import annotations
import time
import httpx
from . import config
from .models import AttemptLog, QuoteResult

_TECHNICAL_STATUS = (500, 502, 503)


def call_quote(payload: dict) -> QuoteResult:
    attempts: list[AttemptLog] = []

    for attempt_number in range(1, config.QUOTE_MAX_ATTEMPTS + 1):
        start = time.monotonic()
        try:
            response = httpx.post(
                f"{config.QUOTE_SERVICE_URL}/quote",
                json=payload,
                timeout=config.QUOTE_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException:
            latencia_ms = int((time.monotonic() - start) * 1000)
            attempts.append(AttemptLog(status="falha_tecnica", http_status=None, motivo="timeout", latencia_ms=latencia_ms))
            if attempt_number < config.QUOTE_MAX_ATTEMPTS:
                time.sleep(config.QUOTE_BACKOFF_SECONDS)
                continue
            return QuoteResult(status="falha_tecnica", motivo="timeout", attempts=attempts)
        except httpx.HTTPError:
            latencia_ms = int((time.monotonic() - start) * 1000)
            attempts.append(AttemptLog(status="falha_tecnica", http_status=None, motivo="erro_conexao", latencia_ms=latencia_ms))
            if attempt_number < config.QUOTE_MAX_ATTEMPTS:
                time.sleep(config.QUOTE_BACKOFF_SECONDS)
                continue
            return QuoteResult(status="falha_tecnica", motivo="erro_conexao", attempts=attempts)

        latencia_ms = int((time.monotonic() - start) * 1000)

        if response.status_code == 200:
            attempts.append(AttemptLog(status="sucesso", http_status=200, motivo=None, latencia_ms=latencia_ms))
            return QuoteResult(status="sucesso", data=response.json(), attempts=attempts)

        if response.status_code == 422:
            motivo = response.json().get("motivo", "cotacao_recusada")
            attempts.append(AttemptLog(status="recusada", http_status=422, motivo=motivo, latencia_ms=latencia_ms))
            return QuoteResult(status="recusada", motivo=motivo, attempts=attempts)

        if response.status_code == 400:
            motivo = response.json().get("detalhe", "payload_invalido")
            attempts.append(AttemptLog(status="recusada", http_status=400, motivo=motivo, latencia_ms=latencia_ms))
            return QuoteResult(status="recusada", motivo=motivo, attempts=attempts)

        if response.status_code in _TECHNICAL_STATUS:
            attempts.append(AttemptLog(status="falha_tecnica", http_status=response.status_code, motivo="upstream_unavailable", latencia_ms=latencia_ms))
            if attempt_number < config.QUOTE_MAX_ATTEMPTS:
                time.sleep(config.QUOTE_BACKOFF_SECONDS)
                continue
            return QuoteResult(status="falha_tecnica", motivo="upstream_unavailable", attempts=attempts)

        attempts.append(AttemptLog(status="falha_tecnica", http_status=response.status_code, motivo="resposta_inesperada", latencia_ms=latencia_ms))
        return QuoteResult(status="falha_tecnica", motivo="resposta_inesperada", attempts=attempts)

    return QuoteResult(status="falha_tecnica", motivo="orcamento_esgotado", attempts=attempts)
