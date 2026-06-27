"""
RAG 知识库命令行入口。

用法：
    python -m RAG.main_rag ingest           # 入库（使用默认配置）
    python -m RAG.main_rag ingest --drop     # 删除旧数据后重新入库
    python -m RAG.main_rag ingest --all      # 全部章节
    python -m RAG.main_rag ask "孙悟空大闹天宫在第几回？"
    python -m RAG.main_rag ask --no-rerank "林黛玉进贾府"
    python -m RAG.main_rag interactive       # 交互问答模式
    python -m RAG.main_rag status            # 查看知识库状态
    python -m RAG.main_rag health            # 健康检查
"""
import argparse
import sys
import os
import time

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from util.log import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def cmd_ingest(args):
    """入库命令"""
    from RAG.config import config
    from RAG.ingestion import ingest_documents

    if args.all:
        config.max_chapters = None
        print("模式: 处理全部章节")
    else:
        print(f"模式: 每本书前 {config.max_chapters} 回")

    if args.drop:
        print("警告: 将删除已有数据后重新入库")

    result = ingest_documents(drop_existing=args.drop)
    print(f"\n入库完成:")
    print(f"  总 chunks: {result['total_chunks']}")
    print(f"  耗时: {result['elapsed_seconds']:.1f}s")
    for f in result["files"]:
        print(f"  {f['file']}: {f['chapters']}回 → {f['chunks']} chunks")


def cmd_ask(args):
    """单次问答"""
    from RAG.config import config
    from RAG.retrieval import rewrite_query, hybrid_search
    from RAG.clients import embed_single
    from RAG.rerank import rerank
    from RAG.prompt_builder import build_prompt
    from RAG.generation import generate_answer

    question = args.question
    if args.no_rerank:
        config.enable_rerank = False

    print(f"问题: {question}\n")
    t_total = time.time()

    # 1. 改写
    t0 = time.time()
    rewritten = rewrite_query(question)
    rewrite_ms = (time.time() - t0) * 1000
    print(f"[1/6] 查询改写 ({rewrite_ms:.0f}ms): {rewritten[:80]}")

    # 2. Embedding
    t0 = time.time()
    query_vector = embed_single(rewritten)
    embed_ms = (time.time() - t0) * 1000
    print(f"[2/6] Embedding ({embed_ms:.0f}ms)")

    # 3. 混合检索
    t0 = time.time()
    candidates = hybrid_search(rewritten, query_vector)
    search_ms = (time.time() - t0) * 1000
    print(f"[3/6] 混合检索 ({search_ms:.0f}ms): {len(candidates)} 个候选")

    # 4. 精排
    t0 = time.time()
    if config.enable_rerank:
        candidates = rerank(question, candidates)
        rerank_ms = (time.time() - t0) * 1000
        print(f"[4/6] CrossEncoder 精排 ({rerank_ms:.0f}ms): 保留 Top-{len(candidates)}")
    else:
        candidates = candidates[:config.rerank_top_k]
        print(f"[4/6] 精排已跳过")

    # 5. Prompt 组装
    prompt = build_prompt(question, candidates)
    print(f"[5/6] Prompt 组装: {prompt['context_tokens']} tokens, {len(prompt['context_blocks'])} blocks")

    # 6. 生成
    result = generate_answer(
        user_query=question,
        system_prompt=prompt["system_prompt"],
        user_prompt=prompt["user_prompt"],
        citations=prompt["citations"],
    )

    total_ms = (time.time() - t_total) * 1000
    print(f"[6/6] LLM 生成 ({result['generate_ms']:.0f}ms)")

    print(f"\n{'='*50}")
    print(f"回答 (总耗时 {total_ms:.0f}ms):\n")
    print(result["answer"])
    print(f"\n--- 来源 ---")
    for c in result["citations"]:
        print(f"  [{c['source_id']}] {c['file_name']} chunk {c['chunk_index']+1}: {c['text_preview']}...")


