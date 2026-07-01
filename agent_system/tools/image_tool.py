"""文生图工具 - 复用现有工作台文生图能力，输出 Agent 图片卡片所需结构。"""
from agent_system.tools.base import BaseTool, ToolContext
from service.work_service import generate_image
from util.log import get_logger

logger = get_logger(__name__)


class ImageTool(BaseTool):
    name = "image_tool"
    description = "根据用户提示词生成一张图片，返回图片链接和提示词信息"
    inputs_schema = {"prompt": str}

    def run(self, ctx: ToolContext) -> dict:
        prompt = str(ctx.params.get("prompt", "")).strip()
        if not prompt:
            return {"success": False, "error": "未提供文生图提示词"}

        try:
            result = generate_image(prompt)
        except Exception as exc:
            logger.exception("文生图工具执行异常: %s", exc)
            return {"success": False, "error": f"文生图生成失败: {exc}"}

        if result.get("success") and result.get("image_url"):
            logger.info("文生图工具执行成功: prompt=%s", prompt[:60])
            return {
                "success": True,
                "status": "success",
                "provider": "qwen_image",
                "model": "qwen-image-2.0-pro",
                "prompt": prompt,
                "image_url": result["image_url"],
                "error": None,
            }

        error = result.get("error") or "文生图生成失败"
        logger.warning("文生图工具执行失败: prompt=%s, error=%s", prompt[:60], error)
        return {
            "success": False,
            "status": "error",
            "provider": "qwen_image",
            "model": "qwen-image-2.0-pro",
            "prompt": prompt,
            "image_url": "",
            "error": error,
        }
