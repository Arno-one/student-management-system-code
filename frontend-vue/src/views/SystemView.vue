<template>
  <section id="page-system" class="page active">
    <div class="sub-bar">
      <label>系统管理</label>
      <CustomSelect v-model="sub" :options="subOptions" @update:model-value="saveSub" />
    </div>

    <div id="sys-users" class="card subcard" :class="{ show: sub === 'sys-users' }">
      <h3>用户管理</h3>

      <div class="section-title">查询用户</div>
      <div class="grid">
        <div class="field"><label>账号</label><input v-model="userQuery.username" /></div>
        <div class="field"><label>姓名</label><input v-model="userQuery.realName" /></div>
        <div class="field"><label>状态</label><CustomSelect v-model="userQuery.status" :options="statusFilterOptions" /></div>
        <div class="field"><label>偏移量</label><input v-model.number="userQuery.skip" type="number" /></div>
        <div class="field"><label>每页条数</label><input v-model.number="userQuery.limit" type="number" /></div>
      </div>
      <div class="actions">
        <button class="btn secondary" :disabled="loading" @click="loadUsers">查询用户</button>
      </div>
      <DataTable :data="users" />

      <div class="section-title">新增用户</div>
      <div class="grid">
        <div class="field"><label>账号 *</label><input v-model="userForm.username" /></div>
        <div class="field"><label>初始密码 *</label><input v-model="userForm.password" type="password" /></div>
        <div class="field"><label>姓名 *</label><input v-model="userForm.realName" /></div>
        <div class="field"><label>手机号</label><input v-model="userForm.phone" /></div>
        <div class="field"><label>邮箱</label><input v-model="userForm.email" /></div>
        <div class="field"><label>状态</label><CustomSelect v-model.number="userForm.status" :options="enableDisableOptions" /></div>
        <div class="field"><label>首次登录强制改密</label><CustomSelect v-model.number="userForm.mustChangePassword" :options="yesNoOptions" /></div>
        <div class="field field-span-2"><label>角色</label><div class="check-grid"><label v-for="role in roleOptions" :key="role.id" class="check-item"><input v-model="userForm.roleIds" type="checkbox" :value="role.id" />{{ role.role_name }}</label></div></div>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="createUser">新增用户</button>
      </div>

      <div class="section-title">编辑 / 重置密码 / 分配角色</div>
      <div class="grid">
        <div class="field"><label>用户ID *</label><input v-model.number="userEdit.id" type="number" /></div>
        <div class="field"><label>姓名</label><input v-model="userEdit.realName" /></div>
        <div class="field"><label>手机号</label><input v-model="userEdit.phone" /></div>
        <div class="field"><label>邮箱</label><input v-model="userEdit.email" /></div>
        <div class="field"><label>状态</label><CustomSelect v-model="userEdit.status" :options="statusNoModifyOptions" /></div>
        <div class="field"><label>首次登录强制改密</label><CustomSelect v-model="userEdit.mustChangePassword" :options="yesNoNoModifyOptions" /></div>
        <div class="field"><label>重置密码</label><input v-model="userEdit.newPassword" type="password" placeholder="留空则不重置" /></div>
        <div class="field"><label>重置后强制改密</label><CustomSelect v-model.number="userEdit.resetMustChangePassword" :options="yesNoOptions" /></div>
        <div class="field field-span-2"><label>重新分配角色</label><div class="check-grid"><label v-for="role in roleOptions" :key="'edit-role-' + role.id" class="check-item"><input v-model="userEdit.roleIds" type="checkbox" :value="role.id" />{{ role.role_name }}</label></div></div>
      </div>
      <div class="actions">
        <button class="btn secondary" :disabled="loading" @click="updateUser">更新用户</button>
        <button class="btn secondary" :disabled="loading" @click="assignUserRoles">分配角色</button>
        <button class="btn danger" :disabled="loading" @click="resetUserPassword">重置密码</button>
      </div>
      <ResultBadge :badge="results.user.badge" :text="results.user.text" />
    </div>

    <div id="sys-roles" class="card subcard" :class="{ show: sub === 'sys-roles' }">
      <h3>角色管理</h3>

      <div class="sys-role-top">
        <div class="sys-role-left">
          <div class="section-title">查询角色</div>
          <div class="grid grid-4">
            <div class="field"><label>角色名</label><input v-model="roleQuery.roleName" /></div>
            <div class="field"><label>状态</label><CustomSelect v-model="roleQuery.status" :options="statusFilterOptions" /></div>
            <div class="field"><label>偏移量</label><input v-model.number="roleQuery.skip" type="number" /></div>
            <div class="field"><label>每页条数</label><input v-model.number="roleQuery.limit" type="number" /></div>
          </div>
          <div class="actions">
            <button class="btn secondary" :disabled="loading" @click="loadRoles">查询角色</button>
          </div>
          <DataTable :data="roles" />

          <div class="section-title">新增角色</div>
          <div class="grid grid-4">
            <div class="field"><label>角色编码 *</label><input v-model="roleForm.roleCode" placeholder="例如 counsellor" /></div>
            <div class="field"><label>角色名称 *</label><input v-model="roleForm.roleName" /></div>
            <div class="field"><label>状态</label><CustomSelect v-model.number="roleForm.status" :options="enableDisableOptions" /></div>
            <div class="field"><label>备注</label><input v-model="roleForm.remark" /></div>
          </div>
          <div class="actions">
            <button class="btn" :disabled="loading" @click="createRole">新增角色</button>
          </div>
        </div>
      </div>

      <!-- 权限分配面板：独立于 grid，全宽展示 -->
      <div class="sys-perm-panel">
        <div class="sys-perm-head">
          <div class="section-title">权限分配</div>
          <div class="sys-perm-head-row">
            <div class="field" style="width:140px"><label>角色ID *</label><input v-model.number="roleEdit.id" type="number" /></div>
            <div class="field" style="width:180px"><label>角色名称</label><input v-model="roleEdit.roleName" /></div>
            <div class="field" style="width:100px"><label>状态</label><CustomSelect v-model="roleEdit.status" :options="statusNoModifyOptions" /></div>
            <button class="btn secondary" style="align-self:flex-end;height:36px" :disabled="loading" @click="loadRoleDetail">加载角色</button>
            <button class="btn" style="align-self:flex-end;height:36px" :disabled="loading" @click="assignRolePermissions">保存权限</button>
            <button class="btn secondary" style="align-self:flex-end;height:36px" :disabled="loading" @click="updateRole">更新信息</button>
          </div>
        </div>

        <!-- 权限分组双列布局 -->
        <div class="sys-perm-grid">
          <div v-for="group in permissionGroups" :key="group.module" class="sys-perm-module">
            <div class="sys-perm-module-head">
              <span class="sys-perm-module-name">{{ group.module }}</span>
              <span class="sys-perm-module-count">{{ enabledCount(group) }} / {{ group.items.length }}</span>
            </div>
            <div class="sys-perm-item" v-for="perm in group.items" :key="perm.id">
              <div class="sys-perm-item-info">
                <span class="sys-perm-item-name">{{ perm.permission_name }}</span>
                <span class="sys-perm-item-code">{{ perm.permission_code }}</span>
              </div>
              <label class="sys-toggle" :class="{ 'sys-toggle--on': roleEdit.permissionIds.includes(perm.id) }">
                <input type="checkbox" :value="perm.id" v-model="roleEdit.permissionIds" />
                <span class="sys-toggle-track">
                  <span class="sys-toggle-knob"></span>
                </span>
                <span class="sys-toggle-label">{{ roleEdit.permissionIds.includes(perm.id) ? '开启' : '禁止' }}</span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <ResultBadge :badge="results.role.badge" :text="results.role.text" />
    </div>

    <div id="sys-agent-monitor" class="card subcard" :class="{ show: sub === 'sys-agent-monitor' }">
      <div class="agent-monitor-head">
        <div>
          <h3>Agent 监控</h3>
          <p class="agent-monitor-sub">调用量、成功率、耗时、工具失败率与用户反馈质量</p>
        </div>
        <div class="agent-monitor-filters">
          <div class="field"><label>时间范围</label><CustomSelect v-model.number="monitorQuery.days" :options="monitorDayOptions" /></div>
          <div class="field"><label>状态</label><CustomSelect v-model="monitorQuery.status" :options="monitorStatusOptions" /></div>
          <div class="field"><label>意图</label><CustomSelect v-model="monitorQuery.intent" :options="monitorIntentOptions" /></div>
          <button class="btn secondary" :disabled="loading" @click="loadAgentMonitor">刷新</button>
        </div>
      </div>

      <div class="agent-monitor-cards">
        <div class="agent-monitor-card">
          <span>总调用量</span>
          <strong>{{ monitorMetrics.total_tasks }}</strong>
          <small>近 {{ monitorMetrics.window_days || monitorQuery.days }} 天</small>
        </div>
        <div class="agent-monitor-card">
          <span>任务成功率</span>
          <strong>{{ monitorMetrics.success_rate }}%</strong>
          <small>{{ monitorMetrics.success_count }} 成功 / {{ monitorMetrics.error_count }} 失败</small>
        </div>
        <div class="agent-monitor-card">
          <span>平均耗时</span>
          <strong>{{ fmtMs(monitorMetrics.avg_duration_ms) }}</strong>
          <small>P50 {{ fmtMs(monitorMetrics.p50_duration_ms) }}</small>
        </div>
        <div class="agent-monitor-card">
          <span>P99 耗时</span>
          <strong>{{ fmtMs(monitorMetrics.p99_duration_ms) }}</strong>
          <small>慢请求观察</small>
        </div>
        <div class="agent-monitor-card">
          <span>反馈数</span>
          <strong>{{ monitorMetrics.feedback_count }}</strong>
          <small>好评 {{ monitorMetrics.positive_rate }}%</small>
        </div>
        <div class="agent-monitor-card">
          <span>待确认/取消</span>
          <strong>{{ monitorMetrics.awaiting_hitl_count + monitorMetrics.cancelled_count }}</strong>
          <small>{{ monitorMetrics.awaiting_hitl_count }} 待确认 / {{ monitorMetrics.cancelled_count }} 取消</small>
        </div>
      </div>

      <div class="agent-monitor-grid">
        <div class="agent-monitor-panel">
          <div class="section-title">每日调用趋势</div>
          <div class="agent-trend-list">
            <div class="agent-trend-row" v-for="item in monitorTimeseries" :key="item.date">
              <span class="agent-trend-date">{{ item.date.slice(5) }}</span>
              <div class="agent-trend-track">
                <span class="agent-trend-bar" :style="{ width: trendWidth(item.total) }"></span>
              </div>
              <span class="agent-trend-num">{{ item.total }}</span>
              <span class="agent-trend-error" v-if="item.error">失败 {{ item.error }}</span>
            </div>
            <div class="agent-monitor-empty" v-if="monitorTimeseries.length === 0">暂无趋势数据</div>
          </div>
        </div>

        <div class="agent-monitor-panel">
          <div class="section-title">意图调用排行</div>
          <div class="agent-rank-list">
            <div class="agent-rank-row" v-for="item in monitorIntents" :key="item.intent">
              <div>
                <strong>{{ intentLabel(item.intent) }}</strong>
                <small>{{ item.intent }} · P99 {{ fmtMs(item.p99_duration_ms) }}</small>
              </div>
              <span>{{ item.count }}</span>
            </div>
            <div class="agent-monitor-empty" v-if="monitorIntents.length === 0">暂无意图数据</div>
          </div>
        </div>

        <div class="agent-monitor-panel">
          <div class="section-title">工具失败排行</div>
          <div class="agent-rank-list">
            <div class="agent-rank-row" v-for="item in monitorTools" :key="item.tool_name">
              <div>
                <strong>{{ toolLabel(item.tool_name) }}</strong>
                <small>{{ item.success }} 成功 / {{ item.error }} 失败</small>
              </div>
              <span :class="{ danger: item.failure_rate > 0 }">{{ item.failure_rate }}%</span>
            </div>
            <div class="agent-monitor-empty" v-if="monitorTools.length === 0">暂无工具调用数据</div>
          </div>
        </div>
      </div>

      <div class="section-title">最近任务</div>
      <DataTable :data="monitorTasks" />
      <ResultBadge :badge="results.monitor.badge" :text="results.monitor.text" />
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { request, qs } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import DataTable from '../components/DataTable.vue'
import CustomSelect from '../components/CustomSelect.vue'
import { validateFields } from '../utils/helpers'

