/**
 * ============================================================
 * Axios 客户端配置与 JWT 认证机制详解
 * ============================================================
 *
 * 【核心概念说明】
 *
 * 一、什么是 Axios？
 * -----------------
 * Axios 是一个基于 Promise 的 HTTP 客户端，用于浏览器和 Node.js。
 * 它提供了简洁的 API 来发送 HTTP 请求（GET、POST、PUT、DELETE 等），
 * 并内置了请求/响应拦截、自动转换 JSON 数据、取消请求等功能。
 *
 * 二、什么是拦截器（Interceptor）？
 * ---------------------------------
 * 拦截器是 Axios 提供的一种机制，允许你在**请求发送前**或**响应接收后**
 * 执行自定义逻辑。就像快递站的安检环节：
 *
 *   [客户端] → [请求拦截器] → [服务器] → [响应拦截器] → [业务代码]
 *                (安检出门)              (安检进门)
 *
 * 【请求拦截器】在请求发出之前执行，常用于：
 *   - 统一添加认证头（如 JWT Token）
 *   - 设置通用的请求头（Content-Type 等）
 *   - 显示加载动画
 *   - 请求参数的统一处理
 *
 * 【响应拦截器】在收到服务器响应后、业务代码处理前执行，常用于：
 *   - 统一处理错误（如 401 跳转登录）
 *   - 自动刷新 Token
 *   - 响应数据的格式化
 *   - 隐藏加载动画
 *
 * 三、什么是 JWT（JSON Web Token）？
 * ----------------------------------
 * JWT 是一种用于在网络应用间传递信息的开放标准（RFC 7519）。
 * 它是一个紧凑的、URL 安全的令牌，由三部分组成，用点号（.）分隔：
 *
 *   Header.Payload.Signature
 *
 * 例如：eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
 *       eyJzdWIiOiIxMjM0NTY3ODkwIn0.
 *       dummy-signature
 *
 * 各部分含义：
 * ┌─────────────────────────────────────────────────────────────┐
 * │ 1. Header（头部）：声明算法和 Token 类型                     │
 * │    示例：{"alg": "HS256", "typ": "JWT"}                      │
 * │    说明：alg 表示签名算法（如 HS256, RS256），typ 固定为 JWT     │
 * ├─────────────────────────────────────────────────────────────┤
 * │ 2. Payload（载荷）：存放实际数据（称为 Claims/声明）           │
 * │    标准声明包括：                                              │
 * │    - sub（subject）：Token 的主体，通常是用户 ID               │
 * │    - iat（issued at）：签发时间                                │
 * │    - exp（expiration time）：过期时间                          │
 * │    - iss（issuer）：签发者                                     │
 * │    自定义声明可以添加任意数据（如用户名、角色等）                  │
 * ├─────────────────────────────────────────────────────────────┤
 * │ 3. Signature（签名）：防止 Token 被篡改                        │
 * │    生成方式：HMACSHA256(                                    │
 * │      base64UrlEncode(header) + "." + base64UrlEncode(payload),│
 * │      your_secret_key                                        │
 * │    )                                                        │
 * │    作用：接收方可以用密钥验证签名，确保 Token 内容未被篡改         │
 * └─────────────────────────────────────────────────────────────┘
 *
 * ┌─────────────────────────────────────────────────────────────┐
 * │          🔐 签名机制：生成、验证与防篡改（通俗版）            │
 * ├─────────────────────────────────────────────────────────────┤
 * │                                                             │
 * │ 【核心一句话】                                               │
 * │   签名 = 用密钥把【头+内容】加密成一串密码                    │
 * │   验证 = 把返回来的数据提取出【头+内容】用同样密钥重新算一遍，对比是否一样                   │
 * │   一样 = 没被改；不一样 = 被改了                             │
 * │                                                             │
 * │ 【签名生成 — 5 步】                                          │
 * │   ① 准备数据                                                 │
 * │     Header: {alg:"HS256", typ:"JWT"}                         │
 * │     Payload: {userId:1001, name:"张三"}                      │
 * │   ② 分别做 base64Url 编码                                    │
 * │     → 头: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9              │
 * │     → 内容: eyJ1c2VySWQiOjEwMDEsIm5hbWUiOiLkuIrmiq8ifQ     │
 * │   ③ 用"."连接                                                │
 * │     → 头.内容                                                │
 * │   ④ 用服务器密钥(secret_key)做 HMAC-SHA256 加密               │
 * │   ⑤ 得到最终签名串                                           │
 * │     → 完整JWT = 头.内容.签名                                  │
 * │                                                             │
 * │ 【签名验证 — 4 步】                                          │
 * │   ① 收到客户端传来的 JWT (头.内容.签名)                       │
 * │   ② 取出 头+内容 部分                                       │
 * │   ③ 服务器用【同一密钥】重新计算签名                          │
 * │   ④ 对比新旧签名                                            │
 * │     一致 ✅ → 没被篡改，放行                                 │
 * │     不一致 ❌ → 被篡改了，拒绝                                │
 * │                                                             │
 * │ 【为什么能防篡改？】                                          │
 * │   改一个字 → 拼接字符串变 → 签名完全变！                     │
 * │   例：userId:1001 → 改成 userId:9999(冒充管理员)             │
 * │   内容变了，但黑客不知道密钥 → 算不出正确的新签名             │
 * │   服务器一验 → 签名对不上 → 直接拒绝 ❌                      │
 * │                                                             │
 * └─────────────────────────────────────────────────────────────┘
 *
 * 四、JWT 的完整生命周期
 * ----------------------
 *
 *   用户登录 → 服务器验证 → 生成 JWT → 返回给前端
 *        ↓
 *   前端存储 Token（localStorage / sessionStorage / Cookie）
 *        ↓
 *   后续请求携带 Token（Authorization: Bearer <token>）
 *        ↓
 *   服务器验证 Token（检查签名、过期时间）
 *        ↓
 *   ┌─── 验证通过 → 返回请求数据
 *   └─── 验证失败 → 返回 401 未授权错误
 *        ↓ (如果接近过期)
 *   使用 Refresh Token 获取新的 Access Token
 *        ↓
 *   更新本地存储的 Token，重发原请求
 *
 * 五、为什么需要双 Token 机制？（Access Token + Refresh Token）
 * ----------------------------------------------------------------
 * 为了平衡安全性和用户体验，通常采用双 Token 策略：
 *
 * ┌─────────────────┬──────────────────────────────────────────┐
 * │   Access Token  │  Refresh Token                            │
 * ├─────────────────┼──────────────────────────────────────────┤
 * │  有效期短        │  有效期长                                  │
 * │  （如 15 分钟）  │  （如 7 天）                               │
 * ├─────────────────┼──────────────────────────────────────────┤
 * │  每次请求都携带   │  仅在 Access Token 过期时使用             │
 * ├─────────────────┼──────────────────────────────────────────┤
 * │  存储于内存或    │  存储（更安全的方式是 HttpOnly Cookie）     │
 * │  localStorage   │                                          │
 * ├─────────────────┼──────────────────────────────────────────┤
 * │  用于访问 API    │  用于获取新的 Access Token                 │
 * └─────────────────┴──────────────────────────────────────────┘
 *
 * 优势：
 * 1. Access Token 短期有效，即使泄露风险也有限
 * 2. Refresh Token 可以被单独撤销（加入黑名单）
 * 3. 用户无需频繁重新登录
 * 4. Access Token 泄露时攻击者窗口期短
 *
 * ============================================================
 */

