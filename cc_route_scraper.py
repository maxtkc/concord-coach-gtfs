#!/usr/bin/env python3
import sys
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# ── CONFIGURATION ──
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Safari/537.36"
)
ROUTE_SITEMAP_URL = "https://concordcoachlines.com/route-sitemap.xml"

# ── UTILITIES ──


def fetch_route_urls(sitemap_url: str) -> list[str]:
    resp = requests.get(sitemap_url, headers={"User-Agent": BROWSER_UA})
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    return [
        loc.text
        for loc in root.findall(".//{*}loc")
        if urlparse(loc.text).path.startswith("/route/")
    ]


def extract_route_name(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    if not h1:
        raise ValueError("No <h1> found on route page.")
    return h1.get_text(strip=True)


# ── MAIN ──
def main():
    route_urls = fetch_route_urls(ROUTE_SITEMAP_URL)
    base_consts = []  # list of (CONST_NAME, slug)
    route_data = []  # list of (CONST_NAME, route_name)

    for url in route_urls:
        try:
            slug = urlparse(url).path.rstrip("/").split("/")[-1]
            const_name = slug.upper().replace("-", "_")

            resp = requests.get(url, headers={"User-Agent": BROWSER_UA})
            resp.raise_for_status()
            name = extract_route_name(resp.text)

            base_consts.append((const_name, slug))
            route_data.append((const_name, name))
        except Exception as e:
            print(f"ERROR processing {url}: {e}", file=sys.stderr)

    # output base route ID constants
    for name, slug in base_consts:
        print(f'{name} = "{slug}"')
    print()

    # output ROUTES list
    print("ROUTES = [")
    for const_name, name in route_data:
        print("    {")
        print(f'        "route_id": {const_name},')
        print(f'        "agency_id": AGENCY_ID,')
        print(f'        "route_short_name": "{name}",')
        print(f'        "route_long_name": "{name}",')
        print(f'        "route_desc": "{name}",')
        print(f'        "route_type": RouteTypes.BUS.value,')
        print("    },")
    print("]")


if __name__ == "__main__":
    main()
