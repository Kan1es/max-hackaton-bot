"""МСП.РФ — the Digital SME Platform of the SME Corporation and the Ministry of
Economic Development. It aggregates federal, regional and municipal support
measures, including every subsidy selection of the Ministry of Finance's
promote.budget.gov.ru, filtered by region and applicant type.

The catalog page is a Vue app that loads measures through the Bitrix AJAX
action `nota:regions.support.proactive → getItems`. The page itself carries
what that call needs — the component's signed parameters, the session id and
the region dictionary — so the adapter loads it once and then pages through
getItems for every configured (applicant type × region × support view).
Each measure's public page (/services/support/<code>/<id>/) has the
operator and the full description, which go to the LLM.

The site answers foreign IPs with "доступ запрещен": it needs COLLECTOR_PROXY.
"""
import logging
import re
from datetime import date, datetime
from typing import AsyncIterator, Dict, List, Optional

import httpx

from app.collector.base import RawItem, clip, page_text
from app.core.config import settings

logger = logging.getLogger(__name__)

BASE = "https://xn--l1agf.xn--p1ai"
CATALOG_URL = f"{BASE}/services/support/filter/"
AJAX_URL = f"{BASE}/bitrix/services/main/ajax.php?mode=class&c=nota:regions.support.proactive&action=getItems"
DETAIL_URL = f"{BASE}/services/support/{{code}}/{{id}}/"
PAGE_SIZE = 12
FEDERAL_REGION = "Россия (все регионы)"

_SIGNED = re.compile(r"signedParameters\s*=\s*'([^']+)'")
_SESSID = re.compile(r"'bitrix_sessid'\s*:\s*'([a-f0-9]+)'")
_REGION = re.compile(r"'ID':'(\d+)','UF_NAME':'([^']+)'")
# The page shows this to anonymous visitors in place of the requirements.
_LOGIN_NAG = re.compile(r"Вы не авторизовались.*?Авторизоваться", re.DOTALL)


class GeoBlocked(RuntimeError):
    """The site refused us: without a Russian IP there is nothing to collect."""


def _check_access(response: httpx.Response) -> None:
    if response.status_code == 403 or "доступ запрещен" in response.text[:5000].lower():
        raise GeoBlocked("МСП.РФ отказал в доступе — нужен российский IP (COLLECTOR_PROXY)")
    response.raise_for_status()


def parse_catalog_page(html: str):
    """(signed parameters, session id, {region key: region id}) from the catalog page."""
    signed, sessid = _SIGNED.search(html), _SESSID.search(html)
    if not signed or not sessid:
        raise RuntimeError("МСП.РФ: на странице каталога нет signedParameters/bitrix_sessid — сайт изменился")
    regions = {_region_key(name): rid for rid, name in _REGION.findall(html)}
    return signed.group(1), sessid.group(1), regions


def _region_key(name: str) -> str:
    """"г. Москва" and "Москва" are the same region to us."""
    return re.sub(r"^г\.\s*", "", name.strip()).lower()


def _date(value: Optional[str]) -> Optional[date]:
    try:
        return datetime.strptime(value or "", "%d.%m.%Y").date()
    except ValueError:
        return None


def card_text(item: Dict) -> str:
    view = (item.get("UF_SERVICE_VIEW_ARRAY") or {}).get("VALUE")
    directions = ", ".join((item.get("REGION_SERVICE_SUPPORT_DIRECTION") or {}).values())
    lines = [
        f"Название: {item.get('REGION_SERVICE_NAME', '')}",
        f"Вид поддержки: {item.get('REGION_SUPPORT_VIEW_NAME', '')}",
        f"Уровень: {view}" if view else "",
        f"Направление: {directions}" if directions else "",
        f"Оператор: {item['INSTITUTE_TAG_NAME']}" if item.get("INSTITUTE_TAG_NAME") else "",
        f"Приём заявок: с {item.get('REGION_SUPPORT_DATE_BEGIN') or '—'} по {item.get('REGION_SUPPORT_DATE_END') or '—'}",
        f"Описание: {item['REGION_SERVICE_PREVIEW']}" if item.get("REGION_SERVICE_PREVIEW") else "",
        f"Ссылка на подачу: {item['URL']}" if item.get("URL") else "",
    ]
    return "\n".join(line for line in lines if line)


