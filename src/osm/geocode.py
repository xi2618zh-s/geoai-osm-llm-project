# src/osm/geocode.py
from __future__ import annotations
from typing import Tuple
import requests
import time

def geocode_to_bbox(place: str, sleep_s: float = 1.0) -> Tuple[float, float, float, float]:
    """
    Return (minlon, minlat, maxlon, maxlat)
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": place,
        "format": "json",
        "limit": 1,
    }
    headers = {
        "User-Agent": "GeoAI-OSM-RAG/1.0 (educational project)"
    }

    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data:
        raise ValueError(f"No geocoding result for place: {place}")

    item = data[0]
    lat = float(item["lat"])
    lon = float(item["lon"])
    bbox = item["boundingbox"]  # [south, north, west, east] as strings

    minlat, maxlat = float(bbox[0]), float(bbox[1])
    minlon, maxlon = float(bbox[2]), float(bbox[3])

    time.sleep(sleep_s)  # be nice to Nominatim
    return minlon, minlat, maxlon, maxlat
