# Agent系统v2.3-FloatingAgent Persona记忆测试数据

## 一、测试目标

验证 v2.3 第四个功能「FloatingAgent Persona 记忆」是否完成轻量 UI 偏好闭环：

1. 悬浮 Agent 支持角色切换。
2. 最近选择的 persona 保存到浏览器 `localStorage`。
3. 下次打开悬浮 Agent 时读取最近使用的 persona。
4. 发送消息时使用当前选择的 persona，不再固定为 `academic_mentor`。
5. 陪伴班主任角色有更温和的空态文案。
6. 新增「昕哥」Agent 角色，并支持主 Agent / 悬浮 Agent 角色选择展示 emoji 标识。
7. 该记忆只属于 UI 偏好，不写入后端用户画像，不展示用户画像。

## 二、实现范围

| 模块 | 说明 |
| --- | --- |
| `agent_system/prompts/persona_prompt.py` | 新增 `xinge` persona、提示词和 emoji 标识 |
| `agent_system/api/agent_api.py` | `/agent/personas` 返回 `icon` 字段 |
| `frontend-vue/src/views/AgentView.vue` | 主 Agent 角色选项显示 emoji，并补充昕哥示例和空态 |
| `frontend-vue/src/components/FloatingAgent.vue` | 新增 persona 下拉、偏好读写、按 persona 发送请求、陪伴班主任空态 |
| `frontend-vue/scripts/ui-regression-check.mjs` | 新增 FloatingAgent persona 偏好静态回归检查 |

## 三、关键设计

### 新增角色

```text
id=xinge
name=昕哥
icon=😎
```

提示词特点：

```text
喜欢称呼用户为好兄弟、好兄弟们
喜欢鼓励大家
遇到错误时讲清为什么不要再犯、可能导致什么后果
会适度引经据典
喜欢嘿嘿笑
定位是大家的好老师好兄弟
```

### 存储边界

```text
localStorage key=floating-agent-persona
```

说明：

```text
只保存用户最近选择的 UI 角色偏好。
不写数据库。
不扩展为长期用户画像。
不在前端展示用户画像。
```

### 发送请求

修复前：

```text
FloatingAgent 固定 persona=academic_mentor
```

修复后：

```text
FloatingAgent 使用 persona: selectedPersona.value
```

## 四、回归用例

### 用例 1：读取 persona 偏好

预期源码特征：

```text
localStorage.getItem('floating-agent-persona')
```

结论：通过。

### 用例 2：保存 persona 偏好

预期源码特征：

```text
localStorage.setItem('floating-agent-persona', selectedPersona.value)
```

结论：通过。

### 用例 3：发送时使用当前 persona

预期源码特征：

```text
persona: selectedPersona.value
```

反向检查：

```text
FloatingAgent 不再出现 persona: 'academic_mentor' 的硬编码发送逻辑
```

结论：通过。

### 用例 4：陪伴班主任空态

预期源码特征：

```text
companion_head_teacher
慢慢说，我在这儿
可以聊压力、拖延、考试焦虑，也可以一起拆一个小计划
```

结论：通过。

### 用例 5：昕哥 persona 注册与 emoji 角色选择

预期源码特征：

```text
"xinge"
XINGE_PERSONA
personaTitle(p)
personaTitle(item)
```

预期展示：

```text
😎 昕哥
```

结论：通过。

## 五、自动化验证

### 后端编译

命令：

```text
python -m compileall agent_system DAO model main.py
```

结果：

```text
后端编译通过
```

### 前端构建

命令：

```text
npm.cmd run build
```

结果：

```text
前端生产构建通过
```

### UI 回归

命令：

```text
npm.cmd run test:ui-regression
```

结果：

```text
UI 回归检查通过：58/58
Playwright UI 回归通过：2/2
```

新增静态护栏：

```text
PASS 后端注册昕哥 persona
PASS 后端存在昕哥提示词
PASS AgentView 角色选项显示 emoji 标识
PASS AgentView 支持昕哥示例和空态
PASS FloatingAgent 读取 persona 偏好
PASS FloatingAgent 保存 persona 偏好
PASS FloatingAgent 发送时使用当前 persona
PASS FloatingAgent 不再硬编码默认 persona 发送
PASS FloatingAgent 支持陪伴班主任空态
PASS FloatingAgent 支持昕哥空态
PASS FloatingAgent 角色选项显示 emoji 标识
```

## 六、结论

FloatingAgent Persona 记忆已完成：

```text
加载 persona 列表
  -> 读取 localStorage 最近选择
  -> 用户可在主 Agent / 悬浮 Agent 中看到 emoji 角色标识
  -> 用户可在悬浮 Agent 头部切换角色
  -> 保存 floating-agent-persona
  -> 发送消息时使用 selectedPersona
  -> 陪伴班主任 / 昕哥显示对应空态
```

该功能保持轻量，只解决悬浮 Agent 的角色偏好体验，不引入长期用户画像。
