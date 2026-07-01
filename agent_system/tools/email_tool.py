"""邮件生成工具 — LLM 写邮件内容 + 预览，发送由 HITL 确认环节完成"""
import re
from agent_system.tools.base import BaseTool, ToolContext
from agent_system.tools.email_whitelist import ALLOWED_RECIPIENTS
from util.email import generate_email_content
from util.log import get_logger

logger = get_logger(__name__)

_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')


class EmailTool(BaseTool):
    name = "email_tool"
    description = "根据用户需求生成邮件内容并展示预览，经用户确认后发送"
    inputs_schema = {"prompt": str, "receiver": str}

    def run(self, ctx: ToolContext) -> dict:
        prompt = ctx.params.get("prompt", "")
        receiver = ctx.params.get("receiver", "")

        if not prompt:
            return {"success": False, "error": "未提供邮件内容描述"}

        # 如果未显式指定收件人，尝试从 prompt 中提取邮箱地址
        if not receiver:
            found = _EMAIL_RE.findall(prompt)
            if found:
                receiver = found[0]
                logger.info("从消息中自动提取收件人邮箱: %s", receiver)

        if not receiver:
            return {"success": False, "error": "未指定收件人邮箱，请在消息中包含收件人邮箱地址"}

        # 白名单校验
        if receiver not in ALLOWED_RECIPIENTS:
            logger.warning("邮件工具收件人不在白名单中: %s", receiver)
            return {
                "success": False,
                "status": "blocked",
                "error": f"收件人 {receiver} 不在允许列表内，当前仅支持发送至: {', '.join(ALLOWED_RECIPIENTS)}",
            }

        # Supervisor 多 Agent 协作场景下，邮件工具可以读取上游通勤结果，把路线摘要带入邮件正文生成。
        commute_context = _build_commute_context(ctx.upstream_results.get("commute_plan_tool"))
        if commute_context:
            prompt = f"{prompt}\n\n请在邮件中结合以下通勤规划结果：\n{commute_context}"

        # 调用 LLM 生成邮件内容
        try:
            content = generate_email_content(prompt)
        except Exception as e:
            logger.exception("邮件内容生成失败: %s", e)
            return {"success": False, "error": f"邮件内容生成失败: {e}"}

        logger.info("邮件预览已生成: receiver=%s, subject=%s", receiver, content.get("subject", "")[:40])
        return {
            "success": True,
            "status": "awaiting_confirmation",
            "preview": {
                "subject": content["subject"],
                "body": content["body"],
                "receiver": receiver,
            },
        }


def _build_commute_context(result: dict | None) -> str:
    """把通勤工具结果压缩成邮件可读摘要，避免把整段 JSON 塞给 LLM。"""
    if not isinstance(result, dict) or not result.get("success"):
        return ""
    lines = [
        f"起点：{result.get('origin_text', '')}",
        f"终点：{result.get('destination_text', '')}",
    ]
    for route in result.get("routes", [])[:3]:
        if route.get("success"):
            lines.append(
                f"{route.get('label', route.get('mode', '路线'))}："
                f"{route.get('duration_text', '耗时未知')}，{route.get('distance_text', '距离未知')}"
            )
    if result.get("weather_reminder"):
        lines.append(f"天气提醒：{result['weather_reminder']}")
    return "\n".join(item for item in lines if item.strip("："))
