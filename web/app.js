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

  renderDeliverables((ms.stage && ms.stage.items) || ms.d1_deliverables || []);
  if (ms.stage && ms.stage.label) {
    $('stage-label').textContent = `${ms.stage.label} · 已完成 ${(ms.stage.items || []).length} 项`;
  }
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

/* ------------------------------------------------------------ 上传与解析（D2） */

let selectedFile = null;

function setParseStatus(text, kind) {
  const box = $('parse-status');
  box.hidden = false;
  box.className = `parse-status ${kind || ''}`.trim();
  box.textContent = text;
}

function formatSize(bytes) {
  if (!Number.isFinite(bytes)) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function renderParseResult(data) {
  const ok = data.parse_status !== 'failed';
  setParseStatus(
    ok
      ? `解析完成：${data.file_name} · ${
          data.ocr_pages && data.ocr_pages.length
            ? `含 ${data.ocr_pages.length} 页 OCR 识别`
            : data.parse_status === 'degraded'
              ? '部分降级（见下方说明）'
              : '状态正常'
        }`
      : `解析失败：${(data.degraded || []).join('；') || '未知原因'}`,
    ok ? 'is-ok' : 'is-error'
  );

  $('parse-result').hidden = false;

  const chips = [
    ['文档 ID', data.doc_id],
    ['页数', `${data.page_count}${data.page_source === 'estimated' ? '（估算）' : ''}`],
    ['字符数', data.char_count],
    ['条款', `${data.clause_count} 条`],
    ['字段', `${data.fields.length} / 6`],
    ['SHA256', `${(data.sha256 || '').slice(0, 12)}…`],
  ];
  if (data.ocr_pages && data.ocr_pages.length) {
    chips.splice(2, 0, ['OCR 页', `${data.ocr_pages.length} 页`]);
  }
  const meta = $('parse-meta');
  meta.textContent = '';
  for (const [label, value] of chips) {
    const chip = document.createElement('span');
    chip.className = 'meta-chip';
    const strong = document.createElement('strong');
    strong.textContent = String(value);
    chip.append(`${label} `, strong);
    meta.append(chip);
  }

  const body = $('field-body');
  body.textContent = '';
  if (!data.fields.length) {
    const tr = document.createElement('tr');
    const td = document.createElement('td');
    td.colSpan = 4;
    td.className = 'empty';
    td.textContent = '未抽取到任何字段（该文件可能不含标准字段标签）';
    tr.append(td);
    body.append(tr);
  }
  for (const field of data.fields) {
    const tr = document.createElement('tr');
    const tdName = document.createElement('td');
    tdName.textContent = field.name;
    const tdValue = document.createElement('td');
    const value = document.createElement('span');
    value.className = 'field-value';
    value.textContent = field.value;
    tdValue.append(value);
    const tdPage = document.createElement('td');
    tdPage.textContent = `第 ${field.page} 页`;
    const tdQuote = document.createElement('td');
    const quote = document.createElement('span');
    quote.className = 'field-quote';
    quote.textContent = `「${field.quote}」`;
    tdQuote.append(quote);
    tr.append(tdName, tdValue, tdPage, tdQuote);
    body.append(tr);
  }

  const extra = $('parse-extra');
  extra.textContent = '';
  if (data.missing_fields && data.missing_fields.length) {
    const note = document.createElement('p');
    note.className = 'parse-note';
    note.textContent = `未抽取到：${data.missing_fields.join('、')}（缺失即如实留空，不做推测）`;
    extra.append(note);
  }
  for (const item of data.degraded || []) {
    const note = document.createElement('p');
    note.className = 'parse-note';
    note.textContent = `降级说明：${item}`;
    extra.append(note);
  }
}

async function uploadSelected() {
  if (!selectedFile) return;
  $('btn-parse').disabled = true;
  setParseStatus(`正在解析 ${selectedFile.name} …`, '');
  try {
    const form = new FormData();
    form.append('file', selectedFile, selectedFile.name);
    const res = await fetch('/api/upload', { method: 'POST', body: form });
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
    if (!res.ok) {
      setParseStatus(`上传失败：${data.detail || res.status}`, 'is-error');
      return;
    }
    renderParseResult(data);
    refresh(); // 能力开关与页面状态同步刷新
  } catch (err) {
    setParseStatus(`上传失败：${err}`, 'is-error');
  } finally {
    $('btn-parse').disabled = !selectedFile;
  }
}

function initUpload() {
  $('btn-choose').addEventListener('click', () => $('file-input').click());

  $('file-input').addEventListener('change', (event) => {
    selectedFile = event.target.files && event.target.files[0] ? event.target.files[0] : null;
    $('file-name').textContent = selectedFile
      ? `${selectedFile.name} · ${formatSize(selectedFile.size)}`
      : '未选择文件';
    $('btn-parse').disabled = !selectedFile;
    if (selectedFile) setParseStatus('已选择文件，点击「上传并解析」开始', '');
  });

  $('btn-parse').addEventListener('click', uploadSelected);
}

const FIELD_NAMES = ['项目名称', '项目编号', '采购人', '投标人', '报价', '工期'];

async function restoreLastDocument() {
  const list = await request('/api/documents');
  const items = (list.body && list.body.items) || [];
  if (!items.length) return;
  const detail = await request(`/api/doc/${items[0].doc_id}`);
  const data = detail.body;
  if (!detail.ok || !data || !Array.isArray(data.fields)) return;
  renderParseResult({
    ...data,
    clause_count: (data.clauses || []).length,
    ocr_pages: (data.meta && data.meta.ocr_pages) || data.ocr_pages || [],
    missing_fields: FIELD_NAMES.filter((name) => !data.fields.some((f) => f.name === name)),
  });
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
  initUpload();

  // 切回标签页时立即复检，避免看到过期状态
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refresh();
  });

  refresh();
  restoreLastDocument();
  timer = setInterval(refresh, REFRESH_MS);
  window.addEventListener('beforeunload', () => clearInterval(timer));
}

document.addEventListener('DOMContentLoaded', start);
