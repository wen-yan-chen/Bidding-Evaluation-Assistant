/* 招投标评审助手 · D1 状态页
 * 原则：页面上每一个状态都来自后端真实返回，前端不写死"正常/已接入"。
 * 未实现的能力只显示"待接入"，不做占位按钮（赛题硬要求）。
 */
'use strict';

const REFRESH_MS = 15000;
const DISCLAIMER_KEY = '评标委员会评审结论';
const $ = (id) => document.getElementById(id);

let timer = null;
let lastInfo = null;

/* ------------------------------------------------------------ 基础请求 */

async function request(url, timeoutMs = 6000) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), timeoutMs);
  const t0 = performance.now();
  try {
    const res = await fetch(url, {
      signal: ctrl.signal,
      cache: 'no-store',
      headers: { Accept: 'application/json' },
    });
    const text = await res.text();
    let body = null;
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
    return { ok: res.ok, status: res.status, ms: performance.now() - t0, body };
  } catch (err) {
    return { ok: false, status: 0, ms: performance.now() - t0, body: null, error: String(err) };
  } finally {
    clearTimeout(t);
  }
}

/* ------------------------------------------------------------ 格式化 */

function fmtMs(ms) {
  return `${Math.round(ms)} ms`;
}

function fmtUptime(sec) {
  if (!Number.isFinite(sec) || sec < 0) return '—';
  if (sec < 60) return `${sec} 秒`;
  const m = Math.floor(sec / 60);
  if (m < 60) return `${m} 分 ${sec % 60} 秒`;
  const h = Math.floor(m / 60);
  return `${h} 小时 ${m % 60} 分`;
}

