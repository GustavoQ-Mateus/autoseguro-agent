from __future__ import annotations
import hashlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from . import config, storage, llm, quote_client, state_machine, replies
from .models import ConversationState
from .pii import mask_pii
from .schemas import WebhookMessageIn, WebhookMessageOut


@asynccontextmanager
async def _lifespan(app: FastAPI):
    storage.init_db()
    yield


app = FastAPI(title="AutoSeguro Agent", version="1.0.0", lifespan=_lifespan)


def _build_message_id(msg: WebhookMessageIn, masked_body: str) -> str:
    raw = f"{msg.conversation_id}|{msg.sender_role}|{msg.message_type}|{msg.timestamp}|{masked_body}"
    return "msg_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _finish(message_id: str, reply: str) -> WebhookMessageOut:
    masked_reply = mask_pii(reply)
    storage.save_response(message_id, masked_reply)
    return WebhookMessageOut(message_id=message_id, reply=masked_reply)


@app.post("/webhook/message", response_model=WebhookMessageOut)
def webhook_message(msg: WebhookMessageIn) -> WebhookMessageOut:
    masked_body = mask_pii(msg.message_body)
    message_id = _build_message_id(msg, masked_body)

    cached = storage.get_message(message_id)
    if cached:
        return WebhookMessageOut(**cached)

    storage.save_message(message_id, msg.conversation_id, msg.sender_role,
                          msg.message_type, masked_body, msg.timestamp)

    state = storage.load_state(msg.conversation_id)

    if state.status == "escalonada":
        return _finish(message_id, replies.ESCALONADA)

    history = storage.recent_messages(msg.conversation_id, config.HISTORY_LIMIT)
    slots_delta, intent = llm.extract_and_classify(history, masked_body)

    decision = state_machine.pre_quote_decision(state, intent, slots_delta)

    if decision.action == "escalar":
        storage.log_escalation(msg.conversation_id, decision.motivo)
        storage.save_state(ConversationState(msg.conversation_id, decision.slots, decision.stagnation_count, "escalonada"))
        return _finish(message_id, replies.ESCALONADA)

    if decision.action == "pedir_dado":
        storage.save_state(ConversationState(msg.conversation_id, decision.slots, decision.stagnation_count, "em_andamento"))
        return _finish(message_id, replies.ask_missing(decision.missing))

    payload = state_machine.build_quote_payload(decision.slots)
    result = quote_client.call_quote(payload)
    for attempt in result.attempts:
        storage.log_quote_attempt(msg.conversation_id, payload, attempt)

    post = state_machine.post_quote_decision(result)

    if post.action == "responder_cotacao":
        storage.save_state(ConversationState(msg.conversation_id, decision.slots, 0, "cotado"))
        return _finish(message_id, replies.quote_success(result.data))

    if post.action == "responder_recusa":
        storage.save_state(ConversationState(msg.conversation_id, decision.slots, 0, "recusado"))
        return _finish(message_id, replies.quote_refusal(result.motivo))

    storage.log_escalation(msg.conversation_id, post.motivo)
    storage.save_state(ConversationState(msg.conversation_id, decision.slots, 0, "escalonada"))
    return _finish(message_id, replies.INSTABILIDADE_ESCALONADA)


@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str) -> dict:
    data = storage.get_conversation_full(conversation_id)
    if data is None:
        raise HTTPException(status_code=404, detail="conversa_nao_encontrada")
    return data
