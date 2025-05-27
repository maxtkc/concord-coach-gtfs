#!/usr/bin/env python3
"""
generate_brouter_web_urls.py

For each trip in your GTFS TRIPS, generate a BRouter-Web URL
(with car-fast profile) including a default map view centered
at zoom 8 / 43.269,-70.464.
Override Boston South Station with two straight‐line points,
and Logan Airport with a custom point, adding `straight=1`
if any override was applied.
"""

from gen_gtfs import TRIPS, STOPS

# STOP IDs for overrides
SOUTH_STATION_ID = "STOP-0a858b61-d2dc-44f8-a6fd-9a528df6a3a8"
LOGAN_AIRPORT_ID = "STOP-9a1d503f-4812-4ec4-af0d-6275316cc2c4"

# Manual points around South Station (lon, lat)
SOUTH_STRAIGHT_POINTS = [
    (-71.05537, 42.350096),
    (-71.056301, 42.350161),
]

# Updated custom override point for Logan Airport
LOGAN_OVERRIDE_POINT = (-71.018114, 42.365582)

# build stop_id → (lon, lat) lookup
stop_lookup = {s["stop_id"]: (s["stop_lon"], s["stop_lat"]) for s in STOPS}

if __name__ == "__main__":
    # Map center & zoom: zoom 8 at lat=43.269, lon=-70.464
    base   = "https://brouter.de/brouter-web/#map=8/43.269/-70.464/standard&lonlats="
    suffix = "&profile=car-fast"

    for trip in TRIPS:
        coords = []
        override_applied = False

        for _, sid in trip["stop_times"]:
            if sid == SOUTH_STATION_ID:
                coords.extend(SOUTH_STRAIGHT_POINTS)
                override_applied = True

            elif sid == LOGAN_AIRPORT_ID:
                coords.append(LOGAN_OVERRIDE_POINT)
                override_applied = True

            else:
                coord = stop_lookup.get(sid)
                if coord:
                    coords.append(coord)

        straight_flag = "&straight=1" if override_applied else ""
        lonlats = ";".join(f"{lon},{lat}" for lon, lat in coords)
        url = f"{base}{lonlats}{suffix}{straight_flag}"

        print(f"{trip['trip_id']}: {url}")
