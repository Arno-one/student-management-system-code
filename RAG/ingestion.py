"""
文档解析、清洗、切片、Embedding、入库 的完整离线管线。

支持三种数据源：
  1. 四大名著 txt 文件 → 章回解析 → 切片 → 入库 (source_type="txt")
  2. Q&A 问答对 markdown → 解析 JSON → 入库 (source_type="qa")
  3. 通用 markdown 文档 → 按 ## 标题分节 → 切片 → 入库 (source_type="md")
"""
import json
import re
import time
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from RAG.config import config
from RAG.clients import embed_texts, get_milvus_client
from RAG.schemas import get_or_create_collection, load_collection
from util.log import get_logger

logger = get_logger(__name__)

# 四大名著文件在 RAG/docs/ 目录下
_DOCS_DIR = Path(__file__).resolve().parent / "docs"

# 章回标题正则：匹配 "第一回" ~ "第一百二十回"
_CHAPTER_RE = re.compile(r"^第[一二三四五六七八九十百千零\d]+回")

# 通用 Markdown 二级标题正则
_MD_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _find_novel_files() -> list[Path]:
    """扫描 docs 目录，返回四大名著 txt 文件路径"""
    files = sorted(_DOCS_DIR.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"未在 {_DOCS_DIR} 找到任何 txt 文件")
    logger.info("发现 %d 个文档文件: %s", len(files), [f.name for f in files])
    return files


def _find_qa_files() -> list[Path]:
    """扫描 docs 目录，返回 Q&A 问答对 markdown 文件路径"""
    files = sorted(_DOCS_DIR.glob("*Q&A*.md"))
    logger.info("发现 %d 个 QA 文件: %s", len(files), [f.name for f in files])
    return files


def _find_generic_md_files() -> list[Path]:
    """递归扫描 docs 目录，返回非 Q&A 的普通 markdown 文件"""
    all_md = sorted(_DOCS_DIR.rglob("*.md"))
    qa_names = {f.name for f in _find_qa_files()}
    files = [f for f in all_md if f.name not in qa_names]
    if files:
        logger.info("发现 %d 个通用 Markdown 文件: %s", len(files), [str(f.relative_to(_DOCS_DIR)) for f in files])
    return files


def _parse_md_sections(text: str) -> list[tuple[str, str]]:
    """
    按 ## 二级标题将 Markdown 文档切分为逻辑节。

    每个节 = (section_title, section_content)。
    ## 之前的内容作为"文档前言"处理。
    """
    # 找到所有 ## 标题的位置
    matches = list(_MD_H2_RE.finditer(text))
    if not matches:
        return [("全文", text.strip())]

    sections = []
    # 前言：第一个 ## 之前的内容
    preamble = text[:matches[0].start()].strip()
    if preamble:
        sections.append(("前言", preamble))

    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((title, body))

    return sections


def _parse_qa_file(filepath: Path) -> list[dict]:
    """
    解析单个 QA markdown 文件，返回 QA 对列表。

    文件格式：markdown 标题 + JSON 数组，尾部可能有备注。
    """
    text = filepath.read_text(encoding="utf-8")
    # 去掉标题行
    text = re.sub(r"^# .*\n", "", text)
    # 修复 markdown JSON 转义
    text = text.replace("\\[", "[").replace("\\]", "]")
    text = text.replace("\\{", "{").replace("\\}", "}")
    text = text.replace("\\&", "&")
    # 去除非法 JSON 转义（保留合法转义 \" \\ \/ \b \f \n \r \t \u）
    text = re.sub(r'\\(?!["\\/bfnrtu])', "", text)
    text = text.strip()

    # 切除 JSON 数组结束 ] 之后的尾部内容（备注等）
    last_bracket = text.rfind("]")
    if last_bracket >= 0:
        text = text[:last_bracket + 1]

    pairs = json.loads(text)
    # 过滤无效条目
    valid = [p for p in pairs if all(p.get(k) for k in ("question", "answer", "reason"))]
    if len(valid) != len(pairs):
        logger.warning("%s: %d/%d 条有效", filepath.name, len(valid), len(pairs))
    return valid


