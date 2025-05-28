#!/usr/bin/env python3
import json
import os
import re
import sys
import uuid
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, unquote_plus, urlparse

import requests
from bs4 import BeautifulSoup

# ── CONFIGURATION ──
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not API_KEY:
    sys.exit("Error: set your GOOGLE_MAPS_API_KEY in the environment")

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Safari/537.36"
)

SITEMAP_URL = "https://concordcoachlines.com/stop-sitemap.xml"


# ── UTILITIES ──
def fetch_stop_urls(sitemap_url: str) -> list[str]:
    resp = requests.get(sitemap_url, headers={"User-Agent": BROWSER_UA})
    resp.raise_for_status()
    root = ET.fromstring(resp.text)
    all_urls = [loc.text for loc in root.findall(".//{*}loc")]
    return [u for u in all_urls if urlparse(u).path.startswith("/stop/")]


def extract_iframe_src(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    iframe = soup.find("iframe", src=re.compile(r"google\.com/maps/embed"))
    if not iframe:
        raise ValueError("No Google Maps iframe found")
    return iframe["src"]


def geocode_google(address: str) -> tuple[float, float]:
    resp = requests.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={"address": address, "key": API_KEY},
        headers={"User-Agent": BROWSER_UA},
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "OK" or not data.get("results"):
        raise ValueError(f"Geocode failed: {data.get('status')}")
    loc = data["results"][0]["geometry"]["location"]
    return loc["lat"], loc["lng"]


def parse_coords_from_embed(src: str) -> tuple[float, float]:
    # 1) !3dLAT!4dLON
    m = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", src)
    if m:
        return float(m.group(1)), float(m.group(2))
    # 2) !2dLON!3dLAT
    m = re.search(r"!2d(-?\d+\.\d+)!3d(-?\d+\.\d+)", src)
    if m:
        return float(m.group(2)), float(m.group(1))
    # 3) ll=LAT,LON
    qs = parse_qs(urlparse(src).query)
    if "ll" in qs:
        lat, lon = qs["ll"][0].split(",", 1)
        return float(lat), float(lon)
    # 4) embed/v1/place → geocode `q=`
    if "embed/v1/place" in src:
        params = parse_qs(urlparse(src).query)
        if "q" in params:
            addr = unquote_plus(params["q"][0])
            return geocode_google(addr)
    raise ValueError("Could not parse coordinates from iframe src")


def extract_metadata(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    if not h1:
        raise ValueError("No <h1> found")
    name = h1.get_text(strip=True)
    desc = None
    for sib in h1.next_siblings:
        text = getattr(sib, "string", None)
        if text and text.strip():
            desc = text.strip()
            break
    if not desc:
        p = h1.find_next("p")
        desc = p.get_text(strip=True) if p else ""
    return name, desc


# ── MAIN ──
def main():
    stops = fetch_stop_urls(SITEMAP_URL)
    results = []

    for stop_url in stops:
        try:
            # fetch and parse
            r = requests.get(stop_url, headers={"User-Agent": BROWSER_UA})
            r.raise_for_status()
            html = r.text

            # metadata
            name, desc = extract_metadata(html)
            src = extract_iframe_src(html)
            lat, lon = parse_coords_from_embed(src)

            # build stop object
            stop_obj = {
                "stop_id": f"STOP-{uuid.uuid4()}",
                "stop_name": name,
                "stop_desc": desc,
                "stop_lat": lat,
                "stop_lon": lon,
            }
            results.append(stop_obj)

        except Exception as e:
            print(f"ERROR processing {stop_url}: {e}", file=sys.stderr)

    # output JSON
    json.dump(results, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
