import hashlib
import json
import logging
import os

from web3 import Web3

logger = logging.getLogger(__name__)

CONTRACT_ADDRESS = os.getenv(
    "CONTRACT_ADDRESS",
    "0xd00a12D1a67fE239cA9f628667a139087BFCB4Bd"
)

SEPOLIA_RPC = os.getenv(
    "SEPOLIA_RPC_URL",
    "https://ethereum-sepolia-rpc.publicnode.com"
)

PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY", "")

CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "wallet", "type": "address"},
            {"internalType": "bytes32", "name": "reportHash", "type": "bytes32"}
        ],
        "name": "submitReport",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "wallet", "type": "address"},
            {"internalType": "bytes32", "name": "reportHash", "type": "bytes32"}
        ],
        "name": "verifyReport",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "address", "name": "wallet", "type": "address"},
            {"internalType": "bytes32", "name": "reportHash", "type": "bytes32"}
        ],
        "name": "getRecord",
        "outputs": [
            {
                "components": [
                    {"internalType": "address", "name": "wallet", "type": "address"},
                    {"internalType": "bytes32", "name": "reportHash", "type": "bytes32"},
                    {"internalType": "uint256", "name": "blockNumber", "type": "uint256"},
                    {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                    {"internalType": "bool", "name": "exists", "type": "bool"}
                ],
                "internalType": "struct ReportVerifier.ReportRecord",
                "name": "record",
                "type": "tuple"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
]


def compute_report_hash(report: dict) -> bytes:
    """Вычисляет keccak256-хэш отчёта."""
    report_json = json.dumps(report, sort_keys=True, ensure_ascii=False)
    return Web3.keccak(text=report_json)


class BlockchainVerifier:
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(SEPOLIA_RPC))
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI,
        )

    def is_configured(self) -> bool:
        return bool(PRIVATE_KEY) and self.w3.is_connected()

    async def submit_report(self, wallet_address: str, report: dict) -> dict:
        """Записывает хэш отчёта в блокчейн. Возвращает tx_hash и report_hash."""
        if not self.is_configured():
            logger.warning("Blockchain не настроен — пропускаем верификацию")
            return {"skipped": True}

        report_hash = compute_report_hash(report)
        wallet = Web3.to_checksum_address(wallet_address)
        account = self.w3.eth.account.from_key(PRIVATE_KEY)

        nonce = self.w3.eth.get_transaction_count(account.address)
        tx = self.contract.functions.submitReport(wallet, report_hash).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "gas": 100000,
            "gasPrice": self.w3.eth.gas_price,
        })

        signed = self.w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)

        logger.info("Отчёт записан в блокчейн: %s", tx_hash.hex())
        return {
            "tx_hash": tx_hash.hex(),
            "report_hash": report_hash.hex(),
            "skipped": False,
        }

    def verify_report(self, wallet_address: str, report_hash_hex: str) -> bool:
        """Проверяет существование записи в контракте."""
        wallet = Web3.to_checksum_address(wallet_address)
        report_hash = bytes.fromhex(report_hash_hex.lstrip("0x"))
        return self.contract.functions.verifyReport(wallet, report_hash).call()