const sub = ref(localStorage.getItem('sub-system') || 'sys-users')
const loading = ref(false)
const users = ref([])
const roles = ref([])
const permissions = ref([])
const monitorMetrics = reactive({
  window_days: 7,
  total_tasks: 0,
  success_rate: 0,
  success_count: 0,
  error_count: 0,
  cancelled_count: 0,
  awaiting_hitl_count: 0,
  avg_duration_ms: 0,
  p50_duration_ms: 0,
  p99_duration_ms: 0,
  feedback_count: 0,
  positive_rate: 0,
})
const monitorTimeseries = ref([])
const monitorIntents = ref([])
const monitorTools = ref([])
const monitorTasks = ref([])

const userQuery = reactive({ username: '', realName: '', status: '', skip: 0, limit: 20 })
const roleQuery = reactive({ roleName: '', status: '', skip: 0, limit: 20 })
const monitorQuery = reactive({ days: 7, status: '', intent: '' })

const userForm = reactive({ username: '', password: '', realName: '', phone: '', email: '', status: 1, mustChangePassword: 1, roleIds: [] })
const userEdit = reactive({ id: null, realName: '', phone: '', email: '', status: '', mustChangePassword: '', newPassword: '', resetMustChangePassword: 1, roleIds: [] })

const roleForm = reactive({ roleCode: '', roleName: '', status: 1, remark: '' })
const roleEdit = reactive({ id: null, roleName: '', status: '', remark: '', permissionIds: [] })

