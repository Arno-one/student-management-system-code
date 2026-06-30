"""腾讯地图 MCP 客户端底座。

这个模块只负责“发现和调用 MCP 工具”，业务工具仍然保留自己的兜底逻辑。
MCP SDK、腾讯地图 Key 或远端服务不可用时，都只记录状态，不影响主应用启动。
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from config import TENCENT_MAP_KEY, TENCENT_MAP_MCP_STARTUP_MODE
from util.log import get_logger

logger = get_logger(__name__)


class TencentMapMcpClient:
    """腾讯地图 MCP 可复用客户端。

    v2.1 先接天气查询，但这里保留通用 call_tool 能力，后续路线规划、地点检索等
    腾讯地图 MCP tool 可以直接复用这个底座。
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key if api_key is not None else TENCENT_MAP_KEY
        self.startup_mode = TENCENT_MAP_MCP_STARTUP_MODE
        self.endpoint = f"https://mcp.map.qq.com/mcp?key={self.api_key}&format=0" if self.api_key else ""
        self.enabled = bool(self.api_key) and self.startup_mode != "disabled"
        self.connected = False
        self.tools: list[dict[str, Any]] = []
        self.last_error: str | None = (
            "TENCENT_MAP_MCP_STARTUP_MODE=disabled" if self.startup_mode == "disabled" else None
        )
        self.last_success_at: str | None = None

    async def startup(self) -> None:
        """应用启动时探测 MCP 可用性；失败只降级，不向外抛异常。"""
        if self.startup_mode == "disabled":
            self._mark_disabled("TENCENT_MAP_MCP_STARTUP_MODE=disabled")
            return
        if not self.api_key:
            self._mark_disabled("未配置 TENCENT_MAP_KEY")
            return

        try:
            ClientSession, streamablehttp_client = self._load_sdk()
            async with streamablehttp_client(self.endpoint) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()

            self.tools = self._normalize_tools(tools_result)
            self.connected = True
            self.enabled = True
            self.last_error = None
            self.last_success_at = datetime.now().isoformat(timespec="seconds")
            logger.info("腾讯地图 MCP 初始化成功，可用工具数=%s", len(self.tools))
        except Exception as exc:
            self.enabled = bool(self.api_key)
            self.connected = False
            self.last_error = str(exc)
            logger.warning("腾讯地图 MCP 初始化失败，天气工具将使用 REST 兜底: %s", exc)

    async def shutdown(self) -> None:
        """应用关闭时标记 MCP 不再可用。"""
        self.connected = False

    async def ensure_connected(self) -> None:
        """首次使用 MCP 工具时按需连接，避免把远端探测放在应用启动关键路径里。"""
        if self.connected:
            return
        if not self.enabled:
            return
        await self.startup()

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """调用指定 MCP tool，统一返回 dict，便于业务工具做兼容处理。"""
        if not self.connected:
            await self.ensure_connected()
        if not self.connected:
            raise RuntimeError(self.last_error or "腾讯地图 MCP 未连接")

        ClientSession, streamablehttp_client = self._load_sdk()
        # 每次调用临时建立会话，避免复用启动阶段 session 时遇到跨事件循环问题。
        async with streamablehttp_client(self.endpoint) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
        self.last_success_at = datetime.now().isoformat(timespec="seconds")
        return self._normalize_call_result(result)

    def call_tool_sync(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """同步工具调用入口，适配当前 Agent Tool.run 的同步接口。"""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.call_tool(tool_name, arguments))
        raise RuntimeError("当前线程已有事件循环，无法同步调用腾讯地图 MCP")

    def health(self) -> dict[str, Any]:
        """返回 MCP 当前状态，供管理员监控接口读取。"""
        return {
            "provider": "tencent_map_mcp",
            "enabled": self.enabled,
            "connected": self.connected,
            "startup_mode": self.startup_mode,
            "endpoint": "https://mcp.map.qq.com/mcp?key=***&format=0" if self.api_key else "",
            "tool_count": len(self.tools),
            "tools": self.tools,
            "last_error": self.last_error,
            "last_success_at": self.last_success_at,
        }

    def find_tool_name(self, keywords: list[str]) -> str | None:
        """按关键字在已发现工具中找一个最可能匹配的 tool。"""
        lowered = [item.lower() for item in keywords]
        for tool in self.tools:
            name = str(tool.get("name") or "")
            desc = str(tool.get("description") or "")
            haystack = f"{name} {desc}".lower()
            if all(keyword in haystack for keyword in lowered):
                return name
        return None

    def _load_sdk(self):
        """延迟导入 MCP SDK；没安装时让客户端自动降级。"""
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
        except Exception as exc:
            raise RuntimeError("未安装 MCP Python SDK") from exc
        return ClientSession, streamablehttp_client

    def _mark_disabled(self, reason: str) -> None:
        self.enabled = False
        self.connected = False
        self.tools = []
        self.last_error = reason
        logger.info("腾讯地图 MCP 未启用: %s", reason)

    @staticmethod
    def _normalize_tools(tools_result: Any) -> list[dict[str, Any]]:
        raw_tools = getattr(tools_result, "tools", tools_result)
        if not isinstance(raw_tools, list):
            return []

        normalized = []
        for tool in raw_tools:
            if isinstance(tool, dict):
                normalized.append({
                    "name": tool.get("name"),
                    "description": tool.get("description"),
                })
            else:
                normalized.append({
                    "name": getattr(tool, "name", None),
                    "description": getattr(tool, "description", None),
                })
        return [item for item in normalized if item.get("name")]

    @staticmethod
    def _normalize_call_result(result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return result

        content = getattr(result, "content", None)
        if content is not None:
            return {
                "content": [
                    item.model_dump() if hasattr(item, "model_dump") else getattr(item, "__dict__", item)
                    for item in content
                ],
                "is_error": getattr(result, "isError", getattr(result, "is_error", False)),
                "raw": result,
            }
        return {"raw": result}


tencent_map_mcp_client = TencentMapMcpClient()
