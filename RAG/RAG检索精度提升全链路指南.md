# RAG 检索精度提升全链路指南：从检索前、检索中到检索后的工程实践

> 基于我自己写的真实项目的 RAG 知识库实际构建经验，系统梳理检索精度优化的方法、策略与取舍。

---

## 前言：RAG 检索的精度问题出在哪？

RAG（Retrieval-Augmented Generation）的核心公式看起来简单：检索相关文档 → 塞进 Prompt → LLM 生成答案。但真正落地时，每一个环节都可能成为精度瓶颈：

- **检索前**：文档切得太大导致语义稀释，用户问题太口语化导致关键词失配
- **检索中**：纯向量检索对专有名词不敏感，纯关键词检索又不懂同义词
- **检索后**：召回的结果冗余、重复，或者最相关的被埋在后面

本文按照"检索前 → 检索中 → 检索后"的时间线，逐一拆解我们在本项目中落地的方法和策略，以及它们的实际收益。

---

## 一、检索前：把数据准备好，把问题问清楚

检索前的优化是**成本最低、收益最大**的环节。输入端的一点点改进，能让后续所有环节都受益。

### 1.1 文档切片：粒度决定上限

**问题**：如果把一篇 5000 字的文档整段存入向量库，embedding 会被稀释为"平均语义"——一段讲 5 个主题的文字，向量指向的却是哪个都不精准的中间地带。

**我们的方案**：

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,       # 每段约 500 字
    chunk_overlap=50,     # 相邻段重叠 50 字，防止语义断裂
    separators=["\n\n", "\n", "。", "；", "，", " "],
    # 优先级：段落 → 句子 → 词，尽可能在语义边界上切
)
```

**关键设计决策**：

| 场景 | chunk_size | 理由 |
|------|-----------|------|
| 工程文档/技术规范 | 500 | 平衡语义完整性和检索精度 |
| 小说文本 | 按章节切分后再递归切 | 保留叙事结构 |
| QA 对 | 保持 question + answer + reasoning 完整 | 不做切分 |

**收益**：长文档场景下，检索精度质的提升。小切片让向量更精准，BM25 也不会因为关键词只出现在文档 5% 的位置而误判整段为相关。

### 1.2 Schema 设计：双向量字段 + BM25 自动化

**核心思路**：让 Milvus 自己维护稠密向量（语义）和稀疏向量（关键词）两套索引，插入时只需提供文本和 embedding，稀疏向量由 BM25 Function 自动生成。

```python
# 文本字段开启分词和匹配
schema.add_field(
    field_name="text", datatype=DataType.VARCHAR,
    max_length=2000,
    enable_analyzer=True,   # 启用内置分词器
    enable_match=True,      # 启用 BM25 文本匹配
)

# BM25 自动生成稀疏向量
bm25_function = Function(
    name="text_bm25",
    input_field_names=["text"],
    output_field_names=["sparse_vector"],
    function_type=FunctionType.BM25,
)
schema.add_function(bm25_function)
```

**关键设计决策——QA 集合的 search_text 字段**：

QA 集合有三个字段：`question`、`answer`、`reasoning`。用户查询可能命中任何一个字段的关键词。我们的做法是：

```python
# 插入时合并为 search_text
search_text = f"{question} {answer} {reasoning}"

# BM25 Function 绑定到 search_text，而不是只绑 question
```

这让 QA 检索的 BM25 召回率大幅提升——一个关于"变压器接线方式"的查询，即使问题字段里没出现"接线方式"，但只要答案或推理过程里提到了，就能命中。

### 1.3 批量并发 Embedding：入库效率 5-10x 提升

串行调 embedding API 在文档量上百时不可接受。我们用批量 API + asyncio 并发：

```python
# 批量调用，每批 10-25 条
def embed_texts(texts: list[str], batch_size: int = 10) -> list[list[float]]:
    all_vectors = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        result = TextEmbedding.call(
            model="text-embedding-v3",
            input=batch,
            dimension=1024,
        )
        all_vectors.extend([r["embedding"] for r in result["data"]])
    return all_vectors
