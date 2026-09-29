"""Collector of real support programs from official Russian portals.

    python -m app.collector            # one run over COLLECTOR_SOURCES
    python -m app.collector --loop     # every COLLECTOR_INTERVAL_HOURS
    python -m app.collector --source msp_rf --limit 5 --dry-run

Sources: corpmsp (SME Corporation's federal programs) and msp_rf (the МСП.РФ
catalog, which also carries every Ministry of Finance subsidy selection).

Each source adapter yields raw items (an id, a link, and the item's text).
An LLM turns the text into catalog fields (app.collector.extract), and
app.collector.sync upserts the result, hides what closed or disappeared, and
switches the demo catalog off once real programs exist.
"""
