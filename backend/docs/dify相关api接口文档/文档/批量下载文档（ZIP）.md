> ## Documentation Index
> Fetch the complete documentation index at: https://docs.dify.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# 批量下载文档（ZIP）

> 将多个上传文件文档下载为单个 ZIP 压缩包。最多接受 `100` 个文档 ID。



## OpenAPI

````yaml /zh/api-reference/openapi_knowledge.json post /datasets/{dataset_id}/documents/download-zip
openapi: 3.0.1
info:
  title: 知识库 API
  description: >-
    用于管理知识库、文档、分段、元数据和标签的 API，包括创建、检索和配置操作。**注意：**单个知识库 API
    密钥有权操作同一账户下所有可见的知识库。请注意数据安全。
  version: 1.0.0
servers:
  - url: '{apiBaseUrl}'
    description: Knowledge API 的基础 URL。
    variables:
      apiBaseUrl:
        default: https://api.dify.ai/v1
        description: API 的实际基础 URL
security:
  - ApiKeyAuth: []
tags:
  - name: 知识库
    description: 用于管理知识库的操作，包括创建、配置和检索。
  - name: 文档
    description: 用于在知识库中创建、更新和管理文档的操作。
  - name: 分段
    description: 用于管理分段和子分段的操作。
  - name: 元数据
    description: 用于管理知识库元数据字段和文档元数据值的操作。
  - name: 标签
    description: 用于管理知识库标签和标签绑定的操作。
  - name: 模型
    description: 用于获取可用模型的操作。
  - name: 知识流水线
    description: 用于管理和运行知识流水线的操作，包括数据源插件和流水线执行。
paths:
  /datasets/{dataset_id}/documents/download-zip:
    post:
      tags:
        - 文档
      summary: 批量下载文档（ZIP）
      description: 将多个上传文件文档下载为单个 ZIP 压缩包。最多接受 `100` 个文档 ID。
      operationId: downloadDocumentsZipZh
      parameters:
        - name: dataset_id
          in: path
          required: true
          schema:
            type: string
            format: uuid
          description: 知识库 ID。
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - document_ids
              properties:
                document_ids:
                  type: array
                  minItems: 1
                  maxItems: 100
                  items:
                    type: string
                    format: uuid
                  description: 要包含在 ZIP 压缩包中的文档 ID 数组。
      responses:
        '200':
          description: 包含所请求文档的 ZIP 压缩包。
          content:
            application/zip:
              schema:
                type: string
                format: binary
                description: ZIP 压缩包二进制流。
        '403':
          description: '`forbidden` : 权限不足。'
          content:
            application/json:
              examples:
                forbidden:
                  summary: forbidden
                  value:
                    status: 403
                    code: forbidden
                    message: Insufficient permissions.
        '404':
          description: '`not_found` : 文档或知识库未找到。'
          content:
            application/json:
              examples:
                not_found:
                  summary: not_found
                  value:
                    status: 404
                    code: not_found
                    message: Document not found.
components:
  securitySchemes:
    ApiKeyAuth:
      type: http
      scheme: bearer
      bearerFormat: API_KEY
      description: >-
        API Key 认证。对于所有 API 请求，请在 `Authorization` HTTP 头中包含您的 API Key，并加上
        `Bearer ` 前缀。示例：`Authorization: Bearer {API_KEY}`。**强烈建议将 API Key
        存储在服务端，不要在客户端共享或存储，以避免 API Key 泄漏导致严重后果。**

````