```

**注意事项**：text-embedding-v3 输出 1024 维。如果后续需要降级到本地模型，必须确保维度一致，否则不能写入同一个 Collection。

### 1.4 查询改写：输入端放大器（10-50ms 换 10-20% Recall）

这是**性价比最高的单点优化**。

**问题**：用户输入"那个可以做向量搜索的数据库叫啥来着？"直接检索——BM25 找不到"Milvus"，语义向量也一头雾水。

**方案**：用一个廉价 LLM 在检索前先改写查询：

```python
def rewrite_query(user_query: str) -> str:
    response = llm.chat(
        messages=[{
            "role": "system",
            "content": (
                "你是一个搜索查询优化器。将用户的口语化问题改写为简洁、"
                "关键词密集的检索查询。保留所有技术术语和专有名词。"
                "只输出改写后的查询，不要解释。"
            )
        }, {
            "role": "user",
            "content": user_query
        }],
        temperature=0.1,   # 低温度保证一致性
        max_tokens=200,
    )
    return response.strip()
```

**改写原则**：
- 只服务于检索，不改变用户意图
- 专有名词、产品名、代码符号必须保留
- 输出尽量短、关键词密集
- 保留 `original_query` 给 LLM 回答用，`retrieval_query` 给检索引擎用

**容错**：改写失败自动回退到原始问题，不中断检索流程。

### 1.5 预处理小结

| 优化项 | 延迟代价 | 精度收益 | 实施阶段 |
|--------|:---:|:---:|:---:|
| 文档切片 | 0ms（离线） | 长文档场景质的提升 | 离线入库 |
| Schema 双向量 | 0ms | 打通混合检索基础 | 离线入库 |
| 批量 Embedding | 0ms | 入库速度 5-10x | 离线入库 |
| **Query Rewrite** | +10-50ms | **Recall +10-20%** | 在线检索 |

---

## 二、检索中：双路召回 + 融合 + 智能路由

检索阶段的核心思想就一个字：**多**。多条路径各取所长，然后聪明地融合。

### 2.1 混合检索：稠密 + 稀疏，两条腿走路

这是整个检索架构的骨架。稠密向量擅长语义匹配，BM25 擅长精确关键词——它们天然互补：

| 维度 | 稠密向量（COSINE） | BM25 稀疏向量 |
|------|-------------------|-------------|
| 匹配方式 | 余弦相似度（语义距离） | TF-IDF（字面匹配） |
| 擅长 | 同义词、改写、上下文理解 | 专有名词、代码、精确术语 |
| 典型失败 | "Transformer"无特殊权重 | "汽车"和"轿车"无法关联 |

**实现**：

```python
# 稠密检索 — 语义匹配
req_dense = AnnSearchRequest(
    data=[query_vector], anns_field="dense_vector",
    param={"metric_type": "COSINE", "nprobe": 16}, limit=top_k,
)

# 稀疏检索 — 关键词匹配（直接传文本，不是向量）
req_sparse = AnnSearchRequest(
    data=[rewritten_query], anns_field="sparse_vector",
    param={"metric_type": "BM25"}, limit=top_k,
)

# 两路一起搜
results = client.hybrid_search(
    collection_name=collection_name,
    reqs=[req_dense, req_sparse],
    ranker=RRFRanker(k=60),
    limit=10,
)
```

### 2.2 RRF 融合：排名算术，不是模型精排

一个常见误区是把 RRF 当成"精排"。RRF 的本质是把两路检索的排名做一次算术融合，纯 O(K) 计算，**耗时 < 1ms，几乎零成本**。

```
RRF score(doc) = Σ 1/(k + rank_i(doc))
其中 k=60（平滑参数），rank_i 是文档在第 i 路检索中的排名
```

**什么时候用加权排序替代 RRF？**

- 默认首选 RRF，因为它不需要调参，对分数不敏感
- 如果明确知道语义更重要 → 加权 [0.7 稠密, 0.3 稀疏]
- 如果关键词更重要（如代码搜索）→ 加权 [0.3 稠密, 0.7 稀疏]

### 2.3 双集合并行检索：文档 + QA 对

我们的系统有两个知识来源：

| 集合 | 存什么 | 像什么 |
|------|--------|--------|
| `document_chunks` | 文档切片 + 来源元数据 | 搜索引擎的文档索引 |
| `qa_pairs` | 问题 + 答案 + 推理过程 | FAQ 知识库 |

两者并行检索，结果统一为 `Candidate` 结构：

```python
{
    "id": "...",
    "source": "document_chunks | qa_pairs",
    "text": "用于精排和 Prompt 的主体文本",
    "title": "标题或问题",
    "score": 0.0,
    "file_name": "来源文件",
    "doc_id": "原始文档 ID",
    "chunk_index": 3,
    "metadata": {"source_type": "qa", "created_at": 1718697600},
}
```

### 2.4 QA 优先路由：能直接回答就别折腾

生产环境中，很多问题已经被 QA 对覆盖了。我们实现了一个智能路由：

```
用户问题
  → 先搜 source_type == "qa"
    → QA Top-1 分数 >= 阈值 且 与 Top-2 分差 >= 安全边际？
      ├ YES → 直接返回 QA 答案（零 LLM 成本，< 100ms）
      └ NO  → 继续搜文档 chunks → 召回 → LLM 生成
