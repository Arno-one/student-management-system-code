"""
批量评测模块。

评测集采用结构化 JSON，支持按回答模式、关键词、来源类型等规则自动判定通过失败。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from RAG.ask_service import ask_question
from RAG.config import config


@dataclass
class EvaluationCase:
    """单条评测用例。"""

    question: str
    expected_mode: str
    must_include: list[str] = field(default_factory=list)
    must_not_include: list[str] = field(default_factory=list)
    expected_source_type: str | None = None
    note: str = ""


def load_cases(kb_id: str) -> list[EvaluationCase]:
    """从当前知识库配置的评测文件中加载用例。"""
    with config.use_kb(kb_id):
        eval_file = config.current_kb.eval_file
        if not eval_file:
            raise FileNotFoundError(f"知识库 {kb_id} 未配置评测文件")

        payload = json.loads(Path(eval_file).read_text(encoding="utf-8"))
        return [EvaluationCase(**item) for item in payload]


def evaluate_kb(kb_id: str, enable_rerank: bool | None = None) -> dict:
    """批量执行评测并返回结构化报告。"""
    cases = load_cases(kb_id)
    rows = []
    passed = 0

    for index, case in enumerate(cases, start=1):
        result = ask_question(case.question, kb_id=kb_id, enable_rerank=enable_rerank)
        answer = result["answer"]
        trace = result["trace"]
        citations = result["citations"]

        reasons = []
        if trace.get("answer_mode") != case.expected_mode:
            reasons.append(f"回答模式不匹配: expected={case.expected_mode}, actual={trace.get('answer_mode')}")

        for keyword in case.must_include:
            if keyword not in answer:
                reasons.append(f"缺少必含关键词: {keyword}")

        for keyword in case.must_not_include:
            if keyword in answer:
                reasons.append(f"出现禁用关键词: {keyword}")

        if case.expected_source_type and not any(
            citation.get("source_type") == case.expected_source_type for citation in citations
        ):
            reasons.append(f"未命中预期来源类型: {case.expected_source_type}")

        row_passed = not reasons
        if row_passed:
            passed += 1

        rows.append(
            {
                "index": index,
                "question": case.question,
                "passed": row_passed,
                "reasons": reasons,
                "expected_mode": case.expected_mode,
                "actual_mode": trace.get("answer_mode"),
                "answer": answer,
                "citations": citations,
                "note": case.note,
            }
        )

    return {
        "kb_id": kb_id,
        "total": len(cases),
        "passed": passed,
        "failed": len(cases) - passed,
        "pass_rate": round((passed / len(cases)) * 100, 2) if cases else 0.0,
        "rows": rows,
    }
