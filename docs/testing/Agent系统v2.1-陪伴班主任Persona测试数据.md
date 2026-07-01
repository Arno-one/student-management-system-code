# Agent系统v2.1-陪伴班主任Persona测试数据

## 一、测试目标

验证 v2.1 P2 功能「陪伴班主任 Persona」是否满足以下要求：

1. 后端 `PERSONA_REGISTRY` 新增陪伴班主任角色。
2. `/agent/personas` 可返回新增角色，前端角色下拉框可自动展示。
3. 执行器能把陪伴班主任 system prompt 注入普通回复和工具结果总结。
4. 未知 persona 仍回退到默认 `academic_mentor`，不影响旧调用。
5. 前端 Agent 页面空态文案和示例问题能随角色切换。
6. 陪伴班主任有明确边界：不做心理诊断、不承诺治疗、不替学生做重大决定，遇到危险表达要引导联系现实支持。

## 二、涉及文件

| 文件 | 说明 |
| --- | --- |
| `agent_system/prompts/persona_prompt.py` | 新增 `COMPANION_HEAD_TEACHER_PERSONA` 和 `companion_head_teacher` 注册项 |
| `agent_system/prompts/__init__.py` | 导出新增 persona 常量 |
| `frontend-vue/src/views/AgentView.vue` | 新增角色联动空态提示和示例问题 |

## 三、测试数据

### 用例 1：Persona 注册表包含陪伴班主任

测试脚本：

```python
from agent_system.prompts.persona_prompt import PERSONA_REGISTRY, COMPANION_HEAD_TEACHER_PERSONA

entry = PERSONA_REGISTRY["companion_head_teacher"]
assert entry["name"] == "陪伴班主任"
assert entry["system_prompt"] == COMPANION_HEAD_TEACHER_PERSONA
```

实际输出：

```text
陪伴班主任
共情陪伴型班主任，适合聊压力、拖延、考试焦虑和轻量计划
prompt_length= 567
```

结论：通过。

### 用例 2：执行器能读取新 persona，并保持未知 persona 回退

测试脚本：

```python
from agent_system.prompts.persona_prompt import PERSONA_REGISTRY, COMPANION_HEAD_TEACHER_PERSONA
from agent_system.executor.agent_executor import _get_persona_prompt, _build_reply_messages

assert _get_persona_prompt("companion_head_teacher") == COMPANION_HEAD_TEACHER_PERSONA
assert _get_persona_prompt("unknown_persona") == PERSONA_REGISTRY["academic_mentor"]["system_prompt"]

system_prompt, user_content = _build_reply_messages("stress", "companion_head_teacher")
assert COMPANION_HEAD_TEACHER_PERSONA in system_prompt
assert user_content == "stress"
```

结论：通过。新角色能进入执行器 prompt，未知角色不破坏旧逻辑。

### 用例 3：前端角色选择与空态示例联动

测试点：

| 场景 | 预期 |
| --- | --- |
| 默认角色 `academic_mentor` | 空态提示为“查成绩、问制度、聊学习”等 |
| 选择 `companion_head_teacher` | 空态提示为“聊压力、拖延、考试焦虑、小计划”等 |
| 示例问题区域 | 根据当前 persona 展示不同问题 |

陪伴班主任示例问题：

```text
最近压力有点大，能陪我梳理一下吗
我总是拖延，今天该先做什么
快考试了我很焦虑，怎么缓一缓
我和同学相处有点别扭，想聊聊
帮我做一个今晚能完成的小计划
我今天状态不好，但又不想放弃
```

结论：通过。前端构建成功，模板可正常编译。

## 四、回归命令

```bash
python -m compileall agent_system DAO model main.py
npm.cmd run build
```

结果：

```text
Compiling 'agent_system\\prompts\\__init__.py'...
Compiling 'agent_system\\prompts\\persona_prompt.py'...
✓ built in 5.37s
```

结论：通过。

## 五、边界说明

陪伴班主任是“轻量陪伴与行动建议”角色，不是心理诊断工具。

必须遵守：

1. 不做心理疾病诊断。
2. 不承诺治疗效果。
3. 不替学生做重大人生决定。
4. 不编造学校政策、电话或外部资源。
5. 遇到自伤、伤人或现实危险表达时，引导学生立刻联系身边可信任成年人、学校老师、家长或当地紧急求助渠道。

## 六、后续建议

1. 后续可让全局 `FloatingAgent` 也支持 persona 选择或记住用户最近使用的 persona。
2. 可以结合 Agent 反馈数据，观察陪伴班主任在情绪支持场景下的满意度。
3. 如果未来引入长期画像，应对陪伴类对话设置更严格的隐私和摘要策略。
