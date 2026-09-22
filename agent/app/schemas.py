from __future__ import annotations
from typing import Literal
from pydantic import BaseModel


class WebhookMessageIn(BaseModel):
    conversation_id: str
    sender_role: Literal["lead"]
    message_body: str
    message_type: Literal["text", "image", "audio", "document"]
    timestamp: str


class WebhookMessageOut(BaseModel):
    message_id: str
    reply: str