```

这带来两个好处：
1. **降低延迟**：QA 命中时直接返回，跳过 LLM 调用
2. **提高精度**：已审核的 QA 对比 LLM 现编更可靠

### 2.5 检索中小结

| 策略 | 作用 | 延迟 |
|------|------|:---:|
| 稠密 + 稀疏双路 | 语义 + 关键词互补 | 50ms |
| RRF 融合 | 自动融合两路排名 | < 1ms |
| 双集合并行 | 覆盖文档 + FAQ 两类知识 | +10ms |
| QA 优先路由 | 高频问题零 LLM 成本 | -500ms* |

> *命中时反而省了 LLM 时间

---

## 三、检索后：去重、精排、组装、降级

检索回来的 Top-K 不等于最终的上下文。检索后的链路决定了塞进 Prompt 的到底是不是最好的那几条。

### 3.1 CrossEncoder 精排：模型级别的相关性打分

RRF 只看排名高低，完全不理解 query 和 doc 的内容。可能某个文档在两个路径排名都不错，但实际上跟问题只有一点点关系。CrossEncoder 就是来解决这个问题的。

```
RRF 融合 → Top-10 候选 → CrossEncoder 精排 → Top-3 → 进入 Prompt
 └─ 融合 ─┘              └─ 精排（< 1ms）─────────┘
```

**实现**：

```python
from sentence_transformers import CrossEncoder

class Reranker:
    def __init__(self, model_name="BAAI/bge-reranker-v2-m3"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, candidates: list[dict], top_k: int = 3):
        # 将 query 和每个候选 doc 拼接后一起过 Transformer
        pairs = [[query, c["text"]] for c in candidates]
        scores = self.model.predict(pairs)

        # 按分数重排
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
```

**延迟实测**：

| 候选数 | MiniLM (80MB) | bge-reranker-v2-m3 (560MB) |
|--------|:---:|:---:|
| Top-5 | ~25ms | ~150ms |
| Top-10 | ~50ms | ~300ms |
| Top-20 | ~100ms | ~600ms |

**按场景决策**：

- 实时对话 / 延迟 < 300ms → 不加 CrossEncoder，直接用 RRF Top-K
- 精准问答 / 用户能接受 1-2 秒 → 加 CrossEncoder，N=10 → +300ms 换 5-15% P@3 提升
- 离线批处理 → 必加，N 甚至可以到 20

**容错**：CrossEncoder 加载失败或推理报错时，自动跳过精排，直接使用 RRF Top-K。

### 3.2 Small-to-Big：把命中的邻居也带上

一个 500 字的 chunk 被命中时，它前后的 chunk 往往也包含有用信息。我们的做法是：按 `doc_id` + `chunk_index` 查询相邻 chunk，作为"邻居"合并到结果中：

```python
def fetch_neighbors(hits, collection):
    """对每个命中 chunk，拉取它的 chunk_index ± 1 的邻居"""
    expanded = {}
    for hit in hits:
        neighbors = collection.query(
            filter=f'doc_id == "{hit["doc_id"]}" and '
                   f'chunk_index in [{hit["chunk_index"]-1}, {hit["chunk_index"]+1}]'
        )
        # 合并到 expanded，标记 is_neighbor=True
    return expanded
