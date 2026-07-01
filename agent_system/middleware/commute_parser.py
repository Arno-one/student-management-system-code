"""通勤规划输入解析 — 中间件和工具共用同一套规则。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class CommuteRequest:
    """通勤规划请求的结构化结果。"""
    is_commute: bool
    origin_text: str | None = None
    destination_text: str | None = None
    city_context: str | None = None
    travel_modes: list[str] = field(default_factory=list)
    departure_time_text: str = "当前时间"
    missing_fields: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return self.is_commute and not self.missing_fields


_COMMUTE_KEYWORDS = [
    "通勤", "路线", "怎么去", "如何去", "到达", "出发", "公交", "地铁", "开车", "驾车", "步行", "走路",
]

_MODE_KEYWORDS = {
    "transit": ["公交", "地铁", "公共交通", "巴士"],
    "driving": ["开车", "驾车", "自驾"],
    "walking": ["步行", "走路", "走过去"],
}

_TIME_KEYWORDS = ["今天", "明天", "后天", "早高峰", "晚高峰", "上午", "中午", "下午", "晚上", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]

_DEFAULT_CITY = "深圳市"

_CITY_ALIASES = {
    "深圳": "深圳市",
    "深圳市": "深圳市",
    "广州": "广州市",
    "广州市": "广州市",
    "北京": "北京市",
    "北京市": "北京市",
    "上海": "上海市",
    "上海市": "上海市",
}

_CITY_DISTRICTS = {
    "深圳市": ["罗湖", "福田", "南山", "宝安", "龙岗", "盐田", "龙华", "坪山", "光明", "大鹏"],
    "广州市": ["越秀", "海珠", "荔湾", "天河", "白云", "黄埔", "番禺", "花都", "南沙", "从化", "增城"],
    "北京市": ["东城", "西城", "朝阳", "海淀", "丰台", "石景山", "通州", "昌平", "大兴", "顺义", "房山", "门头沟", "怀柔", "平谷", "密云", "延庆"],
    "上海市": ["黄浦", "徐汇", "长宁", "静安", "普陀", "虹口", "杨浦", "闵行", "宝山", "嘉定", "浦东", "金山", "松江", "青浦", "奉贤", "崇明"],
}


def parse_commute_request(message: str) -> CommuteRequest:
    """从自然语言里解析通勤规划必填项：起点、终点、出行方式。"""
    text = (message or "").strip()
    is_commute = any(keyword in text for keyword in _COMMUTE_KEYWORDS)
    origin, destination = _extract_origin_destination(text)
    city_context = _infer_city_context(text, origin, destination)
    modes = _extract_modes(text)
    departure_time = _extract_departure_time(text)

    missing = []
    if is_commute:
        if not origin:
            missing.append("origin")
        if not destination:
            missing.append("destination")
        if not modes:
            missing.append("travel_mode")
        if origin and destination and not city_context and _needs_city_context(origin, destination):
            missing.append("city_context")

    return CommuteRequest(
        is_commute=is_commute,
        origin_text=origin,
        destination_text=destination,
        city_context=city_context,
        travel_modes=modes,
        departure_time_text=departure_time,
        missing_fields=missing,
    )


def build_clarification_message(parsed: CommuteRequest) -> str:
    """根据缺失字段生成用户可执行的补充提示。"""
    label_map = {
        "origin": "起点",
        "destination": "终点",
        "travel_mode": "出行方式（公交/地铁、开车或步行）",
        "city_context": "城市信息",
    }
    missing = "、".join(label_map.get(item, item) for item in parsed.missing_fields)
    if "city_context" in parsed.missing_fields:
        return (
            f"我还需要你补充{missing}，才能准确规划路线。\n"
            "比如：从广州市天河区到番禺区坐地铁怎么去？"
        )
    return (
        f"我还需要你补充{missing}，才能帮你做通勤规划。\n"
        "你可以这样说：从学校到腾讯滨海大厦，坐地铁怎么去？"
    )


def normalize_geocode_address(address: str, city_context: str | None = None) -> str:
    """按城市上下文补全短行政区，提升 geocoder 稳定性。"""
    cleaned = (address or "").strip()
    if not cleaned:
        return cleaned

    city = city_context or _infer_city_context(cleaned)
    if city:
        district = _match_district(cleaned, city)
        if district:
            return f"{city}{district}区"
        return cleaned if cleaned.startswith(city) else cleaned

    district = _match_district(cleaned, _DEFAULT_CITY)
    if district:
        return f"{_DEFAULT_CITY}{district}区"
    return cleaned


def _extract_origin_destination(text: str) -> tuple[str | None, str | None]:
    """支持“从 A 到 B”和“起点 A 终点 B”两类常见说法。"""
    from_idx = text.find("从")
    to_idx = text.find("到", from_idx + 1) if from_idx >= 0 else -1
    if from_idx >= 0 and to_idx > from_idx:
        origin = text[from_idx + 1:to_idx]
        destination = _cut_destination_tail(text[to_idx + 1:])
        return _clean_place(origin), _clean_place(destination)

    origin = None
    destination = None
    origin_match = re.search(r"(?:起点|出发地|从)\s*[:：]?\s*(?P<origin>[^，。；;]+)", text)
    destination_match = re.search(r"(?:终点|目的地|到)\s*[:：]?\s*(?P<destination>[^，。；;]+)", text)
    if origin_match:
        origin = _clean_place(origin_match.group("origin"))
    if destination_match:
        destination = _clean_place(destination_match.group("destination"))
    return origin, destination


def _cut_destination_tail(value: str) -> str:
    """从“终点 + 出行方式/问句”片段里切出终点，避免把“龙岗”截成“龙”。"""
    stop_words = [
        "坐地铁", "坐公交", "乘地铁", "乘公交", "坐", "乘",
        "开车", "驾车", "自驾", "步行", "走路",
        "怎么去", "如何去", "通勤", "路线", "要多久", "需要多久",
    ]
    indexes = [value.find(word) for word in stop_words if value.find(word) >= 0]
    if indexes:
        value = value[:min(indexes)]
    return value


def _extract_modes(text: str) -> list[str]:
    modes = []
    for mode, keywords in _MODE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            modes.append(mode)
    return modes


def _extract_departure_time(text: str) -> str:
    for keyword in _TIME_KEYWORDS:
        if keyword in text:
            return keyword
    return "当前时间"


def _infer_city_context(*values: str | None) -> str | None:
    """从原句、起点、终点中提取明确城市上下文。"""
    joined = " ".join(value for value in values if value)
    # 长别名优先，避免“广州市”被“广州”提前命中后不一致。
    for alias in sorted(_CITY_ALIASES, key=len, reverse=True):
        if alias in joined:
            return _CITY_ALIASES[alias]
    return None


def _needs_city_context(origin: str, destination: str) -> bool:
    """非默认城市的短区名不盲猜，要求用户补充城市。"""
    for place in [origin, destination]:
        cleaned = _strip_city_prefix(place)
        if _match_district(cleaned, _DEFAULT_CITY):
            continue
        if any(_match_district(cleaned, city) for city in _CITY_DISTRICTS if city != _DEFAULT_CITY):
            return True
    return False


def _match_district(address: str, city: str) -> str | None:
    """匹配“天河 / 天河区 / 广州市天河”等行政区短写。"""
    cleaned = _strip_city_prefix(address).strip("区")
    for district in _CITY_DISTRICTS.get(city, []):
        if cleaned == district:
            return district
    return None


def _strip_city_prefix(address: str) -> str:
    cleaned = address.strip()
    for alias, city in sorted(_CITY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if cleaned.startswith(alias):
            return cleaned[len(alias):].strip()
    return cleaned


def _clean_place(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip(" ，。；;？?的")
    for word in ["坐地铁", "坐公交", "公交", "地铁", "开车", "驾车", "自驾", "步行", "走路"]:
        cleaned = cleaned.replace(word, "")
    return cleaned.strip(" ，。；;？?的") or None
