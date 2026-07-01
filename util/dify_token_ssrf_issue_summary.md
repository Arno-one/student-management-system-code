# Dify HTTP 模块未传 Token 导致接口异常问题总结

> 更新时间：2026-06-09  
> 适用场景：Dify 通过 HTTP 节点对接本项目后端接口时，登录正常，但其他接口调用异常

---

## 1. 问题现象

在 Dify 对接本项目接口时，出现了下面的现象：

- `POST /auth/login` 可以正常调用
- 登录成功后也能拿到 `data.token`
- 但后续其他业务接口无法正常访问
- 在排查过程中，现象一度看起来像是被 Dify 的 SSRF 相关限制拦住了

典型表现就是：

- 只有登录接口能通
- 其他需要登录态的接口全部失败

---

## 2. 最终根因

最终确认，**不是接口本身有问题，也不是单纯的网络连通问题**，而是：

**在 Dify 的 HTTP 模块中，后续请求没有带上鉴权 Token。**

也就是没有传：

```http
Authorization: Bearer <token>
```

本项目中：

- `/auth/login` 是免鉴权接口，所以可以正常调用
- 除登录外的大多数业务接口，都必须携带 Bearer Token

因此就会出现“登录可以，其他接口都不行”的情况。

---

## 3. 为什么容易误判成 SSRF 问题

这个问题容易被误判，主要是因为表面现象很像：

- Dify 已经能访问服务
- 登录接口也确实成功了
- 说明基地址、端口、路径大概率没问题
- 但后续接口就是调用不过去

这时候很容易先怀疑：

- Dify 的网络策略
- 回环地址 / 内网地址限制
- SSRF 防护
- URL 配置错误

但这次实际根因是：

**后续 HTTP 节点没有把登录接口返回的 token 继续传下去。**

所以更准确地说，这次问题是：

**表象像 SSRF / 访问限制，实质是鉴权头缺失。**

---

## 4. 正确配置方式

### 4.1 第一步：调用登录接口

接口：

```text
POST /auth/login
```

请求体示例：

```json
{
  "username": "admin",
  "password": "你的密码"
}
```

从响应中提取：

```text
data.token
```

建议在 Dify 中保存为变量：

```text
token
```

---

### 4.2 第二步：后续 HTTP 节点统一带上 Token

后续所有需要鉴权的接口，都要在 Header 中传入：

```http
Authorization: Bearer {{token}}
Content-Type: application/json
```

其中：

- `{{token}}` 是上一步从登录接口响应中提取出来的变量
- 如果是 `GET` 请求，没有请求体，也仍然要带 `Authorization`
- 如果是 `POST`、`PATCH`、`PUT` 等请求，通常还需要加 `Content-Type: application/json`

---

## 5. 一个可直接复用的 Dify 调用链路

### 节点 1：登录

- 方法：`POST`
- URL：`http://localhost:8088/auth/login`
- Body：

```json
{
  "username": "admin",
  "password": "你的密码"
}
```

提取变量：

```text
data.token -> token
```

### 节点 2：调用业务接口

例如：

```text
GET /statistics/stu_count
```

或：

```text
POST /nl2sql/query
```

Header：

```http
Authorization: Bearer {{token}}
Content-Type: application/json
```

这样配置后，接口即可正常通过鉴权。

---

## 6. 以后排查这类问题的建议顺序

以后如果再遇到“Dify 能登录，但其他接口都失败”的情况，建议按下面顺序排查：

### 6.1 先确认是否只有登录接口免鉴权

先区分：

- 登录接口是否免鉴权
- 其他业务接口是否要求 Bearer Token

如果是，就优先怀疑 **token 是否没有传递成功**。

### 6.2 检查 token 是否真的提取到了

重点看 Dify 变量里保存的是不是：

```text
data.token
```

避免出现这些问题：

- 提取路径写错
- 提取到的是整个 `data`
- 变量名写了，但后续 Header 没引用对
- token 为空字符串或 null

### 6.3 检查 Header 是否真的加到了后续节点

重点确认后续节点里是否显式存在：

```http
Authorization: Bearer {{token}}
```

注意：

- 不是只在登录节点配置
- 而是每个需要鉴权的 HTTP 节点都要带上

### 6.4 最后再排查网络 / SSRF / 地址限制

只有在确认以下内容都没问题之后，再去怀疑 SSRF 或网络策略：

- 基地址正确
- Dify 能访问该服务
- token 已成功提取
- Header 已正确传递

这样能明显减少误判。

---

## 7. 本次问题的结论

本次问题可以总结为一句话：

**Dify 里“登录能通、其他接口不通”时，不要先盯着 SSRF，先检查后续 HTTP 节点有没有传 `Authorization: Bearer {{token}}`。**

这次的最终解决方式就是：

**在 Dify 的 HTTP 模块中补上传入 token 鉴权。**

补上之后，问题解决。

---

## 8. 推荐做法

为了避免后续重复踩坑，建议固定采用下面的对接模式：

1. 第一个 HTTP 节点专门登录
2. 从响应中提取 `data.token`
3. 后续所有业务节点统一复用 `Authorization: Bearer {{token}}`
4. 调试时优先检查“变量提取”和“Header 传递”
5. 确认鉴权无误后，再排查 SSRF、网络、地址白名单等问题

这样排查效率会高很多。
