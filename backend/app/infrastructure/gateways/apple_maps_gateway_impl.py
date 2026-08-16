"""Apple Maps Server API 検索 Gateway 実装 (スパイク)

GoogleMapsGateway を差し替えず、カテゴリ検索 + 日本語クエリバッグの品質検証専用。

- 円近傍: center+radius → searchRegion bbox に近似し、自前で距離帯フィルタ
- カテゴリ検索: includePoiCategories (q は省略を試し、400 なら汎用 q にフォールバック)
- 件数不足時: 公園/神社/カフェ/... のクエリバッグを同一 bbox で再検索
- place_id は `apple:<id>` で Google place_id と衝突しないようにする

参考: https://developer.apple.com/documentation/applemapsserverapi/-v1-search
"""

from __future__ import annotations

import logging
import math
from typing import Any

import requests
from requests.exceptions import HTTPError, RequestException, Timeout

from app.application.gateway_interfaces.apple_maps_gateway import (
    AppleMapsGateway,
    AppleSearchHit,
    AppleSearchSource,
)
from app.config import (
    LANDMARK_DISTANCE_TOLERANCE_PERCENT,
    LANDMARK_SEARCH_TARGET_COUNT,
    REQUEST_TIMEOUT_SECONDS,
)
from app.domain.exceptions import ExternalServiceError, ExternalServiceTimeoutError
from app.domain.services.coordinate_service import calculate_distance
from app.domain.value_objects import Coordinate
from app.infrastructure.gateways.apple_maps_auth import (
    APPLE_MAPS_BASE_URL,
    AppleMapsTokenProvider,
)
from app.infrastructure.gateways.apple_poi_category_mapping import (
    map_google_types_to_apple_poi_categories,
)

logger = logging.getLogger(__name__)

SERVICE_NAME = "Apple Maps Server API"
PLACE_ID_PREFIX = "apple:"

# 1 度の緯度あたりのおよそのメートル (bbox 近似用)
_METERS_PER_DEGREE_LAT = 111_320.0

# カテゴリ検索で `q` 省略が 400 になった場合の汎用クエリ。
# コミュニティ SDK は q を required と記載。omit / empty / 汎用の可否は probe で確認する。
CATEGORY_SEARCH_GENERIC_Q = "スポット"

# カテゴリ検索でヒットが少ないときの日本語クエリバッグ
FALLBACK_QUERY_BAG: tuple[str, ...] = (
    "公園",
    "神社",
    "カフェ",
    "博物館",
    "城",
    "展望台",
)

SearchRegion = tuple[float, float, float, float]  # north, east, south, west


def circle_to_search_region(center: Coordinate, radius_m: float) -> SearchRegion:
    """中心 + 半径 (m) を Apple searchRegion (north,east,south,west) に近似する。

    Args:
        center: 円の中心
        radius_m: 半径 (メートル)

    Returns:
        SearchRegion: (north, east, south, west)
    """
    lat = float(center.latitude)
    lng = float(center.longitude)
    delta_lat = radius_m / _METERS_PER_DEGREE_LAT
    cos_lat = math.cos(math.radians(lat))
    # 極付近で cos≈0 になるのを防ぐ
    meters_per_degree_lng = _METERS_PER_DEGREE_LAT * max(abs(cos_lat), 1e-6)
    delta_lng = radius_m / meters_per_degree_lng

    north = min(90.0, lat + delta_lat)
    south = max(-90.0, lat - delta_lat)
    east = lng + delta_lng
    west = lng - delta_lng
    if east > 180.0:
        east = 180.0
    if west < -180.0:
        west = -180.0
    return (north, east, south, west)


def format_search_region(region: SearchRegion) -> str:
    """searchRegion クエリ文字列 (north,east,south,west) を作る。"""
    north, east, south, west = region
    return f"{north},{east},{south},{west}"


def distance_band_bounds(
    target_distance_m: float,
    tolerance_percent: float,
) -> tuple[float, float]:
    """目標距離に対する ±tolerance% の下限・上限 (m) を返す。"""
    ratio = tolerance_percent / 100.0
    return target_distance_m * (1.0 - ratio), target_distance_m * (1.0 + ratio)