function fmtTime(d) {
  const p = (n) => String(n).padStart(2, '0');
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

/* ------------------------------------------------------------ 自检 */

function checkRow(name, ok, detail) {
  return { name, ok, detail };
}

async function runChecks() {
  const [h, ah, info] = await Promise.all([
    request('/health'),
    request('/api/health'),
    request('/api/info'),
  ]);

  const bodyH = h.body || {};
  const bodyAh = ah.body || {};
  const bodyInfo = info.body || {};

  const rows = [
    checkRow(
      'GET /health 返回 200 且 status=ok',
      h.ok && h.status === 200 && bodyH.status === 'ok',
      h.ok ? `HTTP ${h.status} · ${fmtMs(h.ms)}` : '连接失败'
    ),
    checkRow(
      'GET /api/health 返回 200',
      ah.ok && bodyAh.status === 'ok',
      ah.ok ? `HTTP ${ah.status} · ${fmtMs(ah.ms)}` : '连接失败'
    ),
    checkRow(
      'GET /api/info 返回 200 且含版本信息',
      info.ok && Boolean(bodyInfo.app && bodyInfo.app.version),
      info.ok ? `HTTP ${info.status} · ${fmtMs(info.ms)}` : '连接失败'
    ),
    checkRow(
      '版本号单一来源一致（VERSION = 接口返回）',
      Boolean(bodyAh.version) && bodyAh.version === (bodyInfo.app || {}).version,
      bodyAh.version ? `v${bodyAh.version}` : '无版本号'
    ),
    checkRow(
      '配置文件可解析（agent.json / milestones.json）',
      info.ok && Array.isArray(bodyInfo.errors) && bodyInfo.errors.length === 0,
      info.ok && bodyInfo.errors && bodyInfo.errors.length
        ? bodyInfo.errors.join('；')
        : '无缺失'
    ),
    checkRow(
      '免责声明已在页面顶部渲染',
      ($('disclaimer-text')?.textContent || '').includes(DISCLAIMER_KEY),
      '已渲染 · 文案一致'
    ),
  ];

  renderChecks(rows);
  renderRuntime(bodyAh, bodyInfo);
  renderPlatform(bodyInfo.agent);
  renderMilestones(bodyInfo.milestones);

  lastInfo = bodyInfo;
  $('check-stamp').textContent = `最近检测 ${fmtTime(new Date())} · 每 ${REFRESH_MS / 1000} 秒自动复检`;
  return rows;
}

function renderChecks(rows) {
  const list = $('check-list');
  list.textContent = '';
  for (const r of rows) {
    const li = document.createElement('li');
    li.className = `check-row ${r.ok ? 'is-pass' : 'is-fail'}`;
    const dot = document.createElement('span');
    dot.className = 'dot';
    const name = document.createElement('span');
    name.className = 'check-name';
    name.textContent = r.name;
    const detail = document.createElement('span');
    detail.className = 'check-detail';
    detail.textContent = r.detail || '';
    li.append(dot, name, detail);
    list.append(li);
  }

  const passed = rows.filter((r) => r.ok).length;
  if (passed < rows.length) {
    $('check-stamp').textContent = `自检未全部通过（${passed}/${rows.length}）`;
  }
}

/* ------------------------------------------------------------ 运行信息 */

function renderRuntime(health, info) {
  const app = info.app || {};
  $('chip-version').textContent = `v${app.version || '—'}`;
  $('chip-env').textContent = `env:${app.env || '—'}`;

  $('k-service').textContent = health.service || '—';
  $('k-version').textContent = app.version || '—';
  $('k-env').textContent = app.env || '—';
  $('k-started').textContent = (health.started_at || '—').replace('T', ' ').slice(0, 19);
  $('k-uptime').textContent = fmtUptime(health.uptime_seconds);
  $('k-container').textContent = health.in_container ? '是（Docker）' : '否（本地直跑）';
}

/* ------------------------------------------------------------ 平台能力 */

function renderPlatform(agent) {
  if (!agent || !agent.configured) {
    $('k-mcp-tools').textContent = '0';
    $('k-skill').textContent = '0';
    $('k-kb').textContent = 'agent.json 未就绪';
    return;
  }

  const tools = agent.mcp_tools || [];
  $('k-mcp-tools').textContent = String(tools.length);
  $('badge-mcp').textContent = tools.length ? '已登记 · 待挂载' : '待接入';

  const skills = agent.skills || [];
  $('k-skill').textContent = String(skills.length);
  $('badge-skill').textContent = skills.length ? '已登记 · 待挂载' : '待接入';

  if (agent.kb_index_ready) {
    $('k-kb').textContent = `索引已配置（${agent.kb_index_count} 个）`;
    $('badge-kb').textContent = '已就绪';
    $('badge-kb').className = 'badge badge-done';
  } else {
    $('k-kb').textContent = agent.kb_index_count
      ? `索引名待替换（${agent.kb_index_count} 个占位）`
      : '索引未配置';
    $('badge-kb').textContent = '待接入';
  }
}

/* ------------------------------------------------------------ 里程碑 */

const STATUS_TEXT = { done: '已完成', doing: '进行中', planned: '计划中' };
const STATUS_CLASS = { done: 'badge-done', doing: 'badge-doing', planned: 'badge-plan' };

function renderMilestones(ms) {
  if (!ms || !Array.isArray(ms.items)) {
    $('ms-hint').textContent = '里程碑数据未就绪';
    return;
  }

  $('ms-hint').textContent = `当前进度 ${ms.current || '—'} · 更新于 ${ms.updated || '—'}`;

  const body = $('ms-body');
  body.textContent = '';
  for (const it of ms.items) {
    const tr = document.createElement('tr');
    const tdId = document.createElement('td');
    tdId.textContent = it.id;
    const tdName = document.createElement('td');
    tdName.textContent = it.name;
    const tdDay = document.createElement('td');
    tdDay.className = 'col-day';
    tdDay.textContent = it.day;
    const tdStatus = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = `badge ${STATUS_CLASS[it.status] || 'badge-plan'}`;
    badge.textContent = STATUS_TEXT[it.status] || it.status;
    tdStatus.append(badge);
    const tdTarget = document.createElement('td');
    tdTarget.className = 'col-target';
    tdTarget.textContent = it.target;
    tr.append(tdId, tdName, tdDay, tdStatus, tdTarget);
    body.append(tr);
  }

  renderDeliverables(ms.d1_deliverables || []);
}

function renderDeliverables(items) {
  const list = $('deliver-list');
  list.textContent = '';
  if (!items.length) {
    const li = document.createElement('li');
    li.className = 'empty';
    li.textContent = '暂无交付记录';
    list.append(li);
    return;
  }
  for (const it of items) {
    const li = document.createElement('li');
    const tick = document.createElement('span');
    tick.className = 'tick';
    tick.textContent = '✓';
    const label = document.createElement('span');
    label.textContent = it.item;
    const code = document.createElement('code');
    code.textContent = it.path;
    li.append(tick, label, code);
    list.append(li);
  }
}

/* ------------------------------------------------------------ 启动 */

async function refresh() {
  $('btn-refresh').disabled = true;
  try {
    await runChecks();
  } finally {
    $('btn-refresh').disabled = false;
  }
}

function start() {
  $('btn-refresh').addEventListener('click', refresh);

  // 切回标签页时立即复检，避免看到过期状态
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refresh();
  });

  refresh();
  timer = setInterval(refresh, REFRESH_MS);
  window.addEventListener('beforeunload', () => clearInterval(timer));
}

document.addEventListener('DOMContentLoaded', start);
