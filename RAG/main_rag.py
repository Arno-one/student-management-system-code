"""
RAG 命令行入口。

这里统一承接多知识库命令，避免再维护第二套独立脚本。
"""
from __future__ import annotations

import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from util.log import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def _resolve_kb(args) -> str:
    """统一处理命令行上的 kb 参数。"""
    from RAG.config import config

    return getattr(args, "kb", None) or config.default_kb_id


def cmd_ingest(args):
    """文档入库命令。"""
    from RAG.config import config
    from RAG.ingestion import ingest_documents

    kb_id = _resolve_kb(args)
    ingest_all = getattr(args, "all", False)
    with config.use_kb(kb_id):
        original_max_chapters = config.max_chapters
        if ingest_all and kb_id == "novels":
            config.max_chapters = None
            print("模式: novels 全部章节入库")
        elif kb_id == "novels":
            print(f"模式: novels 仅处理前 {config.max_chapters} 回")

        if args.drop:
            print(f"警告: 将删除 {config.milvus_collection_name} 后重建")

        try:
            result = ingest_documents(drop_existing=args.drop)
        finally:
            config.max_chapters = original_max_chapters
        print("\n入库完成:")
        print(f"  知识库: {kb_id}")
        print(f"  Collection: {result['collection_name']}")
        print(f"  总 chunks: {result['total_chunks']}")
        print(f"  耗时: {result['elapsed_seconds']:.1f}s")
        print(f"  来源统计: {result.get('source_counts', {})}")


def cmd_ask(args):
    """单次问答命令。"""
    from RAG.ask_service import ask_question

    kb_id = _resolve_kb(args)
    result = ask_question(
        question=args.question,
        kb_id=kb_id,
        enable_rerank=not args.no_rerank if args.no_rerank else None,
    )

    print(f"知识库: {kb_id}")
    print(f"问题: {args.question}")
    print(f"改写: {result.get('rewritten_query') or '无'}")
    print(f"模式: {result['trace'].get('answer_mode')}")
    print(f"\n回答:\n{result['answer']}")

    if result["citations"]:
        print("\n来源:")
        for citation in result["citations"]:
            print(
                f"  [来源 {citation['source_id']}] {citation['file_name']} "
                f"({citation.get('source_type', '')})"
            )

    print("\nTrace:")
    for key, value in result["trace"].items():
        print(f"  {key}: {value}")


def cmd_interactive(args):
    """交互问答模式。"""
    from RAG.ask_service import ask_question

    kb_id = _resolve_kb(args)
    print(f"RAG 交互问答模式，当前知识库: {kb_id}")
    print("输入 /quit 退出，输入 /status 查看知识库状态。\n")

    while True:
        try:
            question = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break

        if not question:
            continue
        if question.lower() in {"/quit", "/exit", "/q"}:
            print("再见。")
            break
        if question == "/status":
            cmd_status(args)
            continue

        result = ask_question(
            question=question,
            kb_id=kb_id,
            enable_rerank=not args.no_rerank if args.no_rerank else None,
        )
        print(f"\n助手({result['trace'].get('answer_mode')}):\n{result['answer']}\n")


def cmd_status(args):
    """查看当前知识库状态。"""
    from collections import Counter

    from RAG.clients import get_milvus_client
    from RAG.config import config

    kb_id = _resolve_kb(args)
    with config.use_kb(kb_id):
        client = get_milvus_client()
        collection_name = config.milvus_collection_name

        print(f"知识库: {kb_id}")
        print(f"Milvus: {config.milvus_uri}")
        print(f"数据库: {config.milvus_db_name}")
        print(f"Collection: {collection_name}")
        print(f"文档目录: {config.docs_dir}")

        if not client.has_collection(collection_name):
            print("Collection 不存在，请先执行 ingest。")
            return

        try:
            stats = client.get_collection_stats(collection_name)
            print(f"Chunk 总数: {stats.get('row_count', 'unknown')}")
        except Exception as exc:
            print(f"Chunk 总数获取失败: {exc}")

        try:
            rows = client.query(
                collection_name=collection_name,
                filter="id >= 0",
                output_fields=["file_name", "source_type"],
                limit=10000,
            )
            file_counter = Counter(row["file_name"] for row in rows)
            type_counter = Counter(row.get("source_type", "") for row in rows)
            print(f"来源类型统计: {dict(type_counter)}")
            print("文件分布:")
            for file_name, count in file_counter.most_common():
                print(f"  {file_name}: {count} chunks")
        except Exception as exc:
            print(f"文件分布获取失败: {exc}")


def cmd_health(args):
    """组件健康检查。"""
    from RAG.clients import embed_single, get_llm_client, get_milvus_client
    from RAG.config import config

    checks = {}

    try:
        checks["milvus"] = f"OK ({len(get_milvus_client().list_collections())} collections)"
    except Exception as exc:
        checks["milvus"] = f"FAIL: {exc}"

    try:
        embed_single("测试")
        checks["embedding"] = "OK"
    except Exception as exc:
        checks["embedding"] = f"FAIL: {exc}"

    try:
        llm = get_llm_client()
        llm.chat.completions.create(
            model=config.llm_rewrite_model,
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=10,
        )
        checks["llm"] = "OK"
    except Exception as exc:
        checks["llm"] = f"FAIL: {exc}"

    if config.enable_rerank:
        try:
            from RAG.clients import get_reranker

            get_reranker()
            checks["cross_encoder"] = "OK"
        except Exception as exc:
            checks["cross_encoder"] = f"FAIL: {exc}"
    else:
        checks["cross_encoder"] = "disabled"

    print("组件健康检查:")
    for name, status in checks.items():
        print(f"  {name}: {status}")


