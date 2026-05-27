import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="CryptoTax Orchestrator")

ETHERSCAN_URL = "http://etherscan-wallet-service:8000"
COINGECKO_URL = "http://coingecko-rate-service:8000"
AI_URL = "http://ai-service:8000"


class AnalyzeRequest(BaseModel):
    wallet_address: str
    period: str = "2024"
    usd_rub_rate: float = 90.0
    page_size: int = 100


@app.get("/health")
async def health():
    return {"status": "ok"}


def wei_to_eth(value_wei: str) -> float:
    try:
        return int(value_wei) / 10**18
    except (ValueError, TypeError):
        return 0.0


def calculate_tax_rub(tax_base_rub: float) -> float:
    """Прогрессивная шкала НДФЛ РФ 2025."""
    if tax_base_rub <= 2_400_000:
        return round(tax_base_rub * 0.13, 2)
    elif tax_base_rub <= 5_000_000:
        return round(2_400_000 * 0.13 + (tax_base_rub - 2_400_000) * 0.15, 2)
    elif tax_base_rub <= 20_000_000:
        return round(2_400_000 * 0.13 + 2_600_000 * 0.15 + (tax_base_rub - 5_000_000) * 0.18, 2)
    elif tax_base_rub <= 50_000_000:
        return round(2_400_000 * 0.13 + 2_600_000 * 0.15 + 15_000_000 * 0.18 + (tax_base_rub - 20_000_000) * 0.20, 2)
    else:
        return round(2_400_000 * 0.13 + 2_600_000 * 0.15 + 15_000_000 * 0.18 + 30_000_000 * 0.20 + (tax_base_rub - 50_000_000) * 0.22, 2)


@app.post("/api/v1/analyze")
async def analyze_wallet(payload: AnalyzeRequest):
    async with httpx.AsyncClient(timeout=300.0) as client:

        # Шаг 1 — тянем транзакции
        etherscan_resp = await client.get(
            f"{ETHERSCAN_URL}/api/v1/wallets/{payload.wallet_address}/native-transactions",
            params={"page_size": payload.page_size, "sort": "desc"},
        )
        if etherscan_resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Etherscan сервис вернул ошибку: {etherscan_resp.text}")
        transactions = etherscan_resp.json().get("items", [])

        if not transactions:
            raise HTTPException(status_code=404, detail="Транзакции не найдены")

        # Шаг 2 — обогащаем курсами
        coingecko_resp = await client.post(
            f"{COINGECKO_URL}/api/v1/rates/eth-usd/enrich",
            json={"transactions": [
                {"tx_hash": tx["tx_hash"], "timestamp": tx["timestamp"]}
                for tx in transactions
            ]},
        )
        if coingecko_resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"CoinGecko сервис вернул ошибку: {coingecko_resp.text}")

        rates_by_hash = {
            item["tx_hash"]: item.get("pricing", {})
            for item in coingecko_resp.json().get("items", [])
        }

        # Шаг 3 — считаем реальные суммы
        for tx in transactions:
            pricing = rates_by_hash.get(tx["tx_hash"], {})
            eth_usd = pricing.get("eth_usd", 0.0)

            eth_amount = wei_to_eth(tx.get("value_wei", "0"))
            fee_eth = wei_to_eth(tx.get("fee_wei", "0"))

            tx["pricing"] = pricing
            tx["eth_amount"] = round(eth_amount, 6)
            tx["fee_eth"] = round(fee_eth, 6)
            tx["value_usd"] = round(eth_amount * eth_usd, 2)
            tx["fee_usd"] = round(fee_eth * eth_usd, 2)
            tx["value_rub"] = round(tx["value_usd"] * payload.usd_rub_rate, 2)
            tx["fee_rub"] = round(tx["fee_usd"] * payload.usd_rub_rate, 2)

        # Шаг 4 — отдаём в AI
        ai_resp = await client.post(
            f"{AI_URL}/api/v1/report",
            json={
                "wallet_address": payload.wallet_address,
                "period": payload.period,
                "transactions": transactions,
                "usd_rub_rate": payload.usd_rub_rate,
            },
        )
        if ai_resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"AI сервис вернул ошибку: {ai_resp.text}")

        report = ai_resp.json().get("report", {})

        # Пересчитываем налог по реальной прогрессивной шкале
        tax_base_rub = report.get("tax_base_rub", 0)
        correct_tax = calculate_tax_rub(tax_base_rub)
        report["estimated_tax_rub"] = correct_tax
        report["tax_rate_note"] = "Рассчитано по прогрессивной шкале НДФЛ РФ 2025"

        # Выделяем спорные транзакции для проверки пользователем
        requires_review = [
            {
                "tx_hash": tx.get("tx_hash"),
                "category": tx.get("category"),
                "confidence": tx.get("confidence"),
                "reasoning": tx.get("reasoning"),
                "eth_amount": tx.get("eth_amount", 0),
                "value_rub": tx.get("value_rub", 0),
            }
            for tx in transactions
            if tx.get("confidence", 1.0) < 0.75 or tx.get("category") == "UNKNOWN"
        ]

        requires_review_hashes = report.get("requires_review_hashes", [])

        return {
            "wallet_address": payload.wallet_address,
            "period": payload.period,
            "transactions_analyzed": len(transactions),
            "report": report,
            "requires_review": requires_review_hashes,
            "requires_review_count": len(requires_review_hashes),
        }


@app.post("/api/v1/chat")
async def chat(payload: dict):
    async with httpx.AsyncClient(timeout=30.0) as client:
        ai_resp = await client.post(
            f"{AI_URL}/api/v1/chat",
            json=payload,
        )
        if ai_resp.status_code != 200:
            raise HTTPException(status_code=502, detail=ai_resp.text)
        return ai_resp.json()
