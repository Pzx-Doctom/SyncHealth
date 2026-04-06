# SyncHealth Mobile

SyncHealth 移动端 — 通过 Apple HealthKit 采集健康数据并同步到 SyncHealth 后端。

## 技术栈

| 技术 | 用途 |
|---|---|
| React Native + TypeScript | 跨平台移动开发 |
| Expo SDK 52 | 构建工具 + OTA 热更新 |
| @kingstinct/react-native-healthkit | HealthKit 数据访问（iOS） |
| Zustand | 状态管理 |
| expo-secure-store | Token 安全存储 |
| NativeWind (Tailwind CSS) | 样式 |
| Expo Router | 文件路由 |

## 项目结构

```
mobile/
├── src/
│   ├── app/              # Expo Router 页面（文件路由）
│   │   ├── _layout.tsx           # 根布局 + 认证守卫
│   │   ├── (auth)/               # 登录/注册页
│   │   └── (tabs)/               # Dashboard/Settings 标签页
│   ├── components/       # 通用组件
│   ├── constants/        # 颜色、HealthKit 数据类型映射
│   ├── services/         # API、认证、HealthKit、同步服务
│   ├── stores/           # Zustand 状态管理
│   ├── types/            # TypeScript 类型定义
│   └── utils/            # 工具函数
├── app.json              # Expo 配置
├── eas.json              # EAS 云端构建配置
├── tailwind.config.js    # NativeWind 主题
└── package.json
```

## 快速开始

### 1. 安装依赖

```bash
cd mobile
npm install
```

### 2. 启动开发服务器

```bash
npx expo start
```

然后：
- **Android**：按 `a` 启动 Android 模拟器
- **iOS**（需 Mac）：按 `i` 启动 iOS 模拟器

### 3. 配置后端服务器地址

1. 启动 SyncHealth 后端服务
2. 在手机/模拟器的「设置」页面修改服务器地址
3. 如果在同一 WiFi 网络，使用电脑的局域网 IP：
   ```
   http://192.168.1.100:8000/api/v1
   ```

### 4. Android 调试（Windows）

Android 端无法访问 HealthKit，自动使用 **模拟数据**，可以完整测试：
- 登录/注册流程
- 数据同步流程
- UI 交互
- 同步历史展示

## iOS 真机测试

### 方式一：EAS 云端构建（推荐，无需 Mac）

1. 安装 EAS CLI：
   ```bash
   npm install -g eas-cli
   ```

2. 登录 Expo 账号：
   ```bash
   eas login
   ```

3. 构建开发版本：
   ```bash
   eas build --profile development --platform ios
   ```

4. 通过 TestFlight 或直接安装 IPA 到 iPhone

5. 使用 Expo Go 扫码开发：

### 方式二：Mac 本地构建

```bash
# 需要 Xcode 和 CocoaPods
npx expo prebuild
npx expo run:ios
```

### HealthKit 权限

首次运行时，应用会自动请求以下健康数据权限：
- 心率、心率变异性 (HRV)
- 步数、距离、能量消耗
- 睡眠分析、正念会话
- 血氧饱和度、体温、呼吸频率
- 环境噪声暴露

**注意**：HealthKit 数据**必须在真机上测试**，iOS 模拟器不支持。

## 与后端的数据契约

应用上传的数据严格对应后端 Pydantic Schema：

- `POST /api/v1/auth/login` — 登录
- `POST /api/v1/auth/register` — 注册
- `POST /api/v1/sync/upload` — 上传 SyncPayload（包含 11 种健康数据）
- `GET /api/v1/sync/status` — 获取同步状态
- `GET /api/v1/sync/history` — 获取同步历史

类型定义见 `src/types/` 目录，字段名与 `backend/app/schemas/` 完全一致。

## 常见问题

### Q: Android 上同步数据是真实的吗？
A: 不是。Android 使用 `mockHealthService` 生成模拟数据，确保开发调试流程完整。真实 HealthKit 数据仅在 iOS 真机上可用。

### Q: 没有 Mac 怎么测试 iOS？
A: 使用 [EAS Build](https://docs.expo.dev/build/introduction/) 云端构建。免费版每月 30 次构建，足够开发使用。构建完成后通过 TestFlight 安装到 iPhone。

### Q: 后端连接失败？
A: 检查：
1. 后端是否已启动 (`cd backend && python -m uvicorn app.main:app --reload`)
2. 手机和电脑是否在同一 WiFi 网络
3. 服务器地址是否正确（注意包含 `/api/v1` 后缀）
4. 防火墙是否阻止了 8000 端口

### Q: 如何查看电脑的局域网 IP？
A:
- **Windows**: `ipconfig` → 找到 WiFi 适配器的 IPv4 地址
- **macOS**: `ifconfig | grep "inet "` 或 系统偏好设置 → 网络

### Q: HealthKit 数据不显示？
A: 确保：
1. 使用的是 iPhone 真机（不是模拟器）
2. 在 iPhone 的「健康」App 中有对应数据（如佩戴了 Apple Watch）
3. 已在应用中授权了健康数据权限
4. 可以在 iPhone「设置 → 隐私 → 健康 → SyncHealth」中检查权限
