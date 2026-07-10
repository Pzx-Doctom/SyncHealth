# SyncHealth Backend RAG 评估框架 —— 技术原理详解

> **版本**: v1.0  
> **适用范围**: Backend 层 Dify 知识库 RAG 管道  
> **依赖**: RAGAS、Rich、Pytest  

---

## 目录

1. [整体架构概览](#1-整体架构概览)
2. [被评估系统：Backend RAG 管道](#2-被评估系统backend-rag-管道)
3. [评估数据集设计](#3-评估数据集设计)
4. [检索层评估：Precision@k、Recall@k、MRR、NDCG](#4-检索层评估precisionk-recallk-mrr-ndcg)
5. [生成层评估：RAGAS 三大指标](#5-生成层评估ragas-三大指标)
6. [A/B 对比实验框架](#6-ab-对比实验框架)
7. [代码架构与数据流](#7-代码架构与数据流)
8. [报告系统：Rich 终端 + JSON 结构化输出](#8-报告系统rich-终端--json-结构化输出)
9. [结果解读指南](#9-结果解读指南)
10. [局限性与改进方向](#10-局限性与改进方向)

---

## 1. 整体架构概览

RAG（Retrieval-Augmented Generation）系统的质量评估需要同时衡量"检索质量"和"生成质量"两个维度。本框架采用**分层解耦**的评估策略，将评估拆分为三个独立阶段：

```
┌──────────────────────────────────────────────────────────────┐
│                    评估框架整体架构                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Phase 1: 检索层评估                                          │
│  ┌─────────────┐     ┌──────────────┐    ┌───────────────┐  │
│  │   Test      │ ──► │  Dify 知识库  │ ──►│ Precision@k   │  │
│  │   Queries   │     │  检索 API     │    │ Recall@k      │  │
│  └─────────────┘     └──────────────┘    │ MRR           │  │
│                                          │ NDCG@k        │  │
│                                          └───────────────┘  │
│                                                              │
│  Phase 2: 生成层评估                                          │
│  ┌─────────────┐   ┌──────────┐   ┌─────────┐  ┌──────────┐│
│  │   Test      │ ► │ Dify 检索│ ► │  LLM    │ ►│ RAGAS    ││
│  │   Queries   │   │ 上下文   │   │ 生成    │  │ 指标     ││
│  └─────────────┘   └──────────┘   └─────────┘  └──────────┘│
│                                                              │
│  Phase 3: A/B 对比                                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Comparison A: RAG 上下文注入 vs 纯 LLM 回答          │   │
│  │  Comparison B: DeepSeek (云端) vs Ollama (本地)       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 核心设计原则

| 原则 | 说明 |
|------|------|
| **无侵入** | 所有评估代码位于 `backend/tests/`，不改动任何业务模块 |
| **分层解耦** | 检索、生成、对比三个阶段可独立运行，互不阻塞 |
| **可复现** | 数据集、指标计算、LLM 调用全部可追踪，JSON 持久化结果 |
| **可扩展** | 新增查询只需追加 JSON 条目；新增指标只需在对应模块注册 |

---

## 2. 被评估系统：Backend RAG 管道

在深入评估原理之前，先理解被评估的 RAG 管道本身。

### 2.1 数据流

```
用户提问 query
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  dify_retriever.py                                  │
│  retrieve_from_dify(query)                          │
│                                                     │
│  POST /datasets/{id}/retrieve                       │
│  ┌─────────────────────────────────────────────┐    │
│  │  search_method: hybrid_search               │    │
│  │  top_k: 5                                   │    │
│  │  score_threshold: 0.5                       │    │
│  │  reranking_enable: false                    │    │
│  └─────────────────────────────────────────────┘    │
│         │                                           │
│         ▼                                           │
│  Dify API 返回 records[]                            │
│  每条 record 包含:                                   │
│    - segment.content    (文本片段)                   │
│    - segment.document.name  (来源文档名)             │
│    - score             (相关度评分)                  │
│    - segment.keywords  (关键词列表)                  │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  format_dify_context(records)                       │
│                                                     │
│  将 records 格式化为 Markdown 注入 LLM:              │
│  ## Medical Knowledge Reference                     │
│  ### [内科.txt] (relevance: 0.92)                   │
│  > Keywords: 高血压, 饮食                            │
│  高血压患者应低盐低脂饮食...                          │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  agent_runtime.py / 评估脚本                        │
│                                                     │
│  SystemMessage 序列:                                 │
│  [0] system_prompt (角色设定)                        │
│  [1] health_context (可穿戴设备数据, 评估中省略)      │
│  [2] dify_context  ← RAG 知识注入点                  │
│  [3] history (对话历史, 评估中省略)                   │
│  [4] user_message (用户提问)                         │
│         │                                           │
│         ▼                                           │
│  LLM: DeepSeek API (主) / Ollama (fallback)         │
│         │                                           │
│         ▼                                           │
│  answer (最终回答)                                   │
└─────────────────────────────────────────────────────┘
```

### 2.2 评估关注点

评估框架基于上述管道精确复现 RAG 行为，但做了以下简化以保证评估纯粹性：

- **省略 `health_context`**: 评估数据集不涉及真实可穿戴设备数据，仅评估医学知识检索与生成
- **省略对话历史**: 每条查询独立评估，不携带多轮上下文
- **直接调用 `retrieve_from_dify()` + `provider.chat()`**: 绕过 `agent_runtime.py` 的数据库和会话逻辑，直接评估核心链路

---

## 3. 评估数据集设计

### 3.1 数据结构

```json
{
  "query": "高血压患者日常饮食需要注意什么？",
  "ground_truth_answer": "高血压患者应坚持低盐低脂饮食...",
  "expected_doc_names": ["内科.txt"],
  "category": "慢性病管理"
}
```

| 字段 | 用途 | 使用者 |
|------|------|--------|
| `query` | 用户提问，作为检索输入 | 检索评估 + 生成评估 |
| `ground_truth_answer` | 参考答案（人工编写），RAGAS 的 Ground Truth | 生成评估 (RAGAS) |
| `expected_doc_names` | 预期检索到的文档名列表，检索评估的 Ground Truth | 检索评估 |
| `category` | 场景分类，便于分场景分析 | 报告与分析 |

### 3.2 数据分布（20 条，4 个场景）

| 场景 | 条数 | 说明 |
|------|------|------|
| 慢性病管理 | 5 | 高血压/糖尿病/冠心病/高血脂/痛风 |
| 用药咨询 | 5 | 抗生素/镇痛药/降压药/阿司匹林/药物副作用 |
| 体检解读 | 5 | 转氨酶/白细胞/血糖/心电图/尿酸 |
| 常见症状 | 5 | 头痛/胸痛/抽筋/疲劳/胃胀 |

### 3.3 设计原则

1. **覆盖多场景**: 4 类场景确保评估不偏向单一领域
2. **答案可验证**: 每个 query 都有明确定义的 `ground_truth_answer`，避免主观判断
3. **文档可追踪**: `expected_doc_names` 对应 Dify 知识库中的实际文档名，使检索评估量化可测
4. **医学专业性**: 所有 query 和 answer 均为真实医学场景，反映系统实际使用情况

> **重要**: `expected_doc_names` 必须与 Dify 知识库中实际存在的文档名一致。首次使用时需根据知识库内容调整此字段。

---

## 4. 检索层评估：Precision@k、Recall@k、MRR、NDCG

检索评估衡量"Dify 知识库是否能返回与 query 相关的文档"，这是整个 RAG 系统的上游质量基线。

### 4.1 评估流程

```
for each query in dataset:
    ① 调用 retrieve_from_dify(query) → 获取 records[]
    ② 提取每条 record 的文档名: segment.document.name
    ③ 与 expected_doc_names 匹配，生成 relevance 向量
    ④ 计算 4 个指标
→ 汇总为 Macro Average
```

### 4.2 核心概念：Relevance 判定

对于每个 query，Dify 返回一个**有序**的文档列表。将每篇文档与 `expected_doc_names` 集合进行匹配：

```
relevant_at = [1 if doc in expected else 0 for doc in retrieved_docs]
```

这是一个**二值相关度**判定（不涉及分段相关度分数），简化了计算但牺牲了部分精细度。

### 4.3 指标详解

#### 4.3.1 Precision@k — 查准率

**定义**: 前 k 个检索结果中，相关文档所占比例。

\[
\text{Precision@k} = \frac{|\{\text{前k个结果}\} \cap \{\text{相关文档}\}|}{k}
\]

**解读**: 衡量检索结果的**精确性**。Precision@5 = 0.8 意味着 top-5 中有 4 篇是相关的。

**代码实现**:
```python
top_k_rel = relevant_at[:k]
retrieved_k = min(k, len(doc_names))
precision = sum(top_k_rel) / retrieved_k
```

#### 4.3.2 Recall@k — 查全率

**定义**: 前 k 个检索结果中，命中的相关文档占所有相关文档的比例。

\[
\text{Recall@k} = \frac{|\{\text{前k个结果}\} \cap \{\text{相关文档}\}|}{|\{\text{所有相关文档}\}|}
\]

**解读**: 衡量检索结果的**覆盖性**。Recall@5 = 1.0 意味着所有预期文档都被检索到了。

**代码实现**:
```python
recall = sum(top_k_rel) / len(expected)
```

#### 4.3.3 MRR — 平均倒数排名

**定义**: 第一个相关文档的排名的倒数的平均值。

\[
\text{MRR} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}
\]

其中 \(\text{rank}_i\) 是第 i 个查询中第一个相关文档的排名位置（从 1 开始）。

**解读**: 
- MRR = 1.0 → 所有 query 的第一个结果就是相关文档
- MRR = 0.5 → 平均第 2 位才找到
- MRR = 0 → 没有任何相关文档被返回

**优劣**:
- **优点**: 简单直观，关注用户最可能看的第一条结果
- **缺点**: 只关心第一个相关结果，忽略后续相关文档的贡献

**代码实现**:
```python
rr = 0.0
for rank, rel in enumerate(relevant_at, start=1):
    if rel == 1:
        rr = 1.0 / rank
        break
# MRR = mean of all rr values
```

#### 4.3.4 NDCG@k — 归一化折损累积增益

这是四个指标中最**精细**的一个，因为它同时考虑了：
- **排名位置**（排名越靠前贡献越大）
- **折损因子**（靠后的位置贡献递减）
- **理想排序**（与最佳可能排序对比）

**计算步骤**:

##### Step 1: DCG（折损累积增益）

\[
\text{DCG@k} = \sum_{i=1}^{k} \frac{rel_i}{\log_2(i+1)}
\]

其中 \(rel_i\) 是第 i 位的相关度（本框架中为 0 或 1），\(\log_2(i+1)\) 是折损因子：

| 排名 i | \(1\) | \(2\) | \(3\) | \(4\) | \(5\) |
|--------|-------|-------|-------|-------|-------|
| 折损因子 | \(1.00\) | \(1.58\) | \(2.00\) | \(2.32\) | \(2.58\) |

排名越靠后，对 DCG 的贡献越小，模拟了用户浏览行为——越后面的结果越不关注。

##### Step 2: IDCG（理想 DCG）

构造"完美排序"——把所有相关文档排在最前面，计算该理想排序的 DCG：

```python
# 如果 expected 有 2 个文档，k=5
# ideal_rels = [1, 1, 0, 0, 0]  (两个相关文档排在最前面)
idcg = sum(rel / log2(i+1) for i, rel in enumerate(ideal_rels, start=1))
```

##### Step 3: NDCG

\[
\text{NDCG@k} = \frac{\text{DCG@k}}{\text{IDCG@k}}
\]

**解读**:
- NDCG = 1.0 → 检索结果达到最佳可能排序
- NDCG = 0.5 → 检索结果为最佳的一半
- NDCG = 0 → 没有任何相关文档

**代码实现**:
```python
# DCG
dcg = 0.0
for i, rel_val in enumerate(top_k_rel, start=1):
    if rel_val:
        dcg += rel_val / math.log2(i + 1)

# IDCG
ideal_rels = sorted([1] * min(len(expected), k) + [0] * max(0, k - len(expected)), reverse=True)[:k]
idcg = 0.0
for i, rel_val in enumerate(ideal_rels, start=1):
    if rel_val:
        idcg += rel_val / math.log2(i + 1)

# NDCG
ndcg = dcg / idcg if idcg > 0 else 0.0
```

### 4.4 指标选择指南

| 场景 | 推荐关注指标 | 原因 |
|------|-------------|------|
| 监控检索基本可用性 | MRR | 最敏感，第一个相关结果出现的排名 |
| 评估 top-5 质量 | NDCG@5 | 综合考虑排名与相关性 |
| 确保不遗漏关键文档 | Recall@5 | 衡量覆盖率 |
| 避免噪声干扰 LLM | Precision@3 | 前 3 个结果的相关性直接影响生成质量 |

### 4.5 汇总方式：Macro Average

对于每条 query 先独立计算指标，然后对所有 query 求算术平均：

\[
\text{Macro Precision@k} = \frac{1}{N} \sum_{i=1}^{N} \text{Precision@k}_i
\]

选择 Macro 而非 Micro 的原因：每条 query 同等重要，避免长文档覆盖多场景的场景偏差。

---

## 5. 生成层评估：RAGAS 三大指标

生成层评估衡量"LLM 基于检索到的上下文生成的回答质量"。本框架使用 [RAGAS](https://docs.ragas.io/)（Retrieval Augmented Generation Assessment）框架。

### 5.1 RAGAS 核心概念

RAGAS 将 LLM 本身用作评估器（LLM-as-Judge），通过精心设计的 prompt 让 LLM 对生成结果进行评判。RAGAS 需要的输入是：

```
{
  "question":      "用户提问",
  "answer":         "LLM 生成的回答",
  "contexts":       ["检索到的上下文片段列表"],
  "ground_truth":   "参考答案（人工编写）"
}
```

### 5.2 评估流程

```
Phase 1: 检索 + 生成
  for each query:
    ① retrieve_from_dify(query) → records
    ② format_dify_context(records) → dify_context (Markdown)
    ③ 构建 messages = [system_prompt, dify_context, user_query]
    ④ provider.chat(messages) → answer
    ⑤ 构建 RAGAS 样本: {question, answer, contexts, ground_truth}

Phase 2: RAGAS 评分
    ① 将样本转为 HuggingFace Dataset
    ② ragas.evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_relevancy])
    ③ 输出各指标得分
```

### 5.3 指标详解

#### 5.3.1 Faithfulness（忠实度）

**定义**: 回答中的所有陈述是否都能从检索到的上下文中推断出来。

**计算原理**:
1. RAGAS 使用 LLM 将 answer 拆解为独立的"陈述"列表（claims）
2. 逐一判断每个陈述是否可以被 contexts 支持
3. Faithfulness = 被上下文支持的陈述数 / 总陈述数

**数学形式**:

\[
\text{Faithfulness} = \frac{|\text{可支持的陈述}|}{|\text{总陈述}|}
\]

**解读**:
- 1.0 → 回答中所有信息都来自检索到的上下文，无幻觉
- 0.5 → 一半的信息来自上下文，另一半可能是编造的
- 0.0 → 回答与检索到的上下文完全无关

**示例**:
```
Question: 高血压患者日常饮食需要注意什么？
Context:  "高血压患者应坚持低盐低脂饮食，每日食盐摄入不超过6克。"
Answer:   "高血压患者应该低盐饮食，每天盐不超过6克。建议每天跑步30分钟。"

Claims:
  ✓ "低盐饮食，每天盐不超过6克" — 可以在 Context 中找到
  ✗ "建议每天跑步30分钟" — Context 中没有此信息

Faithfulness = 1/2 = 0.5
```

#### 5.3.2 AnswerRelevancy（回答相关性）

**定义**: 回答与用户问题的相关程度。

**计算原理**:
1. RAGAS 使用 LLM 基于 answer 反向生成若干个"假设问题"
2. 计算这些假设问题与原始 question 的余弦相似度（embedding 层）
3. AnswerRelevancy = 假设问题与原始问题的平均相似度

**数学形式**:

\[
\text{AnswerRelevancy} = \frac{1}{N} \sum_{i=1}^{N} \cos(E(q_i), E(q_{original}))
\]

其中 \(E\) 是 embedding 函数，\(q_i\) 是反向生成的第 i 个假设问题。

**解读**:
- 1.0 → 回答完全围绕用户问题展开
- 0.3 → 回答与用户问题关联微弱，可能偏题
- 0.0 → 回答与问题完全无关

**示例**:
```
Question: 高血压患者日常饮食需要注意什么？
Answer:   "高血压患者应低盐饮食。另外，糖尿病患者的饮食也很重要，需要控制糖分摄入。"

Generated Questions:
  Q1: 高血压患者应该怎么吃？ → 与原始问题相似度 0.9
  Q2: 糖尿病患者饮食如何管理？ → 与原始问题相似度 0.2

AnswerRelevancy ≈ (0.9 + 0.2) / 2 = 0.55
```

#### 5.3.3 ContextRelevancy（上下文相关性）

**定义**: 检索到的上下文与用户问题的相关程度。

**计算原理**:
1. RAGAS 使用 LLM 从 contexts 中提取与问题相关的"句子"
2. ContextRelevancy = 相关句子数 / 上下文总句子数

**数学形式**:

\[
\text{ContextRelevancy} = \frac{|\text{相关句子}|}{|\text{上下文总句子}|}
\]

**解读**:
- 1.0 → 检索的所有上下文都与问题高度相关，无浪费 Token
- 0.3 → 仅 30% 的上下文有用，其余是噪音
- 0.0 → 检索到的上下文完全不相关

**意义**: 此指标间接衡量 Dify 检索质量对 LLM 的影响——低 ContextRelevancy 意味着大量 Token 被浪费在无关信息上。

### 5.4 RAGAS 综合得分

RAGAS 还提供一个 `ragas_score`，是上述三个指标的调和平均：

\[
\text{RAGAS\_Score} = \frac{3}{\frac{1}{F} + \frac{1}{AR} + \frac{1}{CR}}
\]

使用调和平均而非算术平均的原因是：任一维度的严重不足都应该被惩罚。

### 5.5 RAGAS 的局限性

| 局限 | 影响 |
|------|------|
| **LLM-as-Judge 偏差** | 评估器 LLM 可能有自身偏好，不是完全客观 |
| **依赖 LLM 调用** | 每条样本触发多次 LLM 推理，耗时且消耗 Token |
| **Embedding 模型依赖** | AnswerRelevancy 的余弦相似度依赖 embedding 模型质量 |
| **中文支持** | RAGAS 默认英文 prompt，中文评估效果可能略有折扣 |

---

## 6. A/B 对比实验框架

对比实验用于量化 RAG 知识注入的效果差异。

### 6.1 Comparison A: RAG vs No RAG

**实验设计**:

```
┌──────────────────────────────────────────────────────┐
│  控制变量                                           │
│  - 同一 LLM Provider (DeepSeek)                     │
│  - 同一 System Prompt                               │
│  - 同一 Query 列表                                  │
│                                                      │
│  独立变量: 是否注入 dify_context                     │
│                                                      │
│  条件 A: messages = [system_prompt, dify_context, q] │
│  条件 B: messages = [system_prompt, q]               │
│                                                      │
│  测量指标:                                           │
│  - 回答长度 (avg_length)  → 信息丰富度               │
│  - 生成耗时 (avg_time)    → 管道开销                │
│  - 更长回答计数           → 哪个版本更有信息量        │
└──────────────────────────────────────────────────────┘
```

**关键发现方向**:
- RAG 回答平均长度 > 无 RAG → 知识注入有效提高了回答信息量
- RAG 耗时 ≈ 无 RAG 耗时 + Dify API 延迟 → 可量化检索开销
- 部分 query RAG 更短 → 可能检索结果不相关，LLM 忽略了上下文

### 6.2 Comparison B: DeepSeek vs Ollama

**实验设计**:

```
┌──────────────────────────────────────────────────────┐
│  控制变量                                           │
│  - 同一 System Prompt                               │
│  - 同一 dify_context（从 Dify 检索）                 │
│  - 同一 Query 列表                                  │
│                                                      │
│  独立变量: LLM Provider                             │
│                                                      │
│  条件 A: DeepSeek API (云端大模型)                   │
│  条件 B: Ollama 本地模型                             │
│                                                      │
│  测量指标:                                           │
│  - 回答长度           → 模型回答的详细程度            │
│  - 生成耗时           → 云端 vs 本地延迟对比          │
│  - Ollama 成功率       → 本地模型可用性               │
└──────────────────────────────────────────────────────┘
```

**关键发现方向**:
- DeepSeek 通常提供更详细、更专业的回答
- Ollama 本地模型延迟更低，但回答质量可能下降
- 如果 Ollama 回答长度接近 DeepSeek 的 80%，说明本地模型可作为合格的 fallback

### 6.3 对比限制说明

当前的对比仅测量了**表面指标**（长度、耗时），未进行深层质量评判。完整的 A/B 应在两组上都运行 RAGAS 评估，但这会翻倍 Token 消耗。当前实现作为第一版提供了**快速定性判断**，后续可扩展。

---

## 7. 代码架构与数据流

### 7.1 文件组织

```
backend/tests/
├── conftest.py                 # pytest 共享 fixtures
│   ├── eval_dataset()          # 加载 eval_dataset.json
│   ├── provider()              # 获取主要 LLM Provider (session scope)
│   └── ollama_provider()       # 获取 Ollama Provider (session scope)
│
├── eval_dataset.json           # 评估数据集 (20 条)
│
├── test_rag_retrieval.py       # 检索层评估
│   ├── _compute_retrieval_metrics()  # 核心指标计算
│   └── test_dify_retrieval_metrics() # pytest 入口
│
├── test_rag_generation.py      # 生成层评估 (RAGAS)
│   ├── _build_ragas_data()     # 构建 RAGAS 样本
│   └── test_ragas_evaluation() # pytest 入口
│
├── test_rag_compare.py         # A/B 对比实验
│   ├── test_rag_vs_no_rag()    # RAG vs 纯 LLM
│   └── test_deepseek_vs_ollama() # DeepSeek vs Ollama
│
├── eval_runner.py              # 一键 CLI 运行器
│   ├── _run_retrieval()        # Phase 1 异步执行
│   ├── _run_generation()       # Phase 2 异步执行
│   └── _run_compare()          # Phase 3 异步执行
│
├── eval_report.py              # Rich 终端报告生成器
│   ├── _rich_report()          # Rich 格式化输出
│   ├── _plain_report()         # 纯文本 fallback
│   └── generate_report()       # 主入口
│
└── rag_eval_README.md          # 用户使用指南
```

### 7.2 Provider 复用机制

为避免每次测试都重新创建 HTTP 连接，Provider 实例使用 pytest 的 `scope="session"` 级别复用：

```python
@pytest.fixture(scope="session")
def provider() -> BaseLLMProvider:
    reset_provider()       # 清除单例缓存
    return get_provider()  # 创建一次，整个 session 复用
```

这意味着同一 session 内的所有测试共享同一个 LLM 连接，大幅减少初始化开销。

### 7.3 异步执行策略

由于 Dify API 和 LLM API 都是异步 I/O，所有评估函数使用 `async/await`：

```python
@pytest.mark.asyncio
async def test_dify_retrieval_metrics(eval_dataset):
    metrics = _compute_retrieval_metrics(eval_dataset)
    # ...
```

但检索评估中有一个已知局限：`_compute_retrieval_metrics()` 内部对 `retrieve_from_dify()` 使用了**同步调用**（未 await），这可能导致在 pytester 环境下报错。推荐使用 `eval_runner.py` 而非 pytest 运行完整评估。

### 7.4 结果持久化

每个评估阶段结束后，结果自动保存为 JSON 文件：

```
backend/tests/
├── test_rag_retrieval_results.json    # 检索指标 + 逐条详情
├── test_rag_generation_results.json   # RAGAS 得分 + 逐条回答
├── test_rag_compare_results.json      # 对比汇总 + 逐条对比
└── rag_eval_report.json              # eval_report.py 汇总输出
```

JSON 文件设计原则：
- **完整可读**: 包含 `macro_avg`（汇总）+ `query_details`（逐条），方便细粒度分析
- **可串联**: `eval_report.py` 读取所有 `*_results.json` 输出统一报告
- **可对比**: 不同时间运行的结果可以 diff 对比

---

## 8. 报告系统：Rich 终端 + JSON 结构化输出

### 8.1 Rich 终端报告

使用 Python `rich` 库提供彩色格式化输出：

```
╭──────────────────────────────────────────────╮
│           RAG Evaluation Report              │
╰──────────────────────────────────────────────╯

         Dify Retrieval Metrics (Macro Average)
┌───────────────┬──────────┬──────────┐
│ Metric        │       @3 │       @5 │
├───────────────┼──────────┼──────────┤
│ Precision     │   0.7333 │   0.6400 │
│ Recall        │   0.5500 │   0.8000 │
│ NDCG          │   0.6188 │   0.7553 │
│ MRR           │   0.7833 │          │
└───────────────┴──────────┴──────────┘
  Queries evaluated: 20

       Generation Metrics (RAGAS)
┌──────────────────────┬────────┬──────────────────────────────┐
│ Metric               │  Score │ Bar                          │
├──────────────────────┼────────┼──────────────────────────────┤
│ Faithfulness         │ 0.8234 │ ████████████████████████     │
│ Answer Relevancy     │ 0.7601 │ ██████████████████████       │
│ Context Relevancy    │ 0.6512 │ ███████████████████          │
└──────────────────────┴────────┴──────────────────────────────┘
```

### 8.2 颜色编码规则

基于分数自动选择颜色（`eval_report.py` 的 `_metric_color()` 函数）：

| 分数区间 | 颜色 | 含义 |
|----------|------|------|
| ≥ 0.7 | 🟢 绿色 | 良好 |
| 0.4 ~ 0.7 | 🟡 黄色 | 一般，有改进空间 |
| < 0.4 | 🔴 红色 | 差，需排查问题 |

### 8.3 纯文本 Fallback

当 Rich 库未安装时，自动降级为纯文本输出，确保任何环境下都能运行。

---

## 9. 结果解读指南

### 9.1 理想指标范围

| 指标 | 较差 | 一般 | 良好 | 优秀 |
|------|------|------|------|------|
| Precision@5 | < 0.3 | 0.3-0.5 | 0.5-0.7 | > 0.7 |
| Recall@5 | < 0.3 | 0.3-0.6 | 0.6-0.8 | > 0.8 |
| MRR | < 0.3 | 0.3-0.5 | 0.5-0.7 | > 0.7 |
| NDCG@5 | < 0.3 | 0.3-0.5 | 0.5-0.7 | > 0.7 |
| Faithfulness | < 0.5 | 0.5-0.7 | 0.7-0.85 | > 0.85 |
| AnswerRelevancy | < 0.5 | 0.5-0.7 | 0.7-0.85 | > 0.85 |
| ContextRelevancy | < 0.4 | 0.4-0.6 | 0.6-0.8 | > 0.8 |

### 9.2 常见问题诊断

| 现象 | 可能原因 | 建议操作 |
|------|---------|---------|
| Precision 高，Recall 低 | top_k 太小，只返回了最相关的文档 | 增大 `DIFY_RETRIEVE_TOP_K` |
| Precision 低，Recall 高 | 返回了太多不相关的文档 | 提高 `DIFY_SCORE_THRESHOLD` 或启用 reranking |
| MRR 低 (< 0.3) | 最相关的文档不在靠前位置 | 尝试 `semantic_search` 换 `hybrid_search` |
| Faithfulness 低 (< 0.5) | LLM 大量编造信息，不依赖检索上下文 | 调整 System Prompt 强化"仅使用提供的信息" |
| ContextRelevancy 低 | 检索到的上下文包含大量无关信息 | 检查 Dify 知识库质量，可能有大量低质量文档 |
| AnswerRelevancy 低 | LLM 回答偏题 | 检查 System Prompt 是否足够聚焦 |

### 9.3 对比实验解读

**RAG vs No RAG**:
- RAG 回答长度明显更长 → RAG 知识注入有效
- RAG 回答长度反而更短 → 检索上下文可能干扰了 LLM，需查 ContextRelevancy
- 两者长度接近 → Dify 检索可能没有返回有价值的内容（查 Recall）

**DeepSeek vs Ollama**:
- Ollama 回答长度 ≈ DeepSeek 的 70%+ → 本地模型可作为合格 fallback
- Ollama 成功率 < 100% → 需排查 Ollama 服务可用性
- Ollama 耗时 > DeepSeek → 本地硬件不足，考虑升级或换更小模型

---

## 10. 局限性与改进方向

### 当前局限

| 局限 | 影响 | 优先级 |
|------|------|--------|
| `expected_doc_names` 只包含单文档名 | 无法评估跨文档检索质量 | 中 |
| 检索相关度为二值判定 (0/1) | 忽略了部分相关的情况 | 中 |
| 对比实验仅测量表面指标（长度、耗时） | 无法量化回答质量差异 | 高 |
| 未评估 `health_context` 对 RAG 的影响 | 未覆盖生产环境完整链路 | 中 |
| RAGAS 中文效果未经充分验证 | 评估结果可信度未知 | 低 |
| 20 条数据集偏小 | 统计显著性不足 | 中 |

### 后续改进方向

1. **对比实验加入 RAGAS**: 在 RAG vs No RAG / DeepSeek vs Ollama 的两组回答上都运行 RAGAS 评估
2. **引入 LLM-as-Judge 直接对比**: 让 LLM 对两组回答打 1-5 分，更直接地量化质量差异
3. **扩展数据集**: 扩大至 50-100 条，并按场景分别统计指标
4. **参与完整链路评估**: 加入 `health_context`（真实可穿戴数据），评估完整业务链路
5. **时序对比**: 每次代码变更后运行评估，记录得分趋势，作为 CI 门禁的一部分
6. **多级相关度**: 将 `expected_doc_names` 改为带权重的文档列表 (`{"内科.txt": 3.0, "心血管.txt": 1.0}`)，支持 NDCG 分级相关度计算

---

## 附录：运行命令参考

```bash
cd backend

# 安装依赖
pip install ragas rich datasets

# 一键运行全部评估
python tests/eval_runner.py

# 快速验证（前 5 条，约 2 分钟）
python tests/eval_runner.py --quick

# 仅运行检索评估（无需 LLM，秒级）
python tests/eval_runner.py --skip-generation --skip-compare

# 运行后查看 Rich 报告
python tests/eval_report.py

# 以 pytest 方式运行单项（不推荐，推荐用 eval_runner.py）
python -m pytest tests/test_rag_retrieval.py -v -s -m rag_retrieval
python -m pytest tests/test_rag_generation.py -v -s -m rag_generation
python -m pytest tests/test_rag_compare.py -v -s -m rag_compare
```