def _parse_chapters(text: str, max_chapters: int | None) -> list[tuple[str, int]]:
    """
    按章回标题切分文本。

    Returns:
        [(chapter_text, chapter_number), ...]
    """
    lines = text.splitlines()
    chapters = []
    current_lines = []
    current_chapter_num = 0
    in_preamble = True  # 第一回标题之前的内容（序言等）

    for line in lines:
        line = line.strip()
        match = _CHAPTER_RE.match(line)
        if match:
            # 保存上一个章节
            if current_lines and current_chapter_num > 0:
                chapters.append(("\n".join(current_lines), current_chapter_num))
            elif current_lines and current_chapter_num == 0:
                # 序言内容，跳过或作为第0章保存
                pass

            current_chapter_num += 1
            if max_chapters and current_chapter_num > max_chapters:
                break
            current_lines = [line]
            in_preamble = False
        elif not in_preamble:
            current_lines.append(line)

    # 最后一个章节
    if current_lines and current_chapter_num > 0:
        if not max_chapters or current_chapter_num <= max_chapters:
            chapters.append(("\n".join(current_lines), current_chapter_num))

    return chapters


def _clean_text(text: str) -> str:
    """基础清洗：去连续空行、去首尾空白"""
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)  # 最多保留一个空行
    text = re.sub(r" {3,}", "  ", text)      # 多余空格压缩
    return text


