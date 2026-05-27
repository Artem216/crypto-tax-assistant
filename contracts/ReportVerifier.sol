// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title ReportVerifier
/// @notice Хранит хэши налоговых отчётов и позволяет верифицировать их существование
contract ReportVerifier {

    // ─── Структуры ───────────────────────────────────────────────────────────

    struct ReportRecord {
        address wallet;       // адрес кошелька
        bytes32 reportHash;   // хэш отчёта (keccak256 от содержимого)
        uint256 blockNumber;  // номер блока в момент записи
        uint256 timestamp;    // временная метка блока
        bool exists;          // флаг существования записи
    }

    // ─── Хранилище ───────────────────────────────────────────────────────────

    // wallet => reportHash => ReportRecord
    mapping(address => mapping(bytes32 => ReportRecord)) private _records;

    // wallet => список хэшей всех отчётов кошелька
    mapping(address => bytes32[]) private _walletReports;

    // ─── События ─────────────────────────────────────────────────────────────

    event ReportSubmitted(
        address indexed wallet,
        bytes32 indexed reportHash,
        uint256 blockNumber,
        uint256 timestamp
    );

    // ─── Ошибки ──────────────────────────────────────────────────────────────

    error ZeroAddress();
    error ZeroHash();
    error ReportAlreadyExists(address wallet, bytes32 reportHash);

    // ─── Основные функции ────────────────────────────────────────────────────

    /// @notice Сохраняет запись об отчёте
    /// @param wallet  Адрес кошелька, к которому относится отчёт
    /// @param reportHash  keccak256-хэш содержимого отчёта
    function submitReport(address wallet, bytes32 reportHash) external {
        if (wallet == address(0)) revert ZeroAddress();
        if (reportHash == bytes32(0)) revert ZeroHash();
        if (_records[wallet][reportHash].exists) {
            revert ReportAlreadyExists(wallet, reportHash);
        }

        _records[wallet][reportHash] = ReportRecord({
            wallet: wallet,
            reportHash: reportHash,
            blockNumber: block.number,
            timestamp: block.timestamp,
            exists: true
        });

        _walletReports[wallet].push(reportHash);

        emit ReportSubmitted(wallet, reportHash, block.number, block.timestamp);
    }

    // ─── Функции верификации ─────────────────────────────────────────────────

    /// @notice Проверяет существование записи об отчёте
    /// @param wallet  Адрес кошелька
    /// @param reportHash  Хэш отчёта
    /// @return true если запись существует
    function verifyReport(address wallet, bytes32 reportHash)
        external
        view
        returns (bool)
    {
        return _records[wallet][reportHash].exists;
    }

    /// @notice Возвращает полную запись об отчёте
    /// @param wallet  Адрес кошелька
    /// @param reportHash  Хэш отчёта
    /// @return record Структура ReportRecord
    function getRecord(address wallet, bytes32 reportHash)
        external
        view
        returns (ReportRecord memory record)
    {
        require(_records[wallet][reportHash].exists, "Record not found");
        return _records[wallet][reportHash];
    }

    /// @notice Возвращает все хэши отчётов для кошелька
    /// @param wallet  Адрес кошелька
    /// @return Массив хэшей отчётов
    function getWalletReports(address wallet)
        external
        view
        returns (bytes32[] memory)
    {
        return _walletReports[wallet];
    }

    /// @notice Возвращает количество отчётов для кошелька
    /// @param wallet  Адрес кошелька
    /// @return Количество отчётов
    function getReportCount(address wallet)
        external
        view
        returns (uint256)
    {
        return _walletReports[wallet].length;
    }
}
