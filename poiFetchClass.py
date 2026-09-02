import json
import os
import re
import threading
import time
from typing import Dict, List

import overpy
import requests


class POIFetcher:
    def __init__(self, radius: int = 300, endpoint_limit: int = 2, tag_filters: List[str] = None):
        self.radius = radius
        self.endpoint_limit = max(1, endpoint_limit)
        self.tag_filters = tag_filters or ["shop", "amenity", "office"]
        self.data_by_category = {}
        self.request_timeout = max(3.0, float(os.getenv("CHAOS_OVERPASS_TIMEOUT_SECONDS", "8")))
        self.cache_ttl = max(30.0, float(os.getenv("CHAOS_POI_CACHE_TTL_SECONDS", "300")))
        self.stale_cache_ttl = max(self.cache_ttl, float(os.getenv("CHAOS_POI_STALE_CACHE_TTL_SECONDS", "1800")))
        self._cache = {}
        self._cache_lock = threading.Lock()

        self.endpoints = [
            "https://overpass-api.de/api/interpreter",
            "https://lz4.overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.nchc.org.tw/api/interpreter",
        ]

    def _build_query(self, lat: float, lon: float, result_limit: int = 0) -> str:
        tag_queries = []
        key_filters = []
        for tag in self.tag_filters:
            if "=" in tag:
                key, value = tag.split("=", 1)
                tag_queries.append(f'  nwr(around:{self.radius},{lat},{lon})["{key}"="{value}"];')
            else:
                key_filters.append(tag)

        if key_filters:
            key_regex = "|".join(re.escape(key) for key in key_filters)
            tag_queries.insert(0, f'  nwr(around:{self.radius},{lat},{lon})[~"^({key_regex})$"~"."];')

        tag_query_str = "\n".join(tag_queries)
        return f"""[out:json][timeout:15];
(
{tag_query_str}
);
out center;
"""

    def _fetch(self, lat: float, lon: float, result_limit: int = 0) -> overpy.Result:
        query = self._build_query(lat, lon, result_limit)
        cache_key = (round(float(lat), 4), round(float(lon), 4), self.radius, tuple(self.tag_filters))
        now = time.monotonic()
        with self._cache_lock:
            cached = self._cache.get(cache_key)
        if cached and now - cached[0] <= self.cache_ttl:
            print(f"Overpass cache hit: {cache_key[:2]}")
            return cached[1]
        endpoints_to_try = self.endpoints[:self.endpoint_limit]
        headers = {
            "User-Agent": "haos-game-dev/0.1",
            "Accept": "application/json,text/plain,*/*",
        }

        for i, endpoint in enumerate(endpoints_to_try):
            try:
                print(f"Overpass try {i + 1}: {endpoint}")
                response = requests.post(
                    endpoint,
                    data={"data": query},
                    headers=headers,
                    timeout=self.request_timeout,
                )
                if response.status_code != 200:
                    error_text = response.text.replace("\n", " ")[:300]
                    raise RuntimeError(f"HTTP {response.status_code}: {error_text}")

                print(f"Overpass success: {endpoint}")
                result = overpy.Result.from_json(response.json())
                with self._cache_lock:
                    self._cache[cache_key] = (time.monotonic(), result)
                return result
            except requests.Timeout:
                print(f"Overpass timeout: {endpoint}")
            except Exception as e:
                print(f"Overpass error on try {i + 1}: {e}")
            if i + 1 < len(endpoints_to_try):
                time.sleep(0.25)

        if cached and now - cached[0] <= self.stale_cache_ttl:
            print(f"Overpass stale cache fallback: {cache_key[:2]}")
            return cached[1]
        raise Exception("All Overpass endpoints failed. Try again later.")

    def _categorize_data(self, result: overpy.Result):
        self.data_by_category = {tag: [] for tag in self.tag_filters}
        self.data_by_category["other"] = []

        elements = [
            *(("node", item) for item in getattr(result, "nodes", []) or []),
            *(("way", item) for item in getattr(result, "ways", []) or []),
            *(("relation", item) for item in getattr(result, "relations", []) or []),
        ]
        for element_type, element in elements:
            lat = getattr(element, "lat", None)
            lon = getattr(element, "lon", None)
            if lat is None or lon is None:
                lat = getattr(element, "center_lat", None)
                lon = getattr(element, "center_lon", None)
            if lat is None or lon is None:
                continue
            entry = {
                "name": element.tags.get("name", ""),
                "osm_id": getattr(element, "id", None),
                "node_id": getattr(element, "id", None) if element_type == "node" else None,
                "osm_type": element_type,
                "lat": float(lat),
                "lon": float(lon),
                "tags": element.tags,
            }

            matched = False
            for tag in self.tag_filters:
                if "=" in tag:
                    key, value = tag.split("=", 1)
                    if element.tags.get(key) == value:
                        self.data_by_category[tag].append(entry)
                        matched = True
                        break
                elif tag in element.tags:
                    self.data_by_category[tag].append(entry)
                    matched = True
                    break

            if not matched:
                self.data_by_category["other"].append(entry)

    def get_all_categories(self, lat: float, lon: float, result_limit: int = 60) -> Dict[str, List[Dict]]:
        print(f"POI scan for point {lat}, {lon} (local limit: {result_limit})")
        result = self._fetch(lat, lon, result_limit)
        self._categorize_data(result)
        if result_limit > 0:
            for category, items in self.data_by_category.items():
                self.data_by_category[category] = items[:result_limit]
        return self.data_by_category

    def get_all(self, lat: float, lon: float, result_limit: int = 60) -> List[Dict]:
        categories = self.get_all_categories(lat, lon, result_limit)
        items = []
        seen = set()

        for category in self.tag_filters + ["other"]:
            for entry in categories.get(category, []):
                key = (entry["lat"], entry["lon"])
                if key in seen:
                    continue
                seen.add(key)
                items.append(entry)
                if result_limit > 0 and len(items) >= result_limit:
                    return items

        return items

    def get_category(self, category: str, lat: float, lon: float, result_limit: int = 10) -> List[Dict]:
        print(f"POI category '{category}' for point {lat}, {lon} (local limit: {result_limit})")
        self.get_all_categories(lat, lon, result_limit)
        return self.data_by_category.get(category, [])

    def summary(self) -> Dict[str, int]:
        return {cat: len(items) for cat, items in self.data_by_category.items()}

    def save_to_file(self, filepath="poi_cache.json"):
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.data_by_category, f, indent=2, ensure_ascii=False)
            print(f"POI cache saved to {filepath}")
        except Exception as e:
            print(f"POI cache save error: {e}")

    def load_from_file(self, filepath="poi_cache.json") -> bool:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    self.data_by_category = json.load(f)
                print(f"POI cache loaded from {filepath}")
                return True
            except json.JSONDecodeError:
                print("POI cache decode error.")
                return False
        return False


if __name__ == "__main__":
    fetcher = POIFetcher()
    shops = fetcher.get_category("shop", lat=52.2297, lon=21.0122, result_limit=10)

    print("\nShops:")
    for shop in shops:
        print(shop["name"])

    print("\nSummary:")
    print(fetcher.summary())
