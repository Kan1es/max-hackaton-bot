from typing import Dict, List

from app.collector.base import Source
from app.collector.sources.corpmsp import CorpMspSource
from app.collector.sources.msp_rf import MspRfSource

SOURCES: Dict[str, Source] = {
    source.name: source for source in (CorpMspSource(), MspRfSource())
}


def get_sources(names: str) -> List[Source]:
    selected = [n.strip() for n in names.split(",") if n.strip()]
    unknown = [n for n in selected if n not in SOURCES]
    if unknown:
        raise ValueError(f"Unknown collector sources: {', '.join(unknown)}; known: {', '.join(SOURCES)}")
    return [SOURCES[n] for n in selected]
