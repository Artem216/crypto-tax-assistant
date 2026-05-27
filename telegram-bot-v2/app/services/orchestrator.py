import os
import httpx

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator:8000")


class OrchestratorClient:
    def __init__(self):
        self.base_url = ORCHESTRATOR_URL
        self.timeout = httpx.Timeout(120.0)  # анализ может занять время

    async def analyze_wallet(
        self,
        wallet_address: str,
        period: str = "2024",
        usd_rub_rate: float = 90.0,
        page_size: int = 100,
    ) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/analyze",
                json={
                    "wallet_address": wallet_address,
                    "period": period,
                    "usd_rub_rate": usd_rub_rate,
                    "page_size": page_size,
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def chat(self, wallet_address: str, question: str, report: dict) -> str:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/chat",
                json={
                    "wallet_address": wallet_address,
                    "question": question,
                    "report": report,
                },
            )
            resp.raise_for_status()
            return resp.json().get("answer", "Не удалось получить ответ")