import axios from 'axios'

/**
 * 创建 Axios 实例
 * ----------------
 * 使用 axios.create() 创建一个预配置的实例，而不是直接使用全局 axios 对象。
 * 这样做的好处：
 * 1. 可以定义不同的实例用于不同的 API（如主 API、第三方 API）
 * 2. 所有通过该实例发出的请求都会共享相同的配置
 * 3. 便于统一管理和修改基础配置
 */
const apiClient = axios.create({
  /**
   * baseURL：API 的基础 URL
   * 所有使用该实例发出的请求都会自动拼接此前缀。
   * 例如：apiClient.get('/users') 会请求 http://127.0.0.1:8000/api/v1/users
   *
   * import.meta.env.VITE_API_BASE_URL 是 Vite 提供的环境变量，
   * 可以在不同环境（开发/生产）中设置不同的 API 地址，
   * || 'http://127.0.0.1:8000/api/v1' 是默认值回退。
   */
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001/api/v1',

  /**
   * headers：默认请求头
   * Content-Type: application/json 表示请求体格式为 JSON。
   * 大多数 RESTful API 都使用 JSON 格式进行数据交换。
   */
  headers: { 'Content-Type': 'application/json' },
})

/*
 * ════════════════════════════════════════════════════════════
 * 第一部分：请求拦截器（Request Interceptor）
 * ════════════════════════════════════════════════════════════
 *
 * 工作原理：
 * 当你调用 apiClient.get()、apiClient.post() 等方法时，
 * 在请求真正发送到服务器之前，Axios 会先执行这里注册的回调函数。
 *
 * 配置方式：
 * apiClient.interceptors.request.use(
 *   onFulfilled  // 请求成功时的回调（必须返回 config）
 *   [, onRejected] // 可选，请求失败时的回调
 * )
 *
 * 回调函数接收一个 config 对象，包含：
 * - url: 请求地址
 * - method: 请求方法（get/post/put/delete）
 * - headers: 请求头对象
 * - data: 请求体数据（post/put 时有值）
 * - params: URL 查询参数
 * - timeout: 超时时间
 * 等等...
 *
 * 你可以修改这个 config 对象然后返回它，Axios 会用修改后的配置发请求。
 */

