"""Apple Maps Gateway / Auth / マッピングのテスト (HTTP はモック、ネットワーク無し)"""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from requests.exceptions import HTTPError

from app.domain.exceptions import ExternalServiceError
from app.domain.value_objects import Coordinate
from app.infrastructure.gateways.apple_maps_auth import (
    AppleMapsCredentialsError,
    AppleMapsTokenProvider,
)
from app.infrastructure.gateways.apple_maps_gateway_impl import (
    CATEGORY_SEARCH_GENERIC_Q,
    AppleMapsGatewayImpl,
    circle_to_search_region,
    distance_band_bounds,
    format_search_region,
    prefix_apple_place_id,
)
from app.infrastructure.gateways.apple_poi_category_mapping import (
    GOOGLE_TYPE_TO_APPLE_POI_CATEGORY,
    map_google_types_to_apple_poi_categories,
)


def _generate_es256_private_key_pem() -> str:
    """テスト用の ES256 秘密鍵 PEM を生成する。"""
    private_key = ec.generate_private_key(ec.SECP256R1())
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("utf-8")


@pytest.fixture
def es256_pem() -> str:
    """ES256 用の一時秘密鍵 PEM。"""
    return _generate_es256_private_key_pem()


@pytest.fixture
def token_provider(es256_pem: str) -> AppleMapsTokenProvider:
    """モック Session 付き TokenProvider。"""
    session = MagicMock()
    return AppleMapsTokenProvider(
        team_id="TEAM12ABCD",
        key_id="KEY12ABCDE",
        private_key_pem=es256_pem,
        base_url="https://maps-api.apple.test/v1",
        session=session,
    )


class TestApplePoiCategoryMapping:
    """Google → Apple カテゴリマッピング"""

    def test_LANDMARKタイプがユニークなAppleカテゴリに畳み込まれること(self) -> None:
        """複数 Google タイプが同一 Apple カテゴリへ重複なく畳み込まれる。"""
        categories = map_google_types_to_apple_poi_categories()
        assert "Park" in categories
        assert "Museum" in categories
        assert "Cafe" in categories
        assert categories.count("Park") == 1

    def test_ReligiousSiteがGoogleリストに無くても追加されること(self) -> None:
        """神社・寺院向けに ReligiousSite を明示追加する。"""
        categories = map_google_types_to_apple_poi_categories()
        assert "ReligiousSite" in categories

    def test_ギャップタイプが粗畳み込みされること(self) -> None:
        """Apple に無い語彙は Spa / Hotel / Landmark へ寄せる。"""
        assert GOOGLE_TYPE_TO_APPLE_POI_CATEGORY["public_bath"] == "Spa"
        assert GOOGLE_TYPE_TO_APPLE_POI_CATEGORY["japanese_inn"] == "Hotel"
        assert GOOGLE_TYPE_TO_APPLE_POI_CATEGORY["ferris_wheel"] == "Landmark"


class TestBboxAndDistanceBand:
    """bbox 近似と距離帯"""

    def test_円をsearchRegionのbboxに近似できること(self) -> None:
        """center+radius が north,east,south,west になる。"""
        center = Coordinate(latitude=35.0, longitude=139.0)
        north, east, south, west = circle_to_search_region(center, 1000.0)
        assert north > 35.0 > south
        assert east > 139.0 > west
        assert format_search_region((north, east, south, west)).count(",") == 3

    def test_距離帯の上下限がtoleranceどおりであること(self) -> None:
        """±15% の距離帯を計算できる。"""
        low, high = distance_band_bounds(2000.0, 15.0)
        assert low == pytest.approx(1700.0)
        assert high == pytest.approx(2300.0)

    def test_place_idにappleプレフィックスが付くこと(self) -> None:
        """Google place_id と衝突しないよう prefix する。"""
        assert prefix_apple_place_id("I123") == "apple:I123"
        assert prefix_apple_place_id("apple:I123") == "apple:I123"


