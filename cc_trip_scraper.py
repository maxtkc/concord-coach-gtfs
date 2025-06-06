#!/usr/bin/env python3
"""
multi_route_scraper.py

Scrape both inbound and outbound schedules for each route in ROUTE_ID_MAP
from the raw HTML, iterating each <div class="schedule"> block and emit a runnable TRIPS list:

  - trip_id         = ROUTEID_DIRECTION_HHMM
  - shape_id        = ROUTEID_DIRECTION
  - trip_short_name = last stop name
  - direction_id    = DirectionId.INBOUND.value or DirectionId.OUTBOUND.value
  - stop_times      = [("HH:MM", stop_id), …]
"""

from datetime import datetime

import requests
from bs4 import BeautifulSoup

from gen_gtfs import (
    DAILY_SERVICE_ID,
    INLAND_ME_ID,
    MIDCOAST_ME_ID,
    NORTHERN_NH_ID,
    NYC_NH_ID,
    PORTLAND_BOS_ID,
    PORTLAND_NYC_ID,
    SOUTHERN_NH_ID,
    STOPS,
    BikesAllowed,
    DirectionId,
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/90.0.4430.212 Safari/537.36"
    )
}

ROUTE_ID_MAP = {
    "https://concordcoachlines.com/route/portland-me-to-from-boston-logan-airport/": PORTLAND_BOS_ID,
    "https://concordcoachlines.com/route/portland-me-new-york-city/": PORTLAND_NYC_ID,
    "https://concordcoachlines.com/route/midcoast-maine-to-from-portlandbostonlogan-airport/": MIDCOAST_ME_ID,
    "https://concordcoachlines.com/route/concord-nhnorth-londonderrysalem-to-from-bostonlogan-airport/": SOUTHERN_NH_ID,
    "https://concordcoachlines.com/route/northern-nh-to-from-boston-logan-airport/": NORTHERN_NH_ID,
    "https://concordcoachlines.com/route/bangoraugustaauburn-to-from-portlandbostonlogan-airport/": INLAND_ME_ID,
    "https://concordcoachlines.com/route/new-hampshire-to-from-new-york-city/": NYC_NH_ID,
}


def fetch_soup(url):
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def scrape_trips(url, route_id):
    lookup = {s["stop_name"]: s["stop_id"] for s in STOPS}
    soup = fetch_soup(url)
    all_trips = []

    # Iterate each schedule block
    for sched in soup.select("div.schedule"):
        h2 = sched.select_one("h2.schedule-name")
        if not h2:
            continue
        dir_token = h2.select_one("span.pre").get_text(strip=True).upper()
        dir_enum = (
            DirectionId.OUTBOUND.value
            if "SOUTH" in dir_token or "EAST" in dir_token
            else DirectionId.INBOUND.value
        )
        tbl = sched.select_one("table.schedule-table-horizontal.schedule-table")
        if not tbl:
            continue
        rows = tbl.select("tbody tr")
        if not rows:
            continue

        # Determine number of columns after the stop-title column
        num_cols = len(rows[0].select("td.cell")) - 1
        valid_cols = []  # each is (col_idx, dep12 at first valid row)
        for idx in range(num_cols):
            dep12 = None
            # find the first non-dash time in this column among rows
            for row in rows:
                cell = row.select("td.cell")[idx + 1]
                base = cell.contents[0].strip() if cell.contents else ""
                ampm = cell.select_one("span.am-pm")
                if ampm and base and base != "—":
                    dep12 = base + ampm.text
                    break
            if dep12:
                valid_cols.append((idx, dep12))

        for col_idx, dep12 in valid_cols:
            dep24 = datetime.strptime(dep12, "%I:%M%p").strftime("%H:%M")
            hhmm = dep24.replace(":", "")
            trip_id = f"{route_id}_{dir_token}_{hhmm}"
            shape_id = f"{route_id}_{dir_token}"

            # derive last stop name
            last_txt = rows[-1].select_one("td.stop-title").get_text(" ", strip=True)
            for p in ("Leaves ", "Arrives "):
                if last_txt.startswith(p):
                    last_stop = last_txt[len(p) :]
                    break
            else:
                last_stop = last_txt

            trip = {
                "route_id": route_id,
                "service_id": DAILY_SERVICE_ID,
                "trip_id": trip_id,
                "trip_short_name": last_stop,
                "direction_id": dir_enum,
                "shape_id": shape_id,
                "bikes_allowed": BikesAllowed.YES.value,
                "stop_times": [],
            }

            # collect stop_times for this column at each row in order
            for row in rows:
                title = row.select_one("td.stop-title").get_text(" ", strip=True)
                for pfx in ("Leaves ", "Arrives "):
                    if title.startswith(pfx):
                        stop_name = title[len(pfx) :]
                        break
                else:
                    stop_name = title

                sid = lookup.get(stop_name)
                if not sid:
                    continue

                cell = row.select("td.cell")[col_idx + 1]
                base = cell.contents[0].strip() if cell.contents else ""
                ampm = cell.select_one("span.am-pm")
                if ampm and base and base != "—":
                    t24 = datetime.strptime(base + ampm.text, "%I:%M%p").strftime(
                        "%H:%M"
                    )
                    trip["stop_times"].append((t24, sid))

            # sort stop_times by time
            trip["stop_times"].sort(key=lambda x: x[0])
            all_trips.append(trip)

    return all_trips


def emit_python(all_trips):
    print("from gen_gtfs import (")
    print("    DAILY_SERVICE_ID, DirectionId, BikesAllowed,")
    for const in sorted({t["route_id"] for t in all_trips}):
        print(f"    {const}_ID,")
    print(")\nTRIPS = [")
    for t in all_trips:
        print("    {")
        print(f"        'route_id':        {t['route_id']}_ID,")
        print(f"        'service_id':      DAILY_SERVICE_ID,")
        print(f"        'trip_id':         '{t['trip_id']}',")
        print(f"        'trip_short_name': '{t['trip_short_name']}',")
        if t["direction_id"] == DirectionId.INBOUND.value:
            print("        'direction_id':    DirectionId.INBOUND.value,")
        else:
            print("        'direction_id':    DirectionId.OUTBOUND.value,")
        print(f"        'shape_id':        '{t['shape_id']}',")
        print(f"        'bikes_allowed':   BikesAllowed.YES.value,")
        print("        'stop_times':      [")
        for tm, sid in t["stop_times"]:
            print(f"            ('{tm}', '{sid}'),")
        print("        ],")
        print("    },")
    print("]")


if __name__ == "__main__":
    all_trips = []
    for url, rid in ROUTE_ID_MAP.items():
        all_trips.extend(scrape_trips(url, rid))
    emit_python(all_trips)