/**
 * 注册请求拦截器
 * ---------------
 * 核心功能：在每个 API 请求发出前，自动将 JWT Access Token 添加到请求头中。
 *
 * 为什么这样做？
 * - 避免在每个请求中手动写 Authorization 头
 * - 统一管理认证逻辑
 * - 如果后续更换认证方式，只需修改此处
 *
 * Bearer Token 格式说明：
 * "Bearer" 是 OAuth 2.0 规范中的标准令牌类型，
 * 表示持有此令牌的一方即为授权方。
 * 格式：Authorization: Bearer <access_token>
 */
apiClient.interceptors.request.use((config) => {
  /**
   * 从 localStorage 获取存储的 access_token
   *
   * localStorage 是浏览器的本地存储机制，特点：
   * - 数据持久存在，关闭浏览器后仍然保留
   * - 同源（域名+端口）下的所有页面共享
   * - 存储容量约 5MB
   * - 只能存储字符串
   *
   * 注意：localStorage 不是最安全的存储方式（易受 XSS 攻击），
   * 更安全的方案是使用 HttpOnly Cookie（JavaScript 无法访问）。
   * 但为了演示清晰，这里使用 localStorage。
   */
  const token = localStorage.getItem('access_token')

  /**
   * 如果 token 存在，将其添加到请求头的 Authorization 字段
   *
   * 这行代码的效果是，每个经过该实例的请求会变成：
   * GET /api/v1/users
   * Headers: {
   *   Content-Type: application/json,
   *   Authorization: Bearer eyJhbGc...
   * }
   */
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  // 必须返回 config，否则请求无法继续
  return config
})

/*
 * ════════════════════════════════════════════════════════════
 * 第二部分：响应拦截器（Response Interceptor）与 Token 刷新机制
 * ════════════════════════════════════════════════════════════
 *
 * 工作原理：
 * 当服务器的响应返回时，在传递给你的 .then() 回调之前，
 * Axios 会先执行这里注册的回调函数。
 *
 * 配置方式：
 * apiClient.interceptors.response.use(
 *   onFulfilled,  // 响应成功时的回调（状态码 2xx）
 *   onRejected     // 响应失败时的回调（状态码非 2xx 或网络错误）
 * )
 *
 * 本文件实现的完整 Token 刷新流程：
 *
 *  发送 API 请求（带 Access Token）
 *          ↓
 *  服务器返回 200 OK → 正常返回响应数据 ✅
 *          ↓
 *  服务器返回 401 Unauthorized
 *          ↓
 *  是否正在刷新 Token？
 *    ├── 否 → 开始刷新流程
 *    │     ├── 用 Refresh Token 调用 /auth/refresh 接口
 *    │     ├── 成功 → 保存新 Token，重发原始请求 ✅
 *    │     └── 失败 → 清除 Token，跳转登录页 ❌
 *    └── 是 → 将请求加入等待队列
 *            └── 等待刷新完成后，自动重发队列中的请求
 */