class TestAppleMapsTokenProvider:
    """JWT / access token"""

    def test_maps_auth_tokenがES256で署名されること(
        self, token_provider: AppleMapsTokenProvider, es256_pem: str
    ) -> None:
        """maps_auth_token の header / claims / 署名を検証する。"""
        token = token_provider.create_maps_auth_token(now=1_700_000_000)
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "ES256"
        assert header["kid"] == "KEY12ABCDE"
        claims = jwt.decode(token, options={"verify_signature": False})
        assert claims["iss"] == "TEAM12ABCD"
        assert claims["scope"] == "server_api"
        private_key = load_pem_private_key(es256_pem.encode(), password=None)
        public_key = private_key.public_key()
        jwt.decode(
            token,
            public_key,
            algorithms=["ES256"],
            options={"verify_exp": False},
        )

    def test_access_tokenをキャッシュして再取得しないこと(
        self, token_provider: AppleMapsTokenProvider
    ) -> None:
        """有効期限内は /v1/token を再呼び出ししない。"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "accessToken": "access-token-1",
            "expiresInSeconds": 1800,
        }
        token_provider._session.get.return_value = mock_response

        first = token_provider.get_access_token(now=1_000.0)
        second = token_provider.get_access_token(now=1_100.0)
        assert first == second == "access-token-1"
        assert token_provider._session.get.call_count == 1

    def test_期限切れ後はaccess_tokenを再取得すること(
        self, token_provider: AppleMapsTokenProvider
    ) -> None:
        """skew を超えたら access token を更新する。"""
        first_response = MagicMock()
        first_response.raise_for_status = MagicMock()
        first_response.json.return_value = {
            "accessToken": "token-a",
            "expiresInSeconds": 100,
        }
        second_response = MagicMock()
        second_response.raise_for_status = MagicMock()
        second_response.json.return_value = {
            "accessToken": "token-b",
            "expiresInSeconds": 1800,
        }
        token_provider._session.get.side_effect = [first_response, second_response]

        assert token_provider.get_access_token(now=0.0) == "token-a"
        assert token_provider.get_access_token(now=50.0) == "token-b"
        assert token_provider._session.get.call_count == 2

    def test_認証情報不足でCredentialsErrorになること(self, tmp_path: Path) -> None:
        """必須 env が無いとき明確なエラーになる。"""
        with pytest.raises(AppleMapsCredentialsError, match="APPLE_TEAM_ID"):
            AppleMapsTokenProvider.from_env(
                team_id=None,
                key_id="KEY",
                private_key_path=str(tmp_path / "missing.p8"),
                backend_dir=tmp_path,
            )


class TestAppleMapsGatewaySearch:
    """カテゴリ検索 / フォールバック / dedup"""

    @pytest.fixture
    def gateway(self, token_provider: AppleMapsTokenProvider) -> AppleMapsGatewayImpl:
        """アクセストークン取得済みの Gateway。"""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "accessToken": "test-access",
            "expiresInSeconds": 1800,
        }
        token_provider._session.get.return_value = mock_response
        return AppleMapsGatewayImpl(
            token_provider,
            base_url="https://maps-api.apple.test/v1",
            session=MagicMock(),
            fallback_queries=("公園", "神社"),
        )

    def _point_at_distance(
        self, center: Coordinate, distance_m: float, bearing_deg: float = 0.0
    ) -> Coordinate:
        """簡易: bearing 方向へ distance_m だけずらす (テスト用近似)。"""
        delta_lat = distance_m / 111_320.0
        radians = math.radians(bearing_deg)
        lat = float(center.latitude) + delta_lat * math.cos(radians)
        meters_per_degree_lng = 111_320.0 * math.cos(math.radians(float(center.latitude)))
        lng = float(center.longitude) + (distance_m / meters_per_degree_lng) * math.sin(radians)
        return Coordinate(latitude=lat, longitude=lng)

    def test_カテゴリ検索で距離帯内のPOIが返ること(self, gateway: AppleMapsGatewayImpl) -> None:
        """カテゴリ検索結果を距離帯で絞り、q 無しで呼ぶ。"""
        center = Coordinate(latitude=35.232, longitude=139.107)
        in_band = self._point_at_distance(center, 2000.0)
        out_of_band = self._point_at_distance(center, 500.0)

        search_response = MagicMock()
        search_response.raise_for_status = MagicMock()
        search_response.json.return_value = {
            "results": [
                {
                    "id": "park-1",
                    "name": "箱根公園",
                    "poiCategory": "Park",
                    "coordinate": {
                        "latitude": in_band.latitude,
                        "longitude": in_band.longitude,
                    },
                },
                {
                    "id": "cafe-near",
                    "name": "近すぎるカフェ",
                    "poiCategory": "Cafe",
                    "coordinate": {
                        "latitude": out_of_band.latitude,
                        "longitude": out_of_band.longitude,
                    },
                },
            ]
        }
        gateway._session.get.return_value = search_response

        hits = gateway.search_landmarks_nearby(
            center, 2000, target_count=1, distance_tolerance_percent=15.0
        )
        assert len(hits) == 1
        assert hits[0].place_id == "apple:park-1"
        assert hits[0].source == "category"
        assert hits[0].display_name == "箱根公園"

        first_params = gateway._session.get.call_args_list[0].kwargs["params"]
        assert "includePoiCategories" in first_params
        assert "searchRegion" in first_params
        assert "searchLocation" not in first_params
        assert "q" not in first_params
        assert first_params["resultTypeFilter"] == "Poi"
        assert first_params["lang"] == "ja-JP"
        assert first_params["limitToCountries"] == "JP"

    def test_カテゴリ検索が400なら汎用qで再試行すること(
        self, gateway: AppleMapsGatewayImpl
    ) -> None:
        """q 省略が拒否されたら汎用 q でリトライする。"""
        center = Coordinate(latitude=35.0, longitude=139.0)
        in_band = self._point_at_distance(center, 2000.0)

        bad_response = MagicMock()
        bad_response.status_code = 400
        bad_response.text = "q is required"
        http_error = HTTPError(response=bad_response)
        bad_response.raise_for_status.side_effect = http_error

        ok_response = MagicMock()
        ok_response.raise_for_status = MagicMock()
        ok_response.json.return_value = {
            "results": [
                {
                    "id": "spot-1",
                    "name": "スポットA",
                    "poiCategory": "Park",
                    "coordinate": {
                        "latitude": in_band.latitude,
                        "longitude": in_band.longitude,
                    },
                }
            ]
        }
        gateway._session.get.side_effect = [bad_response, ok_response]

        hits = gateway.search_landmarks_nearby(
            center, 2000, target_count=1, distance_tolerance_percent=15.0
        )
        assert len(hits) == 1
        second_params = gateway._session.get.call_args_list[1].kwargs["params"]
        assert second_params["q"] == CATEGORY_SEARCH_GENERIC_Q
        assert "searchRegion" in second_params
        assert "searchLocation" not in second_params

    def test_件数不足時にクエリバッグへフォールバックすること(
        self, gateway: AppleMapsGatewayImpl
    ) -> None:
        """カテゴリで足りないとき日本語クエリバッグを使う。"""
        center = Coordinate(latitude=36.122, longitude=139.700)
        in_band = self._point_at_distance(center, 2500.0)

        empty_category = MagicMock()
        empty_category.raise_for_status = MagicMock()
        empty_category.json.return_value = {"results": []}

        empty_query = MagicMock()
        empty_query.raise_for_status = MagicMock()
        empty_query.json.return_value = {"results": []}

        query_hit = MagicMock()
        query_hit.raise_for_status = MagicMock()
        query_hit.json.return_value = {
            "results": [
                {
                    "id": "shrine-1",
                    "name": "久喜神社",
                    "poiCategory": "ReligiousSite",
                    "coordinate": {
                        "latitude": in_band.latitude,
                        "longitude": in_band.longitude,
                    },
                }
            ]
        }
        gateway._session.get.side_effect = [empty_category, empty_query, query_hit]

        hits = gateway.search_landmarks_nearby(
            center, 2500, target_count=1, distance_tolerance_percent=15.0
        )
        assert len(hits) == 1
        assert hits[0].source == "query"
        assert hits[0].place_id == "apple:shrine-1"

        query_params = gateway._session.get.call_args_list[2].kwargs["params"]
        assert query_params["q"] == "神社"
        assert "searchRegion" in query_params
        assert "searchLocation" not in query_params

    def test_同一place_idはdedupされること(self, gateway: AppleMapsGatewayImpl) -> None:
        """カテゴリとクエリで同じ id が出ても 1 件にまとめる。"""
        center = Coordinate(latitude=35.232, longitude=139.107)
        in_band = self._point_at_distance(center, 2000.0)
        payload = {
            "results": [
                {
                    "id": "dup-1",
                    "name": "同じ場所",
                    "poiCategory": "Park",
                    "coordinate": {
                        "latitude": in_band.latitude,
                        "longitude": in_band.longitude,
                    },
                }
            ]
        }
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = payload
        gateway._session.get.return_value = response

        hits = gateway.search_landmarks_nearby(
            center, 2000, target_count=5, distance_tolerance_percent=15.0
        )
        assert len(hits) == 1
        assert hits[0].place_id == "apple:dup-1"

    def test_認証なしでもモジュールimportとマッピングは動くこと(self) -> None:
        """Apple 認証が無くてもマッピング単体は動く。"""
        categories = map_google_types_to_apple_poi_categories(["park", "cafe"])
        assert categories == ["Park", "Cafe", "ReligiousSite"]

    def test_id欠落の結果はスキップすること(self, gateway: AppleMapsGatewayImpl) -> None:
        """id が無い POI は採用しない。"""
        center = Coordinate(latitude=35.0, longitude=139.0)
        in_band = self._point_at_distance(center, 2000.0)
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = {
            "results": [
                {
                    "name": "IDなし",
                    "coordinate": {
                        "latitude": in_band.latitude,
                        "longitude": in_band.longitude,
                    },
                }
            ]
        }
        gateway._session.get.return_value = response
        hits = gateway.search_landmarks_nearby(
            center, 2000, target_count=1, distance_tolerance_percent=15.0
        )
        assert hits == []

    def test_HTTPエラーがExternalServiceErrorになること(
        self, gateway: AppleMapsGatewayImpl
    ) -> None:
        """検索 API の 500 をドメイン例外へ変換する。"""
        center = Coordinate(latitude=35.0, longitude=139.0)
        bad = MagicMock()
        bad.status_code = 500
        bad.text = "boom"
        bad.raise_for_status.side_effect = HTTPError(response=bad)
        gateway._session.get.return_value = bad

        with pytest.raises(ExternalServiceError) as exc_info:
            gateway.search_landmarks_nearby(center, 2000, target_count=1)
        assert exc_info.value.service_name == "Apple Maps Server API"
