/* =========================================================================
 * 沃林学生信息管理系统 —— 前端交互脚本
 * 说明：本文件是从 index.html 拆分出来的纯原生 JS，负责所有接口请求与页面交互。
 * ========================================================================= */

/* ===================== 通用工具函数 ===================== */
// 取接口基地址（去掉结尾多余的斜杠）
function base() { return document.getElementById('baseUrl').value.replace(/\/+$/, ''); }

// 取输入框的值（trim 后），空字符串返回 null
function val(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  const v = (el.value ?? '').toString().trim();
  return v === '' ? null : v;
}
// 取数字，空则 null
function numVal(id) { const v = val(id); return v === null ? null : Number(v); }

// 把对象里值为 null/undefined 的键删掉（用于 PATCH/可选参数）
function clean(obj) {
  const out = {};
  for (const k in obj) if (obj[k] !== null && obj[k] !== undefined && obj[k] !== '') out[k] = obj[k];
  return out;
}

// 把对象转成 query string（自动跳过 null）
function qs(params) {
  const sp = new URLSearchParams();
  for (const k in params) {
    const v = params[k];
    if (v !== null && v !== undefined && v !== '') sp.append(k, v);
  }
  const s = sp.toString();
  return s ? ('?' + s) : '';
}

/* ===================== 表单必填校验（功能 4） ===================== */
// 通用必填校验：fields 形如 [['st_no','学号'], ['st_class','班级ID']]
// 空值的输入框会被加上红框(.invalid)，并弹出一次性提示，全部通过才返回 true
function validate(fields) {
  const missing = [];
  fields.forEach(([id, label]) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (val(id) === null) { el.classList.add('invalid'); missing.push(label); }
    else el.classList.remove('invalid');
  });
  if (missing.length) alert('请填写：' + missing.join('、'));
  return missing.length === 0;
}

// 用户重新输入时，自动清除该控件的红框；富文本正文(mail_body)清除其外层 .rte 红框
document.addEventListener('input', e => {
  const t = e.target;
  if (t.classList && t.classList.contains('invalid')) t.classList.remove('invalid');
  if (t.id === 'mail_body') { const rte = t.closest('.rte'); if (rte) rte.classList.remove('invalid'); }
});

/* ===================== 按钮加载/禁用态（功能 3） ===================== */
// 记录"最近被点击的按钮"，供 request() 自动加上"处理中..."禁用态。
// 用捕获阶段(true)监听，保证在各 onclick 业务函数执行之前就先记录到按钮。
let _lastBtn = null;
document.addEventListener('click', e => {
  const b = e.target.closest('.btn');
  if (b) _lastBtn = b;
}, true);

// 友好展示：徽章 + 可选正文（不 dump 整段 JSON）
function showPlainResult(targetId, ok, badgeText, bodyText) {
  const box = document.getElementById(targetId);
  if (!box) return;
  box.innerHTML = '<span class="badge ' + (ok ? 'ok' : 'err') + '">' + (ok ? '✓ ' : '✗ ') + badgeText + '</span>\n';
  if (bodyText) box.append(document.createTextNode(bodyText));
}

// 从接口统一响应 { code, msg, data } 中取出业务数据
function pickApiContent(apiBody) {
  if (!apiBody || typeof apiBody !== 'object') return '';
  const inner = apiBody.data;
  if (typeof inner === 'string') return inner;
  if (typeof inner === 'number') return String(inner);
  if (inner && typeof inner === 'object') {
    if (inner.reply != null) return String(inner.reply);
    if (inner.message) return String(inner.message);
    if (inner.error) return String(inner.error);
  }
  return '';
}

// 按展示模式写入结果区
// display: msg=只显示提示语 | content=显示 data 正文(大模型/数字等) | json=原始 JSON(调试用) | silent=不写
function paintResultBox(box, resp, parsed, display) {
  const badge = resp.ok
    ? '<span class="badge ok">✓ ' + resp.status + '</span>\n'
    : '<span class="badge err">✗ ' + resp.status + '</span>\n';
  box.innerHTML = badge;
  const api = typeof parsed === 'object' && parsed !== null ? parsed : {};

  if (display === 'msg') {
    box.append(document.createTextNode(api.msg || (resp.ok ? '操作成功' : '操作失败')));
    return;
  }
  if (display === 'content') {
    const text = pickApiContent(api) || api.msg || (resp.ok ? '' : '操作失败');
    if (text) box.append(document.createTextNode(text));
    return;
  }
  // json：完整响应，仅调试时显式指定
  box.append(document.createTextNode(
    typeof parsed === 'string' ? parsed : JSON.stringify(parsed, null, 2)
  ));
}

// 统一的请求方法：自动处理 JSON、错误、状态徽章，并在请求期间禁用触发按钮
// 默认 display='msg'，只展示友好提示，不暴露整段 JSON
async function request(targetId, method, path, { body, silent, display = 'msg' } = {}) {
  const box = document.getElementById(targetId);
  // 取出本次点击的按钮；已被其它逻辑禁用的按钮（如邮件自管理按钮）跳过，避免冲突
  const btn = (_lastBtn && !_lastBtn.disabled) ? _lastBtn : null;
  _lastBtn = null;
  let oldText;
  if (btn) { oldText = btn.textContent; btn.disabled = true; btn.textContent = '处理中...'; }

  if (!silent && box) box.textContent = '请求中...';
  try {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const resp = await fetch(base() + path, opts);
    const text = await resp.text();
    let data;
    try { data = JSON.parse(text); } catch { data = text; }
    if (!silent && box) paintResultBox(box, resp, data, display);
    return { ok: resp.ok, data };
  } catch (e) {
    if (!silent && box) {
      box.innerHTML = '<span class="badge err">✗ 网络错误</span>\n';
      box.append(document.createTextNode(
        e.message + '\n\n提示：请确认后端已启动，且已开启 CORS 跨域允许。'
      ));
    }
    return { ok: false, error: e };
  } finally {
    // 无论成功失败，都恢复按钮可点击状态
    if (btn) { btn.disabled = false; btn.textContent = oldText; }
  }
}