/**
 * isRefreshing：标记是否正在进行 Token 刷新
 * ------------------------------------------
 * 这是一个布尔锁（boolean lock），用于防止并发刷新问题。
 *
 * 问题场景：假设同时发起 3 个 API 请求，都收到 401 错误：
 *   请求A → 401 → 开始刷新 Token
 *   请求B → 401 → ???
 *   请求C → 401 → ???
 *
 * 如果没有这个标志，三个请求都会尝试刷新 Token，导致：
 * - 多次发送 refresh 请求，浪费资源
 * - 可能产生竞态条件（race condition）
 * - 第二个 refresh 可能会用已失效的 refresh_token
 *
 * 解决方案：第一个请求发现 401 后设置 isRefreshing = true，
 * 后续请求看到 isRefreshing 为 true 就知道"有人已经在刷新了"，
 * 于是将自己的请求加入等待队列。
 */
let isRefreshing = false

/**
 * failedQueue：等待 Token 刷新完成的请求队列
 * --------------------------------------------
 * 当 isRefreshing 为 true 时，新的 401 请求不会立即处理，
 * 而是被封装成 Promise 加入这个数组。
 *
 * 数组元素结构：
 * { resolve: Function, reject: Function }
 * - resolve：Token 刷新成功时调用，让请求继续
 * - reject：Token 刷新失败时调用，让请求报错
 *
 * 这是观察者模式（Observer Pattern）的一个简单实现：
 * 多个请求"订阅"了刷新事件，刷新完成时统一"通知"它们。
 */
let failedQueue: Array<{ resolve: (v: unknown) => void; reject: (e: unknown) => void }> = []

/**
 * processQueue：处理等待队列中的请求
 * ------------------------------------
 * @param error - 如果有错误，通知所有排队请求失败；否则通知成功
 *
 * 这个函数会在 Token 刷新操作完成后被调用（无论成功还是失败），
 * 统一处理所有排队的请求：
 * - 成功时：resolve 所有排队的 Promise，触发它们重发请求
 * - 失败时：reject 所有排队的 Promise，让它们报错
 * - 最后清空队列，准备下一次可能需要的排队
 */
const processQueue = (error: unknown) => {
  failedQueue.forEach((p) => {
    if (error) p.reject(error)
    else p.resolve(undefined)
  })
  failedQueue = []
}

/**
 * 注册响应拦截器
 * ---------------
 * 这里实现了完整的"自动 Token 刷新 + 请求重试"逻辑，
 * 是整个认证机制中最复杂的部分。
 *
 * 参数说明：
 * 第一个参数 (response) => response：
 *   - 响应状态码在 2xx 范围内时调用
 *   - 直接返回响应对象，不做任何处理（透传）
 *   - 相当于说"成功的响应我不管"
 *
 * 第二个参数 async (error) => {...}：
 *   - 响应状态码不在 2xx 范围时调用（如 400、401、403、500 等）
 *   - 或者网络错误（无网络、超时、CORS 问题等）
 *   - 这里我们主要关注 401 状态码（未授权）
 */
