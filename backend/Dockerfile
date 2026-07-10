# ============================================================
# SyncHealth Backend Dockerfile (多阶段构建)
# ============================================================

# ===== 阶段 1: 安装依赖 =====
FROM python:3.11-slim AS builder
WORKDIR /app

# 复制依赖声明和源码（setuptools.packages.find 需要 app 目录）
COPY pyproject.toml ./
COPY app/ ./app/

# 安装项目及依赖到 site-packages
RUN pip install --no-cache-dir .

# ===== 阶段 2: 运行阶段 =====
FROM python:3.11-slim AS runner
WORKDIR /app

# 安装 gunicorn（生产多 worker 管理器，uvicorn[standard] 已随项目依赖安装）
RUN pip install --no-cache-dir gunicorn

# 从 builder 复制已安装的依赖和 app 包
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制项目源码
COPY . .

# 创建非 root 用户和运行目录（注意：先 mkdir 再 chown，确保 data 目录属 appuser）
RUN mkdir -p /app/data/uploads && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# gunicorn + uvicorn worker
# SQLite 写锁限制，用 2 个 worker 平衡并发与锁竞争
# 启动前确保 data 目录可写（Docker volume 挂载可能覆盖权限）
CMD ["sh", "-c", "mkdir -p /app/data/uploads && exec gunicorn app.main:app -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --timeout 300 --graceful-timeout 30"]