// 把数组数据渲染成表格（自动取并集列）
function renderTable(targetId, rows) {
  const wrap = document.getElementById(targetId);
  if (!wrap) return;
  if (!Array.isArray(rows) || rows.length === 0 || typeof rows[0] !== 'object') {
    wrap.innerHTML = '';
    return;
  }
  const cols = [...new Set(rows.flatMap(r => Object.keys(r)))];
  let html = '<div class="table-wrap"><table><thead><tr>';
  cols.forEach(c => html += '<th>' + c + '</th>');
  html += '</tr></thead><tbody>';
  rows.forEach(r => {
    html += '<tr>';
    cols.forEach(c => {
      let v = r[c];
      if (v === null || v === undefined) v = '';
      else if (typeof v === 'object') v = JSON.stringify(v);
      html += '<td>' + String(v).replace(/</g, '&lt;') + '</td>';
    });
    html += '</tr>';
  });
  html += '</tbody></table></div>';
  wrap.innerHTML = html;
}

// 从各种返回结构里尽量提取出"列表"用于渲染表格
function pickList(data) {
  if (Array.isArray(data)) return data;
  if (data && typeof data === 'object') {
    for (const key of ['data', 'items', 'list', 'records', 'result', 'rows']) {
      if (Array.isArray(data[key])) return data[key];
      if (data[key] && Array.isArray(data[key].items)) return data[key].items;
    }
  }
  return null;
}

// 后端统一响应是 {code, msg, data, total}，单条查询时把内层 data 取出来渲染成一行表格
function pickOne(resp) {
  const inner = (resp && typeof resp === 'object' && 'data' in resp) ? resp.data : resp;
  if (Array.isArray(inner)) return inner;
  if (inner && typeof inner === 'object') return [inner];
  return null;
}

/* ===================== 左侧大模块导航切换 + 记忆（功能 2） ===================== */
const titles = {
  student: '学生信息管理', score: '考核成绩管理', employment: '就业信息管理',
  class: '班级管理', teacher: '教师管理', statistics: '统计分析',
  work: 'AI 作业模块', email: '邮件管理'
};

// 切换到指定大模块（更新导航高亮、页面显示、顶栏标题）
function activatePage(page) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.page === page));
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const pg = document.getElementById('page-' + page);
  if (pg) pg.classList.add('active');
  document.getElementById('pageTitle').textContent = titles[page] || '';
}

document.getElementById('nav').addEventListener('click', e => {
  const item = e.target.closest('.nav-item');
  if (!item) return;
  const page = item.dataset.page;
  localStorage.setItem('active-page', page); // 记住当前所在模块
  activatePage(page);
});

// 页面加载时恢复上次所在模块（无记录则默认学生模块）
const savedPage = localStorage.getItem('active-page');
activatePage(savedPage && titles[savedPage] ? savedPage : 'student');

/* ===================== 模块内功能下拉切换 + 记忆（功能 2） ===================== */
// 每个模块顶部有一个下拉框，选中后只显示对应的功能卡片，其余隐藏，保持界面整洁
function applySubSelect(sel) {
  const mod = sel.dataset.module;
  // 先隐藏该模块下所有子卡片
  document.querySelectorAll('#page-' + mod + ' .subcard').forEach(c => c.classList.remove('show'));
  // 再显示当前选中的子卡片
  const target = document.getElementById('sub-' + sel.value);
  if (target) target.classList.add('show');
}
document.querySelectorAll('.sub-select').forEach(sel => {
  const key = 'sub-' + sel.dataset.module;
  // 恢复上次选中的功能（校验仍存在于选项中才使用，避免选项变更后失效）
  const saved = localStorage.getItem(key);
  if (saved && [...sel.options].some(o => o.value === saved)) sel.value = saved;
  // 切换时记住选择并刷新显示
  sel.addEventListener('change', () => { localStorage.setItem(key, sel.value); applySubSelect(sel); });
  applySubSelect(sel); // 初始化：显示当前（恢复后的）功能
});