const results = reactive({
  user: { badge: null, text: '' },
  role: { badge: null, text: '' },
  monitor: { badge: null, text: '' }
})

// ── Select 选项数据 ──
const subOptions = [
  { value: 'sys-users', label: '用户管理' },
  { value: 'sys-roles', label: '角色管理' },
  { value: 'sys-agent-monitor', label: 'Agent监控' },
]

const monitorDayOptions = [
  { value: 1, label: '近 1 天' },
  { value: 7, label: '近 7 天' },
  { value: 30, label: '近 30 天' },
]

const monitorStatusOptions = [
  { value: '', label: '全部' },
  { value: 'success', label: '成功' },
  { value: 'error', label: '失败' },
  { value: 'awaiting_hitl', label: 'HITL等待' },
  { value: 'cancelled', label: '已取消' },
]

const statusFilterOptions = [
  { value: '', label: '全部' },
  { value: '1', label: '启用' },
  { value: '0', label: '禁用' },
]

const enableDisableOptions = [
  { value: 1, label: '启用' },
  { value: 0, label: '禁用' },
]

const yesNoOptions = [
  { value: 1, label: '是' },
  { value: 0, label: '否' },
]

const statusNoModifyOptions = [
  { value: '', label: '不修改' },
  { value: '1', label: '启用' },
  { value: '0', label: '禁用' },
]

