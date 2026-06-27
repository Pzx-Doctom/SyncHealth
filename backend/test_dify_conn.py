"""检查知识库详情和文档状态"""
import os
import sys
sys.path.insert(0, ".")

for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(key, None)

import requests
from app.config import settings

headers = {"Authorization": f"Bearer {settings.DIFY_API_KEY}"}
proxies = {"http": None, "https": None}
base = settings.DIFY_API_BASE.rstrip("/")
ds_id = settings.DIFY_DATASET_ID

# 1. 知识库详情
print("=== 知识库详情 ===")
resp = requests.get(f"{base}/datasets/{ds_id}", headers=headers, timeout=30, proxies=proxies)
print(f"HTTP {resp.status_code}")
if resp.status_code == 200:
    import json
    data = resp.json()
    print(json.dumps(data, indent=2, ensure_ascii=False))
print()

# 2. 文档列表
print("=== 文档列表 ===")
resp = requests.get(f"{base}/datasets/{ds_id}/documents", headers=headers, params={"page": 1, "limit": 20}, timeout=30, proxies=proxies)
print(f"HTTP {resp.status_code}")
if resp.status_code == 200:
    import json
    data = resp.json()
    docs = data.get("data", [])
    for doc in docs:
        print(f"  ID: {doc.get('id')}")
        print(f"  名称: {doc.get('name')}")
        print(f"  状态: indexing_status={doc.get('indexing_status')}, display_status={doc.get('display_status')}")
        print(f"  字数: {doc.get('word_count')}")
        print(f"  段数: {doc.get('segment_count')}")
        print(f"  索引方式: {doc.get('indexing_technique')}")
        print(f"  created_at: {doc.get('created_at')}")
        print()
else:
    print(resp.text[:500])
print()

# 3. 尝试不同检索方式
print("=== 尝试不同检索方式 ===")
for method in ["semantic_search", "full_text_search", "keyword_search", "hybrid_search"]:
    body = {
        "query": "高血压",
        "retrieval_model": {
            "search_method": method,
            "top_k": 5,
            "score_threshold_enabled": False,
            "reranking_enable": False,
        },
    }
    resp = requests.post(f"{base}/datasets/{ds_id}/retrieve", headers=headers, json=body, timeout=30, proxies=proxies)
    status = resp.status_code
    if status == 200:
        records = resp.json().get("records", [])
        print(f"  {method}: ✅ 返回 {len(records)} 条记录")
    else:
        err = resp.json().get("message", resp.text[:100]) if resp.headers.get("content-type","").startswith("application/json") else resp.text[:100]
        print(f"  {method}: ❌ HTTP {status} - {err}")
