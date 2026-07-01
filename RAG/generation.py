"""
LLM 答案生成模块：调用 Qwen 生成带来源引用的答案，含降级策略。
"""
import time
from RAG.config import config
from RAG.clients import get_llm_client
from util.log import get_logger

logger = get_logger(__name__)


def generate_answer(
    user_query: str,
    system_prompt: str,
    user_prompt: str,
    citations: list[dict],
) -> dict:
    """
    调用 LLM 生成答案。

    Returns:
        {
            "answer": str,
            "citations": [...],
            "model": str,
            "generate_ms": float,
            "fallback": bool,
        }
    """
    try:
        client = get_llm_client()
        t0 = time.time()

        response = client.chat.completions.create(
            model=config.llm_generate_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1500,
        )

        elapsed = (time.time() - t0) * 1000
        answer = response.choices[0].message.content.strip()
        usage = response.usage

        logger.info(
            "LLM 生成完成: model=%s, tokens(prompt=%d, completion=%d), %.0fms",
            config.llm_generate_model,
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
            elapsed,
        )

        return {
            "answer": answer,
            "citations": citations,
            "model": config.llm_generate_model,
            "generate_ms": round(elapsed, 1),
            "fallback": False,
        }

    except Exception as e:
        logger.error("LLM 生成失败: %s", e)
        return _fallback_answer(citations, str(e))


def _fallback_answer(citations: list[dict], error_msg: str) -> dict:
    """降级：LLM 不可用时返回检索结果原文"""
    previews = []
    for c in citations:
        previews.append(
            f"[来源 {c['source_id']}] {c['file_name']} "
            f"(chunk {c['chunk_index'] + 1}): {c['text_preview']}..."
        )

    fallback_text = (
        f"模型暂时不可用（{error_msg}）。以下是从知识库中检索到的最相关内容：\n\n"
        + "\n\n".join(previews)
    )

    return {
        "answer": fallback_text,
        "citations": citations,
        "model": "fallback",
        "generate_ms": 0,
        "fallback": True,
    }