const yesNoNoModifyOptions = [
  { value: '', label: '不修改' },
  { value: '1', label: '是' },
  { value: '0', label: '否' },
]

const roleOptions = computed(() => roles.value.map(item => ({ id: item.id, role_name: item.role_name })))
const monitorIntentOptions = computed(() => {
  const options = [{ value: '', label: '全部' }]
  for (const item of monitorIntents.value) {
    options.push({ value: item.intent, label: intentLabel(item.intent) })
  }
  return options
})
const maxTrendTotal = computed(() => Math.max(1, ...monitorTimeseries.value.map(item => item.total || 0)))
const permissionGroups = computed(() => {
  const map = new Map()
  for (const item of permissions.value) {
    if (!map.has(item.module)) map.set(item.module, [])
    map.get(item.module).push(item)
  }
  return Array.from(map.entries()).map(([module, items]) => ({ module, items }))
})

function saveSub() {
  localStorage.setItem('sub-system', sub.value)
  if (sub.value === 'sys-agent-monitor' && monitorTimeseries.value.length === 0) {
    loadAgentMonitor()
  }
}

function setResult(target, ok, text) {
  results[target].badge = { ok, text }
  results[target].text = ''
}

async function apiCall(target, method, path, opts = {}) {
  loading.value = true
  try {
    const r = await request(method, path, opts)
    if (!r.ok) setResult(target, false, r?.data?.msg || '操作失败')
    return r
  } catch (e) {
    setResult(target, false, `网络错误: ${e.message}`)
    return { ok: false }
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  const r = await apiCall('user', 'GET', '/system/users' + qs({
    skip: userQuery.skip || 0,
    limit: userQuery.limit || 20,
    username: userQuery.username || null,
    real_name: userQuery.realName || null,
    status: userQuery.status === '' ? null : userQuery.status
  }))
  if (r.ok) {
    users.value = r?.data?.data || []
    setResult('user', true, '用户列表加载成功')
  }
}

async function loadRoles() {
  const r = await apiCall('role', 'GET', '/system/roles' + qs({
    skip: roleQuery.skip || 0,
    limit: roleQuery.limit || 20,
    role_name: roleQuery.roleName || null,
    status: roleQuery.status === '' ? null : roleQuery.status
  }))
  if (r.ok) {
    // 去掉三个巨型权限字段，避免 DataTable 行高爆炸
    roles.value = (r?.data?.data || []).map(({ permissions, permission_ids, permission_codes, ...rest }) => rest)
    setResult('role', true, '角色列表加载成功')
  }
}

async function loadPermissions() {
  const r = await apiCall('role', 'GET', '/system/permissions')
  if (r.ok) permissions.value = r?.data?.data || []
}

async function loadAgentMonitor() {
  const days = monitorQuery.days || 7
  const [metrics, timeseries, intents, tools, tasks] = await Promise.all([
    apiCall('monitor', 'GET', '/agent/admin/metrics' + qs({ days })),
    apiCall('monitor', 'GET', '/agent/admin/metrics/timeseries' + qs({ days })),
    apiCall('monitor', 'GET', '/agent/admin/metrics/intents' + qs({ days })),
    apiCall('monitor', 'GET', '/agent/admin/metrics/tools' + qs({ days })),
    apiCall('monitor', 'GET', '/agent/admin/tasks' + qs({
      days,
      status: monitorQuery.status || null,
      intent: monitorQuery.intent || null,
      limit: 50,
    })),
  ])

  if (metrics.ok) Object.assign(monitorMetrics, metrics?.data?.data || {})
  if (timeseries.ok) monitorTimeseries.value = timeseries?.data?.data || []
  if (intents.ok) monitorIntents.value = intents?.data?.data || []
  if (tools.ok) monitorTools.value = tools?.data?.data || []
  if (tasks.ok) {
    monitorTasks.value = (tasks?.data?.data || []).map(item => ({
      id: item.id,
      时间: fmtDateTime(item.create_time),
      用户: item.user_id,
      角色: personaLabel(item.persona),
      意图: intentLabel(item.intent),
      状态: statusLabel(item.status),
      耗时: fmtMs(item.total_duration_ms),
      工具: item.tool_summary || '-',
      反馈: item.feedback_rating ? `${item.feedback_rating}分${item.feedback_comment ? '：' + item.feedback_comment : ''}` : '-',
      问题: item.original_message,
    }))
  }
  if (metrics.ok && timeseries.ok && intents.ok && tools.ok && tasks.ok) {
    setResult('monitor', true, 'Agent 监控数据加载成功')
  }
}

function fmtMs(value) {
  const ms = Number(value || 0)
  if (ms >= 1000) return (ms / 1000).toFixed(2) + 's'
  return ms + 'ms'
}

function fmtDateTime(value) {
  if (!value) return ''
  const d = new Date(value)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function trendWidth(total) {
  return `${Math.max(4, Math.round(((total || 0) / maxTrendTotal.value) * 100))}%`
}

function intentLabel(value) {
  const map = {
    score_query: '成绩查询',
    academic_analysis: '学业分析',
    knowledge_qa: '知识问答',
    data_query: '数据统计',
    weather_query: '天气查询',
    email_draft: '邮件撰写',
    emotional_support: '情绪陪伴',
    daily_chat: '日常闲聊',
  }
  return map[value] || value || '未知'
}

function toolLabel(value) {
  const map = {
    score_tool: '成绩工具',
    rag_tool: '知识检索',
    nl2sql_tool: '智能问数',
    student_tool: '学生识别',
    weather_tool: '天气工具',
    email_tool: '邮件工具',
  }
  return map[value] || value || '未知工具'
}

function personaLabel(value) {
  const map = {
    academic_mentor: '学业导师',
  }
  return map[value] || value || '未知'
}

function statusLabel(value) {
  const map = {
    pending: '待执行',
    running: '执行中',
    awaiting_hitl: '等待确认',
    success: '成功',
    error: '失败',
    cancelled: '已取消',
  }
  return map[value] || value || '未知'
}

async function createUser() {
  if (!validateFields([['#sys-users', '账号', userForm.username], ['#sys-users', '初始密码', userForm.password], ['#sys-users', '姓名', userForm.realName]])) return
  const r = await apiCall('user', 'POST', '/system/users', {
    body: {
      username: userForm.username,
      password: userForm.password,
      real_name: userForm.realName,
      phone: userForm.phone || null,
      email: userForm.email || null,
      status: userForm.status,
      must_change_password: userForm.mustChangePassword,
      role_ids: userForm.roleIds
    }
  })
  if (r.ok) {
    setResult('user', true, '用户创建成功')
    await loadUsers()
  }
}

async function updateUser() {
  if (!validateFields([['#sys-users', '用户ID', userEdit.id]])) return
  const body = {}
  if (userEdit.realName) body.real_name = userEdit.realName
  if (userEdit.phone) body.phone = userEdit.phone
  if (userEdit.email) body.email = userEdit.email
  if (userEdit.status !== '') body.status = Number(userEdit.status)
  if (userEdit.mustChangePassword !== '') body.must_change_password = Number(userEdit.mustChangePassword)
  const r = await apiCall('user', 'PATCH', '/system/users/' + userEdit.id, { body })
  if (r.ok) {
    setResult('user', true, '用户更新成功')
    await loadUsers()
  }
}

async function resetUserPassword() {
  if (!validateFields([['#sys-users', '用户ID', userEdit.id], ['#sys-users', '重置密码', userEdit.newPassword]])) return
  const r = await apiCall('user', 'POST', `/system/users/${userEdit.id}/reset-password`, {
    body: {
      new_password: userEdit.newPassword,
      must_change_password: userEdit.resetMustChangePassword
    }
  })
  if (r.ok) setResult('user', true, '密码重置成功')
}

async function assignUserRoles() {
  if (!validateFields([['#sys-users', '用户ID', userEdit.id]])) return
  const r = await apiCall('user', 'POST', `/system/users/${userEdit.id}/assign-roles`, {
    body: { role_ids: userEdit.roleIds }
  })
  if (r.ok) {
    setResult('user', true, '用户角色分配成功')
    await loadUsers()
  }
}

async function createRole() {
  if (!validateFields([['#sys-roles', '角色编码', roleForm.roleCode], ['#sys-roles', '角色名称', roleForm.roleName]])) return
  const r = await apiCall('role', 'POST', '/system/roles', {
    body: {
      role_code: roleForm.roleCode,
      role_name: roleForm.roleName,
      status: roleForm.status,
      remark: roleForm.remark || null
    }
  })
  if (r.ok) {
    setResult('role', true, '角色创建成功')
    await loadRoles()
  }
}

async function updateRole() {
  if (!validateFields([['#sys-roles', '角色ID', roleEdit.id]])) return
  const body = {}
  if (roleEdit.roleName) body.role_name = roleEdit.roleName
  if (roleEdit.status !== '') body.status = Number(roleEdit.status)
  if (roleEdit.remark) body.remark = roleEdit.remark
  const r = await apiCall('role', 'PATCH', '/system/roles/' + roleEdit.id, { body })
  if (r.ok) {
    setResult('role', true, '角色更新成功')
    await loadRoles()
  }
}

async function assignRolePermissions() {
  if (!validateFields([['#sys-roles', '角色ID', roleEdit.id]])) return
  const r = await apiCall('role', 'POST', `/system/roles/${roleEdit.id}/assign-permissions`, {
    body: { permission_ids: roleEdit.permissionIds }
  })
  if (r.ok) {
    setResult('role', true, '角色权限分配成功')
    await loadRoles()
  }
}

async function loadRoleDetail() {
  if (!validateFields([['#sys-roles', '角色ID', roleEdit.id]])) return
  const r = await apiCall('role', 'GET', `/system/roles?skip=0&limit=100`)
  if (r.ok) {
    const list = r?.data?.data || []
    const found = list.find(item => item.id === roleEdit.id)
    if (found) {
      roleEdit.roleName = found.role_name || ''
      roleEdit.status = found.status ?? ''
      roleEdit.permissionIds = found.permission_ids || []
      setResult('role', true, `已加载角色: ${found.role_name} (${roleEdit.permissionIds.length} 项权限)`)
    } else {
      setResult('role', false, '未找到该角色')
    }
  }
}

function enabledCount(group) {
  return group.items.filter(p => roleEdit.permissionIds.includes(p.id)).length
}

onMounted(async () => {
  await Promise.all([loadUsers(), loadRoles(), loadPermissions()])
  if (sub.value === 'sys-agent-monitor') await loadAgentMonitor()
})
</script>

<style scoped>
/* ── 权限分配面板 ── */
.sys-perm-panel {
  margin-top: 32px; padding: 20px 24px 24px;
  border: 1px solid var(--line-strong); border-radius: var(--radius);
  background: var(--panel-2);
}
.sys-perm-head-row {
  display: flex; align-items: flex-end; gap: 12px; flex-wrap: wrap; margin-bottom: 20px;
}

/* ── 权限双列网格 ── */
.sys-perm-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.sys-perm-module {
  background: var(--panel-solid); border: 1px solid var(--line);
  border-radius: var(--radius-sm); overflow: hidden;
}
.sys-perm-module-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 14px; background: rgba(209,161,90,0.08);
  border-bottom: 1px solid var(--line);
}
.sys-perm-module-name {
  font-weight: 700; font-size: 13px; color: var(--gold); text-transform: uppercase; letter-spacing: 0.5px;
}
.sys-perm-module-count {
  font-size: 11px; color: var(--text-muted); font-family: var(--font-mono);
}

.sys-perm-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 14px; border-bottom: 1px solid var(--line);
}
.sys-perm-item:last-child { border-bottom: none; }
.sys-perm-item-info {
  display: flex; flex-direction: column; gap: 1px; min-width: 0;
}
.sys-perm-item-name {
  font-size: 13px; color: var(--text-soft); font-weight: 500;
}
.sys-perm-item-code {
  font-size: 10px; color: var(--text-muted); font-family: var(--font-mono);
}