def cmd_eval(args):
    """批量评测命令。"""
    from RAG.evaluation import evaluate_kb

    kb_id = _resolve_kb(args)
    report = evaluate_kb(kb_id=kb_id, enable_rerank=not args.no_rerank if args.no_rerank else None)

    print(f"知识库: {report['kb_id']}")
    print(f"总用例: {report['total']}")
    print(f"通过: {report['passed']}")
    print(f"失败: {report['failed']}")
    print(f"通过率: {report['pass_rate']}%")

    for row in report["rows"]:
        status = "PASS" if row["passed"] else "FAIL"
        print(f"\n[{status}] Q{row['index']}: {row['question']}")
        print(f"  expected_mode={row['expected_mode']} actual_mode={row['actual_mode']}")
        if row["reasons"]:
            print(f"  reasons={'; '.join(row['reasons'])}")

    if report["failed"]:
        raise SystemExit(1)


def cmd_http_smoke(args):
    """很薄的一层 HTTP 冒烟测试：只验证接口是否能通到内部服务层。"""
    from fastapi.testclient import TestClient

    from main import app
    from RAG.evaluation import load_cases

    kb_id = _resolve_kb(args)
    question = args.question
    if not question:
        cases = load_cases(kb_id)
        question = cases[0].question if cases else "测试问题"

    client = TestClient(app)

    status_resp = client.get(f"/rag/kbs/{kb_id}/status")
    if status_resp.status_code != 200:
        print(f"状态接口失败: status={status_resp.status_code}, body={status_resp.text}")
        raise SystemExit(1)

    ask_payload = {
        "question": question,
        "enable_rerank": False if args.no_rerank else None,
        "top_k": None,
    }
    ask_resp = client.post(f"/rag/kbs/{kb_id}/ask", json=ask_payload)
    if ask_resp.status_code != 200:
        print(f"问答接口失败: status={ask_resp.status_code}, body={ask_resp.text}")
        raise SystemExit(1)

    body = ask_resp.json()
    data = body.get("data") or {}
    answer = data.get("answer", "")
    trace = data.get("trace") or {}
    if not answer:
        print(f"问答接口返回空答案: body={body}")
        raise SystemExit(1)

    print("HTTP 冒烟通过:")
    print(f"  知识库: {kb_id}")
    print(f"  问题: {question}")
    print(f"  模式: {trace.get('answer_mode')}")
    print(f"  回答预览: {answer[:120]}")


def cmd_rebuild_and_eval(args):
    """整库重建并串行跑批量评测。"""
    args.drop = True
    cmd_ingest(args)
    print("\n开始执行评测...\n")
    cmd_eval(args)


def main():
    from RAG.config import config

    parser = argparse.ArgumentParser(description="多知识库 RAG 命令行入口")
    subparsers = parser.add_subparsers(dest="command")

    def add_kb_argument(command_parser):
        command_parser.add_argument(
            "--kb",
            default=config.default_kb_id,
            choices=sorted(config.knowledge_bases),
            help="要操作的知识库 ID",
        )

    ingest_parser = subparsers.add_parser("ingest", help="文档入库")
    add_kb_argument(ingest_parser)
    ingest_parser.add_argument("--drop", action="store_true", help="删除已有数据后重建")
    ingest_parser.add_argument("--all", action="store_true", help="novels 知识库处理全部章节")

    ask_parser = subparsers.add_parser("ask", help="单次问答")
    add_kb_argument(ask_parser)
    ask_parser.add_argument("question", help="问题内容")
    ask_parser.add_argument("--no-rerank", action="store_true", help="关闭精排")

    interactive_parser = subparsers.add_parser("interactive", help="交互问答模式")
    add_kb_argument(interactive_parser)
    interactive_parser.add_argument("--no-rerank", action="store_true", help="关闭精排")

    status_parser = subparsers.add_parser("status", help="查看知识库状态")
    add_kb_argument(status_parser)

    health_parser = subparsers.add_parser("health", help="组件健康检查")
    add_kb_argument(health_parser)

    eval_parser = subparsers.add_parser("eval", help="执行结构化批量评测")
    add_kb_argument(eval_parser)
    eval_parser.add_argument("--no-rerank", action="store_true", help="关闭精排")

    smoke_http_parser = subparsers.add_parser("smoke-http", help="执行很薄的 HTTP 冒烟测试")
    add_kb_argument(smoke_http_parser)
    smoke_http_parser.add_argument("question", nargs="?", help="可选：指定一条冒烟问题")
    smoke_http_parser.add_argument("--no-rerank", action="store_true", help="关闭精排")

    rebuild_eval_parser = subparsers.add_parser("rebuild-and-eval", help="整库重建并串行执行评测")
    add_kb_argument(rebuild_eval_parser)
    rebuild_eval_parser.add_argument("--no-rerank", action="store_true", help="关闭精排")

    args = parser.parse_args()

    if args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "ask":
        cmd_ask(args)
    elif args.command == "interactive":
        cmd_interactive(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "health":
        cmd_health(args)
    elif args.command == "eval":
        cmd_eval(args)
    elif args.command == "smoke-http":
        cmd_http_smoke(args)
    elif args.command == "rebuild-and-eval":
        cmd_rebuild_and_eval(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