def known_fields(item: Dict, region_name: str) -> Dict[str, object]:
    """What the API states outright; these override the LLM's reading."""
    level = ((item.get("UF_SERVICE_VIEW_ARRAY") or {}).get("XML_ID") or "").lower()
    return {
        "name": (item.get("REGION_SERVICE_NAME") or "").strip()[:500],
        "ends_at": _date(item.get("REGION_SUPPORT_DATE_END")),
        "region": FEDERAL_REGION if level == "federal" else region_name,
    }


def _csv(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


class MspRfSource:
    name = "msp_rf"

    async def items(self, client: httpx.AsyncClient, limit: int) -> AsyncIterator[RawItem]:
        response = await client.get(CATALOG_URL)
        _check_access(response)
        signed, sessid, region_ids = parse_catalog_page(response.text)

        regions = []
        for name in _csv(settings.COLLECTOR_MSP_REGIONS):
            rid = region_ids.get(_region_key(name))
            if rid is None:
                logger.warning("МСП.РФ: регион «%s» не найден в справочнике сайта", name)
            else:
                regions.append((name, rid))

        produced, seen = 0, set()
        for opf in _csv(settings.COLLECTOR_MSP_APPLICANTS):
            for region_name, region_id in regions:
                for view in _csv(settings.COLLECTOR_MSP_VIEWS):
                    page = 1
                    while True:
                        data = await self._page(client, signed, sessid, opf, region_id, view, page)
                        for item in data.get("items") or []:
                            key = f"{item.get('REGION_CODE')}/{item.get('REGION_SERVICE_ID')}"
                            if key in seen or item.get("REGION_SERVICE_IS_FINISHED"):
                                continue
                            seen.add(key)
                            if produced >= limit:
                                return
                            produced += 1
                            yield await self._item(client, item, key, region_name)
                        if page >= int(data.get("pages") or 1):
                            break
                        page += 1

    async def _page(self, client, signed, sessid, opf, region_id, view, page) -> Dict:
        response = await client.post(
            AJAX_URL,
            data={
                "signedParameters": signed,
                "sessid": sessid,
                "FILTER[COMPANY_ID]": opf,
                "FILTER[REGION]": region_id,
                "FILTER[UF_SUPPORT_VIEW]": view,
                "PAGE_SKIP": str(page),
                "PAGE_SIZE": str(PAGE_SIZE),
                "SORT": "WEIGHT_INTEGRAL",
            },
            headers={"X-Bitrix-Csrf-Token": sessid, "X-Requested-With": "XMLHttpRequest",
                     "Referer": CATALOG_URL},
        )
        _check_access(response)
        payload = response.json()
        if payload.get("status") != "success":
            raise RuntimeError(f"МСП.РФ getItems: {payload.get('errors')}")
        return payload.get("data") or {}

    async def _item(self, client, item: Dict, key: str, region_name: str) -> RawItem:
        url = DETAIL_URL.format(code=item.get("REGION_CODE"), id=item.get("REGION_SERVICE_ID"))
        text = card_text(item)
        try:
            response = await client.get(url)
            _check_access(response)
            detail = _LOGIN_NAG.sub("", page_text(response.text))
            text = f"{text}\n\n{detail}"
        except httpx.HTTPError as exc:
            # The card alone still names the measure, its level and dates.
            logger.info("msp_rf %s: страница меры недоступна (%r)", url, exc)
        return RawItem(
            external_id=key,
            url=url,
            title=item.get("REGION_SERVICE_NAME", ""),
            text=clip(text),
            known=known_fields(item, region_name),
        )
