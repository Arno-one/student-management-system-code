"""周边生活服务输入完整性检查节点。"""
from agent_system.middleware.middleware_schema import MiddlewareResult
from agent_system.middleware.nearby_parser import build_nearby_clarification_message, parse_nearby_request


def check(message: str) -> MiddlewareResult:
    """周边服务类请求缺少地点或服务类型时，直接返回澄清。"""
    parsed = parse_nearby_request(message)
    if not parsed.is_nearby:
        return MiddlewareResult(decision="pass", original_message=message)

    metadata = {
        "intent": "nearby_service",
        "nearby": {
            "center_text": parsed.center_text,
            "query_text": parsed.query_text,
            "keyword": parsed.keyword,
            "radius_meters": parsed.radius_meters,
            "limit": parsed.limit,
            "missing_fields": parsed.missing_fields,
        },
    }
    if parsed.is_complete:
        return MiddlewareResult(decision="pass", original_message=message, metadata=metadata)

    return MiddlewareResult(
        decision="clarification",
        original_message=message,
        clarification_message=build_nearby_clarification_message(parsed),
        metadata=metadata,
    )
