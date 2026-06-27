"""多种检索方式 + 多个查询词测试"""
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

# 不带 retrieval_model（使用知识库默认配置）
print("=== 不带 retrieval_model（用知识库默认配置）===")
for query in ["高血压", "糖尿病", "肺炎", "发热", "内科"]:
    body = {"query": query}
    resp = requests.post(f"{base}/datasets/{ds_id}/retrieve", headers=headers, json=body, timeout=30, proxies=proxies)
    if resp.status_code == 200:
        records = resp.json().get("records", [])
        print(f"  '{query}': ✅ {len(records)} 条记录")
        if records:
            for r in records[:2]:
                print(f"    score={r.get('score',0):.2f} | {r.get('segment',{}).get('content','')[:80]}")
    else:
        print(f"  '{query}': ❌ HTTP {resp.status_code}")

print()
print("=== semantic_search ===")
for query in ["高血压", "发热"]:
    body = {
        "query": query,
        "retrieval_model": {
            "search_method": "semantic_search",
            "top_k": 5,
            "score_threshold_enabled": False,
            "reranking_enable": False,
        },
    }
    resp = requests.post(f"{base}/datasets/{ds_id}/retrieve", headers=headers, json=body, timeout=30, proxies=proxies)
    if resp.status_code == 200:
        records = resp.json().get("records", [])
        print(f"  '{query}': ✅ {len(records)} 条记录")
    else:
        print(f"  '{query}': ❌ HTTP {resp.status_code} - {resp.text[:100]}")