```

邻居在后续排序中优先级低于原生命中，但高于被丢弃的低分结果。这样既补全了上下文，又不会让 LLM 读到一堆无关信息。

### 3.3 两重去重：别让 LLM 看到三遍同样的内容

双集合检索 + small-to-big 扩展后，很容易出现重复——比如 QA 对和文档切片同时提到了"变压器接线方式"，两个结果几乎一模一样。

```python
def deduplicate(candidates, jaccard_threshold=0.85):
    # 第一层：相同 (doc_id, chunk_index) 直接去掉
    seen_keys = set()
    unique = []
    for c in candidates:
        key = (c.get("doc_id"), c.get("chunk_index"))
        if key not in seen_keys:
            seen_keys.add(key)
            unique.append(c)

    # 第二层：Jaccard 字符集相似度 > 0.85 的视为重复
    result = []
    for c in unique:
        is_dup = False
        for r in result:
            if jaccard_charset(c["text"], r["text"]) > jaccard_threshold:
                is_dup = True
                break
        if not is_dup:
            result.append(c)
    return result
```

### 3.4 Token 预算管理：精打细算每一段上下文

检索回 6 条结果，每条 500 字，总共 3000 字——已经超出 DeepSeek 的上下文窗口了吗？不会。但如果不控制预算，系统很容易在大量检索结果面前"塞满"上下文，LLM 反而抓不住重点。

```python
def build_context_blocks(candidates, max_tokens=2000):
    # 1. 排序：非邻居优先（原始命中）；同级按 rerank_score 降序
    sorted_hits = sorted(candidates, key=lambda h: (
        h.get("is_neighbor", False),   # 邻居放后面
        -(h.get("rerank_score", h.get("score", 0)))
    ))

    # 2. 逐个加入上下文，累积 token 数
    blocks = []
    tokens_used = 0
    for hit in sorted_hits:
        formatted = format_context(hit)
        estimated = estimate_tokens(formatted)  # 中文保守估计：1 字符 ≈ 1 token
        if tokens_used + estimated > max_tokens:
            # 剩余预算 > 80 字则截断加入
            remaining = max_tokens - tokens_used
            if remaining > 80:
                blocks.append(formatted[:remaining * 4] + "...")
            break
        blocks.append(formatted)
        tokens_used += estimated
    return blocks
```

**优先级排序**：QA 精准答案 > 高分文档 chunk > 邻居 chunk > 低分结果。

### 3.5 领域分数修正：让模型更懂你的行话

通用检索不知道哪些词在你的领域更重要。我们实现了一个领域感知的分数调节器，针对工程 KB：

```python
# 领域关键词列表
DOMAIN_KEYWORDS = [
    "单机容量", "总装机容量", "接线方式", "海缆", "升压站",
    "MW", "kV", "GIS", "AIS", "主变压器", "开关站", ...
]

def adjust_qa_score(query, candidate):
    score = candidate["score"]
    # 问题问"本项目"而结果在说"参考项目"→ 降权
    if "本工程" in query and "参考工程" in candidate["text"]:
        score *= 0.5
    # 匹配到领域关键词 → 加分
    for kw in DOMAIN_KEYWORDS:
        if kw in candidate["text"]:
            score *= 1.1
    return score
```

这个策略虽然简单，但在特定领域的 QA 检索中效果显著——它让系统不会把"参考项目的海缆方案"当成"本项目的海缆方案"返回给用户。

### 3.6 用户反馈闭环：让人工标注反哺检索

前述所有策略都是"系统自己想办法"，但最精准的信号其实来自终端用户——用户看到答案后点个 👍 或 👎，这个反馈比任何模型打分都更接近真实相关性。

核心思路是 **Relevance Feedback**，分两个阶段落地：

**第一阶段（轻量，马上可用）——文档级质量分调整**

不绑定具体 query，而是统计每篇文档的全局反馈：

```python
# 反馈记录表
doc_feedback = {
    "doc_id": "milvus_intro_003",
    "thumbs_up": 15,
    "thumbs_down": 3,
}