/* ── 胶囊开关 ── */
.sys-toggle {
  display: flex; align-items: center; gap: 8px; cursor: pointer; flex-shrink: 0; user-select: none;
}
.sys-toggle input { display: none; }
.sys-toggle-track {
  width: 44px; height: 24px; border-radius: 12px;
  background: rgba(255,255,255,0.15); transition: background var(--dur-fast);
  position: relative; flex-shrink: 0;
}
.sys-toggle--on .sys-toggle-track { background: var(--gold); }
.sys-toggle-knob {
  position: absolute; top: 3px; left: 3px;
  width: 18px; height: 18px; border-radius: 50%;
  background: #fff; transition: transform var(--dur-fast);
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}
.sys-toggle--on .sys-toggle-knob { transform: translateX(20px); }
.sys-toggle-label {
  font-size: 11px; font-weight: 600; width: 22px; text-align: center;
  color: var(--text-muted); transition: color var(--dur-fast);
}
.sys-toggle--on .sys-toggle-label { color: var(--gold); }

/* ── 紧凑网格 ── */
.grid-4 { grid-template-columns: repeat(4, 1fr); }

/* ── 用户管理 grid 也收紧 ── */
#sys-users .grid { grid-template-columns: repeat(4, 1fr); }
#sys-users .field-span-2 { grid-column: span 2; }

