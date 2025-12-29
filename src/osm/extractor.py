# src/osm/extractor.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import subprocess

import osmium


@dataclass
class OSMPoint:
    osm_type: str  # "node"
    osm_id: int
    lon: float
    lat: float
    name: Optional[str]
    tags: Dict[str, str]


class TagNodeHandler(osmium.SimpleHandler):
    def __init__(self, key: str, value: str):
        super().__init__()
        self.key = key
        self.value = value
        self.rows: List[OSMPoint] = []

    def node(self, n):
        if n.tags.get(self.key) == self.value and n.location.valid():
            self.rows.append(
                OSMPoint(
                    osm_type="node",
                    osm_id=int(n.id),
                    lon=float(n.location.lon),
                    lat=float(n.location.lat),
                    name=n.tags.get("name"),
                    tags=dict(n.tags),
                )
            )


def osmium_extract_bbox(input_pbf: Path, output_pbf: Path, bbox: Tuple[float, float, float, float]) -> None:
    """
    bbox = (minlon, minlat, maxlon, maxlat)
    """
    output_pbf.parent.mkdir(parents=True, exist_ok=True)
    bbox_str = ",".join(str(x) for x in bbox)

    cmd = ["osmium", "extract", "--bbox", bbox_str, str(input_pbf), "-o", str(output_pbf), "-O"]
    # -O overwrite if exists
    subprocess.run(cmd, check=True)


def extract_nodes_to_geojson(
    input_pbf: Path,
    key: str,
    value: str,
    out_geojson: Path,
) -> List[OSMPoint]:
    h = TagNodeHandler(key, value)
    h.apply_file(str(input_pbf), locations=True)

    features = []
    for r in h.rows:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "osm_type": r.osm_type,
                    "osm_id": r.osm_id,
                    "name": r.name,
                    "tags": r.tags,
                },
                "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]},
            }
        )

    fc = {"type": "FeatureCollection", "features": features}
    out_geojson.parent.mkdir(parents=True, exist_ok=True)
    with open(out_geojson, "w", encoding="utf-8") as f:
        json.dump(fc, f, ensure_ascii=False)

    return h.rows
