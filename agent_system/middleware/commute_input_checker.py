"""通勤规划输入完整性检查节点。"""
from agent_system.middleware.commute_parser import build_clarification_message, parse_commute_request
from agent_system.middleware.middleware_schema import MiddlewareResult


def check(message: str) -> MiddlewareResult:
    """通勤类请求缺少起点、终点或出行方式时，直接返回澄清。"""
    parsed = parse_commute_request(message)
    if not parsed.is_commute:
        return MiddlewareResult(decision="pass", original_message=message)

    metadata = {
        "commute": {
            "origin_text": parsed.origin_text,
            "destination_text": parsed.destination_text,
            "city_context": parsed.city_context,
            "travel_modes": parsed.travel_modes,
            "departure_time_text": parsed.departure_time_text,
            "missing_fields": parsed.missing_fields,
        }
    }
    if parsed.is_complete:
        return MiddlewareResult(decision="pass", original_message=message, metadata=metadata)

    return MiddlewareResult(
        decision="clarification",
        original_message=message,
        clarification_message=build_clarification_message(parsed),
        metadata=metadata,
    )