/* ── Agent 监控工作台 ── */
.agent-monitor-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 18px;
}
.agent-monitor-head h3 { margin: 0 0 4px; }
.agent-monitor-sub {
  margin: 0;
  color: var(--text-dim);
  font-size: 13px;
}
.agent-monitor-filters {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}
.agent-monitor-filters .field { width: 132px; }
.agent-monitor-filters .btn { height: 36px; }

.agent-monitor-cards {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}
.agent-monitor-card {
  min-height: 84px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel-2);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.agent-monitor-card span {
  color: var(--text-dim);
  font-size: 12px;
}
.agent-monitor-card strong {
  color: var(--text);
  font-family: var(--font-display);
  font-size: 24px;
  line-height: 1.1;
}
.agent-monitor-card small {
  color: var(--text-muted);
  font-size: 11px;
}

.agent-monitor-grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr 1fr;
  gap: 14px;
  margin: 16px 0 20px;
}
.agent-monitor-panel {
  min-height: 220px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel-2);
}
.agent-monitor-panel .section-title { margin-top: 0; }
.agent-monitor-empty {
  padding: 24px 0;
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
}

.agent-trend-list,
.agent-rank-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.agent-trend-row {
  display: grid;
  grid-template-columns: 44px 1fr 34px auto;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.agent-trend-date {
  color: var(--text-dim);
  font-family: var(--font-mono);
}
.agent-trend-track {
  height: 9px;
  border-radius: 999px;
  background: var(--panel-solid);
  overflow: hidden;
}
.agent-trend-bar {
  display: block;
  height: 100%;
  min-width: 4px;
  border-radius: inherit;
  background: var(--gold);
}
.agent-trend-num {
  color: var(--text-soft);
  text-align: right;
  font-family: var(--font-mono);
}
.agent-trend-error {
  color: var(--danger);
  font-size: 11px;
}

.agent-rank-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--line);
}
.agent-rank-row:last-child { border-bottom: none; }
.agent-rank-row strong {
  display: block;
  color: var(--text-soft);
  font-size: 13px;
}
.agent-rank-row small {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 11px;
}
.agent-rank-row > span {
  color: var(--gold);
  font-family: var(--font-mono);
  font-weight: 700;
  white-space: nowrap;
}
.agent-rank-row > span.danger { color: var(--danger); }

@media (max-width: 1200px) {
  .agent-monitor-cards { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .agent-monitor-grid { grid-template-columns: 1fr; }
}

@media (max-width: 760px) {
  .agent-monitor-head { flex-direction: column; }
  .agent-monitor-filters { width: 100%; }
  .agent-monitor-filters .field { width: calc(50% - 5px); }
  .agent-monitor-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
