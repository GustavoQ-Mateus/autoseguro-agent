from __future__ import annotations
import sqlite3, json, uuid, datetime as dt
from contextlib import contextmanager
from . import config
from .models import ConversationState, AttemptLog


def init_db() -> None:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(config.SCHEMA_PATH.read_text(encoding="utf-8"))


@contextmanager
def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def get_message(message_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, response_body FROM messages WHERE id = ?", (message_id,)
        ).fetchone()
    if row is None or row[1] is None:
        return None
    return {"message_id": row[0], "reply": row[1]}


def save_message(message_id: str, conversation_id: str, sender_role: str,
                  message_type: str, body: str, timestamp: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO messages "
            "(id, conversation_id, sender_role, message_type, body, timestamp, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'recebida', ?)",
            (message_id, conversation_id, sender_role, message_type, body, timestamp, _now()),
        )


def save_response(message_id: str, reply: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE messages SET response_body = ?, status = 'processada' WHERE id = ?",
            (reply, message_id),
        )


def recent_messages(conversation_id: str, limit: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT sender_role, body, timestamp FROM messages "
            "WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
    return [{"sender_role": r[0], "body": r[1], "timestamp": r[2]} for r in reversed(rows)]


def load_state(conversation_id: str) -> ConversationState:
    with _connect() as conn:
        row = conn.execute(
            "SELECT slots, stagnation_count, status, llm_failure_count FROM conversation_state WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
    if row is None:
        return ConversationState(conversation_id=conversation_id)
    return ConversationState(
        conversation_id=conversation_id,
        slots=json.loads(row[0]),
        stagnation_count=row[1],
        status=row[2],
        llm_failure_count=row[3],
    )


def save_state(state: ConversationState) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversation_state (conversation_id, slots, stagnation_count, llm_failure_count, status, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(conversation_id) DO UPDATE SET "
            "slots = excluded.slots, stagnation_count = excluded.stagnation_count, "
            "llm_failure_count = excluded.llm_failure_count, "
            "status = excluded.status, updated_at = excluded.updated_at",
            (state.conversation_id, json.dumps(state.slots), state.stagnation_count,
             state.llm_failure_count, state.status, _now()),
        )


def log_quote_attempt(conversation_id: str, payload: dict, attempt: AttemptLog) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO quote_attempts "
            "(id, conversation_id, timestamp, payload, status, motivo, http_status, latencia_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), conversation_id, _now(), json.dumps(payload),
             attempt.status, attempt.motivo, attempt.http_status, attempt.latencia_ms),
        )


def log_escalation(conversation_id: str, motivo: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO escalations (id, conversation_id, timestamp, motivo) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), conversation_id, _now(), motivo),
        )


def get_conversation_full(conversation_id: str) -> dict | None:
    with _connect() as conn:
        state_row = conn.execute(
            "SELECT slots, stagnation_count, status, llm_failure_count FROM conversation_state WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        if state_row is None:
            return None
        messages = conn.execute(
            "SELECT id, sender_role, message_type, body, response_body, timestamp, status "
            "FROM messages WHERE conversation_id = ? ORDER BY created_at",
            (conversation_id,),
        ).fetchall()
        attempts = conn.execute(
            "SELECT id, timestamp, payload, status, motivo, http_status, latencia_ms "
            "FROM quote_attempts WHERE conversation_id = ? ORDER BY timestamp",
            (conversation_id,),
        ).fetchall()
        escalations = conn.execute(
            "SELECT id, timestamp, motivo FROM escalations WHERE conversation_id = ? ORDER BY timestamp",
            (conversation_id,),
        ).fetchall()

    return {
        "conversation_id": conversation_id,
        "status": state_row[2],
        "slots": json.loads(state_row[0]),
        "stagnation_count": state_row[1],
        "llm_failure_count": state_row[3],
        "messages": [
            {
                "message_id": m[0], "sender_role": m[1], "message_type": m[2],
                "body": m[3], "response_body": m[4], "timestamp": m[5], "status": m[6],
            }
            for m in messages
        ],
        "quote_attempts": [
            {
                "id": a[0], "timestamp": a[1], "payload": json.loads(a[2]), "status": a[3],
                "motivo": a[4], "http_status": a[5], "latencia_ms": a[6],
            }
            for a in attempts
        ],
        "escalations": [
            {"id": e[0], "timestamp": e[1], "motivo": e[2]} for e in escalations
        ],
    }
