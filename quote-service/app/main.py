"""
Servico de cotacao de seguro auto (mock) para o desafio FDE.

POST /quote  -> calcula uma cotacao a partir dos dados do lead/veiculo.
GET  /health -> health check (sempre estavel).
GET  /planos -> tabela de planos e regras (consulta).

Observacao de operacao: este servico simula um sistema legado real. Ele NEM SEMPRE
responde de primeira -- parte das chamadas falha ou demora. Trate isso no seu agente.
A taxa e a latencia sao configuraveis por variavel de ambiente:
    QUOTE_FAILURE_RATE   (default 0.20)  -> fracao de chamadas que falham
    QUOTE_SLOW_RATE      (default 0.10)  -> fracao de chamadas lentas
    QUOTE_SLOW_SECONDS   (default 8)     -> duracao da chamada lenta (simula timeout)
    QUOTE_SEED           (opcional)      -> fixa o gerador p/ falhas reproduziveis
"""
from __future__ import annotations
import os, time, random
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from .quote_logic import cotar, load_plans, CotacaoRecusada

FAILURE_RATE = float(os.getenv("QUOTE_FAILURE_RATE", "0.20"))
SLOW_RATE = float(os.getenv("QUOTE_SLOW_RATE", "0.10"))
SLOW_SECONDS = float(os.getenv("QUOTE_SLOW_SECONDS", "8"))
_seed = os.getenv("QUOTE_SEED")
_rng = random.Random(int(_seed)) if _seed else random.Random()

app = FastAPI(title="AutoSeguro Quote API (mock)", version="1.0.0")


class QuoteRequest(BaseModel):
    plano_id: str = Field("essencial", description="essencial | completo | premium")
    idade: int = Field(..., ge=0, le=200)
    veiculo_ano: int = Field(..., ge=1950, le=2100)
    cep: str | None = None
    data_inicio: str | None = Field(None, description="YYYY-MM-DD (opcional)")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/planos")
def planos():
    return load_plans()


@app.post("/quote")
def quote(req: QuoteRequest):
    # --- instabilidade simulada (de proposito) ---
    roll = _rng.random()
    if roll < FAILURE_RATE:
        kind = _rng.choice(["500", "502", "503"])
        return JSONResponse(status_code=int(kind),
                            content={"error": "upstream_unavailable",
                                     "message": "Servico de cotacao temporariamente indisponivel. Tente novamente."})
    if roll < FAILURE_RATE + SLOW_RATE:
        time.sleep(SLOW_SECONDS)  # simula timeout / lentidao

    # --- cotacao ---
    try:
        return cotar(req.model_dump())
    except CotacaoRecusada as e:
        return JSONResponse(status_code=422, content={"error": "cotacao_recusada", "motivo": e.motivo})
    except (KeyError, ValueError, TypeError) as e:
        return JSONResponse(status_code=400, content={"error": "payload_invalido", "detalhe": str(e)})
