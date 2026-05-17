from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.clients.groq_client import GroqClient
from app.services.classifier import TransactionClassifier
from app.services.report_generator import ReportGenerator

router = APIRouter()


class ClassifyRequest(BaseModel):
    wallet_address: str
    transactions: list[dict]


class ReportRequest(BaseModel):
    wallet_address: str
    period: str
    transactions: list[dict]
    usd_rub_rate: float = 90.0


class ChatRequest(BaseModel):
    wallet_address: str
    question: str
    report: dict  # передаём уже готовый отчёт как контекст


def get_groq_client() -> GroqClient:
    import os
    return GroqClient(api_key=os.environ["GROQ_API_KEY"])


@router.post("/api/v1/classify")
async def classify_transactions(payload: ClassifyRequest):
    try:
        client = get_groq_client()
        classifier = TransactionClassifier(client)
        result = classifier.classify_many(
            transactions=payload.transactions,
            wallet_address=payload.wallet_address,
        )
        return {"wallet_address": payload.wallet_address, "classifications": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/report")
async def generate_report(payload: ReportRequest):
    try:
        client = get_groq_client()
        classifier = TransactionClassifier(client)
        generator = ReportGenerator(client)

        classified = classifier.classify_many(
            transactions=payload.transactions,
            wallet_address=payload.wallet_address,
        )
        report = generator.generate(
            wallet=payload.wallet_address,
            period=payload.period,
            classified_txs=classified,
            usd_rub_rate=payload.usd_rub_rate,
        )
        return {"wallet_address": payload.wallet_address, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/chat")
async def chat(payload: ChatRequest):
    try:
        client = get_groq_client()
        import json
        answer = client.complete(
            system="""Ты — налоговый консультант по криптовалютам. 
            Отвечай на вопросы пользователя по его налоговому отчёту.
            Будь конкретным, ссылайся на данные из отчёта.
            Отвечай на русском языке.""",
            user=f"""Отчёт пользователя:
            {json.dumps(payload.report, ensure_ascii=False, indent=2)}
            
            Вопрос: {payload.question}""",
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))