/* ===================== 学生信息管理 ===================== */
function createStudent() {
  if (!validate([['st_no', '学号'], ['st_class', '班级ID'], ['st_name', '姓名']])) return;
  const body = clean({
    student_no: val('st_no'),
    class_id: numVal('st_class'),
    student_name: val('st_name'),
    gender: val('st_gender'),
    age: numVal('st_age'),
    native_place: val('st_native'),
    graduate_school: val('st_school'),
    major: val('st_major'),
    education: val('st_edu'),
    admission_time: val('st_admit'),
    graduate_time: val('st_grad'),
    advisor_id: numVal('st_advisor')
  });
  request('r_st_create', 'POST', '/student/students', { body });
}
async function getAllStudents() {
  const r = await request('r_st_query', 'GET', '/student/students' + qs({ skip: val('st_skip'), limit: val('st_limit') }));
  renderTable('r_st_query_table', pickList(r.data));
}
async function getStudentById() {
  if (!validate([['st_id', '学生ID']])) return;
  const r = await request('r_st_query', 'GET', '/student/students/' + val('st_id'));
  renderTable('r_st_query_table', pickOne(r.data));
}
async function getStudentByNo() {
  if (!validate([['st_no_q', '学号']])) return;
  const r = await request('r_st_query', 'GET', '/student/students/no/' + encodeURIComponent(val('st_no_q')));
  renderTable('r_st_query_table', pickOne(r.data));
}
async function getStudentByClass() {
  if (!validate([['st_class_q', '班级ID']])) return;
  const r = await request('r_st_query', 'GET', '/student/students/class/' + val('st_class_q') + qs({ skip: val('st_skip'), limit: val('st_limit') }));
  renderTable('r_st_query_table', pickList(r.data));
}
function updateStudent() {
  if (!validate([['st_op_id', '学生ID']])) return;
  const body = clean({
    class_id: numVal('st_up_class'),
    student_name: val('st_up_name'),
    gender: val('st_up_gender'),
    age: numVal('st_up_age'),
    major: val('st_up_major')
  });
  request('r_st_op', 'PATCH', '/student/students/' + val('st_op_id'), { body });
}
function deleteStudent() {
  if (!validate([['st_op_id', '学生ID']])) return;
  if (!confirm('确认逻辑删除该学生？')) return;
  request('r_st_op', 'DELETE', '/student/students/' + val('st_op_id'));
}
function restoreStudent() {
  if (!validate([['st_op_id', '学生ID']])) return;
  request('r_st_op', 'POST', '/student/students/' + val('st_op_id') + '/restore');
}

/* ===================== 成绩管理 ===================== */
function addScore() {
  if (!validate([['sc_no', '学号'], ['sc_order', '考试次序'], ['sc_score', '成绩']])) return;
  const body = {
    student_no: val('sc_no'),
    exam_order: numVal('sc_order'),
    score: numVal('sc_score')
  };
  request('r_sc_add', 'POST', '/score/add', { body });
}
function batchAddScore() {
  let arr;
  try { arr = JSON.parse(val('sc_batch')); }
  catch (e) { return alert('JSON 格式有误：' + e.message); }
  request('r_sc_batch', 'POST', '/score/batch_add', { body: arr });
}
function updateScore() {
  if (!validate([['sc_up_no', '学号'], ['sc_up_order', '考试次序'], ['sc_up_score', '新成绩']])) return;
  const body = {
    student_no: val('sc_up_no'),
    exam_order: numVal('sc_up_order'),
    score: numVal('sc_up_score')
  };
  request('r_sc_op', 'PUT', '/score/update', { body });
}
function deleteScore() {
  if (!validate([['sc_up_no', '学号'], ['sc_up_order', '考试次序']])) return;
  if (!confirm('确认删除该成绩？')) return;
  request('r_sc_op', 'POST', '/score/is_delete' + qs({ student_no: val('sc_up_no'), exam_order: val('sc_up_order') }));
}
async function queryScore() {
  const r = await request('r_sc_query', 'GET', '/score/query' + qs({
    page: val('sc_page'), page_size: val('sc_psize'),
    student_no: val('sc_q_no'), exam_order: val('sc_q_order'),
    class_id: val('sc_q_class'), min_score: val('sc_q_min'), max_score: val('sc_q_max'),
    sort_no: val('sc_q_sortno'), sort_score: val('sc_q_sortsc')
  }));
  renderTable('r_sc_query_table', pickList(r.data));
}

/* ===================== 就业管理 ===================== */
function createEmployment() {
  if (!validate([['em_no', '学号'], ['em_name', '姓名'], ['em_class', '班级ID']])) return;
  const body = clean({
    student_no: val('em_no'),
    student_name: val('em_name'),
    class_id: numVal('em_class'),
    job_open_time: val('em_open'),
    offer_send_time: val('em_offer'),
    company_name: val('em_company'),
    salary: numVal('em_salary')
  });
  request('r_em_create', 'POST', '/Employment/employment_create', { body });
}
async function listEmployment() {
  const r = await request('r_em_query', 'GET', '/Employment/employment_list' + qs({
    page: val('em_page'), size: val('em_size'),
    student_name: val('em_q_name'), class_id: val('em_q_class'), company_name: val('em_q_company')
  }));
  renderTable('r_em_query_table', pickList(r.data));
}
async function getEmployment() {
  if (!validate([['em_id', '就业记录ID']])) return;
  const r = await request('r_em_query', 'GET', '/Employment/employment_get/' + val('em_id'));
  renderTable('r_em_query_table', pickOne(r.data));
}
function updateEmployment() {
  if (!validate([['em_op_id', '就业记录ID']])) return;
  const body = clean({
    company_name: val('em_up_company'),
    salary: numVal('em_up_salary'),
    offer_send_time: val('em_up_offer')
  });
  request('r_em_op', 'PUT', '/Employment/employment_update/' + val('em_op_id'), { body });
}
function deleteEmployment() {
  if (!validate([['em_op_id', '就业记录ID']])) return;
  if (!confirm('确认逻辑删除？')) return;
  request('r_em_op', 'DELETE', '/Employment/employment_delete/' + val('em_op_id'));
}
function recoverEmployment() {
  if (!validate([['em_op_id', '就业记录ID']])) return;
  request('r_em_op', 'PUT', '/Employment/employment_recover/' + val('em_op_id'));
}
function hardDeleteEmployment() {
  if (!validate([['em_op_id', '就业记录ID']])) return;
  if (!confirm('物理删除不可恢复，确认？')) return;
  request('r_em_op', 'DELETE', '/Employment/employment_hard/' + val('em_op_id'));
}

