#!/usr/bin/env python3
"""
generate_brouter_web_urls.py

For each trip in your GTFS TRIPS, generate a BRouter-Web URL
(with car-fast profile) including a default map view centered
at zoom 8 / 43.269,-70.464, applying South Station and Logan Airport
overrides. Print only unique combinations of shape_id and URL.
"""

from gen_gtfs import STOPS, TRIPS

# STOP IDs for overrides
SOUTH_STATION_ID = "STOP-0a858b61-d2dc-44f8-a6fd-9a528df6a3a8"
LOGAN_AIRPORT_ID = "STOP-9a1d503f-4812-4ec4-af0d-6275316cc2c4"

# Manual points around South Station (lon, lat)
SOUTH_STRAIGHT_POINTS = [
    (-71.05537, 42.350096),
    (-71.056301, 42.350161),
]

# Custom override point for Logan Airport
LOGAN_OVERRIDE_POINT = (-71.018114, 42.365582)

# build stop_id → (lon, lat) lookup
stop_lookup = {s["stop_id"]: (s["stop_lon"], s["stop_lat"]) for s in STOPS}

if __name__ == "__main__":
    base = "https://brouter.de/brouter-web/#map=8/43.269/-70.464/standard&lonlats="
    suffix = "&profile=car-fast"

    seen = set()
    for trip in TRIPS:
        # sort stop_times by the HH:MM string
        sorted_st = sorted(trip["stop_times"], key=lambda x: x[0])

        coords = []
        south_index = None

        # apply overrides and build coords list
        for time, sid in sorted_st:
            if sid == SOUTH_STATION_ID:
                south_index = len(coords)
                coords.extend(SOUTH_STRAIGHT_POINTS)
            elif sid == LOGAN_AIRPORT_ID:
                coords.append(LOGAN_OVERRIDE_POINT)
            else:
                coords.append(stop_lookup[sid])

        lonlats = ";".join(f"{lon},{lat}" for lon, lat in coords)
        straight_param = f"&straight={south_index}" if south_index is not None else ""
        url = f"{base}{lonlats}{suffix}{straight_param}"

        key = (trip["shape_id"], url)
        if key in seen:
            continue
        seen.add(key)
        print(f"{trip['shape_id']}: {url}")