# 检索后乘一个信誉系数
def apply_doc_reputation(candidate):
    feedback = get_feedback(candidate["doc_id"])
    if feedback.total == 0:
        return candidate  # 无反馈，保持原分数
    # 好评率映射为 0.5x ~ 1.5x 的权重
    ratio = feedback.thumbs_up / feedback.total
    candidate["score"] *= 0.5 + ratio  # 好评率 100% → 1.5x，0% → 0.5x
    return candidate
```

实现成本极低——一个反馈表 + 检索后乘系数，但能有效压制"被反复踩过"的劣质文档，抬升"经过多人验证"的优质文档。

**第二阶段（真正有效果）——微调 CrossEncoder**

当反馈积累到一定量级（500-1000 条以上），将标注转化为精排模型的训练样本：

```
标注结构：(query_text, doc_text, label)
  - 用户点 👍 → label=1（正例）
  - 用户点 👎 → label=0（负例）
  - 用户没反馈的 → 不参与训练

用这些样本定期微调 bge-reranker 或 MiniLM：
  → 精排模型学会"这类问题应该偏好这类文档"
  → 不增加检索链路延迟（模型还是原来的推理速度）
  → 标注越多、效果越稳定
```

Snowflake 的 Arctic 和 Cohere 的 Rerank 走的都是这条路——用真实用户反馈 Fine-Tune 精排模型，比任何规则调参都有效。

**两个需要注意的问题**：

1. **"同类问题"怎么匹配？** 不是简单字符串匹配。用户问"变压器怎么接线"和"主变接线方案"措辞不同但意图相同。最可靠的方式是对 query 做 embedding，用向量相似度（COSINE > 0.9）找邻近的历史标注，把邻近标注也纳入当前查询的分数修正。

2. **标注稀疏性**。假设每天 100 次查询、10% 用户愿意反馈，一天只积累 10 条。建议第一阶段至少跑 1-2 个月，积累够量再进入第二阶段。在此之前保持规则修正为主，不要过早引入稀疏的反馈信号。

### 3.7 检索后小结

| 优化项 | 作用 | 延迟 |
|--------|------|:---:|
| CrossEncoder | 模型级相关性重排 | +50-300ms（可选） |
| Small-to-Big | 补全上下文，不丢信息 | +10ms |
| 两重去重 | 减少 LLM 上下文浪费 | +5ms |
| Token 预算 | 防止超长导致截断或注意力分散 | +5ms |
| 领域分数修正 | 让行话和语境更准确 | < 1ms |
| 用户反馈闭环 | 人工标注反哺检索，持续进化 | +5ms（查反馈表） |

---

## 四、兜底：降级链路与质量防线

每一层都可能出问题——API 挂了、模型加载失败、检索结果为 0。一个好的 RAG 系统必须有清晰的降级策略。

### 4.1 全链路降级

```
查询改写 ──失败──→ 使用原始问题
    │
embedding API ──失败──→ 纯 BM25 检索
    │
CrossEncoder ──失败──→ 直接用 RRF Top-K
    │
LLM API ──失败──→ 返回检索原文 + "模型暂时不可用"
    │
检索结果为空 ──→ 明确告知"知识库未收录相关内容"
```

### 4.2 置信度拒绝：不该答的坚决不答

检索分数太低时，系统会直接拒答，而不是凭 LLM 的记忆去编造：

```python
def _should_refuse(results):
    """Top-1 分数 < retrieval_min_score（默认 0.15）→ 拒答"""
    if not results or results[0]["score"] < config.retrieval_min_score:
        return True
    return False
```

这是防止幻觉的**最后一道防线**——宁可说"我不知道"，也不能编一个看起来像真的错误答案。

---

## 五、评估：用数据说话

没有评估的优化是盲目的。我们的评估方案分两个层次：

### 5.1 结构化的功能评估

预定义测试用例，每个 case 包含预期 answer mode、必须包含的关键词、不能出现的关键词、预期的来源类型：

```python
class EvaluationCase:
    question: str
    expected_mode: str          # "qa_direct" | "doc_retrieval" | "refuse"
    must_include: list[str]     # 答案必须包含的短语
    must_not_include: list[str] # 答案不能包含的短语
    expected_source_type: str   # "qa" | "document_chunks" | None
