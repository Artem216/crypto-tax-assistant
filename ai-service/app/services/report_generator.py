import json
from app.clients.groq_client import GroqClient
from app.prompts.report import SYSTEM_REPORT, build_report_prompt


class ReportGenerator:
    def __init__(self, groq_client: GroqClient):
        self._groq = groq_client

    def generate(
        self,
        wallet: str,
        period: str,
        classified_txs: list[dict],
        usd_rub_rate: float,
    ) -> dict:
        raw = self._groq.complete(
            system=SYSTEM_REPORT,
            user=build_report_prompt(wallet, period, classified_txs, usd_rub_rate),
        )

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return {
                    "summary": "Не удалось сформировать отчёт",
                    "error": raw,
                }