/* ===================== 班级管理 ===================== */
function saveClass() {
  if (!validate([['cl_code', '班级编号'], ['cl_name', '班级名称'], ['cl_start', '开班时间']])) return;
  const body = {
    class_code: val('cl_code'),
    class_name: val('cl_name'),
    // datetime-local 没有秒，补成后端要的 ISO 格式
    start_time: val('cl_start') ? val('cl_start') + ':00' : null
  };
  const id = val('cl_id');
  request('r_cl_save', 'POST', '/class/create_or_update_class' + qs({ id }), { body });
}
async function getClasses() {
  const r = await request('r_cl_query', 'GET', '/class/get_class' + qs({ page: val('cl_page'), limit: val('cl_limit') }));
  renderTable('r_cl_query_table', pickList(r.data));
}
async function getClassById() {
  if (!validate([['cl_q_id', '班级ID']])) return;
  const r = await request('r_cl_query', 'GET', '/class/get_class/' + val('cl_q_id'));
  renderTable('r_cl_query_table', pickOne(r.data));
}
function delClass() {
  if (!validate([['cl_q_id', '班级ID']])) return;
  if (!confirm('确认删除该班级？')) return;
  request('r_cl_query', 'DELETE', '/class/del_class' + qs({ id: val('cl_q_id') }));
}

/* ===================== 教师管理 ===================== */
// 单个新增教师：一张表单填一位老师，提交即可
function createTeacher() {
  if (!validate([
    ['te_c_name', '姓名'], ['te_c_gender', '性别'], ['te_c_phone', '联系电话'],
    ['te_c_title', '职务'], ['te_c_class', '所带班级ID'], ['te_c_hire', '入职日期']
  ])) return;
  const body = clean({
    name: val('te_c_name'),
    gender: val('te_c_gender'),
    phone: val('te_c_phone'),
    title: val('te_c_title'),
    class_id: numVal('te_c_class'),
    hire_date: val('te_c_hire'),
    birth_date: val('te_c_birth'),
    email: val('te_c_email')
  });
  request('r_te_create', 'POST', '/teacher', { body });
}

