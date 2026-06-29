"""周边生活服务输入解析 — 识别地点、服务类型、半径和结果数量。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent_system.middleware.commute_parser import normalize_geocode_address


@dataclass
class NearbyServiceRequest:
    """周边服务推荐请求的结构化结果。"""

    is_nearby: bool
    center_text: str | None = None
    query_text: str | None = None
    keyword: str | None = None
    radius_meters: int = 2000
    limit: int = 10
    missing_fields: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return self.is_nearby and not self.missing_fields


_NEARBY_KEYWORDS = ["附近", "周边", "旁边", "周围"]
_COMMUTE_HINTS = ["怎么去", "如何去", "路线", "通勤", "到达", "坐地铁", "坐公交", "开车", "步行"]
_SERVICE_QUERY_HINTS = ["有没有", "有哪些", "有什么", "有啥", "推荐"]
_AMBIGUOUS_CENTERS = {
    "我",
    "我这",
    "我这里",
    "当前位置",
    "这里",
    "学校",
    "校区",
    "公司",
    "实习公司",
    "实习单位",
    "单位",
}
_DEFAULT_RADIUS_METERS = 2000
_MAX_RADIUS_METERS = 5000
_DEFAULT_LIMIT = 10
_MAX_LIMIT = 10

_KEYWORD_ALIASES = [
    # 把学生常用的口语问法归一到地图更稳定的 POI 类目，避免用“好吃”这类泛词直接搜空。
    (["餐饮", "吃饭", "餐厅", "饭店", "小吃", "美食", "吃的", "吃饭的地方", "好吃", "好吃的", "吃啥", "吃什么"], "餐饮"),
    (["医院", "诊所", "看病", "医疗"], "医疗"),
    (["药店", "买药", "药房"], "药店"),
    (["打印", "复印", "打印店", "复印店"], "打印店"),
    (["银行", "ATM", "atm"], "银行"),
    (["地铁", "地铁站"], "地铁站"),
    (["公交", "公交站", "巴士站"], "公交站"),
    (["便利店", "超市", "商店"], "便利店"),
]


def parse_nearby_request(message: str) -> NearbyServiceRequest:
    """从自然语言里解析周边服务查询的地点、关键词、半径和返回数量。"""
    text = (message or "").strip()
    is_nearby = _is_nearby_intent(text)
    center, query = _extract_center_and_query(text) if is_nearby else (None, None)
    center = _clean_center(center)
    query = _clean_query(query)
    keyword = _normalize_keyword(query)
    radius = _extract_radius(text)
    limit = _extract_limit(text)

    missing = []
    if is_nearby:
        if not center or _is_ambiguous_center(center):
            missing.append("center")
        if not keyword:
            missing.append("query")

    return NearbyServiceRequest(
        is_nearby=is_nearby,
        center_text=center,
        query_text=query,
        keyword=keyword,
        radius_meters=radius,
        limit=limit,
        missing_fields=missing,
    )


def build_nearby_clarification_message(parsed: NearbyServiceRequest) -> str:
    """根据缺失字段生成周边服务查询的澄清提示。"""
    if "center" in parsed.missing_fields and "query" in parsed.missing_fields:
        return "我还需要你补充要查询的地点和服务类型。比如：腾讯滨海大厦附近有什么吃饭的地方？"
    if "center" in parsed.missing_fields:
        service = parsed.keyword or parsed.query_text or "这类服务"
        return f"你想查哪个地点附近的{service}？可以补充学校、公司、小区或具体地标。"
    if "query" in parsed.missing_fields:
        center = parsed.center_text or "这个地点"
        return f"你想找{center}附近的哪类地点？比如吃饭、医院、打印店、银行或地铁站。"
    return "请补充更具体的地点和服务类型后再试。"


def normalize_nearby_center(center: str | None) -> str:
    """复用地图地址补全规则，让“宝安/天河”等短区名更容易解析。"""
    return normalize_geocode_address(center or "")


def _is_nearby_intent(text: str) -> bool:
    if not text:
        return False
    # “从 A 到 B 怎么去”这类强通勤句优先交给通勤规划，不抢意图。
    if "从" in text and "到" in text and any(hint in text for hint in _COMMUTE_HINTS):
        return False
    if any(word in text for word in _NEARBY_KEYWORDS):
        return True
    # 兼容“某地点有什么餐饮推荐”这类自然问法：没有“附近/周边”，但同时包含服务类目和查询动词。
    return _has_known_service_keyword(text) and any(hint in text for hint in _SERVICE_QUERY_HINTS)


def _extract_center_and_query(text: str) -> tuple[str | None, str | None]:
    for marker in _NEARBY_KEYWORDS:
        idx = text.find(marker)
        if idx < 0:
            continue
        center = text[:idx]
        query = text[idx + len(marker):]
        return center, query
    for marker in _SERVICE_QUERY_HINTS:
        idx = text.find(marker)
        if idx <= 0:
            continue
        center = text[:idx]
        query = text[idx + len(marker):]
        return center, query
    return None, None


def _clean_center(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip(" ，。；;？?的")
    prefixes = ["帮我找", "帮我查", "查一下", "查询", "找一下", "找", "请问", "我想知道"]
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    return cleaned.strip(" ，。；;？?的") or None


def _clean_query(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip(" ，。；;？?的")
    for word in ["有没有", "有哪些", "有什么", "有啥", "有", "推荐", "可以", "能", "吗", "呢"]:
        cleaned = cleaned.replace(word, "")
    for word in ["的地方", "地方", "服务", "店铺", "地点"]:
        cleaned = cleaned.replace(word, "")
    cleaned = re.sub(r"\d+\s*(?:米|公里|千米|km|KM|m|M)(?:内|以内)?", "", cleaned)
    return cleaned.strip(" ，。；;？?的") or None


def _normalize_keyword(query: str | None) -> str | None:
    if not query:
        return None
    for aliases, keyword in _KEYWORD_ALIASES:
        if any(alias in query for alias in aliases):
            return keyword
    return query


def _has_known_service_keyword(text: str) -> bool:
    """判断文本里是否包含已知生活服务类目，辅助识别省略“附近”的 POI 问法。"""
    return any(alias in text for aliases, _ in _KEYWORD_ALIASES for alias in aliases)


def _is_ambiguous_center(center: str) -> bool:
    cleaned = center.strip(" ，。；;？?的")
    return cleaned in _AMBIGUOUS_CENTERS


def _extract_radius(text: str) -> int:
    match = re.search(r"(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>公里|千米|km|KM|米|m|M)(?:内|以内)?", text)
    if not match:
        return _DEFAULT_RADIUS_METERS
    num = float(match.group("num"))
    unit = match.group("unit")
    meters = int(num * 1000) if unit in {"公里", "千米", "km", "KM"} else int(num)
    return min(max(meters, 1), _MAX_RADIUS_METERS)


def _extract_limit(text: str) -> int:
    match = re.search(r"(?:前|最多|返回)?\s*(?P<num>\d{1,2})\s*(?:个|家|条|处)", text)
    if not match:
        return _DEFAULT_LIMIT
    return min(max(int(match.group("num")), 1), _MAX_LIMIT)
