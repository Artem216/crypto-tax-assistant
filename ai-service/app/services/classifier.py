from __future__ import annotations

import json
from app.clients.groq_client import GroqClient
from app.prompts.classify import SYSTEM_CLASSIFY, build_classify_prompt

# Известные адреса DEX — алгоритмически, без ИИ
DEX_ADDRESSES = {
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2",
    "0xe592427a0aece92de3edee1f18e0157c05861564": "Uniswap V3",
    "0x1111111254eeb25477b68fb85ed929f73a960582": "1inch V5",
    "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": "SushiSwap",
}


def classify_algorithmically(tx: dict, wallet_address: str) -> dict | None:
    """Простые случаи без ИИ."""
    to = (tx.get("to_address") or "").lower()
    from_ = (tx.get("from_address") or "").lower()
    wallet = wallet_address.lower()
    value = tx.get("value_wei", "0")

    # Нулевая транзакция — скорее всего вызов контракта
    if value == "0" and to not in DEX_ADDRESSES:
        return None  # отдаём ИИ

    # Известный DEX
    if to in DEX_ADDRESSES:
        return {
            "tx_hash": tx["tx_hash"],
            "category": "DEX_SWAP",
            "confidence": 1.0,
            "reasoning": f"Взаимодействие с {DEX_ADDRESSES[to]}",
        }

    # Входящий от себя или исходящий себе — самоперевод
    if from_ == wallet and to == wallet:
        return {
            "tx_hash": tx["tx_hash"],
            "category": "SELF_TRANSFER",
            "confidence": 1.0,
            "reasoning": "Перевод между адресами одного владельца",
        }

    return None  # не определили — идёт в ИИ


class TransactionClassifier:
    def __init__(self, groq_client: GroqClient):
        self._groq = groq_client

    def classify_one(self, tx: dict, wallet_address: str) -> dict:
        # Базовые поля которые всегда сохраняем
        base = {
            "tx_hash": tx.get("tx_hash"),
            "eth_amount": tx.get("eth_amount", 0),
            "value_usd": tx.get("value_usd", 0),
            "value_rub": tx.get("value_rub", 0),
            "fee_rub": tx.get("fee_rub", 0),
        }

        # Сначала пробуем алгоритмически
        result = classify_algorithmically(tx, wallet_address)
        if result:
            return {**base, **result}

        # Иначе — ИИ
        tx_with_wallet = {**tx, "wallet_address": wallet_address}
        raw = self._groq.complete(
            system=SYSTEM_CLASSIFY,
            user=build_classify_prompt(tx_with_wallet),
        )

        try:
            return {**base, **json.loads(raw)}
        except json.JSONDecodeError:
            cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
            try:
                return {**base, **json.loads(cleaned)}
            except json.JSONDecodeError:
                return {
                    **base,
                    "tx_hash": tx["tx_hash"],
                    "category": "UNKNOWN",
                    "confidence": 0.0,
                    "reasoning": "Не удалось распознать ответ модели",
                }

    def classify_many(self, transactions: list[dict], wallet_address: str) -> list[dict]:
        return [self.classify_one(tx, wallet_address) for tx in transactions]