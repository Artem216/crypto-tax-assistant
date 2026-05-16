
## Etherscan Wallet Service

В репозиторий добавлен отдельный микросервис `services/etherscan-wallet-service` на `FastAPI`.
Он получает историю транзакций кошелька через `Etherscan API V2` и отдаёт нормализованный JSON для:

- обычных `native` транзакций;
- `ERC20` переводов.

### Конфигурация

Скопируйте `.env.example` в `.env` и задайте ключ:

```bash
cp .env.example .env
```

Обязательная переменная:

- `ETHERSCAN_API_KEY`

Опциональные переменные:

- `APP_PORT=8000`
- `ETHERSCAN_TIMEOUT_SECONDS=10`
- `ETHERSCAN_RPS_LIMIT=3`
- `DEFAULT_CHAIN_ID=1`

### Запуск через Docker Compose

```bash
docker compose up --build
```

Сервис будет доступен по адресу:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

### Основные endpoint'ы

- `GET /health`
- `GET /api/v1/wallets/{address}/native-transactions`
- `GET /api/v1/wallets/{address}/erc20-transfers`

### `GET /health`

Проверка доступности сервиса.

Пример ответа:

```json
{
  "status": "ok"
}
```

Коды ответа:

- `200` сервис доступен

### `GET /api/v1/wallets/{address}/native-transactions`

Возвращает обычные `native` транзакции кошелька в нормализованном формате.

Path-параметры:

- `address` адрес кошелька в формате `0x` + `40` hex-символов

Query-параметры:

- `chain_id`
- `start_block`
- `end_block`
- `page`
- `page_size`
- `sort`

Значения по умолчанию:

- `chain_id=1`
- `start_block=0`
- `end_block=999999999`
- `page=1`
- `page_size=100`
- `sort=desc`

Ограничения:

- `chain_id > 0`
- `start_block >= 0`
- `end_block >= start_block`
- `page >= 1`
- `page_size` от `1` до `1000`
- `sort`: `asc` или `desc`

Пример запроса:

```bash
curl "http://localhost:8000/api/v1/wallets/0x1111111111111111111111111111111111111111/native-transactions?page=1&page_size=2&sort=desc"
```

Формат ответа:

```json
{
  "wallet_address": "0x1111111111111111111111111111111111111111",
  "chain_id": 1,
  "page": 1,
  "page_size": 2,
  "sort": "desc",
  "items": [
    {
      "tx_hash": "0xabc",
      "block_number": "123",
      "timestamp": "1710000000",
      "from_address": "0x1111111111111111111111111111111111111111",
      "to_address": "0x2222222222222222222222222222222222222222",
      "value_wei": "1000000000000000000",
      "gas_price_wei": "20000000000",
      "gas_used": "21000",
      "fee_wei": "420000000000000",
      "status": "success",
      "is_error": false,
      "method_id": "0xa9059cbb",
      "function_name": "transfer(address,uint256)"
    }
  ]
}
```

Поля `items`:

- `tx_hash` хеш транзакции
- `block_number` номер блока
- `timestamp` unix timestamp как строка
- `from_address` адрес отправителя
- `to_address` адрес получателя или `null`
- `value_wei` значение перевода в `wei`
- `gas_price_wei` цена газа в `wei`
- `gas_used` использованный газ
- `fee_wei` вычисленная комиссия `gas_price_wei * gas_used`
- `status` одно из `success`, `failed`, `unknown`
- `is_error` флаг ошибки из upstream
- `method_id` method id или `null`
- `function_name` имя функции или `null`

### `GET /api/v1/wallets/{address}/erc20-transfers`

Возвращает `ERC20` переводы кошелька в нормализованном формате.

Path-параметры:

- `address` адрес кошелька в формате `0x` + `40` hex-символов

Query-параметры:

- `chain_id`
- `start_block`
- `end_block`
- `page`
- `page_size`
- `sort`
- `contract_address`

Значения по умолчанию:

- те же, что и у `native-transactions`
- `contract_address` не обязателен

Ограничения:

- все ограничения `native-transactions`
- `contract_address` должен быть в формате `0x` + `40` hex-символов

Пример запроса:

```bash
curl "http://localhost:8000/api/v1/wallets/0x1111111111111111111111111111111111111111/erc20-transfers?contract_address=0x2222222222222222222222222222222222222222"
```

Формат ответа:

```json
{
  "wallet_address": "0x1111111111111111111111111111111111111111",
  "chain_id": 1,
  "page": 1,
  "page_size": 100,
  "sort": "desc",
  "items": [
    {
      "tx_hash": "0xdef",
      "block_number": "456",
      "timestamp": "1710001000",
      "from_address": "0x1111111111111111111111111111111111111111",
      "to_address": "0x2222222222222222222222222222222222222222",
      "contract_address": "0x2222222222222222222222222222222222222222",
      "token_name": "USD Coin",
      "token_symbol": "USDC",
      "token_decimals": "6",
      "value_raw": "2500000",
      "gas_price_wei": "5000000000",
      "gas_used": "65000",
      "status": "unknown",
      "method_id": "0xa9059cbb",
      "function_name": "transfer(address,uint256)"
    }
  ]
}
```

Поля `items`:

- `tx_hash` хеш транзакции
- `block_number` номер блока
- `timestamp` unix timestamp как строка
- `from_address` адрес отправителя
- `to_address` адрес получателя или `null`
- `contract_address` адрес ERC20-контракта
- `token_name` имя токена
- `token_symbol` тикер токена
- `token_decimals` decimals токена как строка
- `value_raw` сырое значение перевода без float-конверсии
- `gas_price_wei` цена газа в `wei`
- `gas_used` использованный газ
- `status` одно из `success`, `failed`, `unknown`
- `method_id` method id или `null`
- `function_name` имя функции или `null`

### Коды ошибок

Для обеих транзакционных ручек возможны:

- `200` успешный ответ, включая пустой список `items`
- `400` upstream Etherscan отклонил запрос, например неподдерживаемый `chain_id`
- `422` ошибка валидации входных параметров
- `502` timeout или другая ошибка доступа к Etherscan
- `503` Etherscan вернул rate limit

Ошибки возвращаются в формате:

```json
{
  "detail": "..."
}
```

### Swagger

Интерактивная документация доступна по адресу:

- `http://localhost:8000/docs`
