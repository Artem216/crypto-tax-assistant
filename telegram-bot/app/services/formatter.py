def format_report(data: dict) -> str:
    """Форматирует ответ оркестратора в читаемый текст для Telegram."""
    wallet = data.get("wallet_address", "—")
    period = data.get("period", "—")
    tx_count = data.get("transactions_analyzed", 0)
    report = data.get("report", {})

    summary = report.get("summary", "Нет данных")
    tax_base_rub = report.get("tax_base_rub", 0)
    tax_base_usd = report.get("tax_base_usd", 0)
    estimated_tax = report.get("estimated_tax_rub", 0)
    tax_note = report.get("tax_rate_note", "")
    recommendations = report.get("recommendations", [])
    disclaimer = report.get("disclaimer", "")

    # Налогооблагаемые события
    taxable = report.get("taxable_events", [])
    non_taxable = report.get("non_taxable_events", [])

    lines = [
        f"📊 <b>Налоговый отчёт за {period}</b>",
        f"🔑 Кошелёк: <code>{wallet[:6]}...{wallet[-4:]}</code>",
        f"📋 Проанализировано транзакций: <b>{tx_count}</b>",
        "",
        f"📝 <b>Резюме</b>",
        summary,
        "",
    ]

    if taxable:
        lines.append("💸 <b>Налогооблагаемые операции:</b>")
        for event in taxable:
            cat = event.get("category", "—")
            count = event.get("count", 0)
            total_rub = event.get("total_rub", 0)
            desc = event.get("description", "")
            lines.append(f"  • {cat}: {count} шт. — {total_rub:,.0f} ₽")
            if desc:
                lines.append(f"    <i>{desc}</i>")
        lines.append("")

    if non_taxable:
        lines.append("✅ <b>Необлагаемые операции:</b>")
        for event in non_taxable:
            cat = event.get("category", "—")
            count = event.get("count", 0)
            desc = event.get("description", "")
            lines.append(f"  • {cat}: {count} шт.")
            if desc:
                lines.append(f"    <i>{desc}</i>")
        lines.append("")

    lines += [
        "💰 <b>Итог:</b>",
        f"  Налогооблагаемая база: <b>{tax_base_rub:,.0f} ₽</b> (${tax_base_usd:,.2f})",
        f"  НДФЛ к уплате: <b>{estimated_tax:,.0f} ₽</b>",
    ]
    if tax_note:
        lines.append(f"  <i>{tax_note}</i>")

    if recommendations:
        lines += ["", "💡 <b>Рекомендации:</b>"]
        for rec in recommendations:
            lines.append(f"  • {rec}")

    if disclaimer:
        lines += ["", f"⚠️ <i>{disclaimer}</i>"]

    return "\n".join(lines)


def short_wallet(address: str) -> str:
    if len(address) > 10:
        return f"{address[:6]}...{address[-4:]}"
    return address
