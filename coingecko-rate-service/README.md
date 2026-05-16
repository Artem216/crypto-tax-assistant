# CoinGecko Rate Service

FastAPI-микросервис для обогащения списка транзакций историческими курсами `ETH/USD` через CoinGecko.

## Что делает

- принимает batch транзакций;
- нормализует `timestamp` в UTC;
- группирует транзакции по уникальной UTC-дате;
- получает исторический курс `ETH/USD` из CoinGecko;
- возвращает исходные транзакции с блоком `pricing`.

## API

### `GET /health`

Ответ:

```json
{ "status": "ok" }
```

### `POST /api/v1/rates/eth-usd/enrich`

Пример запроса:

```json
{
  "transactions": [
    {
      "tx_hash": "0xabc",
      "timestamp": "2026-05-15T10:45:00Z",
      "amount_eth": "1.25"
    }
  ]
}
```

Пример ответа:

```json
{
  "asset": "ETH",
  "quote_currency": "USD",
  "items": [
    {
      "tx_hash": "0xabc",
      "timestamp": "2026-05-15T10:45:00Z",
      "amount_eth": "1.25",
      "pricing": {
        "pricing_date_utc": "2026-05-15",
        "eth_usd": 2533.77,
        "coin_id": "ethereum",
        "source": "coingecko"
      }
    }
  ]
}
```

## Ограничения CoinGecko

- `public` и `demo` режимы поддерживают только последние 365 дней исторических данных;
- `pro` режим снимает это ограничение;
- для `demo` нужен `x-cg-demo-api-key`, для `pro` нужен `x-cg-pro-api-key`.

## Конфигурация

Скопируйте `.env.example` в `.env` и при необходимости измените значения.

```env
APP_PORT=8000
COINGECKO_API_TIER=public
COINGECKO_API_KEY=
COINGECKO_TIMEOUT_SECONDS=10
COINGECKO_RPS_LIMIT=3
COINGECKO_RETRY_ATTEMPTS=2
```

## Локальный запуск

Из папки `coingecko-rate-service`:

```bash
python3 -m venv /tmp/coingecko-rate-venv
source /tmp/coingecko-rate-venv/bin/activate
pip install -r requirements-dev.txt
python -m app.main
```

## Тесты

```bash
pytest
```

## Docker

```bash
docker compose up --build coingecko-rate-service
```
