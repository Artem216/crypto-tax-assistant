# CryptoTax Assistant

ИИ-помощник для анализа криптовалютных транзакций и формирования налоговой отчётности по законодательству РФ.

Пользователь вводит адрес Ethereum-кошелька — система автоматически подтягивает историю транзакций, обогащает их историческими курсами ETH/USD, классифицирует с помощью ИИ и формирует налоговый отчёт с расчётом НДФЛ по прогрессивной шкале 2025 года.

---

## Архитектура

Проект состоит из четырёх микросервисов:

```
orchestrator (8003)
├── etherscan-wallet-service (8000)  — транзакции кошелька
├── coingecko-rate-service (8001)    — исторические курсы ETH/USD
└── ai-service (8002)                — классификация и генерация отчёта
```

**etherscan-wallet-service** — получает историю нативных ETH-транзакций и ERC-20 переводов через Etherscan API. Нормализует сырые данные, считает комиссии, определяет статус транзакций.

**coingecko-rate-service** — обогащает транзакции историческим курсом ETH/USD на дату каждой операции через CoinGecko API.

**ai-service** — классифицирует транзакции (DEX_SWAP, INCOME, SELF_TRANSFER и др.) и генерирует читаемый налоговый отчёт на русском языке. Простые случаи определяются алгоритмически, неоднозначные — через LLM (Groq).

**orchestrator** — склеивает все сервисы в единый пайплайн, конвертирует wei → ETH → USD → RUB, рассчитывает налог по прогрессивной шкале НДФЛ РФ 2025.

---

## Быстрый старт

### Требования

- Docker и Docker Compose
- API ключ Etherscan (бесплатно на [etherscan.io](https://etherscan.io))
- API ключ Groq (бесплатно на [console.groq.com](https://console.groq.com))

### Запуск

```bash
# 1. Клонировать репозиторий
git clone https://github.com/ваш-репо/crypto-tax-assistant.git
cd crypto-tax-assistant

# 2. Создать файл с переменными окружения
cp .env.example .env

# 3. Вставить свои ключи в .env
# ETHERSCAN_API_KEY=ваш_ключ
# GROQ_API_KEY=ваш_ключ

# 4. Запустить все сервисы
docker compose up --build
```

После запуска все сервисы доступны:

| Сервис | URL | Swagger |
|--------|-----|---------|
| Orchestrator | http://localhost:8003 | http://localhost:8003/docs |
| AI Service | http://localhost:8002 | http://localhost:8002/docs |
| CoinGecko Service | http://localhost:8001 | http://localhost:8001/docs |
| Etherscan Service | http://localhost:8000 | http://localhost:8000/docs |

---

## Использование

### Анализ кошелька

```bash
curl -X POST http://localhost:8003/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "period": "2024",
    "usd_rub_rate": 90.0,
    "page_size": 50
  }'
```

**Пример ответа:**
```json
{
  "wallet_address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
  "period": "2024",
  "transactions_analyzed": 50,
  "report": {
    "summary": "...",
    "taxable_events": [...],
    "non_taxable_events": [...],
    "tax_base_rub": 4367.4,
    "estimated_tax_rub": 567.76,
    "tax_rate_note": "Рассчитано по прогрессивной шкале НДФЛ РФ 2025",
    "recommendations": [...],
    "disclaimer": "..."
  }
}
```

### Вопрос по отчёту

```bash
curl -X POST http://localhost:8003/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "question": "Нужно ли мне подавать декларацию?",
    "report": {"tax_base_rub": 4367.4, "estimated_tax_rub": 567.76}
  }'
```

---

## Категории транзакций

| Категория | Описание | Налогооблагаемая |
|-----------|----------|-----------------|
| `INCOME` | Получение крипты как доход | ✅ Да |
| `DEX_SWAP` | Обмен токенов на DEX | ✅ Да |
| `SALE` | Продажа крипты | ✅ Да |
| `DEFI_INCOME` | Доход от стейкинга, airdrop | ✅ Да |
| `SELF_TRANSFER` | Перевод между своими кошельками | ❌ Нет |
| `FEE` | Комиссия сети | ❌ Нет |
| `UNKNOWN` | Не удалось определить | ⚠️ Уточнить |

---

## Налоговые ставки НДФЛ РФ 2025

| Годовой доход | Ставка |
|---------------|--------|
| До 2 400 000 руб | 13% |
| 2 400 000 — 5 000 000 руб | 15% |
| 5 000 000 — 20 000 000 руб | 18% |
| 20 000 000 — 50 000 000 руб | 20% |
| Свыше 50 000 000 руб | 22% |

---

## Переменные окружения

| Переменная | Описание | Обязательная |
|------------|----------|--------------|
| `ETHERSCAN_API_KEY` | Ключ Etherscan API | ✅ |
| `GROQ_API_KEY` | Ключ Groq API | ✅ |
| `COINGECKO_API_KEY` | Ключ CoinGecko (для pro-тира) | ❌ |
| `DEFAULT_CHAIN_ID` | ID сети (1 = Ethereum mainnet) | ❌ |

> ⚠️ На бесплатном тире CoinGecko доступны исторические данные только за последние 365 дней.

---

## Стек

- **Python 3.11** + **FastAPI** + **uvicorn**
- **Groq API** — llama-3.3-70b-versatile
- **Etherscan API** — история транзакций
- **CoinGecko API** — исторические курсы
- **Docker** + **Docker Compose**

---

## Ограничения

- Поддерживается только сеть Ethereum (chain_id=1). BSC, Polygon и другие сети — в планах
- Анализируются только нативные ETH-транзакции. ERC-20 токены — в планах
- Суммы в рублях рассчитываются по курсу USD/RUB, указанному вручную
- Отчёт не является официальным налоговым документом

---

> Этот проект создан в учебных целях и не является юридической или налоговой консультацией.
