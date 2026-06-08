<template>
  <section id="page-system" class="page active">
    <div class="sub-bar">
      <label>系统管理</label>
      <select v-model="sub" @change="saveSub">
        <option value="sys-users">用户管理</option>
        <option value="sys-roles">角色管理</option>
      </select>
    </div>

    <div id="sys-users" class="card subcard" :class="{ show: sub === 'sys-users' }">
      <h3>用户管理</h3>

      <div class="section-title">查询用户</div>
      <div class="grid">
        <div class="field"><label>账号</label><input v-model="userQuery.username" /></div>
        <div class="field"><label>姓名</label><input v-model="userQuery.realName" /></div>
        <div class="field"><label>状态</label><select v-model="userQuery.status"><option value="">全部</option><option value="1">启用</option><option value="0">禁用</option></select></div>
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
        <div class="field"><label>状态</label><select v-model.number="userForm.status"><option :value="1">启用</option><option :value="0">禁用</option></select></div>
        <div class="field"><label>首次登录强制改密</label><select v-model.number="userForm.mustChangePassword"><option :value="1">是</option><option :value="0">否</option></select></div>
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
        <div class="field"><label>状态</label><select v-model="userEdit.status"><option value="">不修改</option><option value="1">启用</option><option value="0">禁用</option></select></div>
        <div class="field"><label>首次登录强制改密</label><select v-model="userEdit.mustChangePassword"><option value="">不修改</option><option value="1">是</option><option value="0">否</option></select></div>
        <div class="field"><label>重置密码</label><input v-model="userEdit.newPassword" type="password" placeholder="留空则不重置" /></div>
        <div class="field"><label>重置后强制改密</label><select v-model.number="userEdit.resetMustChangePassword"><option :value="1">是</option><option :value="0">否</option></select></div>
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

      <div class="section-title">查询角色</div>
      <div class="grid">
        <div class="field"><label>角色名</label><input v-model="roleQuery.roleName" /></div>
        <div class="field"><label>状态</label><select v-model="roleQuery.status"><option value="">全部</option><option value="1">启用</option><option value="0">禁用</option></select></div>
        <div class="field"><label>偏移量</label><input v-model.number="roleQuery.skip" type="number" /></div>
        <div class="field"><label>每页条数</label><input v-model.number="roleQuery.limit" type="number" /></div>
      </div>
      <div class="actions">
        <button class="btn secondary" :disabled="loading" @click="loadRoles">查询角色</button>
      </div>
      <DataTable :data="roles" />

      <div class="section-title">新增角色</div>
      <div class="grid">
        <div class="field"><label>角色编码 *</label><input v-model="roleForm.roleCode" placeholder="例如 counsellor" /></div>
        <div class="field"><label>角色名称 *</label><input v-model="roleForm.roleName" /></div>
        <div class="field"><label>状态</label><select v-model.number="roleForm.status"><option :value="1">启用</option><option :value="0">禁用</option></select></div>
        <div class="field field-span-2"><label>备注</label><input v-model="roleForm.remark" /></div>
      </div>
      <div class="actions">
        <button class="btn" :disabled="loading" @click="createRole">新增角色</button>
      </div>

      <div class="section-title">编辑角色 / 分配权限</div>
      <div class="grid">
        <div class="field"><label>角色ID *</label><input v-model.number="roleEdit.id" type="number" /></div>
        <div class="field"><label>角色名称</label><input v-model="roleEdit.roleName" /></div>
        <div class="field"><label>状态</label><select v-model="roleEdit.status"><option value="">不修改</option><option value="1">启用</option><option value="0">禁用</option></select></div>
        <div class="field field-span-2"><label>备注</label><input v-model="roleEdit.remark" /></div>
        <div class="field field-span-2"><label>权限分配</label><div class="perm-groups"><div v-for="group in permissionGroups" :key="group.module" class="perm-group"><div class="perm-group-title">{{ group.module }}</div><div class="check-grid"><label v-for="perm in group.items" :key="perm.id" class="check-item"><input v-model="roleEdit.permissionIds" type="checkbox" :value="perm.id" />{{ perm.permission_name }}</label></div></div></div></div>
      </div>
      <div class="actions">
        <button class="btn secondary" :disabled="loading" @click="updateRole">更新角色</button>
        <button class="btn secondary" :disabled="loading" @click="assignRolePermissions">分配权限</button>
      </div>
      <ResultBadge :badge="results.role.badge" :text="results.role.text" />
    </div>
  </section>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { request, qs } from '../api'
import ResultBadge from '../components/ResultBadge.vue'
import DataTable from '../components/DataTable.vue'
import { validateFields } from '../utils/helpers'

const sub = ref(localStorage.getItem('sub-system') || 'sys-users')
const loading = ref(false)
const users = ref([])
const roles = ref([])
const permissions = ref([])

const userQuery = reactive({ username: '', realName: '', status: '', skip: 0, limit: 20 })
const roleQuery = reactive({ roleName: '', status: '', skip: 0, limit: 20 })

const userForm = reactive({ username: '', password: '', realName: '', phone: '', email: '', status: 1, mustChangePassword: 1, roleIds: [] })
const userEdit = reactive({ id: null, realName: '', phone: '', email: '', status: '', mustChangePassword: '', newPassword: '', resetMustChangePassword: 1, roleIds: [] })

const roleForm = reactive({ roleCode: '', roleName: '', status: 1, remark: '' })
const roleEdit = reactive({ id: null, roleName: '', status: '', remark: '', permissionIds: [] })

const results = reactive({
  user: { badge: null, text: '' },
  role: { badge: null, text: '' }
})

const roleOptions = computed(() => roles.value.map(item => ({ id: item.id, role_name: item.role_name })))
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
    roles.value = r?.data?.data || []
    setResult('role', true, '角色列表加载成功')
  }
}

async function loadPermissions() {
  const r = await apiCall('role', 'GET', '/system/permissions')
  if (r.ok) permissions.value = r?.data?.data || []
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

onMounted(async () => {
  await Promise.all([loadUsers(), loadRoles(), loadPermissions()])
})
</script>