// 下载教师批量导入模板（后端返回 xlsx 二进制，这里用 blob 触发浏览器下载）
async function downloadTeacherTemplate() {
  try {
    const resp = await fetch(base() + '/teachers/import/template');
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'teacher_import_template.xlsx';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (e) {
    alert('下载模板失败：' + e.message + '\n请确认后端已启动。');
  }
}

// 批量导入教师：上传选中的 Excel/CSV 文件，展示成功/失败汇总与失败明细
async function importTeachers() {
  const fileEl = document.getElementById('te_import_file');
  if (!fileEl.files || !fileEl.files.length) {
    fileEl.classList.add('invalid');
    return alert('请先选择要导入的 Excel/CSV 文件');
  }
  fileEl.classList.remove('invalid');

  const box = document.getElementById('r_te_import');
  document.getElementById('r_te_import_summary').innerHTML = '';
  box.textContent = '导入中...';

  // 文件上传用 multipart/form-data，不能走通用的 JSON request()，这里单独发请求
  const fd = new FormData();
  fd.append('file', fileEl.files[0]);
  try {
    const resp = await fetch(base() + '/teachers/import', { method: 'POST', body: fd });
    const data = await resp.json();
    const badge = resp.ok
      ? '<span class="badge ok">✓ ' + resp.status + '</span>\n'
      : '<span class="badge err">✗ ' + resp.status + '</span>\n';
    box.innerHTML = badge;
    if (resp.ok && data && data.data) {
      renderImportSummary(data.data);
      box.append(document.createTextNode(data.msg || '导入完成'));
    } else {
      box.append(document.createTextNode(data.msg || '导入失败，请检查文件格式或表头'));
    }
  } catch (e) {
    box.innerHTML = '<span class="badge err">✗ 网络错误</span>\n';
    box.append(document.createTextNode(e.message + '\n\n提示：请确认后端已启动，且已开启 CORS 跨域允许。'));
  }
}

// 把导入结果渲染成直观的汇总信息 + 失败明细表格
function renderImportSummary(res) {
  const wrap = document.getElementById('r_te_import_summary');
  const head =
    `<div style="font-size:13px;color:var(--text);margin-top:8px">` +
    `本次共 <b>${res.total ?? 0}</b> 行，` +
    `<b style="color:var(--success)">成功 ${res.success_count ?? 0} 条</b>，` +
    `<b style="color:var(--danger)">失败 ${res.fail_count ?? 0} 条</b>。</div>`;
  if (res.failures && res.failures.length) {
    // 把英文字段转成中文表头，失败原因一目了然
    const rows = res.failures.map(f => ({ '行号': f.row, '姓名': f.name || '', '失败原因': f.reason }));
    wrap.innerHTML = head + '<div id="te_import_fail_tbl"></div>';
    renderTable('te_import_fail_tbl', rows);
  } else {
    wrap.innerHTML = head;
  }
}
async function getTeachers() {
  const r = await request('r_te_query', 'GET', '/teachers' + qs({
    name: val('te_name'), gender: val('te_gender'), title: val('te_title'),
    class_id: val('te_class'), phone: val('te_phone'), email: val('te_email'),
    hire_date_start: val('te_hstart'), hire_date_end: val('te_hend'),
    sort_by: val('te_sortby'), sort_order: val('te_sortorder'),
    page: val('te_page'), page_size: val('te_psize')
  }));
  renderTable('r_te_query_table', pickList(r.data));
}
async function getTeacherById() {
  if (!validate([['te_op_id', '教师ID']])) return;
  const r = await request('r_te_op', 'GET', '/teachers/' + val('te_op_id'), { silent: true });
  const rows = pickOne(r.data);
  renderTable('r_te_op_table', rows);
  if (r && r.ok) {
    showPlainResult('r_te_op', true, '查询成功', rows && rows.length ? '详见上方表格' : '未找到该教师');
  } else {
    showPlainResult('r_te_op', false, '查询失败', (r && r.data && r.data.msg) || '请重试');
  }
}
function updateTeacher() {
  if (!validate([['te_op_id', '教师ID']])) return;
  const body = clean({
    name: val('te_up_name'),
    gender: val('te_up_gender'),
    phone: val('te_up_phone'),
    title: val('te_up_title'),
    class_id: numVal('te_up_class'),
    email: val('te_up_email')
  });
  request('r_te_op', 'PUT', '/teachers/' + val('te_op_id'), { body });
}

/* ===================== 统计分析 ===================== */
// 根据下拉框选中的统计项目，调用对应的统计函数
function runStat() {
  const fnName = document.getElementById('sta_select').value;
  const fns = {
    staGeStu, staStuCount, staScoreGreater, staScoreFails,
    staClassAvg, staTallSal, staJobTime, staAvgClassJobTime
  };
  if (fns[fnName]) fns[fnName]();
}
async function staGeStu() {
  const r = await request('r_sta', 'GET', '/statistics/ge_stu/plus' + qs({ skip: val('sta_skip'), limit: val('sta_limit'), age: val('sta_age') }));
  renderTable('r_sta_table', pickList(r.data));
}
async function staStuCount() {
  document.getElementById('r_sta_table').innerHTML = '';
  const r = await request('r_sta', 'GET', '/statistics/stu_count', { silent: true });
  const n = r && r.data && r.data.data;
  showPlainResult('r_sta', !!(r && r.ok), '统计完成',
    r && r.ok ? `学生总数：${n ?? '—'}` : ((r && r.data && r.data.msg) || '统计失败'));
}
async function staScoreGreater() {
  const r = await request('r_sta', 'GET', '/statistics/score_greater/plus' + qs({ skip: val('sta_skip'), limit: val('sta_limit'), grade: val('sta_grade') }));
  renderTable('r_sta_table', pickList(r.data));
}
async function staScoreFails() {
  const r = await request('r_sta', 'GET', '/statistics/score_fails' + qs({ skip: val('sta_skip'), limit: val('sta_limit') }));
  renderTable('r_sta_table', pickList(r.data));
}
async function staClassAvg() {
  const r = await request('r_sta', 'GET', '/statistics/class_avg' + qs({ skip: val('sta_skip'), limit: val('sta_limit') }));
  renderTable('r_sta_table', pickList(r.data));
}
async function staTallSal() {
  const r = await request('r_sta', 'GET', '/statistics/tall_sal' + qs({ limit: val('sta_sal_limit') }));
  renderTable('r_sta_table', pickList(r.data));
}
async function staJobTime() {
  const r = await request('r_sta', 'GET', '/statistics/job_time' + qs({ skip: val('sta_skip'), limit: val('sta_limit') }));
  renderTable('r_sta_table', pickList(r.data));
}
async function staAvgClassJobTime() {
  const r = await request('r_sta', 'GET', '/statistics/avg_class_job_time' + qs({ skip: val('sta_skip'), limit: val('sta_limit') }));
  renderTable('r_sta_table', pickList(r.data));
}

/* ===================== AI 作业模块 ===================== */
async function workEvaluation() {
  if (!validate([['wk_stuid', '学生ID']])) return;
  const box = document.getElementById('r_wk_eval');
  box.textContent = '请求中...';
  const r = await request('r_wk_eval', 'POST', '/work/evaluation' + qs({
    student_id: val('wk_stuid'), style: val('wk_style')
  }), { silent: true });
  if (r && r.ok) showPlainResult('r_wk_eval', true, '评价生成成功', pickApiContent(r.data));
  else showPlainResult('r_wk_eval', false, '评价生成失败', (r && r.data && r.data.msg) || '请重试');
}
async function workImage() {
  if (!validate([['wk_prompt', '提示词']])) return;
  const preview = document.getElementById('r_wk_img_preview');
  preview.innerHTML = '';
  const box = document.getElementById('r_wk_img');
  box.textContent = '请求中...';
  const r = await request('r_wk_img', 'POST', '/work/image' + qs({ prompt: val('wk_prompt') }), { silent: true });
  const inner = r && r.data && r.data.data;
  const url = (inner && typeof inner === 'object' && inner.image_url) || findImageUrl(r.data);
  if (r && r.ok && url) {
    preview.innerHTML = '<img src="' + url + '" alt="生成结果" />';
    showPlainResult('r_wk_img', true, '文生图成功', '图片已生成，请见上方预览');
  } else {
    const err = (inner && inner.error) || (r && r.data && r.data.msg) || '文生图失败，请重试';
    showPlainResult('r_wk_img', false, '文生图失败', String(err));
  }
}
// 递归在返回 JSON 里找看起来像图片地址的字符串
function findImageUrl(obj) {
  if (typeof obj === 'string' && /^https?:\/\/.+\.(png|jpe?g|webp|gif)/i.test(obj)) return obj;
  if (typeof obj === 'string' && /^https?:\/\//.test(obj) && /(image|wanx|dashscope|oss)/i.test(obj)) return obj;
  if (Array.isArray(obj)) { for (const x of obj) { const u = findImageUrl(x); if (u) return u; } }
  else if (obj && typeof obj === 'object') { for (const k in obj) { const u = findImageUrl(obj[k]); if (u) return u; } }
  return null;
}
async function workTalk() {
  if (!validate([['wk_session', '会话ID'], ['wk_talk', '本轮输入']])) return;
  const box = document.getElementById('r_wk_talk');
  box.textContent = '请求中...';
  try {
    const r = await request('r_wk_talk', 'POST', '/work/talks' + qs({
      session_id: val('wk_session'), prompt: val('wk_talk')
    }), { silent: true });
    if (r && r.ok) showPlainResult('r_wk_talk', true, '对话成功', pickApiContent(r.data) || '（无回复内容）');
    else showPlainResult('r_wk_talk', false, '对话失败', (r && r.data && r.data.msg) || '请稍后重试');
  } catch (e) {
    showPlainResult('r_wk_talk', false, '网络错误', e.message);
  }
}

async function workClearTalk() {
  if (!validate([['wk_session', '会话ID']])) return;
  const box = document.getElementById('r_wk_talk');
  box.textContent = '请求中...';
  const r = await request('r_wk_talk', 'POST', '/work/talks/clear' + qs({ session_id: val('wk_session') }), { silent: true });
  const msg = (r && r.ok && r.data && r.data.data && r.data.data.message) || (r && r.data && r.data.msg) || '记忆已清空';
  showPlainResult('r_wk_talk', !!(r && r.ok), r && r.ok ? '已清空记忆' : '操作失败', msg);
}
async function workWeather() {
  const locEl = document.getElementById('wk_location');
  const adEl = document.getElementById('wk_adcode');
  // 经纬度与行政编码二选一，都为空时把两个框都标红提示
  if (!val('wk_location') && !val('wk_adcode')) {
    locEl.classList.add('invalid'); adEl.classList.add('invalid');
    return alert('经纬度或行政编码至少填一个');
  }
  locEl.classList.remove('invalid'); adEl.classList.remove('invalid');
  // 先清空上一次的可视化结果，避免残留
  document.getElementById('wk_weather_view').innerHTML = '';
  const r = await request('r_wk_weather', 'GET', '/work/weather' + qs({
    location: val('wk_location'), adcode: val('wk_adcode'),
    weather_type: val('wk_wtype'), added_fields: val('wk_added'), get_md: val('wk_getmd')
  }), { silent: true });
  // 请求成功后，把返回数据渲染成带图标的天气卡片；失败则给出友好提示
  if (r && r.ok) renderWeather(r.data);
  else document.getElementById('wk_weather_view').innerHTML =
    '<div class="geo-card"><div class="geo-fail">❌ 天气查询失败，请检查参数或稍后重试</div></div>';
}

// 根据天气文字描述映射成对应的 emoji 图标（覆盖接口文档里的天气枚举）
function weatherEmoji(weather) {
  const w = String(weather || '');
  if (/雷/.test(w)) return '⛈️';                 // 雷阵雨、雷阵雨伴有冰雹
  if (/冰雹/.test(w)) return '🌨️';
  if (/雨夹雪|冻雨/.test(w)) return '🌨️';
  if (/暴雪|大雪|中雪|小雪|阵雪|雪/.test(w)) return '❄️';
  if (/暴雨|大雨|中雨|小雨|阵雨|雨/.test(w)) return '🌧️';
  if (/沙尘暴|浮尘|扬沙/.test(w)) return '🌪️';
  if (/霾/.test(w)) return '😷';
  if (/雾/.test(w)) return '🌫️';
  if (/多云/.test(w)) return '⛅';
  if (/阴/.test(w)) return '☁️';
  if (/晴/.test(w)) return '☀️';
  return '🌡️';                                   // 兜底图标
}

// 把单个 infos 对象（实时天气）转成「图标+名称+数值」的指标小格子
function renderMetrics(infos) {
  // 每一项：[图标, 名称, 取值, 单位]
  const items = [
    ['🧭', '风向', infos.wind_direction, ''],
    ['💨', '风力', infos.wind_power, ''],
    ['🍃', '标准风力', infos.wind_power_v2, ''],
    ['💧', '湿度', infos.humidity, '%'],
    ['⏲️', '气压', infos.air_pressure, ' 百帕'],
  ];
  return items
    .filter(([, , v]) => v !== undefined && v !== null && v !== '')
    .map(([ico, lbl, v, unit]) =>
      `<div class="wx-metric"><span class="ico">${ico}</span>` +
      `<span class="meta"><span class="lbl">${lbl}</span>` +
      `<span class="val">${v}${unit}</span></span></div>`
    ).join('');
}

// 渲染顶部「地点 + 更新时间」公共信息
function renderWeatherHead(item) {
  const loc = [item.province, item.city, item.district].filter(Boolean).join(' · ');
  const adcode = item.adcode ? `<span class="wx-adcode">编码 ${item.adcode}</span>` : '';
  const time = item.update_time ? `<div class="wx-time">🕒 更新于 ${item.update_time}</div>` : '';
  return `<div class="wx-head"><div class="wx-loc">📍 ${loc}${adcode}</div>${time}</div>`;
}

// 天气数据可视化主入口：兼容 实时(now)/多日(future)/逐时(hours) 三种返回
function renderWeather(resp) {
  const view = document.getElementById('wk_weather_view');
  // 后端统一响应是 {code,msg,data:{...result...}}，逐层往里取 result
  const result = resp && resp.data && resp.data.result;
  if (!result) { view.innerHTML = '<div class="hint">未解析到天气数据，可展开下方原始 JSON 查看。</div>'; return; }

  // 1) 实时天气
  if (Array.isArray(result.realtime) && result.realtime.length) {
    view.innerHTML = result.realtime.map(item => {
      const f = item.infos || {};
      return `<div class="wx-card">${renderWeatherHead(item)}
        <div class="wx-main">
          <div class="wx-emoji">${weatherEmoji(f.weather)}</div>
          <div>
            <div class="wx-temp">${f.temperature ?? '--'}<small>℃</small></div>
            <div class="wx-desc">${f.weather ?? '未知天气'}</div>
          </div>
        </div>
        <div class="wx-metrics">${renderMetrics(f)}</div>
      </div>`;
    }).join('');
    return;
  }

  // 2) 多日预报：每天有 白天(day)/夜间(night)
  if (Array.isArray(result.forecast) && result.forecast.length) {
    view.innerHTML = result.forecast.map(item => {
      const days = (item.infos || []).map(d => {
        const day = d.day || {}, night = d.night || {};
        return `<div class="wx-day">
          <div class="wx-day-title">${d.week || ''}</div>
          <div class="wx-day-sub">${d.date || ''}</div>
          <div class="wx-day-emoji">${weatherEmoji(day.weather || night.weather)}</div>
          <div class="wx-day-temp">${night.temperature ?? '--'}~${day.temperature ?? '--'}℃</div>
          <div class="wx-day-line">☀️ ${day.weather || '--'}</div>
          <div class="wx-day-line">🌙 ${night.weather || '--'}</div>
          <div class="wx-day-line">💨 ${day.wind_direction || ''} ${day.wind_power || ''}</div>
        </div>`;
      }).join('');
      return `<div class="card" style="padding:16px">${renderWeatherHead(item)}
        <div class="wx-section-h">未来天气预报</div>
        <div class="wx-list">${days}</div></div>`;
    }).join('');
    return;
  }

  // 3) 24小时逐时预报
  if (Array.isArray(result.forecast_hours) && result.forecast_hours.length) {
    view.innerHTML = result.forecast_hours.map(item => {
      const hours = (item.infos || []).map(h => {
        const info = h.info || {};
        // hour 形如 "2026-06-04 10:00"，只展示 时:分 更直观
        const hm = String(h.hour || '').split(' ')[1] || h.hour || '';
        return `<div class="wx-day">
          <div class="wx-day-title">${hm}</div>
          <div class="wx-day-emoji">${weatherEmoji(info.weather)}</div>
          <div class="wx-day-temp">${info.temperature ?? '--'}℃</div>
          <div class="wx-day-line">${info.weather || '--'}</div>
          <div class="wx-day-line">💨 ${info.wind_direction || ''} ${info.wind_power || ''}</div>
        </div>`;
      }).join('');
      return `<div class="card" style="padding:16px">${renderWeatherHead(item)}
        <div class="wx-section-h">24小时逐时预报</div>
        <div class="wx-list">${hours}</div></div>`;
    }).join('');
    return;
  }

  view.innerHTML = '<div class="hint">暂无可展示的天气数据，可展开下方原始 JSON 查看。</div>';
}
async function workGeocoder() {
  if (!validate([['wk_address', '地址']])) return;
  // 先清空上一次的可视化结果
  document.getElementById('wk_geo_view').innerHTML = '';
  const r = await request('r_wk_geo', 'GET', '/work/geocoder' + qs({ address: val('wk_address'), policy: val('wk_policy') }), { silent: true });
  if (r && r.ok) renderGeocoder(r.data);
  else document.getElementById('wk_geo_view').innerHTML =
    '<div class="geo-card"><div class="geo-fail">❌ 地址解析失败，请检查地址或稍后重试</div></div>';
}

// 地址解析结果可视化：把经纬度、行政区划、可信度等渲染成卡片
function renderGeocoder(resp) {
  const view = document.getElementById('wk_geo_view');
  const d = resp && resp.data;   // 内层数据：{success, lat, lng, address_components, adcode, ...}
  if (!d || typeof d !== 'object') { view.innerHTML = '<div class="hint">未解析到地址数据，可展开下方原始 JSON 查看。</div>'; return; }

  // 解析失败的情况
  if (d.success === false) {
    view.innerHTML = '<div class="geo-card"><div class="geo-fail">❌ 地址解析失败，请检查地址是否准确</div></div>';
    return;
  }

  const c = d.address_components || {};
  // 拼出完整地址（过滤掉空字段）
  const fullAddr = [c.province, c.city, c.district, c.street, c.street_number].filter(Boolean).join('');

  // 经纬度、行政编码做成小格子
  const metrics = [
    ['🧭', '纬度', d.lat],
    ['🧭', '经度', d.lng],
    ['🔢', '行政编码', d.adcode],
    ['🎯', '解析等级', d.level],
  ].filter(([, , v]) => v !== undefined && v !== null && v !== '')
   .map(([ico, lbl, v]) =>
     `<div class="geo-metric"><span class="ico">${ico}</span>` +
     `<span class="meta"><span class="lbl">${lbl}</span><span class="val">${v}</span></span></div>`
   ).join('');

  // 可信度 reliability：腾讯地图取值 1~10，做成进度条更直观
  let bar = '';
  if (d.reliability !== undefined && d.reliability !== null) {
    const pct = Math.max(0, Math.min(100, Number(d.reliability) * 10));
    bar = `<div class="geo-bar-wrap">
      <div class="geo-bar-head"><span>📊 解析可信度</span><span>${d.reliability} / 10</span></div>
      <div class="geo-bar"><i style="width:${pct}%"></i></div>
    </div>`;
  }

  // 一键联动按钮：把解析出的 adcode / 经纬度传给天气查询
  // 优先用 adcode，没有则退而用经纬度（location 格式为 "纬度,经度"）
  const adcode = d.adcode ? String(d.adcode) : '';
  const location = (d.lat != null && d.lng != null) ? `${d.lat},${d.lng}` : '';
  let linkBtn = '';
  if (adcode || location) {
    // 用 JSON.stringify 转义参数，避免特殊字符破坏 onclick
    const args = `${JSON.stringify(adcode)}, ${JSON.stringify(location)}`;
    linkBtn = `<div style="margin-top:16px">
      <button class="btn" onclick='useGeoForWeather(${args})'>🌤️ 查该地天气</button>
    </div>`;
  }

  view.innerHTML = `<div class="geo-card">
    <div class="geo-addr">📍 ${fullAddr || '未知地址'}</div>
    <div class="geo-coord">🌐 经纬度坐标：${d.lat ?? '--'}, ${d.lng ?? '--'}</div>
    <div class="geo-metrics">${metrics}</div>
    ${bar}
    ${linkBtn}
  </div>`;
}

// 地址→天气一键联动：把 adcode/经纬度回填到天气查询表单并自动查询
function useGeoForWeather(adcode, location) {
  const adcodeEl = document.getElementById('wk_adcode');
  const locEl = document.getElementById('wk_location');
  // 优先用 adcode 查询，更精准；填一个时清空另一个，避免参数冲突
  if (adcode) { adcodeEl.value = adcode; locEl.value = ''; }
  else { locEl.value = location; adcodeEl.value = ''; }
  // 默认查实时天气
  document.getElementById('wk_wtype').value = 'now';
  // 触发天气查询，并把视图滚动到天气结果区
  workWeather();
  document.getElementById('wk_weather_view').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/* ===================== 邮件管理 ===================== */
// 邮件操作只展示友好的状态徽章，不暴露原始返回 JSON
function mailStatus(ok, msg) {
  document.getElementById('r_mail').innerHTML =
    '<span class="badge ' + (ok ? 'ok' : 'err') + '">' + (ok ? '✓ ' : '✗ ') + msg + '</span>';
}

// 富文本编辑器：执行排版命令（加粗、列表、标题等）
function rteCmd(cmd, value) {
  document.getElementById('mail_body').focus();
  document.execCommand(cmd, false, value || null);
}

// 把纯文本安全地转成 HTML（转义特殊字符 + 换行转 <br>），用于回填大模型生成的内容
function textToHtml(text) {
  const esc = String(text || '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return esc.replace(/\n/g, '<br>');
}

// 第一步：调用大模型生成邮件内容，成功后把主题/正文填入可编辑区供用户修改
async function generateEmail() {
  if (!validate([['mail_prompt', '需求描述']])) return;
  const btn = document.getElementById('mail_gen_btn');
  btn.disabled = true; btn.textContent = '生成中...';
  try {
    const r = await request('r_mail', 'POST', '/email/generate' + qs({ prompt: val('mail_prompt') }), { silent: true });
    const content = r && r.ok && r.data && r.data.data;
    if (content) {
      // 主题填入普通输入框；正文转成 HTML 后填入富文本编辑器
      document.getElementById('mail_subject').value = content.subject || '';
      document.getElementById('mail_body').innerHTML = textToHtml(content.body);
      const box = document.getElementById('mail_edit_box');
      box.style.display = 'block';
      box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      // 不展示原始 JSON，只给一个友好提示
      mailStatus(true, '邮件内容已生成，请在下方编辑后寄出');
    } else {
      mailStatus(false, '邮件生成失败，请重试');
    }
  } finally {
    btn.disabled = false; btn.textContent = '✨ 生成邮件';
  }
}

// 重新生成：基于当前需求再次生成内容，覆盖编辑区
function regenerateEmail() { generateEmail(); }

// 第二步：把用户确认（可能已编辑）后的主题、富文本正文发送出去
async function sendEmail() {
  const bodyEl = document.getElementById('mail_body');
  const bodyHtml = bodyEl.innerHTML.trim();
  // 用纯文本判断是否为空，避免空标签（如 <br>）误判为有内容
  const bodyText = bodyEl.innerText.trim();
  // 正文是富文本（非普通 input），单独校验并给外层 .rte 标红
  const bodyOk = !!bodyText;
  const rte = bodyEl.closest('.rte');
  if (rte) rte.classList.toggle('invalid', !bodyOk);
  // 收件邮箱、主题用通用校验
  const fieldsOk = validate([['mail_receiver', '收件邮箱'], ['mail_subject', '邮件主题']]);
  if (!fieldsOk || !bodyOk) { if (fieldsOk && !bodyOk) alert('请填写：邮件正文'); return; }

  const btn = document.getElementById('mail_send_btn');
  btn.disabled = true; btn.textContent = '寄出中...';
  try {
    const r = await request('r_mail', 'POST', '/email/send' + qs({
      subject: val('mail_subject'), body: bodyHtml, receiver: val('mail_receiver')
    }), { silent: true });
    // 只展示发送结果的友好提示，不暴露原始 JSON
    const res = r && r.data && r.data.data;
    if (res && res.success) mailStatus(true, res.message || '邮件已发送');
    else mailStatus(false, (res && res.message) || '邮件发送失败');
  } finally {
    btn.disabled = false; btn.textContent = '📨 寄出邮件';
  }
}
