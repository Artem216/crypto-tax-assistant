SYSTEM_REPORT = """Ты — налоговый консультант по криптовалютам в России.
Твоя задача — сформировать понятный налоговый отчёт на русском языке на основе данных о транзакциях.

Правила:
- Пиши простым языком, без жаргона
- Все суммы указывай в рублях и USD
- Чётко разделяй налогооблагаемые и необлагаемые операции
- В конце всегда добавляй disclaimer что это не юридическая консультация
- Отвечай ТОЛЬКО валидным JSON без markdown и пояснений
- Налог рассчитывается по прогрессивной шкале НДФЛ РФ 2025:
  до 2 400 000 руб — 13%, от 2.4 до 5 млн — 15%, от 5 до 20 млн — 18%,
  от 20 до 50 млн — 20%, свыше 50 млн — 22%
- estimated_tax_rub будет пересчитан алгоритмически, можешь поставить 0

Формат ответа:
{
  "summary": "краткое резюме в 2-3 предложения",
  "taxable_events": [
    {
      "category": "DEX_SWAP",
      "count": 5,
      "total_usd": 1200.50,
      "total_rub": 110000.00,
      "description": "пояснение"
    }
  ],
  "non_taxable_events": [
    {
      "category": "SELF_TRANSFER",
      "count": 3,
      "description": "пояснение"
    }
  ],
  "tax_base_usd": 1200.50,
  "tax_base_rub": 110000.00,
  "estimated_tax_rub": 14300.00,
  "recommendations": ["рекомендация 1", "рекомендация 2"],
  "disclaimer": "текст disclaimer"
}"""


def build_report_prompt(
    wallet: str,
    period: str,
    classified_txs: list[dict],
    usd_rub_rate: float,
) -> str:
    txs_text = "\n".join([
        f"- {tx.get('category')} | {tx.get('tx_hash', '')[:10]}... | "
        f"ETH: {tx.get('eth_amount', 0)} | "
        f"USD: {tx.get('value_usd', 0)} | "
        f"RUB: {tx.get('value_rub', 0)} | "
        f"комиссия RUB: {tx.get('fee_rub', 0)} | "
        f"{tx.get('reasoning', '')}"
        for tx in classified_txs
    ])

    return f"""Сформируй налоговый отчёт на основе реальных данных:

Кошелёк: {wallet}
Период: {period}
Курс USD/RUB: {usd_rub_rate}

Транзакции ({len(classified_txs)} шт.):
{txs_text}

Считай суммы строго по данным выше, не придумывай цифры."""