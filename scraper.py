from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

GRATKA = "Gratka"
OLX = "OLX"

SEARCHES = [
    (
        GRATKA,
        "https://gratka.pl/nieruchomosci/mieszkania/powiat-poznanski"
        "?cena-calkowita:max=730000&powierzchnia-w-m2:min=55&sort=newest",
    ),
    (
        GRATKA,
        "https://gratka.pl/nieruchomosci/mieszkania/poznan"
        "?cena-calkowita:max=730000&powierzchnia-w-m2:min=55&sort=newest",
    ),
    (
        OLX,
        "https://www.olx.pl/nieruchomosci/mieszkania/sprzedaz/poznan/"
        "?search%5Border%5D=created_at:desc"
        "&search%5Bfilter_float_price:to%5D=730000"
        "&search%5Bfilter_float_m:from%5D=58",
    ),
]
GRATKA_BASE = "https://gratka.pl"
OLX_BASE = "https://www.olx.pl"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
}
TIMEOUT = 20


def fetch_flats(platform: str, url: str) -> list[dict]:
    try:
        if platform == OLX:
            response = curl_requests.get(url, impersonate="chrome", timeout=TIMEOUT)
        else:
            response = httpx.get(
                url,
                headers=HEADERS,
                timeout=TIMEOUT,
                follow_redirects=True,
            )
        response.raise_for_status()
    except Exception as error:
        print(f"[scraper] request failed for {url}: {error}")
        return []

    flats = PARSERS[platform](response.text)
    for flat in flats:
        flat["platform"] = platform
    return flats


def parse_gratka(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    flats = []

    for card in soup.select("div[data-property-id]"):
        link = card.select_one("a.property-card[href]") or card.select_one("a[href]")
        image = card.select_one("img.gallery-slider__img") or card.select_one("img[src]")
        flats.append(
            {
                "id": card["data-property-id"],
                "title": _text(card.select_one(".property-card__title")) or "Untitled",
                "price": _text(card.select_one(".property-card__price--main"))
                or "N/A",
                "price_per_m2": _text(
                    card.select_one(".property-card__price--perM2")
                ),
                "area": _text(card.select_one('[data-cy="cardPropertyInfoArea"]')),
                "location": _text(card.select_one(".property-card__location")),
                "link": urljoin(GRATKA_BASE, link["href"]) if link else GRATKA_BASE,
                "image": image.get("src", "") if image else "",
            }
        )

    return flats


def parse_olx(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    flats = []

    for card in soup.select('div[data-cy="l-card"][id]'):
        link = card.select_one('[data-testid="card-title-link"][href]')
        if not link:
            continue

        image = card.select_one("img[src]")
        params = card.select_one('[data-testid="blueprint-card-param-icon"]')
        params_text = params.find_parent("span").get_text(strip=True) if params else ""
        area, _, price_per_m2 = params_text.partition(" - ")
        location = _text(card.select_one('[data-testid="location-date"]'))
        flats.append(
            {
                "id": card["id"],
                "title": _text(card.select_one('[data-testid="ad-card-title"] h4'))
                or "Untitled",
                "price": _text(card.select_one('[data-testid="ad-price"]')) or "N/A",
                "price_per_m2": price_per_m2,
                "area": area,
                "location": location.rsplit(" - ", 1)[0],
                "link": urljoin(OLX_BASE, link["href"].split("?", 1)[0]),
                "image": image.get("src", "") if image else "",
            }
        )

    return flats


def _text(node) -> str:
    return " ".join(node.stripped_strings) if node else ""


PARSERS = {GRATKA: parse_gratka, OLX: parse_olx}
