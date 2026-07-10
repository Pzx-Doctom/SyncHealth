# RAG 评估工具使用指南

对 Backend 层 Dify 知识库 RAG 管道进行自动化量化评估。

## 目录结构

```
backend/tests/
├── eval_dataset.json              # 评估数据集（20 条医学健康问答）
├── conftest.py                    # pytest 共享 fixtures
├── test_rag_retrieval.py          # 检索层评估
├── test_rag_generation.py         # 生成层评估（RAGAS）
├── test_rag_compare.py            # A/B 对比实验
├── eval_runner.py                 # 一键运行 CLI
├── eval_report.py                 # Rich 终端报告生成
└── rag_eval_README.md             # 本文件
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install ragas rich datasets
```

或在 pyproject.toml 已更新的情况下：

```bash
pip install -e ".[dev]"
```

### 2. 确保 Dify 配置正确

`.env` 中需要设置：

```ini
DIFY_RETRIEVE_ENABLED=true
DIFY_API_KEY=your_dify_api_key
DIFY_DATASET_ID=your_dataset_id
DIFY_SEARCH_METHOD=hybrid_search
DIFY_RETRIEVE_TOP_K=5
```

### 3. 运行评估

```bash
# 一键运行全部评估
cd backend
python tests/eval_runner.py

# 快速验证（仅 5 条数据）
python tests/eval_runner.py --quick

# 跳过生成层（只评估检索，无需 LLM）
python tests/eval_runner.py --skip-generation --skip-compare

# 只生成最终报告（读取已有结果）
python tests/eval_report.py
```

## 指标说明

### 检索层指标（不需要 LLM）

| 指标 | 范围 | 说明 |
|------|------|------|
| **Precision@k** | 0-1 | 前 k 个检索结果中，真正相关的比例。越高越好 |
| **Recall@k** | 0-1 | 所有相关文档中，被前 k 个结果覆盖的比例。越高越好 |
| **MRR** | 0-1 | 第一个相关文档排名的倒数均值。值越大说明相关文档越靠前 |
| **NDCG@k** | 0-1 | 考虑排序位置权重的归一化累计增益。综合评估排序质量 |

### 生成层指标（RAGAS，需 LLM）

| 指标 | 范围 | 说明 |
|------|------|------|
| **Faithfulness** | 0-1 | 回答内容是否忠实于检索到的上下文，不编造信息。> 0.7 为良好 |
| **AnswerRelevancy** | 0-1 | 回答与用户问题的相关程度。> 0.7 为良好 |
| **ContextRelevancy** | 0-1 | 检索到的上下文与用户问题的相关程度。> 0.7 为良好 |

### A/B 对比

| 对比项 | 说明 |
|--------|------|
| **有 RAG vs 无 RAG** | 同一 provider 下，注入 Dify 上下文和不注入的回答差异 |
| **DeepSeek vs Ollama** | 两种 LLM 在相同 RAG 上下文下的回答质量和速度对比 |

## 输出产物

运行后会在 `backend/tests/` 目录下生成：

| 文件 | 内容 |
|------|------|
| `test_rag_retrieval_results.json` | 检索评估原始数据 + 宏观指标 |
| `test_rag_generation_results.json` | RAGAS 分数 + 每个样本的回答 |
| `test_rag_compare_results.json` | A/B 对比原始数据 + 汇总 |
| `rag_eval_report.json` | 所有结果的合并报告 |

## 单独运行某个测试

支持通过 pytest marker 独立运行：

```bash
# 仅检索评估
pytest tests/test_rag_retrieval.py -v -s -m rag_retrieval

# 仅生成评估
pytest tests/test_rag_generation.py -v -s -m rag_generation

# 仅 A/B 对比
pytest tests/test_rag_compare.py -v -s -m rag_compare
```

## 自定义数据集

编辑 `backend/tests/eval_dataset.json`，每条数据格式：

```jsonc
{
  "query": "用户问题",
  "ground_truth_answer": "参考答案（用于 Faithfulness 评估）",
  "expected_doc_names": ["内科.txt"],  // 预期 Dify 检索到的文档名
  "category": "慢性病管理"             // 分类标签
}
```

覆盖四大场景：`慢性病管理`、`用药咨询`、`体检解读`、`常见症状`，每个场景 5 条。

## 注意事项

1. **RAGAS Faithfulness 评估需要 LLM 作为评判**，会产生额外的 API 调用费用
2. **`expected_doc_names` 需要与 Dify 知识库中的实际文档名匹配**，否则检索指标无法正确计算
3. Ollama 本地推理较慢，超时设置见 `OLLAMA_TIMEOUT`（默认 180s）
4. 如果 Dify 知识库中文档名与数据集不匹配，检索指标可能为 0——此时应先确认实际返回的文档名
