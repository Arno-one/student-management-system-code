"""周边生活服务推荐工具 — 基于腾讯地图 MCP/REST 查询 POI 列表。"""
from __future__ import annotations

import json
from typing import Any

import requests

import config
from agent_system.middleware.nearby_parser import normalize_nearby_center, parse_nearby_request
from agent_system.tools.base import BaseTool, ToolContext
from agent_system.tools.mcp_client import tencent_map_mcp_client
from service.work_service import address_to_location
from util.log import get_logger

logger = get_logger(__name__)

PLACE_SEARCH_URL = "https://apis.map.qq.com/ws/place/v1/search"


class NearbyServiceTool(BaseTool):
    name = "nearby_service_tool"
    description = "查询指定地点周边的餐饮、医院、打印店、银行、地铁站等生活服务 POI"
    inputs_schema = {"request_text": str}

    def run(self, ctx: ToolContext) -> dict:
        request_text = ctx.params.get("request_text", "")
        parsed = parse_nearby_request(request_text)
        if not parsed.is_complete:
            return self._build_result(
                success=False,
                status="clarification",
                query=parsed.keyword or parsed.query_text or "",
                center_name=parsed.center_text or "",
                radius_meters=parsed.radius_meters,
                result_count=0,
                error_code="NEARBY_INPUT_INCOMPLETE",
                error_message="周边服务查询缺少地点或服务类型",
                missing_fields=parsed.missing_fields,
            )

        try:
            center = self._geocode(parsed.center_text)
        except Exception as exc:
            logger.warning("周边服务地理编码失败: %s", exc)
            return self._build_result(
                success=False,
                status="error",
                provider="tencent_mcp",
                fallback_used=True,
                query=parsed.keyword,
                center_name=parsed.center_text,
                radius_meters=parsed.radius_meters,
                result_count=0,
                error_code="GEOCODE_FAILED",
                error_message=str(exc),
            )

        search_result = self._search_poi(
            keyword=parsed.keyword or "",
            center=center,
            radius_meters=parsed.radius_meters,
            limit=parsed.limit,
        )
        if not search_result.get("success"):
            return self._build_result(
                success=False,
                status="error",
                provider=search_result.get("provider", "tencent_mcp"),
                fallback_used=search_result.get("fallback_used", False),
                query=parsed.keyword,
                center_name=parsed.center_text,
                center=center,
                radius_meters=parsed.radius_meters,
                result_count=0,
                error_code=search_result.get("error_code", "POI_SEARCH_FAILED"),
                error_message=search_result.get("error", "周边地点查询失败"),
            )

        items = search_result.get("items", [])[: parsed.limit]
        fallback_used = search_result.get("fallback_used", False) or center.get("geocode_provider") == "tencent_rest_fallback"
        status = "success" if items else "empty"
        return self._build_result(
            success=bool(items),
            status=status,
            provider=search_result.get("provider"),
            fallback_used=fallback_used,
            query=parsed.keyword,
            center_name=parsed.center_text,
            center=center,
            radius_meters=parsed.radius_meters,
            result_count=len(items),
            items=items,
            empty_message=None if items else f"已按“{parsed.center_text}”周边 {parsed.radius_meters} 米查找，暂时没有找到相关地点。",
        )

    def _geocode(self, center_text: str | None) -> dict:
        if not center_text:
            raise ValueError("地点为空")
        query_address = normalize_nearby_center(center_text)
        fallback_reason = None
        tool_name = self._resolve_mcp_tool_name("geocoder", ["地址", "经纬度"])
        if tool_name:
            try:
                raw = tencent_map_mcp_client.call_tool_sync(tool_name, {"address": query_address})
                payload = self._unwrap_result(self._extract_mcp_payload(raw))
                lat, lng = self._extract_lat_lng(payload)
                if lat is not None and lng is not None:
                    return self._build_geocode_result(
                        name=center_text,
                        query_address=query_address,
                        lat=lat,
                        lng=lng,
                        adcode=self._extract_adcode(payload),
                        address=payload.get("address") or payload.get("title") or query_address,
                        provider="tencent_mcp",
                    )
                fallback_reason = "腾讯地图 MCP 地址解析未返回经纬度"
            except Exception as exc:
                fallback_reason = str(exc)
                logger.warning("周边服务 MCP 地址解析失败，准备回退 REST: %s", exc)
        else:
            fallback_reason = "腾讯地图 MCP 未发现 geocoder tool"

        geo = address_to_location(query_address, policy=1)
        if not geo.get("success"):
            raise RuntimeError(
                f"{center_text}（已按 {query_address} 查询）未解析到经纬度；"
                f"MCP原因：{fallback_reason or '未返回经纬度'}；REST原因：{geo.get('error', '未知错误')}"
            )
        lat = geo.get("lat")
        lng = geo.get("lng")
        if lat is None or lng is None:
            raise RuntimeError(f"{center_text}（已按 {query_address} 查询）未解析到经纬度")
        return self._build_geocode_result(
            name=center_text,
            query_address=query_address,
            lat=lat,
            lng=lng,
            adcode=geo.get("adcode"),
            address=query_address,
            provider="tencent_rest_fallback",
            fallback_reason=fallback_reason,
        )

    def _search_poi(self, keyword: str, center: dict, radius_meters: int, limit: int) -> dict:
        mcp_result = self._search_poi_by_mcp(keyword, center, radius_meters, limit)
        if mcp_result.get("success"):
            return mcp_result
        rest_result = self._search_poi_by_rest(keyword, center, radius_meters, limit, mcp_result.get("error"))
        if rest_result.get("success"):
            return rest_result
        return {
            "success": False,
            "provider": rest_result.get("provider") or "tencent_rest_fallback",
            "fallback_used": True,
            "error_code": rest_result.get("error_code", "POI_SEARCH_FAILED"),
            "error": rest_result.get("error") or mcp_result.get("error"),
        }

    def _search_poi_by_mcp(self, keyword: str, center: dict, radius_meters: int, limit: int) -> dict:
        if not tencent_map_mcp_client.connected:
            return {"success": False, "error": tencent_map_mcp_client.last_error or "腾讯地图 MCP 未连接"}
        tool_name = self._resolve_mcp_tool_name("placeSearchNearby", ["place", "nearby"])
        if not tool_name:
            return {"success": False, "error": "腾讯地图 MCP 未发现 placeSearchNearby tool"}

        attempts = [
            {
                "keyword": keyword,
                "boundary": f"nearby({center['lat']},{center['lng']},{radius_meters})",
                "page_size": limit,
                "page_index": 1,
            },
            {
                "keyword": keyword,
                "location": center["location"],
                "radius": radius_meters,
                "page_size": limit,
                "page_index": 1,
            },
        ]
        last_error = None
        for args in attempts:
            try:
                raw = tencent_map_mcp_client.call_tool_sync(tool_name, args)
                payload = self._extract_mcp_payload(raw)
                if not payload:
                    last_error = "腾讯地图 MCP 周边查询无有效数据"
                    continue
                if payload.get("status") not in (None, 0, "0"):
                    last_error = payload.get("message") or payload.get("error") or "腾讯地图 MCP 周边查询返回错误"
                    continue
                items = self._normalize_items(payload, limit)
                return {
                    "success": True,
                    "provider": "tencent_mcp",
                    "fallback_used": False,
                    "mcp_tool_name": tool_name,
                    "items": items,
                }
            except Exception as exc:
                last_error = str(exc)
                logger.warning("周边 POI MCP 查询失败: args=%s, error=%s", args, exc)
        return {"success": False, "error": last_error or "腾讯地图 MCP 周边查询失败"}

    def _search_poi_by_rest(
        self,
        keyword: str,
        center: dict,
        radius_meters: int,
        limit: int,
        fallback_reason: str | None,
    ) -> dict:
        params = {
            "key": config.TENCENT_MAP_KEY,
            "keyword": keyword,
            "boundary": f"nearby({center['lat']},{center['lng']},{radius_meters})",
            "page_size": limit,
            "page_index": 1,
        }
        try:
            response = requests.get(PLACE_SEARCH_URL, params=params, timeout=10)
            payload = response.json()
        except Exception as exc:
            logger.warning("周边 POI REST 查询异常: %s", exc)
            return {
                "success": False,
                "provider": "tencent_rest_fallback",
                "fallback_used": True,
                "error_code": "REST_POI_EXCEPTION",
                "error": f"调用腾讯地图周边搜索失败：{exc}",
            }
        if payload.get("status") != 0:
            return {
                "success": False,
                "provider": "tencent_rest_fallback",
                "fallback_used": True,
                "error_code": "REST_POI_ERROR",
                "error": payload.get("message", "腾讯地图周边搜索失败"),
            }
        items = self._normalize_items(payload, limit)
        return {
            "success": True,
            "provider": "tencent_rest_fallback",
            "fallback_used": True,
            "fallback_reason": fallback_reason,
            "items": items,
        }

    @staticmethod
    def _build_result(
        success: bool,
        status: str,
        query: str | None,
        center_name: str | None,
        radius_meters: int,
        result_count: int,
        provider: str | None = None,
        fallback_used: bool = False,
        center: dict | None = None,
        items: list[dict] | None = None,
        error_code: str = "",
        error_message: str = "",
        missing_fields: list[str] | None = None,
        empty_message: str | None = None,
    ) -> dict:
        result = {
            "success": success,
            "status": status,
            "intent": "nearby_service",
            "provider": provider,
            "fallback_used": fallback_used,
            "query": query or "",
            "center_name": center_name or "",
            "center": center,
            "radius_meters": radius_meters,
            "result_count": result_count,
            "items": items or [],
            "error_code": error_code,
            "error_message": error_message,
            "error": error_message,
        }
        if missing_fields:
            result["missing_fields"] = missing_fields
        if empty_message:
            result["empty_message"] = empty_message
        return result

    @staticmethod
    def _build_geocode_result(
        name: str,
        query_address: str,
        lat: Any,
        lng: Any,
        adcode: str | None,
        address: str,
        provider: str,
        fallback_reason: str | None = None,
    ) -> dict:
        result = {
            "name": name,
            "address": address,
            "query_address": query_address,
            "lat": lat,
            "lng": lng,
            "location": f"{lat},{lng}",
            "adcode": adcode,
            "geocode_provider": provider,
        }
        if fallback_reason:
            result["geocode_fallback_reason"] = fallback_reason
        return result

    @staticmethod
    def _normalize_items(payload: dict, limit: int) -> list[dict]:
        data = payload.get("data")
        if not isinstance(data, list):
            result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
            data = result.get("data") or result.get("pois") or result.get("items") or []
        items = []
        for raw in data[:limit] if isinstance(data, list) else []:
            if not isinstance(raw, dict):
                continue
            location = raw.get("location") if isinstance(raw.get("location"), dict) else {}
            distance = raw.get("_distance") or raw.get("distance") or raw.get("distance_meters")
            items.append({
                "id": raw.get("id") or raw.get("uid") or raw.get("poi_id") or raw.get("title") or raw.get("name"),
                "name": raw.get("title") or raw.get("name") or "未命名地点",
                "category": raw.get("category") or raw.get("type") or raw.get("classify") or "地点",
                "address": raw.get("address") or raw.get("formatted_address") or "",
                "distance_meters": NearbyServiceTool._to_int(distance),
                "lat": location.get("lat") or raw.get("lat") or raw.get("latitude"),
                "lng": location.get("lng") or raw.get("lng") or raw.get("longitude"),
                "source": "tencent_map",
                "extra": {
                    "tel": raw.get("tel") or raw.get("phone") or "",
                    "rating": raw.get("rating"),
                    "business_hours": raw.get("business_hours") or raw.get("open_time") or "",
                },
            })
        return items

    @staticmethod
    def _to_int(value: Any) -> int | None:
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    @staticmethod
    def _resolve_mcp_tool_name(preferred_name: str, keywords: list[str]) -> str | None:
        for tool in tencent_map_mcp_client.tools:
            if tool.get("name") == preferred_name:
                return preferred_name
        return tencent_map_mcp_client.find_tool_name(keywords)

    @staticmethod
    def _extract_mcp_payload(raw: dict) -> dict:
        if not isinstance(raw, dict) or raw.get("is_error"):
            return {}
        if isinstance(raw.get("result"), dict):
            return raw["result"]
        contents = raw.get("content")
        if isinstance(contents, list):
            for item in contents:
                text = item.get("text") if isinstance(item, dict) else None
                if not text:
                    continue
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    data = {"text": text}
                if isinstance(data, dict):
                    return data
        return raw

    @staticmethod
    def _unwrap_result(payload: dict) -> dict:
        if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
            return payload["result"]
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _extract_adcode(payload: dict) -> str | None:
        if payload.get("adcode"):
            return str(payload["adcode"])
        ad_info = payload.get("ad_info") or {}
        if isinstance(ad_info, dict) and ad_info.get("adcode"):
            return str(ad_info["adcode"])
        return None

    @staticmethod
    def _extract_lat_lng(payload: dict) -> tuple[Any | None, Any | None]:
        location = payload.get("location")
        if isinstance(location, dict):
            return location.get("lat"), location.get("lng")
        if isinstance(location, str) and "," in location:
            lat, lng = location.split(",", 1)
            return lat.strip(), lng.strip()
        return payload.get("lat") or payload.get("latitude"), payload.get("lng") or payload.get("longitude")
