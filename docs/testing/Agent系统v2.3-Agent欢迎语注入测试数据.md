# Agent系统 v2.3 - Agent 欢迎语注入测试数据

## 一、测试目标

验证本轮 v2.3 功能“新对话欢迎语注入”已经按设计落地：

1. 新开对话时，前端会先展示一条真实的 assistant 欢迎语消息。
2. 欢迎语按 persona 固定模板生成。
3. 欢迎语只存在前端，不写入后端历史，不参与摘要。
4. `AgentView` 和 `FloatingAgent` 都生效。
5. 欢迎语样式跟随当前浅色 / 深色主题。

## 二、实现范围

| 模块 | 说明 |
| --- | --- |
| `frontend-vue/src/config/agentPersonas.js` | 新增 persona 欢迎语模板与欢迎语消息工厂 |
| `frontend-vue/src/views/AgentView.vue` | 主 Agent 新会话注入欢迎语，历史会话不注入 |
| `frontend-vue/src/components/FloatingAgent.vue` | 悬浮 Agent 空会话注入欢迎语，切换 persona 时同步更新 |
| `frontend-vue/scripts/ui-regression-check.mjs` | 新增欢迎语注入静态护栏 |
| `frontend-vue/scripts/ui-regression-playwright.mjs` | 新增欢迎语可视化回归场景 |

## 三、关键设计

### 1. 欢迎语生成方式

```text
前端按 persona 配置固定欢迎语模板
通过 createPersonaWelcomeMessage(personaId) 统一生成消息对象
消息带有 _welcome 标记，便于只在前端识别
```

### 2. 不持久化策略

```text
欢迎语只直接写入前端 messages
不调用后端接口
不写 AgentTask / TalkMessage
切换历史会话时直接用后端真实消息覆盖
```

### 3. 注入规则

```text
AgentView：
- 初次进入空会话时注入
- 点击“新对话”时注入
- 切换 persona 且当前只有欢迎语时，更新欢迎语

FloatingAgent：
- 初次挂载空会话时注入
- 切换 persona 且当前只有欢迎语时，更新欢迎语
- 已进入真实对话后，不回写覆盖已有会话内容
```

## 四、测试用例

### 用例 1：主 Agent 初始欢迎语

预期：

```text
进入 /agent 页面后，聊天区直接出现学业导师欢迎语
不再显示原空态占位块
```

结果：

```text
通过
```

### 用例 2：切换历史会话不保留欢迎语

预期：

```text
点击右侧历史摘要后，聊天区展示后端真实历史消息
前端注入的欢迎语消失
```

结果：

```text
通过
```

### 用例 3：新对话重新注入欢迎语

预期：

```text
点击“新对话”后，当前会话重新显示 persona 欢迎语
不依赖后端返回
```

结果：

```text
通过
```

### 用例 4：悬浮 Agent 支持 persona 切换欢迎语

预期：

```text
悬浮 Agent 初始显示学业导师欢迎语
切换到“昕哥”后，欢迎语同步切换为昕哥风格
```

结果：

```text
通过
```

### 用例 5：进入真实对话后欢迎语不影响消息流

预期：

```text
欢迎语保留在首条 assistant 消息位置
发送真实消息后，新的 assistant streaming 消息继续正常追加
不影响图片卡片、路线卡片、POI 卡片等既有渲染
```

结果：

```text
通过
```

## 五、自动化验证

### 1. 前端静态回归

命令：

```text
npm.cmd run test:ui-regression:static
```

结果：

```text
UI 回归检查通过：116/116
PASS 前端 persona 配置包含欢迎语模板
PASS 前端提供欢迎语消息工厂
PASS AgentView 接入 persona 欢迎语工厂
PASS AgentView 标记前端欢迎语消息
PASS AgentView 新会话注入欢迎语
PASS FloatingAgent 接入 persona 欢迎语工厂
PASS FloatingAgent 标记前端欢迎语消息
PASS FloatingAgent 空会话注入欢迎语
```

### 2. Playwright 可视化回归

命令：

```text
npm.cmd run test:ui-regression:e2e
```

结果：

```text
Playwright 主 Agent 欢迎语与图片卡片回归：通过
Playwright 悬浮 Agent 欢迎语与图片卡片回归：通过
Playwright 折叠侧栏系统管理入口回归：通过
Playwright UI 回归通过：3/3
```

## 六、结论

本轮 v2.3 “新对话欢迎语注入”已完成闭环开发与验证。

当前交付边界：

1. 欢迎语模板固定在前端配置中，不调用大模型动态生成。
2. 欢迎语只覆盖空会话，不改写已有真实聊天记录。
3. 欢迎语不落库、不入历史、不参与摘要生成。