def prefix_apple_place_id(raw_id: str) -> str:
    """Apple place id に衝突回避プレフィックスを付ける。"""
    if raw_id.startswith(PLACE_ID_PREFIX):
        return raw_id
    return f"{PLACE_ID_PREFIX}{raw_id}"


class AppleMapsGatewayImpl(AppleMapsGateway):
    """Apple Maps Server API 検索の実装 (本番 DI には未接続)"""

    def __init__(
        self,
        token_provider: AppleMapsTokenProvider,
        *,
        base_url: str = APPLE_MAPS_BASE_URL,
        session: requests.Session | None = None,
        fallback_queries: tuple[str, ...] = FALLBACK_QUERY_BAG,
        category_generic_q: str = CATEGORY_SEARCH_GENERIC_Q,
    ) -> None:
        """初期化

        Args:
            token_provider: access token 供給
            base_url: API ベース URL
            session: requests.Session
            fallback_queries: 件数不足時のクエリバッグ
            category_generic_q: カテゴリ検索で q 省略が拒否されたときの汎用 q
        """
        self._token_provider = token_provider
        self._base_url = base_url.rstrip("/")
        self._session = session or requests.Session()
        self._fallback_queries = fallback_queries
        self._category_generic_q = category_generic_q

    def search_landmarks_nearby(
        self,
        coordinate: Coordinate,
        radius_m: int,
        *,
        target_count: int | None = None,
        distance_tolerance_percent: float | None = None,
    ) -> list[AppleSearchHit]:
        """カテゴリ検索 → 不足時クエリバッグで距離帯内 POI を返す。"""
        if radius_m <= 0:
            raise ValueError("radius_m must be positive")

        resolved_target = LANDMARK_SEARCH_TARGET_COUNT if target_count is None else target_count
        resolved_tolerance = (
            LANDMARK_DISTANCE_TOLERANCE_PERCENT
            if distance_tolerance_percent is None
            else distance_tolerance_percent
        )
        min_distance_m, max_distance_m = distance_band_bounds(float(radius_m), resolved_tolerance)
        # bbox は距離帯の外側まで覆う
        region = circle_to_search_region(coordinate, max_distance_m)
        categories = map_google_types_to_apple_poi_categories()

        hits_by_id: dict[str, AppleSearchHit] = {}

        category_results = self._search_by_categories(
            center=coordinate,
            region=region,
            categories=categories,
        )
        self._merge_in_band_hits(
            hits_by_id=hits_by_id,
            raw_results=category_results,
            center=coordinate,
            min_distance_m=min_distance_m,
            max_distance_m=max_distance_m,
            source="category",
        )

        if len(hits_by_id) < resolved_target:
            for query in self._fallback_queries:
                if len(hits_by_id) >= resolved_target:
                    break
                query_results = self._search_by_query(
                    center=coordinate,
                    region=region,
                    query=query,
                )
                self._merge_in_band_hits(
                    hits_by_id=hits_by_id,
                    raw_results=query_results,
                    center=coordinate,
                    min_distance_m=min_distance_m,
                    max_distance_m=max_distance_m,
                    source="query",
                )

        return list(hits_by_id.values())

    def _search_by_categories(
        self,
        *,
        center: Coordinate,
        region: SearchRegion,
        categories: list[str],
    ) -> list[dict[str, Any]]:
        """includePoiCategories でカテゴリ検索する。

        q の扱い (スパイク時点の方針):
        1. まず q を付けずにカテゴリのみで呼ぶ (category-only 仮説)
        2. HTTP 400 なら汎用 q (CATEGORY_SEARCH_GENERIC_Q) を付けて再試行
        空文字 q は送らない (Apple が拒否しうるパラメータを増やさない)。
        """
        params = self._base_search_params(center=center, region=region)
        params["includePoiCategories"] = ",".join(categories)

        try:
            return self._get_search_results(params)
        except ExternalServiceError as error:
            if not self._is_bad_request(error):
                raise
            logger.info(
                "Category search without q was rejected; retrying with generic q=%s",
                self._category_generic_q,
            )
            params_with_q = dict(params)
            params_with_q["q"] = self._category_generic_q
            return self._get_search_results(params_with_q)

    def _search_by_query(
        self,
        *,
        center: Coordinate,
        region: SearchRegion,
        query: str,
    ) -> list[dict[str, Any]]:
        """日本語クエリで同一 bbox を再検索する (フォールバック)。"""
        params = self._base_search_params(center=center, region=region)
        params["q"] = query
        return self._get_search_results(params)

    def _base_search_params(
        self,
        *,
        center: Coordinate,
        region: SearchRegion,
    ) -> dict[str, str]:
        lat, lng = center.to_float_tuple()
        return {
            "searchRegion": format_search_region(region),
            "searchLocation": f"{lat},{lng}",
            "resultTypeFilter": "Poi",
            "lang": "ja-JP",
            "limitToCountries": "JP",
        }

    def _get_search_results(self, params: dict[str, str]) -> list[dict[str, Any]]:
        access_token = self._token_provider.get_access_token()
        url = f"{self._base_url}/search"
        try:
            response = self._session.get(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
        except Timeout as error:
            logger.error("Timeout while calling Apple Maps /v1/search")
            raise ExternalServiceTimeoutError(
                "Request timeout: Failed to search Apple Maps",
                service_name=SERVICE_NAME,
            ) from error
        except HTTPError as error:
            status = error.response.status_code if error.response is not None else None
            body = error.response.text if error.response is not None else ""
            message = f"Failed to search Apple Maps: HTTP {status} {body}".strip()
            raise ExternalServiceError(message, service_name=SERVICE_NAME) from error
        except RequestException as error:
            logger.error("Request error while calling Apple Maps /v1/search: %s", error)
            raise ExternalServiceError(
                f"Failed to search Apple Maps: {error}",
                service_name=SERVICE_NAME,
            ) from error

        results = data.get("results", [])
        if not isinstance(results, list):
            return []
        return [item for item in results if isinstance(item, dict)]

    def _merge_in_band_hits(
        self,
        *,
        hits_by_id: dict[str, AppleSearchHit],
        raw_results: list[dict[str, Any]],
        center: Coordinate,
        min_distance_m: float,
        max_distance_m: float,
        source: AppleSearchSource,
    ) -> None:
        for item in raw_results:
            hit = self._parse_hit(item, center=center, source=source)
            if hit is None:
                continue
            if hit.distance_m < min_distance_m or hit.distance_m > max_distance_m:
                continue
            if hit.place_id in hits_by_id:
                continue
            hits_by_id[hit.place_id] = hit

    def _parse_hit(
        self,
        item: dict[str, Any],
        *,
        center: Coordinate,
        source: AppleSearchSource,
    ) -> AppleSearchHit | None:
        raw_id = item.get("id") or item.get("identifier") or item.get("muid")
        if raw_id is None:
            return None
        place_id = prefix_apple_place_id(str(raw_id))

        name = item.get("name")
        if not name or not isinstance(name, str):
            return None

        coordinate_data = item.get("coordinate")
        if not isinstance(coordinate_data, dict):
            return None
        lat_value = coordinate_data.get("latitude")
        lng_value = coordinate_data.get("longitude")
        if lat_value is None or lng_value is None:
            return None
        try:
            landmark_coordinate = Coordinate(
                latitude=float(lat_value),
                longitude=float(lng_value),
            )
        except (TypeError, ValueError):
            return None

        distance_m = calculate_distance(center, landmark_coordinate)
        poi_category = item.get("poiCategory")
        if poi_category is not None and not isinstance(poi_category, str):
            poi_category = str(poi_category)

        return AppleSearchHit(
            place_id=place_id,
            display_name=name,
            coordinate=landmark_coordinate,
            distance_m=distance_m,
            source=source,
            poi_category=poi_category,
        )

    @staticmethod
    def _is_bad_request(error: ExternalServiceError) -> bool:
        return "HTTP 400" in error.message
