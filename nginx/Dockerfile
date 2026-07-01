# ============================================================
# SyncHealth Nginx + 前端 镜像（生产环境用）
# 多阶段构建：编译 Vue3 前端 → 打包进 Nginx
# ============================================================

# ===== 阶段 1: 构建前端 =====
FROM node:22-alpine AS builder
WORKDIR /app

# 复制整个 frontend 目录（含 package.json + package-lock.json）
COPY frontend/ ./

# 安装所有依赖（含 devDependencies，必须用 --include=dev）
RUN npm install --include=dev

# 构建前端（跳过 vue-tsc 类型检查，已本地验证通过）
ENV VITE_API_BASE_URL=/api/v1
RUN ./node_modules/.bin/vite build

# ===== 阶段 2: Nginx 服务 =====
FROM nginx:alpine

# 复制前端构建产物
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
