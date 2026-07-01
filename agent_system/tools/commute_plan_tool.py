"""通勤规划工具 — 封装腾讯地图 MCP 路线能力，不让 Agent 裸调 MCP。"""
import json
from typing import Any

from agent_system.middleware.commute_parser import normalize_geocode_address, parse_commute_request
from agent_system.tools.base import BaseTool, ToolContext
from agent_system.tools.mcp_client import tencent_map_mcp_client
from agent_system.tools.weather_tool import WeatherTool
from service.work_service import address_to_location
from util.log import get_logger

logger = get_logger(__name__)

_MODE_CONFIG = {
    "transit": {"tool": "directionTransit", "label": "公交/地铁"},
    "driving": {"tool": "directionDriving", "label": "开车"},
    "walking": {"tool": "directionWalking", "label": "步行"},
}

class CommutePlanTool(BaseTool):
    name = "commute_plan_tool"
    description = "基于腾讯地图 MCP 规划学生实习或外出通勤路线，并结合天气给出辅助提醒"
    inputs_schema = {"request_text": str}

    def run(self, ctx: ToolContext) -> dict:
        request_text = ctx.params.get("request_text", "")
        parsed = parse_commute_request(request_text)
        if not parsed.is_complete:
            return {
                "success": False,
                "status": "clarification",
                "error": "通勤规划缺少起点、终点或出行方式",
                "missing_fields": parsed.missing_fields,
            }

        if not tencent_map_mcp_client.connected:
            return {
                "success": False,
                "status": "error",
                "provider": "tencent_mcp",
                "error": tencent_map_mcp_client.last_error or "腾讯地图 MCP 未连接",
            }

        try:
            origin = self._geocode(parsed.origin_text, parsed.city_context)
            destination = self._geocode(parsed.destination_text, parsed.city_context)
        except Exception as exc:
            logger.warning("通勤规划地理编码失败: %s", exc)
            return {
                "success": False,
                "status": "error",
                "provider": "tencent_mcp",
                "origin_text": parsed.origin_text,
                "destination_text": parsed.destination_text,
                "error": f"起点或终点解析失败：{exc}",
            }

        routes = []
        for mode in parsed.travel_modes:
            routes.append(self._query_route(mode, origin, destination))

        success_routes = [item for item in routes if item.get("success")]
        if not success_routes:
            return {
                "success": False,
                "status": "error",
                "provider": "tencent_mcp",
                "origin": origin,
                "destination": destination,
                "travel_modes": parsed.travel_modes,
                "departure_time_text": parsed.departure_time_text,
                "routes": routes,
                "error": "所有出行方式路线规划均失败",
            }

        weather = self._query_weather(parsed.destination_text, ctx)
        status = "partial_success" if len(success_routes) < len(routes) else "success"
        return {
            "success": True,
            "status": status,
            "provider": "tencent_mcp",
            "origin_text": parsed.origin_text,
            "destination_text": parsed.destination_text,
            "origin": origin,
            "destination": destination,
            "travel_modes": parsed.travel_modes,
            "departure_time_text": parsed.departure_time_text,
            "routes": routes,
            "weather": weather,
            "weather_reminder": self._build_weather_reminder(weather),
        }

    def _geocode(self, address: str | None, city_context: str | None = None) -> dict:
        if not address:
            raise ValueError("地点为空")
        query_address = normalize_geocode_address(address, city_context)
        tool_name = self._resolve_mcp_tool_name("geocoder", ["地址", "经纬度"])
        payload = {}
        fallback_reason = None

        if tool_name:
            try:
                raw = tencent_map_mcp_client.call_tool_sync(tool_name, {"address": query_address})
                payload = self._unwrap_result(self._extract_mcp_payload(raw))
                lat, lng = self._extract_lat_lng(payload)
                if lat is not None and lng is not None:
                    return self._build_geocode_result(
                        address=address,
                        query_address=query_address,
                        lat=lat,
                        lng=lng,
                        adcode=self._extract_adcode(payload),
                        raw_address=payload.get("address") or payload.get("title") or address,
                        provider="tencent_mcp",
                    )
                fallback_reason = "腾讯地图 MCP 地址解析未返回经纬度"
            except Exception as exc:
                fallback_reason = str(exc)
                logger.warning("腾讯地图 MCP 地址解析失败，准备回退 REST: %s", exc)
        else:
            fallback_reason = "腾讯地图 MCP 未发现 geocoder tool"

        # MCP geocoder 对“宝安/龙岗”等短行政区偶发不返回坐标，REST 宽松模式作为兜底。
        return self._geocode_by_rest(address, query_address, fallback_reason)

    def _geocode_by_rest(self, address: str, query_address: str, fallback_reason: str | None) -> dict:
        """使用腾讯地图 REST 宽松地理编码兜底，把地点文本解析成路线工具需要的经纬度。"""
        geo = address_to_location(query_address, policy=1)
        if not geo.get("success"):
            rest_reason = geo.get("error", "未知错误")
            raise RuntimeError(
                f"{address}（已按 {query_address} 查询）未解析到经纬度；"
                f"MCP原因：{fallback_reason or '未返回经纬度'}；REST原因：{rest_reason}"
            )

        lat = geo.get("lat")
        lng = geo.get("lng")
        if lat is None or lng is None:
            raise RuntimeError(
                f"{address}（已按 {query_address} 查询）未解析到经纬度；"
                f"MCP原因：{fallback_reason or '未返回经纬度'}；REST原因：REST未返回经纬度"
            )

        return self._build_geocode_result(
            address=address,
            query_address=query_address,
            lat=lat,
            lng=lng,
            adcode=geo.get("adcode"),
            raw_address=query_address,
            provider="tencent_rest_fallback",
            fallback_reason=fallback_reason,
        )

    @staticmethod
    def _build_geocode_result(
        address: str,
        query_address: str,
        lat: Any,
        lng: Any,
        adcode: str | None,
        raw_address: str,
        provider: str,
        fallback_reason: str | None = None,
    ) -> dict:
        result = {
            "name": address,
            "query_address": query_address,
            "lat": lat,
            "lng": lng,
            "location": f"{lat},{lng}",
            "adcode": adcode,
            "raw_address": raw_address,
            "geocode_provider": provider,
        }
        if fallback_reason:
            result["geocode_fallback_reason"] = fallback_reason
        return result

    def _query_route(self, mode: str, origin: dict, destination: dict) -> dict:
        config = _MODE_CONFIG.get(mode)
        if not config:
            return {"mode": mode, "success": False, "status": "error", "error": "不支持的出行方式"}
        tool_name = self._resolve_mcp_tool_name(config["tool"], [config["tool"]])
        if not tool_name:
            return {"mode": mode, "label": config["label"], "success": False, "status": "error", "error": f"未发现 {config['tool']} tool"}

        try:
            raw = tencent_map_mcp_client.call_tool_sync(tool_name, {
                "from": origin["location"],
                "to": destination["location"],
            })
            payload = self._extract_mcp_payload(raw)
            route = self._first_route(payload)
            distance = self._find_number(route, ["distance", "distance_meters"])
            duration = self._find_number(route, ["duration", "duration_seconds", "time"])
            return {
                "mode": mode,
                "label": config["label"],
                "success": True,
                "status": "success",
                "mcp_tool_name": tool_name,
                "distance_meters": distance,
                "duration_seconds": duration,
                "distance_text": self._format_distance(distance),
                "duration_text": self._format_duration(duration),
                "summary": self._route_summary(config["label"], distance, duration),
            }
        except Exception as exc:
            logger.warning("通勤路线规划失败: mode=%s, error=%s", mode, exc)
            return {
                "mode": mode,
                "label": config["label"],
                "success": False,
                "status": "error",
                "mcp_tool_name": tool_name,
                "error": str(exc),
            }

    def _query_weather(self, location_text: str | None, ctx: ToolContext) -> dict:
        if not location_text:
            return {"success": False, "error": "未指定天气地点"}
        try:
            weather_ctx = ToolContext(
                params={"location_text": location_text},
                upstream_results=ctx.upstream_results,
                user=ctx.user,
                db=ctx.db,
                db_readonly=ctx.db_readonly,
            )
            return WeatherTool().run(weather_ctx)
        except Exception as exc:
            logger.warning("通勤天气辅助查询失败: %s", exc)
            return {"success": False, "error": str(exc)}

    @staticmethod
    def _build_weather_reminder(weather: dict) -> str:
        if not weather.get("success"):
            return "天气建议暂不可用，路线规划结果不受影响。"
        return "已结合目的地天气作为辅助提醒，实际出行仍以实时路况和天气为准。"

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

    @staticmethod
    def _first_route(payload: dict) -> dict:
        if not isinstance(payload, dict):
            return {}
        result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
        routes = result.get("routes") or result.get("route") or result.get("paths")
        if isinstance(routes, list) and routes:
            return routes[0] if isinstance(routes[0], dict) else {}
        return result

    def _find_number(self, data: Any, keys: list[str]) -> int | None:
        if isinstance(data, dict):
            for key in keys:
                value = data.get(key)
                if isinstance(value, (int, float)):
                    return int(value)
                if isinstance(value, str) and value.isdigit():
                    return int(value)
            for value in data.values():
                found = self._find_number(value, keys)
                if found is not None:
                    return found
        if isinstance(data, list):
            for item in data:
                found = self._find_number(item, keys)
                if found is not None:
                    return found
        return None

    @staticmethod
    def _format_distance(distance: int | None) -> str:
        if distance is None:
            return "距离暂不可用"
        if distance >= 1000:
            return f"{distance / 1000:.1f} 公里"
        return f"{distance} 米"

    @staticmethod
    def _format_duration(duration: int | None) -> str:
        if duration is None:
            return "耗时暂不可用"
        minutes = max(1, round(duration / 60))
        if minutes >= 60:
            return f"{minutes // 60} 小时 {minutes % 60} 分钟"
        return f"{minutes} 分钟"

    def _route_summary(self, label: str, distance: int | None, duration: int | None) -> str:
        return f"{label}预计耗时 {self._format_duration(duration)}，距离 {self._format_distance(distance)}。"
