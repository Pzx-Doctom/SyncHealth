#!/bin/bash
# ============================================================
# SyncHealth 阿里云 ECS 服务器预配置脚本
# ============================================================
# 用途：配置 Docker 镜像加速 + 预拉取基础镜像
# 使用：sudo bash setup-ecs.sh
# ============================================================
set -e

echo "🔧 [1/3] 配置阿里云 Docker 镜像加速..."
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<-'EOF'
{
  "registry-mirrors": [
    "https://<你的阿里云加速器ID>.mirror.aliyuncs.com"
  ],
  "dns": ["223.5.5.5", "8.8.8.8"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
echo "✅ Docker 镜像加速配置完成"

echo ""
echo "📦 [2/3] 预拉取基础镜像..."
docker pull python:3.11-slim
docker pull node:20-alpine
docker pull nginx:alpine
echo "✅ 基础镜像拉取完成"

echo ""
echo "🔍 [3/3] 检查端口占用..."
if ss -tlnp | grep -q ':8080'; then
    echo "⚠️  警告: 8080 端口已被占用，请检查！"
    ss -tlnp | grep ':8080'
else
    echo "✅ 8080 端口空闲，可以部署 SyncHealth"
fi

echo ""
echo "=========================================="
echo "✅ 服务器预配置完成！"
echo ""
echo "下一步："
echo "  1. 记得在阿里云安全组开放 8080 端口（入方向 TCP 0.0.0.0/0）"
echo "  2. 克隆项目: git clone <repo-url> /opt/synchealth"
echo "  3. 启动服务: cd /opt/synchealth && docker compose up -d"
echo "=========================================="
