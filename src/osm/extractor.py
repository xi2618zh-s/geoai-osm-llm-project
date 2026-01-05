# src/osm/extractor.py
"""
OSM 数据提取模块
- osmium 命令行工具提取 bbox 子集
- pyosmium 解析并提取特定 tag 的节点和路径
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import subprocess

import osmium


@dataclass
class OSMPoint:
    """表示一个 OSM 节点（点）"""
    osm_type: str  # "node"
    osm_id: int
    lon: float
    lat: float
    name: Optional[str]
    tags: Dict[str, str]


@dataclass
class OSMWay:
    """表示一个 OSM Way（线或面）"""
    osm_type: str  # "way"
    osm_id: int
    coordinates: List[Tuple[float, float]]  # [(lon, lat), ...]
    name: Optional[str]
    tags: Dict[str, str]
    centroid: Tuple[float, float] = field(default=(0.0, 0.0))  # 中心点


class TagNodeHandler(osmium.SimpleHandler):
    """
    pyosmium Handler: 提取匹配特定 tag 的节点
    """
    def __init__(self, key: str, value: str):
        super().__init__()
        self.key = key
        self.value = value
        self.rows: List[OSMPoint] = []

    def node(self, n):
        """处理每个节点"""
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


class TagWayHandler(osmium.SimpleHandler):
    """
    pyosmium Handler: 提取匹配特定 tag 的 Way（线/面）
    """
    def __init__(self, key: str, value: str):
        super().__init__()
        self.key = key
        self.value = value
        self.ways: List[OSMWay] = []

    def way(self, w):
        """处理每个 way"""
        if w.tags.get(self.key) == self.value:
            # 提取所有节点坐标
            coordinates = []
            for node in w.nodes:
                if node.location.valid():
                    coordinates.append((float(node.location.lon), float(node.location.lat)))
            
            if coordinates:
                # 计算中心点
                avg_lon = sum(c[0] for c in coordinates) / len(coordinates)
                avg_lat = sum(c[1] for c in coordinates) / len(coordinates)
                
                self.ways.append(
                    OSMWay(
                        osm_type="way",
                        osm_id=int(w.id),
                        coordinates=coordinates,
                        name=w.tags.get("name"),
                        tags=dict(w.tags),
                        centroid=(avg_lon, avg_lat),
                    )
                )


class CombinedTagHandler(osmium.SimpleHandler):
    """
    pyosmium Handler: 同时提取匹配的 Node 和 Way
    """
    def __init__(self, key: str, value: str):
        super().__init__()
        self.key = key
        self.value = value
        self.nodes: List[OSMPoint] = []
        self.ways: List[OSMWay] = []

    def node(self, n):
        """处理每个节点"""
        if n.tags.get(self.key) == self.value and n.location.valid():
            self.nodes.append(
                OSMPoint(
                    osm_type="node",
                    osm_id=int(n.id),
                    lon=float(n.location.lon),
                    lat=float(n.location.lat),
                    name=n.tags.get("name"),
                    tags=dict(n.tags),
                )
            )

    def way(self, w):
        """处理每个 way"""
        if w.tags.get(self.key) == self.value:
            coordinates = []
            for node in w.nodes:
                if node.location.valid():
                    coordinates.append((float(node.location.lon), float(node.location.lat)))
            
            if coordinates:
                avg_lon = sum(c[0] for c in coordinates) / len(coordinates)
                avg_lat = sum(c[1] for c in coordinates) / len(coordinates)
                
                self.ways.append(
                    OSMWay(
                        osm_type="way",
                        osm_id=int(w.id),
                        coordinates=coordinates,
                        name=w.tags.get("name"),
                        tags=dict(w.tags),
                        centroid=(avg_lon, avg_lat),
                    )
                )


def osmium_extract_bbox(
    input_pbf: Path,
    output_pbf: Path,
    bbox: Tuple[float, float, float, float]
) -> None:
    """
    使用 osmium CLI 工具从大 PBF 文件中提取 bbox 区域
    
    Args:
        input_pbf: 输入的 PBF 文件路径
        output_pbf: 输出的子集 PBF 文件路径
        bbox: (minlon, minlat, maxlon, maxlat) 边界框
    
    Raises:
        FileNotFoundError: 如果找不到输入文件
        RuntimeError: 如果 osmium 执行失败
    """
    # 检查输入文件
    if not input_pbf.exists():
        raise FileNotFoundError(f"Input PBF file not found: {input_pbf}")
    
    # 确保输出目录存在
    output_pbf.parent.mkdir(parents=True, exist_ok=True)
    
    # 构建 bbox 字符串: minlon,minlat,maxlon,maxlat
    bbox_str = ",".join(str(x) for x in bbox)
    
    # 使用 shell=True 方式运行命令（解决 Windows 路径问题）
    cmd = f'osmium extract --bbox {bbox_str} "{input_pbf}" -o "{output_pbf}" -O --set-bounds'
    
    print(f"[osmium] Running: {cmd}")
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        error_msg = f"osmium extract failed with exit code {result.returncode}"
        if result.stderr:
            error_msg += f" stderr: {result.stderr}"
        if result.stdout:
            error_msg += f" stdout: {result.stdout}"
        raise RuntimeError(error_msg)
    
    if result.stderr:
        print(f"[osmium] stderr: {result.stderr}")
    
    if not output_pbf.exists():
        raise RuntimeError(f"osmium completed but output file not created: {output_pbf}")
    
    print(f"[osmium] Successfully extracted to {output_pbf}")


def extract_nodes_to_geojson(
    input_pbf: Path,
    key: str,
    value: str,
    out_geojson: Path,
) -> List[OSMPoint]:
    """
    从 PBF 文件中提取匹配 key=value 的节点和 Way，保存为 GeoJSON
    
    同时支持：
    - Node（点）：直接作为 Point
    - Way（线/面）：提取为 Polygon 或用中心点作为 Point
    
    Args:
        input_pbf: 输入的 PBF 文件
        key: OSM tag 键，如 "amenity", "aeroway"
        value: OSM tag 值，如 "cafe", "aerodrome"
        out_geojson: 输出的 GeoJSON 文件路径
    
    Returns:
        提取到的 OSMPoint 列表（用于向后兼容）
    """
    if not input_pbf.exists():
        raise FileNotFoundError(f"Input PBF file not found: {input_pbf}")
    
    print(f"[extractor] Scanning {input_pbf} for {key}={value}")
    
    # 使用组合 Handler 同时提取 Node 和 Way
    handler = CombinedTagHandler(key, value)
    handler.apply_file(str(input_pbf), locations=True)
    
    print(f"[extractor] Found {len(handler.nodes)} nodes and {len(handler.ways)} ways")
    
    features = []
    
    # 添加 Node 特征（Point）
    for point in handler.nodes:
        feature = {
            "type": "Feature",
            "properties": {
                "osm_type": point.osm_type,
                "osm_id": point.osm_id,
                "name": point.name,
                "tags": point.tags,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [point.lon, point.lat],
            },
        }
        features.append(feature)
    
    # 添加 Way 特征（Polygon 或 LineString）
    for way in handler.ways:
        # 判断是闭合多边形还是线
        is_closed = (len(way.coordinates) >= 4 and 
                     way.coordinates[0] == way.coordinates[-1])
        
        if is_closed:
            # 闭合的 Way -> Polygon
            feature = {
                "type": "Feature",
                "properties": {
                    "osm_type": way.osm_type,
                    "osm_id": way.osm_id,
                    "name": way.name,
                    "tags": way.tags,
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [way.coordinates],  # Polygon 需要嵌套数组
                },
            }
        else:
            # 非闭合的 Way -> LineString
            feature = {
                "type": "Feature",
                "properties": {
                    "osm_type": way.osm_type,
                    "osm_id": way.osm_id,
                    "name": way.name,
                    "tags": way.tags,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": way.coordinates,
                },
            }
        features.append(feature)
        
        # 同时添加中心点标记（方便在地图上显示）
        centroid_feature = {
            "type": "Feature",
            "properties": {
                "osm_type": "way_centroid",
                "osm_id": way.osm_id,
                "name": way.name,
                "tags": way.tags,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [way.centroid[0], way.centroid[1]],
            },
        }
        features.append(centroid_feature)
    
    feature_collection = {
        "type": "FeatureCollection",
        "features": features,
    }
    
    # 保存 GeoJSON
    out_geojson.parent.mkdir(parents=True, exist_ok=True)
    with open(out_geojson, "w", encoding="utf-8") as f:
        json.dump(feature_collection, f, ensure_ascii=False, indent=2)
    
    total_count = len(handler.nodes) + len(handler.ways)
    print(f"[extractor] Saved GeoJSON with {total_count} features to {out_geojson}")
    
    # 返回 nodes 列表（向后兼容）
    # 同时把 way 的中心点也加入返回值
    result = list(handler.nodes)
    for way in handler.ways:
        result.append(OSMPoint(
            osm_type="way",
            osm_id=way.osm_id,
            lon=way.centroid[0],
            lat=way.centroid[1],
            name=way.name,
            tags=way.tags,
        ))
    
    return result


def extract_ways_to_geojson(
    input_pbf: Path,
    key: str,
    value: str,
    out_geojson: Path,
) -> List[OSMWay]:
    """
    仅提取匹配的 Ways（线/面）
    
    Args:
        input_pbf: 输入的 PBF 文件
        key: OSM tag 键
        value: OSM tag 值
        out_geojson: 输出的 GeoJSON 文件路径
    
    Returns:
        提取到的 OSMWay 列表
    """
    if not input_pbf.exists():
        raise FileNotFoundError(f"Input PBF file not found: {input_pbf}")
    
    print(f"[extractor] Scanning {input_pbf} for ways with {key}={value}")
    
    handler = TagWayHandler(key, value)
    handler.apply_file(str(input_pbf), locations=True)
    
    print(f"[extractor] Found {len(handler.ways)} ways")
    
    features = []
    for way in handler.ways:
        is_closed = (len(way.coordinates) >= 4 and 
                     way.coordinates[0] == way.coordinates[-1])
        
        if is_closed:
            geometry = {
                "type": "Polygon",
                "coordinates": [way.coordinates],
            }
        else:
            geometry = {
                "type": "LineString",
                "coordinates": way.coordinates,
            }
        
        feature = {
            "type": "Feature",
            "properties": {
                "osm_type": way.osm_type,
                "osm_id": way.osm_id,
                "name": way.name,
                "tags": way.tags,
            },
            "geometry": geometry,
        }
        features.append(feature)
    
    feature_collection = {
        "type": "FeatureCollection",
        "features": features,
    }
    
    out_geojson.parent.mkdir(parents=True, exist_ok=True)
    with open(out_geojson, "w", encoding="utf-8") as f:
        json.dump(feature_collection, f, ensure_ascii=False, indent=2)
    
    print(f"[extractor] Saved GeoJSON to {out_geojson}")
    
    return handler.ways