def _split_chunks(text: str) -> list[str]:
    """将文本按配置切片"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
        separators=["\n\n", "\n", "。", "，", " ", ""],
    )
    return splitter.split_text(text)


def ingest_documents(drop_existing: bool = False) -> dict:
    """
    完整入库管线：读取文档 → 清洗 → 切片 → Embedding → 写入 Milvus。

    Args:
        drop_existing: True 则重建 Collection

    Returns:
        {"total_chunks": N, "files": [...], "qa_files": [...], "elapsed_seconds": float}
    """
    t_start = time.time()
    max_ch = config.max_chapters
    chapter_info = f"前 {max_ch} 回" if max_ch else "全部"

    # --- 1. 准备 Collection ---
    collection = get_or_create_collection(drop_existing=drop_existing)

    # --- 2. 扫描文件 ---
    novel_files = _find_novel_files()
    qa_files = _find_qa_files()

    # --- 3. 解析文档 → 切片 ---
    all_chunks = []  # [{text, file_name, doc_id, chunk_index, total_chunks, source_type, ...}]
    stats = []

    for filepath in novel_files:
        filename = filepath.name
        file_t0 = time.time()
        logger.info("开始处理: %s (%s)", filename, chapter_info)

        raw_text = filepath.read_text(encoding="utf-8")
        chapters = _parse_chapters(raw_text, max_ch)

        if not chapters:
            logger.warning("%s: 未解析到任何章回，跳过", filename)
            continue

        doc_chunks = 0
        for chapter_text, chapter_num in chapters:
            cleaned = _clean_text(chapter_text)
            chunks = _split_chunks(cleaned)
            total = len(chunks)

            for i, chunk_text in enumerate(chunks):
                all_chunks.append({
                    "doc_id": f"{filepath.stem}_{chapter_num:03d}",
                    "text": chunk_text,
                    "question": "",
                    "answer": "",
                    "reason": "",
                    "file_name": filename,
                    "chunk_index": i,
                    "total_chunks": total,
                    "source_type": "txt",
                    "created_at": int(time.time()),
                })
                doc_chunks += 1

        elapsed = time.time() - file_t0
        logger.info(
            "%s: %d 回 → %d chunks (%.1fs)",
            filename, len(chapters), doc_chunks, elapsed,
        )
        stats.append({"file": filename, "chapters": len(chapters), "chunks": doc_chunks})

    # --- 3b. 解析 QA 文件 → 转为 chunk 格式 ---
    qa_stats = []
    for filepath in qa_files:
        file_t0 = time.time()
        pairs = _parse_qa_file(filepath)

        if not pairs:
            logger.warning("%s: 无有效 QA 对，跳过", filepath.name)
            continue

        total = len(pairs)
        for i, pair in enumerate(pairs):
            search_text = f"{pair['question']} {pair['answer']} {pair['reason']}"
            all_chunks.append({
                "doc_id": f"{filepath.stem}_qa_{i:03d}",
                "text": search_text,
                "question": pair["question"],
                "answer": pair["answer"],
                "reason": pair["reason"],
                "file_name": filepath.name,
                "chunk_index": i,
                "total_chunks": total,
                "source_type": "qa",
                "created_at": int(time.time()),
            })

        elapsed = time.time() - file_t0
        logger.info(
            "%s: %d 对 QA → %d 条 (%.1fs)",
            filepath.name, total, total, elapsed,
        )
        qa_stats.append({"file": filepath.name, "qa_pairs": total})

    # --- 3c. 解析通用 Markdown 文件 → 按 ## 分节 → 切片 ---
    md_files = _find_generic_md_files()
    md_stats = []
    for filepath in md_files:
        file_t0 = time.time()
        rel_path = str(filepath.relative_to(_DOCS_DIR))
        logger.info("开始处理 Markdown: %s", rel_path)

        raw_text = filepath.read_text(encoding="utf-8")
        # 去掉一级标题行（文件名已包含）
        raw_text = re.sub(r"^# .*\n", "", raw_text)
        sections = _parse_md_sections(raw_text)

        if not sections:
            logger.warning("%s: 未解析到任何节，跳过", rel_path)
            continue

        doc_chunks = 0
        for section_title, section_text in sections:
            cleaned = _clean_text(section_text)
            chunks = _split_chunks(cleaned)
            total = len(chunks)

            for i, chunk_text in enumerate(chunks):
                # 将节标题作为上下文前缀拼入 chunk，提升检索召回质量
                enriched = f"【{section_title}】{chunk_text}"
                all_chunks.append({
                    "doc_id": f"{filepath.stem}_sec_{doc_chunks + i:03d}",
                    "text": enriched,
                    "question": "",
                    "answer": "",
                    "reason": "",
                    "file_name": rel_path,
                    "chunk_index": i,
                    "total_chunks": total,
                    "source_type": "md",
                    "created_at": int(time.time()),
                })
            doc_chunks += total

        elapsed = time.time() - file_t0
        logger.info(
            "%s: %d 节 → %d chunks (%.1fs)",
            rel_path, len(sections), doc_chunks, elapsed,
        )
        md_stats.append({"file": rel_path, "sections": len(sections), "chunks": doc_chunks})

    if not all_chunks:
        logger.warning("没有生成任何 chunk，入库终止")
        return {"total_chunks": 0, "files": stats, "qa_files": qa_stats, "elapsed_seconds": time.time() - t_start}

    doc_count = sum(1 for c in all_chunks if c["source_type"] == "txt")
    qa_count = sum(1 for c in all_chunks if c["source_type"] == "qa")
    md_count = sum(1 for c in all_chunks if c["source_type"] == "md")
    logger.info("共 %d 个条目 (%d 文档 + %d QA + %d MD)，开始批量 Embedding...", len(all_chunks), doc_count, qa_count, md_count)

    # --- 4. 批量 Embedding ---
    texts = [c["text"] for c in all_chunks]
    vectors = embed_texts(texts)

    if len(vectors) != len(all_chunks):
        raise RuntimeError(
            f"Embedding 返回数量 ({len(vectors)}) 与 chunk 数量 ({len(all_chunks)}) 不一致"
        )

    # --- 5. 组装插入数据 ---
    insert_data = []
    for chunk, vector in zip(all_chunks, vectors):
        if len(vector) != config.embedding_dimension:
            raise RuntimeError(
                f"向量维度 {len(vector)} 与配置 {config.embedding_dimension} 不一致"
            )
        insert_data.append({
            "doc_id": chunk["doc_id"],
            "text": chunk["text"],
            "question": chunk["question"],
            "answer": chunk["answer"],
            "reason": chunk["reason"],
            "file_name": chunk["file_name"],
            "chunk_index": chunk["chunk_index"],
            "total_chunks": chunk["total_chunks"],
            "source_type": chunk["source_type"],
            "created_at": chunk["created_at"],
            "dense_vector": vector,
        })

    # --- 6. 批量写入 Milvus ---
    client = get_milvus_client()
    batch_size = 500
    for i in range(0, len(insert_data), batch_size):
        batch = insert_data[i:i + batch_size]
        client.insert(collection_name=config.milvus_collection_name, data=batch)
        logger.debug("插入 batch %d/%d", i // batch_size + 1, (len(insert_data) + batch_size - 1) // batch_size)

    client.flush(config.milvus_collection_name)
    logger.info("数据已 flush 到 Milvus")

    # --- 7. 加载 ---
    load_collection(collection)

    total_elapsed = time.time() - t_start
    logger.info(
        "入库完成: %d 条 (%d 文档 + %d QA + %d MD), 耗时 %.1fs",
        len(insert_data), doc_count, qa_count, md_count, total_elapsed,
    )
    return {
        "total_chunks": len(insert_data),
        "files": stats,
        "qa_files": qa_stats,
        "md_files": md_stats,
        "elapsed_seconds": round(total_elapsed, 2),
    }
