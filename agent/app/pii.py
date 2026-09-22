from __future__ import annotations
import re

_CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_TELEFONE = re.compile(r"(?:\+55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}")
_PLACA = re.compile(r"\b[A-Za-z]{3}\d[A-Za-z]\d{2}\b|\b[A-Za-z]{3}-?\d{4}\b")

_MASKS = (
    (_CPF, "[CPF]"),
    (_EMAIL, "[EMAIL]"),
    (_PLACA, "[PLACA]"),
    (_TELEFONE, "[TELEFONE]"),
)


def mask_pii(text: str) -> str:
    if not text:
        return text
    masked = text
    for pattern, marker in _MASKS:
        masked = pattern.sub(marker, masked)
    return masked