```

跑完后自动统计通过率，每个失败 case 附原因。

### 5.2 各阶段耗时追踪

```python
trace = {
    "rewrite_ms": 45,
    "embed_ms": 120,
    "search_ms": 52,
    "rerank_ms": 280,
    "generate_ms": 800,
    "recalled_ids": [...],
    "citations": [...],
    "fallback_reason": None,
}
```

这让我们能看到优化到底省没省时间、慢在哪一步。

---

## 六、完整链路图：所有策略的位置

```
┌── 检索前（离线）────────────────────────────────────────────┐
│                                                             │
│  原始文档 → 多格式解析 → 清洗 → 递归切片(chunk=500/overlap=50)  │
│    → [QA对合并 search_text] → 批量 Embedding(1024d)           │
│    → Milvus 入库 [双向量 + BM25自动生成 + 标量索引]            │
│                                                             │
├── 检索前（在线）────────────────────────────────────────────┤
│                                                             │
│  用户问题 → Query Rewrite(LLM改写) → 生成 query_vector       │
│                                                             │
├── 检索中 ──────────────────────────────────────────────────┤
│                                                             │
│  稠密检索(COSINE) ─┐                                        │
│                    ├ RRF融合(k=60) → Top-N 候选              │
│  BM25检索(稀疏)  ──┘                                        │
│                                                             │
│  ↓ 同时进行 ↓                                               │
│                                                             │
│  QA集合检索 → QA分数判断 → 够高则直接返回（跳过后续所有步骤）  │
│                                                             │
├── 检索后 ──────────────────────────────────────────────────┤
│                                                             │
│  RRF候选 → [CrossEncoder精排](可选) → small-to-big邻居扩展    │
│    → 两重去重(精确Key + Jaccard 0.85)                        │
│    → Token预算控制(max 2000 tokens)                          │
│    → 领域分数修正                                           │
│    → [用户反馈加权] → 带来源标记的Prompt组装 → LLM生成        │
│                                                             │
├── 反馈闭环 ────────────────────────────────────────────────┤
│                                                             │
│  用户 👍/👎 → 文档信誉系数 → [积累足够后] → 微调 CrossEncoder │
│                                                             │
├── 兜底 ────────────────────────────────────────────────────┤
│                                                             │
│  全链路降级 + 置信度拒答 + 结构化评估                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 七、优先级排序：如果资源有限，先做什么？

从实际工程经验出发，按性价比排序：

| 优先级 | 优化项 | 评级 | 收益 | 代价 |
|:---:|------|:---:|------|:---:|
| 1 | **Query Rewrite** | ★★★★★ | Recall +10-20% | +10-50ms，1 次 LLM 调用 |
| 2 | **文档切片** | ★★★★★ | 长文档场景质的提升 | 0（离线做完） |
| 3 | **CrossEncoder 精排** | ★★★★ | P@3 +5-15% | +50-300ms，按需开启 |
| 4 | **双路混合检索** | ★★★★ | 语义+关键词互补 | 0（架构自带） |
| 5 | **Token 预算 + 去重** | ★★★★ | 防截断防幻觉 | +10ms |
| 6 | **QA 优先路由** | ★★★★ | 高频问题零 LLM 成本 | < 5ms |
| 7 | **领域分数修正** | ★★★ | 领域适配 | < 1ms |
| 8 | **降级链路** | ★★★ | 服务可用性保障 | 0 |
| 9 | **用户反馈闭环** | ★★★ | 长期持续进化 | 阶段一 < 5ms，阶段二离线 |

前三项加在一起，能把一个"能跑"的 RAG 系统提升到"能用"的水平。

---

## 八、一句话总结

> **检索精度不是靠单一技术堆出来的，而是靠检索前（改写+切片）、检索中（双路+融合+路由）、检索后（精排+去重+预算）三层防线层层打磨出来的。Query Rewrite 是性价比最高的单点优化，双路混合检索是架构基石，CrossEncoder 是按需开启的精修器，而全链路降级和置信度拒答是生产环境的安全网。**
