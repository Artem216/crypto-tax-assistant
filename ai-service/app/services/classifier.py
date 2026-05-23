from __future__ import annotations

import json
from app.clients.groq_client import GroqClient
from app.prompts.classify import SYSTEM_CLASSIFY, build_classify_prompt


# (категория, название)
KNOWN_ADDRESSES = {
    # DEX
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": ("DEX_SWAP", "Uniswap V2"),
    "0xe592427a0aece92de3edee1f18e0157c05861564": ("DEX_SWAP", "Uniswap V3"),
    "0x1111111254eeb25477b68fb85ed929f73a960582": ("DEX_SWAP", "1inch V5"),
    "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f": ("DEX_SWAP", "SushiSwap"),
    "0xdef1c0ded9bec7f1a1670819833240f027b25eff": ("DEX_SWAP", "0x Protocol"),
    # Централизованные биржи
    "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be": ("SALE", "Binance"),
    "0xd551234ae421e3bcba99a0da6d736074f22192ff": ("SALE", "Binance 2"),
    "0x564286362092d8e7936f0549571a803b203aaced": ("SALE", "Binance 3"),
    "0xa910f92acdaf488fa6ef02174fb86208ad7722ba": ("SALE", "Kraken"),
    "0x0d0707963952f2fba59dd06f2b425ace40b492fe": ("SALE", "Gate.io"),
    "0x6cc5f688a315f3dc28a7781717a9a798a59fda7b": ("SALE", "OKX"),
    # Мосты
    "0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf": ("DEFI_INCOME", "Polygon Bridge"),
    "0x99c9fc46f92e8a1c0dec1b1747d010903e884be1": ("DEFI_INCOME", "Optimism Bridge"),
    # Стейкинг
    "0x00000000219ab540356cbb839cbe05303d7705fa": ("DEFI_INCOME", "ETH2 Deposit Contract"),
    "0xae7ab96520de3a18e5e111b5eaab095312d7fe84": ("DEFI_INCOME", "Lido stETH"),
}


def classify_algorithmically(tx: dict, wallet_address: str) -> dict | None:
    to = (tx.get("to_address") or "").lower()
    from_ = (tx.get("from_address") or "").lower()
    wallet = wallet_address.lower()
    value = tx.get("value_wei", "0")

    # Известный протокол
    if to in KNOWN_ADDRESSES:
        category, name = KNOWN_ADDRESSES[to]
        return {
            "tx_hash": tx["tx_hash"],
            "category": category,
            "confidence": 1.0,
            "reasoning": f"Взаимодействие с {name}",
        }

    # Входящий из известного протокола
    if from_ in KNOWN_ADDRESSES:
        category, name = KNOWN_ADDRESSES[from_]
        return {
            "tx_hash": tx["tx_hash"],
            "category": "DEFI_INCOME" if category == "DEFI_INCOME" else "INCOME",
            "confidence": 1.0,
            "reasoning": f"Получение средств от {name}",
        }

    # Самоперевод
    if from_ == wallet and to == wallet:
        return {
            "tx_hash": tx["tx_hash"],
            "category": "SELF_TRANSFER",
            "confidence": 1.0,
            "reasoning": "Перевод между адресами одного владельца",
        }

    # Нулевой value — вызов контракта, отдаём ИИ
    if value == "0":
        return None

    # Входящий с ненулевым value — вероятно доход
    if from_ != wallet and to == wallet:
        return {
            "tx_hash": tx["tx_hash"],
            "category": "INCOME",
            "confidence": 0.7,
            "reasoning": "Входящий перевод от неизвестного адреса",
        }

    # Исходящий на неизвестный адрес — вероятно продажа или перевод
    if from_ == wallet and to != wallet:
        return {
            "tx_hash": tx["tx_hash"],
            "category": "SALE",
            "confidence": 0.6,
            "reasoning": "Исходящий перевод на неизвестный адрес",
        }

    return None


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