apiClient.interceptors.response.use(
  // 成功响应：直接透传，不做任何额外处理
  (response) => response,

  // 错误响应：处理各种异常情况
  async (error) => {
    /**
     * originalRequest：保存原始失败的请求配置
     * ----------------------------------------
     * error.config 包含了导致错误的那个请求的完整配置，
     * 我们保存它的引用，以便后续可能需要重试该请求。
     *
     * 为什么需要重试？因为 401 很可能只是 Token 过期了，
     * 刷新 Token 后，同样的请求再发一次就能成功了。
     */
    const originalRequest = error.config

    /**
     * 判断是否需要处理 Token 刷新的条件：
     * 1. error.response?.status === 401：服务器返回未授权
     *    - ? 是可选链操作符，防止 error.response 不存在时报错
     * 2. !originalRequest._retry：该请求尚未尝试过刷新
     *    - _retry 是我们在原请求上添加的自定义标记
     *    - 防止无限循环：如果刷新后又 401，不会再次尝试刷新
     */
    if (error.response?.status === 401 && !originalRequest._retry) {
      /**
       * 场景一：已经有其他请求在刷新 Token 了
       * ---------------------------------------
       * 此时 isRefreshing === true，说明有一个"先行者"正在执行刷新。
       * 我们不应该再发一次 refresh 请求，而是：
       * 1. 创建一个新的 Promise，将其 resolve/reject 加入队列
       * 2. 当 Promise 被 resolve 时（即刷新成功），重发我们的请求
       * 3. 这样就实现了"等待刷新完成后自动重试"
       */
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
          // 当上面的 resolve/reject 被 processQueue 调用时，
          // .then() 会被触发，执行 apiClient(originalRequest) 重发请求
        }).then(() => apiClient(originalRequest))
      }

      /**
       * 场景二：我是第一个遇到 401 的请求，我来负责刷新 Token
       * ---------------------------------------------------------
       * 执行以下步骤：
       * 1. 标记原始请求已尝试过重试（_retry = true）
       * 2. 设置刷新锁定（isRefreshing = true）
       * 3. 获取 refresh_token 并尝试刷新
       * 4. 根据结果处理队列中的其他请求
       */
      originalRequest._retry = true
      isRefreshing = true

      /**
       * 获取 Refresh Token
       * -------------------
       * Refresh Token 是用户登录时服务器同时颁发的长期有效令牌，
       * 专门用于在 Access Token 过期后获取新的 Token 对。
       *
       * 它通常比 Access Token 有更长的有效期（几天到几周），
       * 并且可以被服务器单独撤销（例如用户主动退出登录时）。
       */
      const refreshToken = localStorage.getItem('refresh_token')

      /**
       * 如果没有 Refresh Token，说明无法刷新，只能放弃治疗
       * -----------------------------------------------------
       * 清除所有 Token 信息并跳转到登录页面。
       * window.location.href = '/login' 会触发页面导航到登录页。
       */
      if (!refreshToken) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(error)
      }

      /**
       * 尝试用 Refresh Token 获取新的 Token 对
       * --------------------------------------
       * 调用服务器的 Token 刷新接口（通常是 POST /auth/refresh），
       * 发送当前的 refresh_token，期望返回新的 access_token 和 refresh_token。
       *
       * 注意：这里直接使用原生 axios 而不是 apiClient，
       * 因为 apiClient 有拦截器，可能会递归触发刷新逻辑！
       * 使用裸 axios 可以避免这个问题。
       */
      try {
        const res = await axios.post(
          `${apiClient.defaults.baseURL}/auth/refresh`,
          { refresh_token: refreshToken }
        )

        /**
         * Token 刷新成功！更新本地存储
         * -----------------------------
         * 将新获取的 Token 对保存到 localStorage，
         * 后续的请求就会使用新的 Access Token。
         */
        localStorage.setItem('access_token', res.data.access_token)
        localStorage.setItem('refresh_token', res.data.refresh_token)

        /**
         * 通知等待队列中的所有请求："Token 已刷新，你们可以重发了"
         * processQueue(null) 表示没有错误，会调用所有排队请求的 resolve
         */
        processQueue(null)

        /**
         * 重发原始请求
         * -------------
         * 用更新后的 Token（已在 request interceptor 中自动添加）
         * 重新发送最初失败的请求。
         * 这次请求的 header 里已经包含了新的 Access Token，
         * 所以应该能够正常通过服务器的身份验证。✅
         */
        return apiClient(originalRequest)

      } catch (refreshError) {
        /**
         * Token 刷新失败（Refresh Token 也过期或无效了）
         * ----------------------------------------------
         * 这种情况通常意味着：
         * - Refresh Token 已经过期
         * - Refresh Token 被服务器撤销（用户被禁用等）
         * - Refresh Token 被篡改
         *
         * 处理方式：
         * 1. 通知队列中的所有请求失败了（processQueue(refreshError)）
         * 2. 清除本地存储的所有 Token
         * 3. 跳转到登录页面，要求用户重新登录
         */
        processQueue(refreshError)
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)

      } finally {
        /**
         * 无论成功还是失败，都要释放刷新锁
         * ----------------------------------
         * finally 块确保即使发生异常也会执行。
         * 重置 isRefreshing 为 false，允许下次 401 时再次尝试刷新。
         */
        isRefreshing = false
      }
    }

    /**
     * 非 401 错误或其他不需要特殊处理的情况
     * --------------------------------------
     * 直接将错误抛出，交给调用者（业务代码）处理。
     * 例如：400 参数错误、403 无权限、500 服务器错误等。
     */
    return Promise.reject(error)
  }
)

export default apiClient
