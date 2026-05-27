# ReportVerifier — Смарт-контракт верификации налоговых отчётов

## Описание

`ReportVerifier` — смарт-контракт на Solidity, развёрнутый в сети Ethereum Sepolia. Позволяет сохранять хэши налоговых отчётов в блокчейне и верифицировать их существование.

Каждая запись содержит:
- адрес кошелька
- keccak256-хэш содержимого отчёта
- номер блока в момент записи
- временную метку блока

## Адрес контракта

**Сеть:** Ethereum Sepolia (testnet)  
**Адрес:** `0xd00a12D1a67fE239cA9f628667a139087BFCB4Bd`  
**Etherscan:** [Посмотреть контракт](https://sepolia.etherscan.io/address/0xd00a12D1a67fE239cA9f628667a139087BFCB4Bd)

## Функции

### `submitReport(address wallet, bytes32 reportHash)`
Сохраняет запись об отчёте в блокчейне.
- `wallet` — адрес ETH-кошелька, к которому относится отчёт
- `reportHash` — keccak256-хэш JSON-содержимого отчёта

### `verifyReport(address wallet, bytes32 reportHash) → bool`
Проверяет существование записи. Возвращает `true` если отчёт был ранее записан.

### `getRecord(address wallet, bytes32 reportHash) → ReportRecord`
Возвращает полную запись: кошелёк, хэш, номер блока, timestamp.

### `getWalletReports(address wallet) → bytes32[]`
Возвращает все хэши отчётов для конкретного кошелька.

### `getReportCount(address wallet) → uint256`
Возвращает количество отчётов для кошелька.

## Как вычисляется хэш отчёта

На стороне Python (Telegram-бот):

```python
import hashlib, json

report_hash = hashlib.sha256(
    json.dumps(report, sort_keys=True, ensure_ascii=False).encode()
).hexdigest()
```

## Интеграция с Telegram-ботом

После каждого успешного анализа кошелька бот автоматически:
1. Вычисляет хэш отчёта
2. Вызывает `submitReport` в контракте
3. Отправляет пользователю ссылку на транзакцию в Sepolia Etherscan

## Технический стек

- Solidity `^0.8.20`
- Развёрнут через Remix IDE
- Сеть: Ethereum Sepolia