def cmd_interactive(args):
    """交互问答模式"""
    from RAG.config import config
    if args.no_rerank:
        config.enable_rerank = False

    print("四大名著 RAG 知识库 — 交互问答模式")
    print("输入问题开始对话，输入 /quit 退出，输入 /status 查看状态\n")

    from RAG.retrieval import rewrite_query, hybrid_search
    from RAG.clients import embed_single
    from RAG.rerank import rerank
    from RAG.prompt_builder import build_prompt
    from RAG.generation import generate_answer

    while True:
        try:
            question = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not question:
            continue
        if question.lower() in ("/quit", "/exit", "/q"):
            print("再见！")
            break
        if question == "/status":
            cmd_status(None)
            continue

        t_total = time.time()
        rewritten = rewrite_query(question)
        query_vector = embed_single(rewritten)
        candidates = hybrid_search(rewritten, query_vector)

        if config.enable_rerank:
            candidates = rerank(question, candidates)

        prompt = build_prompt(question, candidates)
        result = generate_answer(
            user_query=question,
            system_prompt=prompt["system_prompt"],
            user_prompt=prompt["user_prompt"],
            citations=prompt["citations"],
        )

        total_ms = (time.time() - t_total) * 1000
        print(f"\n助手 ({total_ms:.0f}ms):\n{result['answer']}\n")


def cmd_status(args):
    """状态查询"""
    from RAG.clients import get_milvus_client
    from RAG.config import config

    client = get_milvus_client()
    collection_name = config.milvus_collection_name

    print(f"Milvus: {config.milvus_uri}")
    print(f"数据库: {config.milvus_db_name}")
    print(f"Collection: {collection_name}")

    if client.has_collection(collection_name):
        try:
            stats = client.get_collection_stats(collection_name)
            print(f"Chunk 总数: {stats.get('row_count', 'unknown')}")
        except Exception as e:
            print(f"Chunk 总数: 获取失败 ({e})")

        # 文件分布
        try:
            results = client.query(
                collection_name=collection_name,
                filter="id >= 0",
                output_fields=["file_name"],
                limit=10000,
            )
            from collections import Counter
            file_counts = Counter(r["file_name"] for r in results)
            print("文件分布:")
            for fname, count in file_counts.most_common():
                print(f"  {fname}: {count} chunks")
        except Exception as e:
            print(f"文件分布: 获取失败 ({e})")
    else:
        print("Collection 不存在，请先执行 ingest 入库")

    print(f"\n配置:")
    print(f"  Embedding: {config.embedding_model} ({config.embedding_dimension}维)")
    print(f"  切片: {config.chunk_size}字 / 重叠{config.chunk_overlap}字")
    print(f"  精排: {'开启' if config.enable_rerank else '关闭'}")
    print(f"  每本处理: {config.max_chapters or '全部'}回")


def cmd_health(args):
    """健康检查"""
    from RAG.clients import get_milvus_client, embed_single, get_llm_client
    from RAG.config import config

    checks = {}

    # Milvus
    try:
        client = get_milvus_client()
        cols = client.list_collections()
        checks["milvus"] = f"OK ({len(cols)} collections)"
    except Exception as e:
        checks["milvus"] = f"FAIL: {e}"

    # Embedding
    try:
        embed_single("测试")
        checks["embedding"] = "OK"
    except Exception as e:
        checks["embedding"] = f"FAIL: {e}"

    # LLM
    try:
        llm = get_llm_client()
        resp = llm.chat.completions.create(
            model=config.llm_rewrite_model,
            messages=[{"role": "user", "content": "你好"}],
            max_tokens=10,
        )
        checks["llm"] = "OK"
    except Exception as e:
        checks["llm"] = f"FAIL: {e}"

    # CrossEncoder
    if config.enable_rerank:
        try:
            from RAG.clients import get_reranker
            get_reranker()
            checks["cross_encoder"] = "OK"
        except Exception as e:
            checks["cross_encoder"] = f"FAIL: {e}"
    else:
        checks["cross_encoder"] = "disabled"

    print("组件健康检查:")
    for name, status in checks.items():
        print(f"  {name}: {status}")


def main():
    parser = argparse.ArgumentParser(description="四大名著 RAG 知识库")
    sub = parser.add_subparsers(dest="command")

    # ingest
    p_ingest = sub.add_parser("ingest", help="文档入库")
    p_ingest.add_argument("--drop", action="store_true", help="删除已有数据后重建")
    p_ingest.add_argument("--all", action="store_true", help="处理全部章节（默认只处理前N回）")

    # ask
    p_ask = sub.add_parser("ask", help="单次问答")
    p_ask.add_argument("question", help="问题内容")
    p_ask.add_argument("--no-rerank", action="store_true", help="关闭精排")

    # interactive
    p_int = sub.add_parser("interactive", help="交互问答模式")
    p_int.add_argument("--no-rerank", action="store_true", help="关闭精排")

    # status
    sub.add_parser("status", help="查看知识库状态")

    # health
    sub.add_parser("health", help="组件健康检查")

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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
