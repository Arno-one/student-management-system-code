"""天气查询工具 — 优先使用腾讯地图 MCP，失败时回退原 REST 链路。"""
import json

from agent_system.tools.base import BaseTool, ToolContext
from agent_system.tools.mcp_client import tencent_map_mcp_client
from service.work_service import address_to_location, query_weather
from util.log import get_logger

logger = get_logger(__name__)


class WeatherTool(BaseTool):
    name = "weather_tool"
    description = "查询指定城市的天气信息，包括实时天气、多日预报、空气质量、预警"
    inputs_schema = {"location_text": str}

    def run(self, ctx: ToolContext) -> dict:
        location_text = ctx.params.get("location_text", "")
        if not location_text:
            return {"success": False, "error": "未指定查询地点"}

        mcp_result = self._query_by_mcp(location_text)
        if mcp_result.get("success"):
            return mcp_result

        fallback_reason = mcp_result.get("error")

        # 1. 地址 → 经纬度（policy=1 宽松模式，支持"宝安""龙岗"等区名省略城市）
        geo = address_to_location(location_text, policy=1)
        if not geo.get("success"):
            return {
                "success": False,
                "provider": "tencent_rest_fallback",
                "fallback_reason": fallback_reason,
                "error": f"地址解析失败: {geo.get('error', '未知错误')}",
            }

        lat = geo.get("lat")
        lng = geo.get("lng")
        adcode = geo.get("adcode")
        location_str = f"{lat},{lng}"

        # 2. 并发查实时 + 预报 + 空气质量 + 预警
        results = {}
        weather_types = [
            ("now", "实时天气"),
            ("future", "多日预报"),
        ]
        for wtype, label in weather_types:
            r = query_weather(location=location_str, weather_type=wtype, added_fields="alarm,air")
            if "error" not in r:
                results[label] = r
            else:
                logger.warning("天气查询 %s 失败: %s", label, r.get("error"))

        has_data = len(results) > 0
        return {
            "success": has_data,
            "provider": "tencent_rest_fallback",
            "fallback_reason": fallback_reason,
            "location_text": location_text,
            "lat": lat,
            "lng": lng,
            "adcode": adcode,
            "weather": results,
            "error": None if has_data else "所有天气类型查询均失败",
        }

    def _query_by_mcp(self, location_text: str) -> dict:
        """通过腾讯地图 MCP 查询天气；任何异常都交给 REST 兜底。"""
        if not tencent_map_mcp_client.connected:
            return {"success": False, "error": tencent_map_mcp_client.last_error or "腾讯地图 MCP 未连接"}

        geocoder_tool = self._resolve_mcp_tool_name("geocoder", ["地址", "经纬度"])
        weather_tool = self._resolve_mcp_tool_name("weather", ["天气"])
        if not geocoder_tool or not weather_tool:
            return {"success": False, "error": "腾讯地图 MCP 未发现 geocoder/weather tool"}

        try:
            # 真实腾讯地图 MCP 的 weather tool 不接收自然语言地点，必须先 geocoder 得到 adcode 或经纬度。
            geo_raw = tencent_map_mcp_client.call_tool_sync(geocoder_tool, {"address": location_text})
            geo_payload = self._unwrap_result(self._extract_mcp_payload(geo_raw))
            adcode = self._extract_adcode(geo_payload)
            lat, lng = self._extract_lat_lng(geo_payload)
            location = f"{lat},{lng}" if lat is not None and lng is not None else None

            if not adcode and not location:
                return {"success": False, "error": "腾讯地图 MCP 地址解析未返回 adcode 或经纬度"}

            weather_args = {"adcode": adcode} if adcode else {"location": location}
            weather_results = {}
            for weather_type, label in [("now", "实时天气"), ("future", "多日预报")]:
                raw = tencent_map_mcp_client.call_tool_sync(
                    weather_tool,
                    {**weather_args, "type": weather_type},
                )
                payload = self._extract_mcp_payload(raw)
                if payload:
                    weather_results[label] = payload

            if not weather_results:
                return {"success": False, "error": "腾讯地图 MCP 天气查询无有效数据"}

            return {
                "success": True,
                "provider": "tencent_mcp",
                "mcp_tool_names": [geocoder_tool, weather_tool],
                "location_text": location_text,
                "lat": lat,
                "lng": lng,
                "adcode": adcode,
                "geocode": geo_payload,
                "weather": weather_results,
                "error": None,
            }
        except Exception as exc:
            logger.warning("腾讯地图 MCP 天气查询失败，自动回退 REST: %s", exc)
            return {"success": False, "error": str(exc)}

    @staticmethod
    def _resolve_mcp_tool_name(preferred_name: str, keywords: list[str]) -> str | None:
        """优先按真实工具名精确匹配，避免关键字误命中相近工具。"""
        for tool in tencent_map_mcp_client.tools:
            if tool.get("name") == preferred_name:
                return preferred_name
        return tencent_map_mcp_client.find_tool_name(keywords)

    @staticmethod
    def _extract_mcp_payload(raw: dict) -> dict:
        """兼容 MCP SDK 的 content/text 返回和测试桩的 dict 返回。"""
        if not isinstance(raw, dict):
            return {}
        if raw.get("is_error"):
            return {}

        if isinstance(raw.get("result"), dict):
            return raw["result"]
        if isinstance(raw.get("weather"), dict):
            return raw

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
        return raw if raw else {}

    @staticmethod
    def _unwrap_result(payload: dict) -> dict:
        """腾讯地图接口常见结构是 {status, result}，这里取出业务 result。"""
        if isinstance(payload, dict) and isinstance(payload.get("result"), dict):
            return payload["result"]
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _extract_adcode(payload: dict) -> str | None:
        """从 geocoder 返回中提取行政区划代码。"""
        if not isinstance(payload, dict):
            return None
        if payload.get("adcode"):
            return str(payload["adcode"])
        ad_info = payload.get("ad_info") or {}
        if isinstance(ad_info, dict) and ad_info.get("adcode"):
            return str(ad_info["adcode"])
        return None

    @staticmethod
    def _extract_lat_lng(payload: dict) -> tuple[float | None, float | None]:
        """从 geocoder 返回中提取 lat/lng，经纬度缺失时返回 None。"""
        if not isinstance(payload, dict):
            return None, None

        location = payload.get("location")
        if isinstance(location, dict):
            return location.get("lat"), location.get("lng")
        if isinstance(location, str) and "," in location:
            lat, lng = location.split(",", 1)
            return lat.strip(), lng.strip()

        lat = payload.get("lat") or payload.get("latitude")
        lng = payload.get("lng") or payload.get("longitude")
        return lat, lng
