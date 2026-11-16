/* 招投标评审助手 · D8 前端
 * 原则：
 *  1) 页面数字全部来自接口（/api/scoring/profiles、/api/review、/api/report/.../meta），不写死示例分数；
 *  2) 每个按钮都有真实行为；未实现能力只在「系统状态」标「待 D9」，不做占位按钮；
 *  3) 双栏对照使用接口返回的 char_start / char_end 高亮原文，找不到偏移时退回 quote 检索。
 */
'use strict';

const $ = (id) => document.getElementById(id);
const DISCLAIMER = 'AI 辅助评审结果，最终以评标委员会评审结论为准';
const MAX_UPLOAD_MB = 50;
const MAX_REPORT_ROWS = 20;

const state = {
  view: 'review',
  docs: [],
  profiles: [],
  selectedDocId: null,
  selectedProfileId: null,
  doc: null,
  review: null,
  compare: null,
  reviews: [],
  reviewsByDoc: Object.create(null),
  reportMeta: new Map(),
  reportMetaFailed: new Set(),
  docsReady: false,
  evidence: [],
  evidenceTab: 'all',
  uploadFiles: [],
  reviewing: false,
  reportsLoaded: false,
  showStale: false,
  adminAuthenticated: false,
  adminUser: null,
  adminData: null,
  adminFilter: '',
  adminLoadSeq: 0,
  adminSelectedDocs: new Set(),
  adminSelectedReviews: new Set(),
};

/* ============================================================ 基础工具 */

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

function badge(text, cls, title) {
  const node = el('span', `badge ${cls || 'badge-plan'}`, text);
  if (title) node.title = title;
  return node;
}

async function api(path, opts = {}) {
  const { method = 'GET', body, timeout = 15000 } = opts;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    const headers = { Accept: 'application/json' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    const res = await fetch(path, {
      method,
      signal: ctrl.signal,
      cache: 'no-store',
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const text = await res.text();
    let data = null;
    if (text) {
      try { data = JSON.parse(text); } catch { data = text; }
    }
    if (!res.ok) {
      const detail = data && typeof data === 'object' && data.detail !== undefined ? data.detail : data;
      const err = new Error(detailText(detail) || `HTTP ${res.status}`);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  } catch (err) {
    if (err && err.name === 'AbortError') {
      const timeoutErr = new Error(`请求超时（${Math.round(timeout / 1000)} 秒）`);
      timeoutErr.timeout = true;
      throw timeoutErr;
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

function detailText(detail) {
  if (detail === undefined || detail === null || detail === '') return '';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (!item || typeof item !== 'object') return String(item);
        const loc = Array.isArray(item.loc) ? item.loc.slice(1).join('.') : '';
        return `${loc ? loc + '：' : ''}${item.msg || JSON.stringify(item)}`;
      })
      .join('；');
  }
  if (typeof detail === 'object') return detail.message || detail.error || JSON.stringify(detail);
  return String(detail);
}

function describeError(err, action) {
  if (!err) return `${action}失败：未知错误`;
  if (err.status === 404) return `${action}失败（404）：${err.message}。请确认文档/评审仍存在，或重新上传后再试。`;
  if (err.status === 413) return `${action}失败（413）：${err.message}。请压缩文件或拆分后再上传。`;
  if (err.status === 415) return `${action}失败（415）：${err.message}`;
  if (err.timeout) return `${action}失败：${err.message}，请检查网络或稍后重试。`;
  return `${action}失败：${err.message}`;
}

function setNotice(id, kind, message) {
  const box = $(id);
  if (!box) return;
  if (!message) { box.hidden = true; box.textContent = ''; return; }
  box.hidden = false;
  box.className = 'notice ' + kind.split(/\s+/).filter(Boolean).map((k) => `notice-${k}`).join(' ');
  box.textContent = message;
}

function startElapsedNotice(id, base, kind = 'info loading') {
  const box = $(id);
  const t0 = performance.now();
  setNotice(id, kind, base);
  if (!box) return () => {};
  const timer = setInterval(() => {
    const sec = ((performance.now() - t0) / 1000).toFixed(1);
    box.textContent = `${base}（已用时 ${sec} 秒）`;
  }, 200);
  return () => clearInterval(timer);
}

function fmtScore(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(1) : '—';
}

function fmtDelta(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return `${n > 0 ? '+' : ''}${n.toFixed(1)}`;
}

function fmtSize(bytes) {
  const n = Number(bytes);
  if (!Number.isFinite(n) || n <= 0) return '—';
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(2)} MB`;
}

function fmtDateTime(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function fmtMoney(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 2 }).format(n);
}

function shortHash(value) {
  return value ? `${String(value).slice(0, 12)}${String(value).length > 12 ? '…' : ''}` : '—';
}

async function safe(promise) {
  try { return { ok: true, data: await promise }; }
  catch (err) { return { ok: false, error: err }; }
}

/* ============================================================ 视图切换 */

const VIEWS = ['review', 'reports', 'status'];

function setView(name, opts = {}) {
  const view = VIEWS.includes(name) ? name : 'review';
  state.view = view;
  for (const v of VIEWS) {
    const node = $(`view-${v}`);
    if (node) node.hidden = v !== view;
  }
  document.querySelectorAll('.navbtn').forEach((btn) => {
    const on = btn.dataset.view === view;
    btn.classList.toggle('is-active', on);
    btn.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  if (opts.updateHash !== false && location.hash !== `#${view}`) {
    history.replaceState(null, '', `#${view}`);
  }
  if (view === 'reports' && state.docsReady) {
    if (!state.reportsLoaded) loadReports();
    else hydrateReportMeta(state.reviews.slice(0, MAX_REPORT_ROWS));
  }
  if (view === 'reports') enterReportsAdmin();
  if (view === 'status') enterStatusView();
  window.scrollTo({ top: 0, behavior: 'auto' });
}

function initNav() {
  document.querySelectorAll('.navbtn').forEach((btn) => {
    btn.addEventListener('click', () => setView(btn.dataset.view));
  });
  window.addEventListener('hashchange', () => {
    const name = (location.hash || '').replace(/^#/, '') || 'review';
    setView(name, { updateHash: false });
  });
}

/* ============================================================ 文档选择与上传 */

function parseStatusLabel(status) {
  if (status === 'ok') return '正常';
  if (status === 'degraded') return '降级';
  if (status === 'failed') return '失败';
  return status || '—';
}

function docLabel(item) {
  if (!item) return '';
  const pages = Number.isFinite(Number(item.page_count)) ? `${item.page_count} 页` : '页数—';
  return `${item.file_name || item.doc_id} · ${pages} · ${parseStatusLabel(item.parse_status)}`;
}

function renderDocSelect(selected) {
  const select = $('doc-select');
  if (!select) return;
  select.textContent = '';
  if (!state.docs.length) {
    const opt = el('option', '', '暂无已解析文档，请先上传');
    opt.value = '';
    select.append(opt);
    select.disabled = true;
    return;
  }
  select.disabled = false;
  for (const item of state.docs) {
    const opt = el('option', '', docLabel(item));
    opt.value = item.doc_id;
    if (item.doc_id === selected) opt.selected = true;
    select.append(opt);
  }
  if (selected && state.docs.some((d) => d.doc_id === selected)) select.value = selected;
}

function renderDocMetaLoading() {
  const box = $('doc-meta');
  if (!box) return;
  box.textContent = '';
  box.append(el('span', 'doc-chip', '正在读取文档详情…'));
}

function appendChip(box, label, value, cls) {
  const chip = el('span', `doc-chip ${cls || ''}`.trim());
  chip.append(`${label} `);
  const strong = el('strong', '', value);
  chip.append(strong);
  box.append(chip);
}

function renderDocMeta(doc) {
  const box = $('doc-meta');
  if (!box) return;
  box.textContent = '';
  if (!doc) {
    box.append(el('span', 'doc-chip', '尚未选择文档'));
    setNotice('doc-degraded', '', '');
    return;
  }
  appendChip(box, '文档', doc.doc_id);
  appendChip(box, '页数', `${doc.page_count}${doc.page_source === 'estimated' ? '（估算）' : ''}`);
  appendChip(box, '字符', doc.char_count);
  appendChip(box, '条款', `${(doc.clauses || []).length} 条`);
  appendChip(box, '字段', `${(doc.fields || []).length} / 6`);
  appendChip(box, '解析', parseStatusLabel(doc.parse_status),
    doc.parse_status === 'failed' ? 'is-danger' : doc.parse_status === 'degraded' ? 'is-warn' : '');
  const ocrPages = (doc.meta && doc.meta.ocr_pages) || [];
  if (ocrPages.length) appendChip(box, 'OCR', `${ocrPages.length} 页`, 'is-warn');
  if (doc.sha256) appendChip(box, 'SHA256', shortHash(doc.sha256));

  const degraded = [
    ...(doc.parse_status === 'failed' ? ['解析失败，无法进入评审'] : []),
    ...(doc.degraded || []),
  ];
  if (degraded.length) {
    setNotice('doc-degraded', doc.parse_status === 'failed' ? 'error' : 'warn', `降级说明：${degraded.join('；')}`);
  } else if (ocrPages.length) {
    setNotice('doc-degraded', 'warn', `OCR 页：${ocrPages.join('、')}；相关页文本来自识别，建议人工核对原件。`);
  } else {
    setNotice('doc-degraded', '', '');
  }
}

async function loadDocs(selectId) {
  let data;
  try {
    data = await api('/api/documents', { timeout: 10000 });
  } catch (err) {
    state.docs = [];
    state.docsReady = true;
    renderDocSelect(null);
    renderDocMeta(null);
    setNotice('upload-status', 'error', describeError(err, '读取文档列表'));
    updateReviewAvailability();
    return;
  }
  state.docs = Array.isArray(data && data.items) ? data.items : [];
  state.docsReady = true;
  let target = selectId || state.selectedDocId || (state.docs[0] && state.docs[0].doc_id) || null;
  if (target && !state.docs.some((doc) => doc.doc_id === target)) target = (state.docs[0] && state.docs[0].doc_id) || null;
  renderDocSelect(target);
  if (!target) {
    state.selectedDocId = null;
    state.doc = null;
    renderDocMeta(null);
    updateReviewAvailability();
    return;
  }
  await selectDoc(target);
}

async function selectDoc(docId) {
  if (!docId) return;
  if (state.review && state.review.doc_id !== docId) clearReviewDisplay();
  state.selectedDocId = docId;
  const select = $('doc-select');
  if (select) select.value = docId;
  renderDocMetaLoading();
  try {
    const doc = await api(`/api/doc/${encodeURIComponent(docId)}`, { timeout: 20000 });
    if (state.selectedDocId !== docId) return;
    state.doc = doc;
    renderDocMeta(doc);
    renderPages(doc);
    updateReviewAvailability();
  } catch (err) {
    if (state.selectedDocId !== docId) return;
    state.doc = null;
    renderDocMeta(null);
    setNotice('doc-degraded', 'error', describeError(err, '读取文档详情'));
    updateReviewAvailability();
  }
}

function renderPages(doc) {
  const wrap = $('pages');
  if (!wrap) return;
  wrap.textContent = '';
  if (!doc || !Array.isArray(doc.pages) || !doc.pages.length) {
    wrap.append(el('p', 'empty-inline', '该文档没有可显示的原文页。'));
    return;
  }
  const ocrPages = new Set((doc.meta && doc.meta.ocr_pages) || []);
  const estimated = doc.page_source === 'estimated';
  for (const span of doc.pages) {
    const article = el('article', 'page');
    article.id = `page-${span.page}`;
    article.dataset.page = String(span.page);

    const head = el('div', 'page-head');
    head.append(el('strong', '', `第 ${span.page} 页`));
    if (estimated) head.append(badge('估算', 'badge-warn', 'docx 无分页符，页码按行数估算，跳转可能偏 1 页'));
    if (ocrPages.has(span.page)) head.append(badge('OCR', 'badge-info', '该页文本来自 OCR，建议人工核对原件'));

    const body = el('div', 'page-text');
    const text = (doc.full_text || '').slice(span.start, span.end);
    body.textContent = text || '（本页无可提取文本）';
    article.append(head, body);
    wrap.append(article);
  }
}

function clearMarks() {
  document.querySelectorAll('#pages mark.hit').forEach((mark) => {
    mark.replaceWith(document.createTextNode(mark.textContent || ''));
  });
  document.querySelectorAll('#pages .page').forEach((page) => page.normalize());
  document.querySelectorAll('#pages .page.is-target').forEach((page) => page.classList.remove('is-target'));
}

function renderPageHighlight(pageEl, text, start, end) {
  const body = pageEl.querySelector('.page-text');
  if (!body) return null;
  body.textContent = '';
  if (!Number.isInteger(start) || !Number.isInteger(end) || end <= start) {
    body.textContent = text || '（本页无可提取文本）';
    return null;
  }
  const s = Math.max(0, Math.min(start, text.length));
  const e = Math.max(s, Math.min(end, text.length));
  if (s > 0) body.append(document.createTextNode(text.slice(0, s)));
  const mark = el('mark', 'hit', text.slice(s, e) || '（空片段）');
  body.append(mark);
  if (e < text.length) body.append(document.createTextNode(text.slice(e)));
  return mark;
}

function resolveSpan(item) {
  const doc = state.doc;
  if (!doc || !Array.isArray(doc.pages) || !doc.pages.length) return null;
  const start = Number(item.start);
  const end = Number(item.end);
  if (Number.isInteger(start) && Number.isInteger(end) && start >= 0 && end > start) {
    let page = doc.pages.find((p) => start >= p.start && start < p.end);
    if (!page) page = doc.pages.find((p) => p.page === item.page) || doc.pages[0];
    return {
      page,
      start: start - page.start,
      end: Math.min(page.end, end) - page.start,
      crossPage: end > page.end,
    };
  }
  if (item.quote) {
    const idx = (doc.full_text || '').indexOf(item.quote);
    if (idx >= 0) {
      const page = doc.pages.find((p) => idx >= p.start && idx < p.end);
      if (page) {
        return {
          page,
          start: idx - page.start,
          end: Math.min(page.end, idx + item.quote.length) - page.start,
          crossPage: idx + item.quote.length > page.end,
        };
      }
    }
    const page = doc.pages.find((p) => p.page === item.page);
    if (page) {
      const pageText = (doc.full_text || '').slice(page.start, page.end);
      const local = pageText.indexOf(item.quote);
      return {
        page,
        start: local >= 0 ? local : null,
        end: local >= 0 ? local + item.quote.length : null,
        crossPage: false,
      };
    }
  }
  if (Number.isInteger(Number(item.page))) {
    const page = doc.pages.find((p) => p.page === Number(item.page));
    if (page) return { page, start: null, end: null, crossPage: false };
  }
  return null;
}

function locateItem(item) {
  const doc = state.doc;
  if (!doc) {
    $('dual-active').textContent = '请先选择文档';
    return;
  }
  const resolved = resolveSpan(item);
  if (!resolved) {
    $('dual-active').textContent = '该条结果没有可定位的原文';
    return;
  }
  clearMarks();
  const pageEl = document.getElementById(`page-${resolved.page.page}`);
  if (!pageEl) {
    $('dual-active').textContent = '原文页未渲染';
    return;
  }
  const text = (doc.full_text || '').slice(resolved.page.start, resolved.page.end);
  const mark = renderPageHighlight(pageEl, text, resolved.start, resolved.end);
  pageEl.classList.add('is-target');
  window.setTimeout(() => pageEl.classList.remove('is-target'), 1800);

  if (mark) {
    mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
  } else {
    pageEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  const suffix = resolved.crossPage ? '（片段跨页，定位起始页）' : '';
  $('dual-active').textContent = `第 ${resolved.page.page} 页 · ${item.label || '原文'}${suffix}`;
}

/* ============================================================ 上传 */

function initUpload() {
  const input = $('file-input');
  const box = $('upload-box');
  $('btn-choose').addEventListener('click', () => input.click());
  $('doc-select').addEventListener('change', (event) => {
    if (event.target.value) selectDoc(event.target.value);
  });
  input.addEventListener('change', (event) => {
    setUploadFiles(Array.from(event.target.files || []));
  });
  if (box) {
    box.addEventListener('dragover', (event) => {
      event.preventDefault();
      box.classList.add('is-dragover');
    });
    box.addEventListener('dragleave', () => box.classList.remove('is-dragover'));
    box.addEventListener('drop', (event) => {
      event.preventDefault();
      box.classList.remove('is-dragover');
      const files = Array.from((event.dataTransfer && event.dataTransfer.files) || []);
      if (files.length) setUploadFiles(files);
    });
  }
  $('btn-upload').addEventListener('click', uploadSelected);
}

function setUploadFiles(files) {
  if ($('btn-choose').disabled) return; // 上传中不接受新的拖拽/选择
  const allowed = ['docx', 'pdf', 'txt', 'md'];
  const valid = [];
  const errors = [];
  for (const file of files) {
    const ext = (file.name.split('.').pop() || '').toLowerCase();
    if (!allowed.includes(ext)) {
      errors.push(`${file.name}：不支持 .${ext || '无扩展名'}`);
      continue;
    }
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      errors.push(`${file.name}：${fmtSize(file.size)} 超过 ${MAX_UPLOAD_MB} MB`);
      continue;
    }
    valid.push(file);
  }
  state.uploadFiles = valid;
  $('upload-progress').hidden = true;
  $('upload-bar').style.width = '0%';
  if (!valid.length) {
    $('file-name').textContent = files.length ? '没有可上传的文件' : '未选择文件';
    $('file-name').title = '';
    $('btn-upload').disabled = true;
    $('btn-upload').textContent = '上传并解析';
    if (errors.length) setNotice('upload-status', 'error', errors.join('；'));
    else setNotice('upload-status', '', '');
    return;
  }
  const names = valid.map((file) => file.name);
  $('file-name').textContent = valid.length === 1
    ? `${names[0]} · ${fmtSize(valid[0].size)}`
    : `已选 ${valid.length} 个：${names.slice(0, 3).join('、')}${names.length > 3 ? '…' : ''}`;
  $('file-name').title = names.join('\n');
  $('btn-upload').disabled = false;
  $('btn-upload').textContent = `上传并解析 (${valid.length})`;
  if (errors.length) {
    setNotice('upload-status', 'warn', `已选 ${valid.length} 个可上传文件；${errors.length} 个被跳过：${errors.join('；')}`);
  } else {
    setNotice('upload-status', 'info', `已选择 ${valid.length} 个文件，点击「上传并解析」。`);
  }
}

async function uploadSelected() {
  const files = [...(state.uploadFiles || [])];
  if (!files.length) return;
  const chooseBtn = $('btn-choose');
  const uploadBtn = $('btn-upload');
  const progress = $('upload-progress');
  const bar = $('upload-bar');
  chooseBtn.disabled = true;
  uploadBtn.disabled = true;
  uploadBtn.textContent = `解析中 0/${files.length}`;
  progress.hidden = false;
  bar.style.width = '0%';

  let ok = 0;
  let lastDocId = null;
  const failed = [];
  for (let i = 0; i < files.length; i += 1) {
    const file = files[i];
    uploadBtn.textContent = `解析中 ${i}/${files.length}`;
    setNotice('upload-status', 'info loading', `第 ${i + 1}/${files.length} 个：正在上传 ${file.name}`);
    try {
      const data = await uploadOne(file, i, files.length, (pct, phase) => {
        const done = i + (phase === 'parse' ? 1 : pct / 100);
        bar.style.width = `${Math.max(1, Math.min(100, Math.round((done / files.length) * 100)))}%`;
        const box = $('upload-status');
        if (!box) return;
        if (phase === 'parse') {
          box.textContent = `第 ${i + 1}/${files.length} 个：${file.name} 服务端解析中（扫描件约 13–16 秒）…`;
        } else {
          box.textContent = `第 ${i + 1}/${files.length} 个：正在上传 ${file.name}：${pct}%`;
        }
      });
      if (data.parse_status === 'failed') {
        failed.push(`${file.name}：解析失败（${(data.degraded || []).join('；') || '原因未给出'}）`);
      } else {
        ok += 1;
        lastDocId = data.doc_id;
      }
    } catch (err) {
      failed.push(`${file.name}：${describeError(err, '上传')}`);
    }
    uploadBtn.textContent = `解析中 ${i + 1}/${files.length}`;
  }

  if (lastDocId) await loadDocs(lastDocId);
  if (failed.length) {
    setNotice('upload-status', ok ? 'warn' : 'error', `批量解析完成：成功 ${ok}，失败 ${failed.length}。${failed.join('；')}`);
  } else {
    setNotice('upload-status', 'success', `批量解析完成：${ok} 个文件全部成功。`);
  }
  state.uploadFiles = [];
  $('file-input').value = '';
  $('file-name').textContent = '未选择文件';
  $('file-name').title = '';
  finishUpload();
}

function uploadOne(file, index, total, onProgress) {
  return new Promise((resolve, reject) => {
    const t0 = performance.now();
    let phase = 'upload';
    const timer = setInterval(() => {
      const box = $('upload-status');
      if (!box) return;
      const sec = ((performance.now() - t0) / 1000).toFixed(1);
      box.textContent = phase === 'parse'
        ? `第 ${index + 1}/${total} 个：服务端解析中…（已用时 ${sec} 秒）`
        : `第 ${index + 1}/${total} 个：正在上传 ${file.name}（已用时 ${sec} 秒）`;
    }, 500);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/upload');
    xhr.timeout = 180000;
    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      const pct = Math.max(1, Math.min(100, Math.round((event.loaded / event.total) * 100)));
      onProgress(pct, 'upload');
    };
    xhr.upload.onload = () => {
      phase = 'parse';
      onProgress(100, 'parse');
    };
    xhr.onload = () => {
      clearInterval(timer);
      let data = null;
      try { data = JSON.parse(xhr.responseText); } catch { data = { detail: xhr.responseText || `HTTP ${xhr.status}` }; }
      if (xhr.status < 200 || xhr.status >= 300) {
        const err = new Error(detailText(data && data.detail !== undefined ? data.detail : data) || `HTTP ${xhr.status}`);
        err.status = xhr.status;
        reject(err);
        return;
      }
      resolve(data);
    };
    xhr.onerror = () => {
      clearInterval(timer);
      reject(new Error('网络错误，无法连接服务；请确认容器 healthy 后重试'));
    };
    xhr.ontimeout = () => {
      clearInterval(timer);
      reject(new Error('超过 180 秒未完成；扫描件建议检查 OCR 依赖或稍后重试'));
    };
    xhr.onabort = () => {
      clearInterval(timer);
      reject(new Error('上传已取消'));
    };

    const form = new FormData();
    form.append('file', file, file.name);
    xhr.send(form);
  });
}

function finishUpload() {
  $('btn-choose').disabled = false;
  $('btn-upload').textContent = state.uploadFiles.length
    ? `上传并解析 (${state.uploadFiles.length})`
    : '上传并解析';
  $('btn-upload').disabled = !state.uploadFiles.length;
  $('upload-progress').hidden = true;
}

/* ============================================================ 评分细则 */

async function loadProfiles() {
  const box = $('profile-list');
  try {
    const data = await api('/api/scoring/profiles', { timeout: 10000 });
    state.profiles = Array.isArray(data && data.items) ? data.items : [];
  } catch (err) {
    state.profiles = [];
    box.textContent = '';
    box.append(el('p', 'empty-inline', describeError(err, '读取评分细则')));
    $('profile-hint').hidden = true;
    updateReviewAvailability();
    return;
  }
  if (!state.profiles.length) {
    box.textContent = '';
    box.append(el('p', 'empty-inline', '服务端没有可用评分细则（data/scoring/*.yaml）。'));
    updateReviewAvailability();
    return;
  }
  if (!state.profiles.some((p) => p.id === state.selectedProfileId)) {
    state.selectedProfileId = state.profiles[0].id;
  }
  renderProfiles();
  updateProfileHint();
  updateReviewAvailability();
}

function renderProfiles() {
  const box = $('profile-list');
  box.textContent = '';
  for (const profile of state.profiles) {
    const label = el('label', 'profile-card');
    label.dataset.profileId = profile.id;
    const input = el('input');
    input.type = 'radio';
    input.name = 'profile';
    input.value = profile.id;
    input.checked = profile.id === state.selectedProfileId;
    const body = el('span', 'profile-body');
    const titleRow = el('span');
    titleRow.append(el('span', 'profile-title', profile.name || profile.id), document.createTextNode(' '));
    titleRow.append(el('span', 'profile-id', profile.id || ''));
    body.append(titleRow);
    const req = profile.requirements || {};
    const parts = [];
    if (req.max_price !== undefined) parts.push(`最高限价 ${fmtMoney(req.max_price)} 元`);
    if (req.duration_days !== undefined) parts.push(`工期要求 ${req.duration_days} 天`);
    if (req.price_unit) parts.push(`报价单位 ${req.price_unit}`);
    body.append(el('span', 'profile-req', parts.length ? parts.join(' · ') : '细则未声明额外要求'));
    body.append(el('span', 'profile-foot',
      `${profile.item_count || 0} 项 · 总分 ${fmtScore(profile.total)} · 指纹 ${profile.digest || '—'}`));
    label.append(input, body);
    label.classList.toggle('is-selected', input.checked);
    input.addEventListener('change', () => selectProfile(profile.id));
    box.append(label);
  }
}

function selectProfile(profileId) {
  state.selectedProfileId = profileId;
  document.querySelectorAll('.profile-card').forEach((card) => {
    card.classList.toggle('is-selected', card.dataset.profileId === profileId);
  });
  updateProfileHint();
  updateReviewAvailability();
}

function currentProfile() {
  return state.profiles.find((p) => p.id === state.selectedProfileId) || null;
}

function updateProfileHint() {
  const hint = $('profile-hint');
  const profile = currentProfile();
  if (!profile) { hint.hidden = true; return; }
  if (state.review && state.review.profile && state.review.profile.id !== profile.id) {
    setNotice('profile-hint', 'info',
      `当前结果来自 ${state.review.profile.id}（${fmtScore(state.review.scoring.total)} 分）。已选择 ${profile.id}，点击「重新评审」后按新细则算分并显示分项差值。`);
  } else {
    setNotice('profile-hint', '', '');
  }
}

/* ============================================================ 评审 */

function initReview() {
  $('btn-review').addEventListener('click', runReview);
  $('btn-export-docx').addEventListener('click', () => exportCurrent('docx'));
  $('btn-export-pdf').addEventListener('click', () => exportCurrent('pdf'));
}

function updateReviewAvailability() {
  const btn = $('btn-review');
  if (!btn) return;
  const profile = currentProfile();
  const docOk = Boolean(state.doc && state.selectedDocId && state.doc.parse_status !== 'failed');
  const can = Boolean(docOk && state.selectedProfileId) && !state.reviewing;
  btn.disabled = !can;
  if (state.reviewing) {
    btn.textContent = '评审中…';
  } else if (state.review && profile && state.review.profile && state.review.profile.id !== profile.id) {
    btn.textContent = `用 ${profile.id} 重新评审`;
  } else if (state.review) {
    btn.textContent = '重新评审（同细则）';
  } else {
    btn.textContent = '开始评审';
  }

  $('sel-doc').textContent = state.doc
    ? `${state.doc.file_name}（${state.doc.doc_id}）`
    : (state.selectedDocId ? `${state.selectedDocId}（详情读取中）` : '未选择');
  $('sel-profile').textContent = profile ? `${profile.id} · ${profile.name}` : '—';
  $('review-timing').textContent = docOk ? '资格性 + 评分 + 风险' : (state.doc && state.doc.parse_status === 'failed' ? '解析失败，无法评审' : '选择文档与细则后可评审');
}

function clearReviewDisplay() {
  state.review = null;
  state.compare = null;
  state.evidence = [];
  $('review-result').hidden = true;
  $('review-empty').hidden = false;
  $('review-head-meta').textContent = '尚未发起评审';
  $('dual-active').textContent = '未定位';
  setNotice('score-export-status', '', '');
  $('evidence-list').textContent = '';
  $('evidence-list').append(el('p', 'empty-inline', '评审完成后，这里列出可定位的原文证据。'));
}

async function runReview() {
  if (state.reviewing) return;
  const doc = state.doc;
  const profile = currentProfile();
  if (!doc) {
    setNotice('review-status', 'error', '还没有选择文档：请先上传文件或从下拉框选择一份已解析文档。');
    return;
  }
  if (doc.parse_status === 'failed') {
    setNotice('review-status', 'error', '该文档解析失败，不能进入评审；请重新上传可解析的文件。');
    return;
  }
  if (!profile) {
    setNotice('review-status', 'error', '没有可用评分细则：请检查 /api/scoring/profiles。');
    return;
  }

  state.reviewing = true;
  updateReviewAvailability();
  const docSelect = $('doc-select');
  if (docSelect) docSelect.disabled = true;
  document.querySelectorAll("input[name='profile']").forEach((input) => { input.disabled = true; });
  const t0 = performance.now();
  const stop = startElapsedNotice('review-status', `正在按 ${profile.id} 核验资格性、计算分项得分并扫描风险`);
  try {
    const data = await api('/api/review', {
      method: 'POST',
      body: { doc_id: doc.doc_id, profile_id: profile.id },
      timeout: 30000,
    });
    const history = state.reviewsByDoc[data.doc_id] || [];
    const previous = history.length ? history[history.length - 1] : null;
    state.compare = previous && previous.profile && data.profile && previous.profile.id !== data.profile.id ? previous : null;
    if (!state.compare) {
      // 页面刷新后内存历史为空：从 /api/review 列表找同文档、不同细则的上一份结果。
      const candidate = (state.reviews || []).find((item) =>
        item.doc_id === data.doc_id && item.profile !== data.profile.id && item.review_id !== data.review_id);
      if (candidate) {
        try {
          const detail = await api(`/api/review/${encodeURIComponent(candidate.review_id)}`, { timeout: 10000 });
          if (detail && detail.profile && detail.profile.id !== data.profile.id) state.compare = detail;
        } catch (err) {
          state.compare = null;
        }
      }
    }
    history.push(data);
    state.reviewsByDoc[data.doc_id] = history;
    state.review = data;
    renderReview();
    const elapsed = ((performance.now() - t0) / 1000).toFixed(1);
    setNotice('review-status', 'success',
      `评审完成：总分 ${fmtScore(data.scoring.total)} / ${fmtScore(data.scoring.total_full)}（${data.profile.id}），${data.risks.length} 条风险命中，用时 ${elapsed} 秒。`);
    state.reportsLoaded = false;
    if (state.view === 'reports') loadReports();
  } catch (err) {
    setNotice('review-status', 'error', describeError(err, '评审'));
  } finally {
    state.reviewing = false;
    stop();
    if (docSelect) docSelect.disabled = !state.docs.length;
    document.querySelectorAll("input[name='profile']").forEach((input) => { input.disabled = false; });
    updateReviewAvailability();
  }
}

function renderReview() {
  const review = state.review;
  const doc = state.doc;
  if (!review) return;
  $('review-result').hidden = false;
  $('review-empty').hidden = true;
  $('review-head-meta').textContent =
    `${review.file_name || review.doc_id} · ${review.profile.id} · ${fmtDateTime(review.created_at)}`;

  const scoring = review.scoring;
  const qualification = review.qualification;
  const risks = Array.isArray(review.risks) ? review.risks : [];
  const high = risks.filter((r) => r.level === '高').length;
  const medium = risks.filter((r) => r.level === '中').length;
  const low = risks.filter((r) => r.level === '低').length;

  $('score-total').textContent = fmtScore(scoring.total);
  $('score-full').textContent = fmtScore(scoring.total_full);
  $('score-profile').textContent =
    `${review.profile.name || review.profile.id} · ${review.profile.id} · 细则版本 ${review.profile.version || '—'}`;
  $('score-review-id').textContent = review.review_id;
  $('score-profile-digest').textContent = review.profile.digest || '—';
  $('score-rule-digest').textContent = review.rule_digest || '—';
  $('score-page-source').textContent =
    doc && doc.page_source === 'estimated' ? '估算（可能偏 1 页）'
      : doc && doc.page_source === 'native' ? '按原文分页'
        : doc && doc.page_source === 'single' ? '单页' : '—';

  const badges = $('score-badges');
  badges.textContent = '';
  if (doc) {
    badges.append(badge(`解析 ${parseStatusLabel(doc.parse_status)}`,
      doc.parse_status === 'failed' ? 'badge-danger' : doc.parse_status === 'degraded' ? 'badge-warn' : 'badge-done'));
    if (doc.page_source === 'estimated') badges.append(badge('页码估算', 'badge-warn', 'docx 无分页符，页码按行数估算'));
    const ocr = (doc.meta && doc.meta.ocr_pages) || [];
    if (ocr.length) badges.append(badge(`OCR ${ocr.length} 页`, 'badge-info'));
  }
  badges.append(badge(qualification.counts.missing ? `资格缺失 ${qualification.counts.missing} 项` : '资格性无缺失',
    qualification.counts.missing ? 'badge-warn' : 'badge-done'));
  badges.append(badge(high ? `高风险 ${high} 条` : '无高风险', high ? 'badge-danger' : 'badge-done'));

  const counts = qualification.counts;
  $('metric-qual').textContent = `${counts.provided}/${counts.missing}`;
  $('metric-qual-note').textContent =
    `已提供 ${counts.provided} · 缺失 ${counts.missing} · 效力不足 ${counts.insufficient} · 共 ${qualification.total}`;
  $('metric-risk').textContent = String(risks.length);
  $('metric-risk-note').textContent = `高 ${high} · 中 ${medium} · 低 ${low}`;
  if (state.compare) {
    const delta = Number(scoring.total) - Number(state.compare.scoring.total);
    $('metric-delta').textContent = fmtDelta(delta);
    $('metric-delta-note').textContent =
      `${state.compare.profile.id} ${fmtScore(state.compare.scoring.total)} → ${review.profile.id} ${fmtScore(scoring.total)}`;
  } else {
    $('metric-delta').textContent = '—';
    $('metric-delta-note').textContent = '切换细则重评后显示差值';
  }

  renderQualTable(review);
  renderScoreTable(review);
  renderRiskTable(review, high, medium, low);

  $('dual-hint').textContent =
    `${qualification.items.length} 个资格项 · ${scoring.items.length} 个评分项 · ${risks.length} 条风险 · ${((doc && doc.fields) || []).length} 个字段`;
  $('dual-doc-meta').textContent = doc
    ? `${doc.file_name} · ${doc.page_count} 页${doc.page_source === 'estimated' ? ' · 页码估算' : ''}${((doc.meta && doc.meta.ocr_pages) || []).length ? ' · 含 OCR' : ''}`
    : '—';
  $('dual-active').textContent = '未定位';
  if (doc) renderPages(doc);
  state.evidence = buildEvidence(review, doc);
  state.evidenceTab = 'all';
  renderEvidence();
}

function statePill(stateValue) {
  const map = {
    provided: ['已提供', 'pill-ok'],
    insufficient: ['效力不足', 'pill-warn'],
    missing: ['缺失', 'pill-danger'],
  };
  const [text, cls] = map[stateValue] || [stateValue || '—', 'pill-neutral'];
  return el('span', `pill ${cls}`, text);
}

function levelPill(level) {
  const map = { 高: 'pill-danger', 中: 'pill-warn', 低: 'pill-info' };
  return el('span', `pill ${map[level] || 'pill-neutral'}`, `${level || '—'}风险`);
}

function addLocatorCell(td, key, label) {
  if (!key) {
    td.append(el('span', 'muted', '—'));
    return;
  }
  const btn = el('button', 'locator', '定位');
  btn.type = 'button';
  btn.title = label ? `定位到「${label}」原文` : '定位原文';
  btn.addEventListener('click', () => focusEvidence(key));
  td.append(btn);
}

function renderQualTable(review) {
  const body = $('qual-body');
  const q = review.qualification;
  body.textContent = '';
  $('qual-hint').textContent =
    `${q.counts.provided} 已提供 / ${q.counts.insufficient} 不足 / ${q.counts.missing} 缺失`;
  $('qual-note').textContent = q.note || '文本核验只判断是否提供/是否自相矛盾，不判断证件真伪。';
  if (!q.items.length) {
    const tr = el('tr');
    const td = el('td', 'empty', '没有资格性核验项');
    td.colSpan = 4;
    tr.append(td);
    body.append(tr);
    return;
  }
  for (const item of q.items) {
    const tr = el('tr');
    tr.title = `${item.title || item.item}｜${item.note || ''}`;
    const tdName = el('td');
    tdName.append(el('span', 'cell-id', item.rule_id), el('span', 'cell-title', item.item));
    tdName.append(el('span', 'cell-sub', item.note || (item.state === 'missing' ? '全文未检出，无原文可定位' : '')));
    tr.append(tdName);
    const tdState = el('td');
    tdState.append(statePill(item.state));
    tr.append(tdState);
    const tdPage = el('td');
    tdPage.append(document.createTextNode(item.page ? `第 ${item.page} 页` : '—'));
    tr.append(tdPage);
    const tdLoc = el('td');
    addLocatorCell(tdLoc, item.quote ? `qual:${item.rule_id}` : null, item.item);
    tr.append(tdLoc);
    body.append(tr);
  }
}

function renderScoreTable(review) {
  const body = $('score-body');
  const items = review.scoring.items || [];
  const compareMap = new Map(
    ((state.compare && state.compare.scoring && state.compare.scoring.items) || []).map((item) => [item.item_id, item]),
  );
  body.textContent = '';
  $('score-hint').textContent = `${items.length} 项 · 合计 ${fmtScore(review.scoring.total)} / ${fmtScore(review.scoring.total_full)}`;
  $('score-note').textContent = state.compare
    ? `当前 ${review.profile.id}；每项显示「较 ${state.compare.profile.id}」的分数变化。`
    : '扣分理由与依据随行展示；换细则后带「较上次」差值。';
  if (!items.length) {
    const tr = el('tr');
    const td = el('td', 'empty', '没有分项评分项');
    td.colSpan = 4;
    tr.append(td);
    body.append(tr);
    return;
  }
  for (const item of items) {
    const tr = el('tr');
    tr.title = `${item.reason || ''}｜依据：${item.basis || '—'}`;
    const tdName = el('td');
    tdName.append(el('span', 'cell-id', item.item_id), el('span', 'cell-title', item.name));
    const previous = compareMap.get(item.item_id);
    let sub = previous
      ? `较 ${state.compare.profile.id}：${fmtScore(previous.score)} → ${fmtScore(item.score)} 分`
      : (item.reason || '');
    if (previous && item.reason) sub += `｜${item.reason}`;
    tdName.append(el('span', 'cell-sub', sub));
    tr.append(tdName);

    const tdScore = el('td', 'cell-score');
    tdScore.append(document.createTextNode(fmtScore(item.score)));
    tdScore.append(el('small', '', ` / ${fmtScore(item.full_score)}`));
    if (previous) {
      const delta = Number(item.score) - Number(previous.score);
      if (Math.abs(delta) >= 0.005) {
        const d = el('span', `delta ${delta > 0 ? 'delta-up' : 'delta-down'}`, fmtDelta(delta));
        d.title = `较 ${state.compare.profile.id}：${fmtScore(previous.score)} → ${fmtScore(item.score)}（满分 ${fmtScore(previous.full_score)} → ${fmtScore(item.full_score)}）`;
        tdScore.append(d);
      }
    }
    tr.append(tdScore);

    const evidence = item.evidence || {};
    const tdPage = el('td');
    tdPage.append(document.createTextNode(evidence.page ? `第 ${evidence.page} 页` : '—'));
    tr.append(tdPage);
    const tdLoc = el('td');
    addLocatorCell(tdLoc, evidence.quote ? `score:${item.item_id}` : null, item.name);
    tr.append(tdLoc);
    body.append(tr);
  }
}

function renderRiskTable(review, high, medium, low) {
  const body = $('risk-body');
  const risks = Array.isArray(review.risks) ? review.risks : [];
  body.textContent = '';
  $('risk-hint').textContent = risks.length ? `${risks.length} 条命中 · 高 ${high} / 中 ${medium} / 低 ${low}` : '0 条命中';
  const notes = $('risk-notes');
  notes.textContent = '';
  if (!risks.length) {
    notes.append(el('p', '', '未命中不等于无风险：需人工核对的规则与未实现自动检测的规则不在本次命中范围内，请结合规则库人工复核。'));
  } else {
    notes.append(el('p', '', '自动命中只表示“疑似”，需人工复核；不得据此直接作出废标/不通过结论。'));
  }
  if (!risks.length) {
    const tr = el('tr');
    const td = el('td', 'empty', '本次扫描 0 条命中');
    td.colSpan = 4;
    tr.append(td);
    body.append(tr);
    return;
  }
  risks.forEach((risk, index) => {
    const tr = el('tr');
    tr.title = `${risk.title || risk.rule_id}｜${risk.reason || ''}｜依据：${risk.legal_basis || '—'}`;
    const tdRule = el('td');
    tdRule.append(el('span', 'cell-id', risk.rule_id), el('span', 'cell-title', risk.title || ''));
    if (risk.reason) tdRule.append(el('span', 'cell-sub', risk.reason));
    tr.append(tdRule);
    const tdLevel = el('td');
    tdLevel.append(levelPill(risk.level));
    tr.append(tdLevel);
    const tdPage = el('td');
    tdPage.append(document.createTextNode(risk.page ? `第 ${risk.page} 页` : '—'));
    tr.append(tdPage);
    const tdLoc = el('td');
    addLocatorCell(tdLoc, risk.quote ? `risk:${index}` : null, risk.title || risk.rule_id);
    tr.append(tdLoc);
    body.append(tr);
  });
}

/* ============================================================ 双栏证据 */

function evidenceKindMeta(kind) {
  return {
    qual: ['资格性', 'badge-info'],
    score: ['分项', 'badge-doing'],
    risk: ['风险', 'badge-danger'],
    field: ['字段', 'badge-done'],
  }[kind] || ['结果', 'badge-plan'];
}

function buildEvidence(review, doc) {
  const list = [];
  for (const item of review.qualification.items) {
    const stateText = item.state === 'provided' ? '已提供' : item.state === 'insufficient' ? '效力不足' : '缺失';
    list.push({
      kind: 'qual',
      key: `qual:${item.rule_id}`,
      label: `${item.rule_id} ${item.item}`,
      value: stateText,
      note: item.note || '',
      page: item.page,
      start: item.char_start,
      end: item.char_end,
      quote: item.quote || '',
      sort: 0,
    });
  }
  for (const item of review.scoring.items || []) {
    const ev = item.evidence || {};
    list.push({
      kind: 'score',
      key: `score:${item.item_id}`,
      label: `${item.item_id} ${item.name}`,
      value: `${fmtScore(item.score)} / ${fmtScore(item.full_score)} 分`,
      note: item.reason || '',
      page: ev.page,
      start: ev.char_start,
      end: ev.char_end,
      quote: ev.quote || '',
      sort: 1,
    });
  }
  (review.risks || []).forEach((risk, index) => {
    list.push({
      kind: 'risk',
      key: `risk:${index}`,
      label: `${risk.rule_id} ${risk.title || ''}`,
      value: `${risk.level || '—'}风险`,
      note: risk.reason || risk.legal_basis || '',
      page: risk.page,
      start: risk.char_start,
      end: risk.char_end,
      quote: risk.quote || '',
      sort: 2,
    });
  });
  for (const field of (doc && doc.fields) || []) {
    list.push({
      kind: 'field',
      key: `field:${field.name}`,
      label: field.name,
      value: field.value || '',
      note: '字段抽取（含页码与原文片段）',
      page: field.page,
      start: field.char_start,
      end: field.char_end,
      quote: field.quote || '',
      sort: 3,
    });
  }
  return list.sort((a, b) => a.sort - b.sort);
}

function renderEvidence() {
  const box = $('evidence-list');
  if (!box) return;
  const counts = { all: state.evidence.length, qual: 0, score: 0, risk: 0, field: 0 };
  for (const item of state.evidence) counts[item.kind] = (counts[item.kind] || 0) + 1;
  const labels = { all: '全部', qual: '资格性', score: '分项', risk: '风险', field: '字段' };
  document.querySelectorAll('.evtab').forEach((tab) => {
    const kind = tab.dataset.kind;
    tab.textContent = `${labels[kind] || kind} ${counts[kind] || 0}`;
    const on = kind === state.evidenceTab;
    tab.classList.toggle('is-active', on);
    tab.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  box.textContent = '';
  const items = state.evidenceTab === 'all'
    ? state.evidence
    : state.evidence.filter((item) => item.kind === state.evidenceTab);
  if (!items.length) {
    box.append(el('p', 'empty-inline', state.evidence.length ? '该分类没有可定位的原文证据。' : '评审完成后，这里列出可定位的原文证据。'));
    return;
  }
  for (const item of items) {
    const btn = el('button', 'ev-item');
    btn.type = 'button';
    btn.dataset.key = item.key;
    const [kindLabel, kindClass] = evidenceKindMeta(item.kind);
    const top = el('span', 'ev-top');
    top.append(badge(kindLabel, kindClass), el('strong', '', item.label));
    top.append(el('span', 'ev-page', item.page ? `第 ${item.page} 页` : '无页码'));
    btn.append(top);
    if (item.value) btn.append(el('span', 'ev-value', item.value));
    if (item.quote) btn.append(el('span', 'ev-quote', `「${item.quote}」`));
    if (item.note) btn.append(el('span', 'ev-note', item.note));
    btn.addEventListener('click', () => activateEvidence(item));
    box.append(btn);
  }
}

function activateEvidence(item) {
  const needsTab = state.evidenceTab !== 'all' && state.evidenceTab !== item.kind;
  if (needsTab) {
    state.evidenceTab = item.kind;
    renderEvidence();
  }
  const current = Array.from(document.querySelectorAll('#evidence-list .ev-item')).find((node) => node.dataset.key === item.key);
  document.querySelectorAll('#evidence-list .ev-item.is-active').forEach((node) => node.classList.remove('is-active'));
  if (current) {
    current.classList.add('is-active');
    current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
  locateItem(item);
}

function focusEvidence(key) {
  const item = state.evidence.find((entry) => entry.key === key);
  if (!item) return;
  activateEvidence(item);
}

function initEvidenceTabs() {
  document.querySelectorAll('.evtab').forEach((tab) => {
    tab.addEventListener('click', () => {
      state.evidenceTab = tab.dataset.kind;
      renderEvidence();
    });
  });
}

/* ============================================================ 报告中心 */

function initReports() {
  $('btn-refresh-reports').addEventListener('click', () => loadReports({ force: true }));
  $('btn-goto-review').addEventListener('click', () => setView('review'));
  $('btn-toggle-stale').addEventListener('click', () => {
    state.showStale = !state.showStale;
    renderReports();
  });
}

async function loadReports(opts = {}) {
  if (state.reportsLoaded && !opts.force && opts.silent) return;
  if (opts.force) {
    state.reportMeta.clear();
    state.reportMetaFailed.clear();
  }
  const hint = $('reports-hint');
  if (hint && !opts.silent) hint.textContent = '正在读取最近评审…';
  if (!opts.silent) setNotice('report-status', '', '');
  try {
    const data = await api('/api/review', { timeout: 15000 });
    state.reviews = Array.isArray(data && data.items) ? data.items : [];
    state.reportsLoaded = true;
  } catch (err) {
    state.reviews = [];
    state.reportsLoaded = false;
    $('reports-table-wrap').hidden = true;
    $('reports-empty').hidden = false;
    $('reports-empty').querySelector('h2').textContent = '评审列表读取失败';
    $('reports-empty').querySelector('p').textContent = describeError(err, '读取最近评审');
    $('btn-goto-review').hidden = false;
    $('btn-toggle-stale').hidden = true;
    if (hint) hint.textContent = '读取失败';
    setNotice('report-status', 'error', describeError(err, '读取最近评审'));
    return;
  }
  renderReports();
}

function renderReports() {
  const body = $('reports-body');
  const tableWrap = $('reports-table-wrap');
  const empty = $('reports-empty');
  const hint = $('reports-hint');
  const toggle = $('btn-toggle-stale');
  body.textContent = '';

  const knownDocs = new Set(state.docs.map((doc) => doc.doc_id));
  const available = state.reviews.filter((review) => knownDocs.has(review.doc_id));
  const stale = state.reviews.filter((review) => !knownDocs.has(review.doc_id));
  const source = state.showStale ? state.reviews : available;
  const shown = source.slice(0, MAX_REPORT_ROWS);

  toggle.hidden = stale.length === 0;
  toggle.textContent = state.showStale
    ? `隐藏 ${stale.length} 份不可用记录`
    : `显示 ${stale.length} 份不可用记录`;

  if (!source.length) {
    tableWrap.hidden = true;
    empty.hidden = false;
    if (!state.reviews.length) {
      empty.querySelector('h2').textContent = '还没有评审记录';
      empty.querySelector('p').textContent = '报告由评审结果生成。先去评审看板上传文件、发起一次评审。';
      hint.textContent = '共 0 份';
    } else {
      empty.querySelector('h2').textContent = '没有可生成报告的评审';
      empty.querySelector('p').textContent =
        `已有 ${stale.length} 份评审对应的文档已不存在。可点右上角「显示 ${stale.length} 份不可用记录」查看历史记录。`;
      hint.textContent = `共 ${state.reviews.length} 份 · 可生成报告 0 份`;
    }
    return;
  }

  tableWrap.hidden = false;
  empty.hidden = true;
  const latest = state.reviews[0] ? fmtDateTime(state.reviews[0].created_at) : '—';
  const staleNote = stale.length && !state.showStale ? ` · 已隐藏 ${stale.length} 份不可用` : '';
  hint.textContent = source.length > shown.length
    ? `共 ${state.reviews.length} 份 · 可生成 ${available.length} 份${staleNote} · 显示最近 ${shown.length} 份 · 最近 ${latest}`
    : `共 ${state.reviews.length} 份 · 可生成 ${available.length} 份${staleNote} · 最近 ${latest}`;

  for (const review of shown) {
    const tr = el('tr');
    tr.dataset.reviewId = review.review_id;

    const tdId = el('td');
    tdId.append(el('code', 'report-id', review.review_id));
    const msg = el('div', 'report-msg', fmtDateTime(review.created_at));
    tdId.append(msg);
    tr.append(tdId);

    const tdFile = el('td');
    tdFile.append(el('span', 'cell-title', review.file_name || '—'));
    tdFile.append(el('span', 'cell-sub', review.doc_id || '—'));
    tr.append(tdFile);

    const tdProfile = el('td');
    tdProfile.append(el('span', 'pill pill-info', review.profile || '—'));
    tr.append(tdProfile);

    const tdTotal = el('td');
    tdTotal.append(el('span', 'report-summary meta-total', '读取中…'));
    tr.append(tdTotal);

    const tdNumbers = el('td');
    tdNumbers.append(el('span', 'report-summary meta-numbers', '读取中…'));
    tr.append(tdNumbers);

    const tdFiles = el('td');
    tdFiles.append(el('span', 'report-summary meta-files', '读取中…'));
    tr.append(tdFiles);

    const tdActions = el('td');
    const actions = el('div', 'report-actions');
    const docxBtn = el('button', 'btn btn-sm', '下载 docx');
    docxBtn.type = 'button';
    docxBtn.addEventListener('click', () => downloadReport(review.review_id, 'docx', { button: docxBtn, row: tr }));
    const pdfBtn = el('button', 'btn btn-sm', '下载 pdf');
    pdfBtn.type = 'button';
    pdfBtn.addEventListener('click', () => downloadReport(review.review_id, 'pdf', { button: pdfBtn, row: tr }));
    const openBtn = el('button', 'locator', '查看评审');
    openBtn.type = 'button';
    openBtn.addEventListener('click', () => openReview(review.review_id));
    actions.append(docxBtn, pdfBtn, openBtn);
    tdActions.append(actions);
    tr.append(tdActions);

    body.append(tr);
  }

  for (const review of shown) {
    const row = Array.from(document.querySelectorAll('#reports-body tr')).find((node) => node.dataset.reviewId === review.review_id);
    if (!row) continue;
    if (state.reportMeta.has(review.review_id)) fillReportMeta(row, state.reportMeta.get(review.review_id));
    else if (!knownDocs.has(review.doc_id)) fillReportMetaMissing(row);
  }

  if (state.view === 'reports') {
    hydrateReportMeta(shown.filter((review) => knownDocs.has(review.doc_id) && !state.reportMeta.has(review.review_id) && !state.reportMetaFailed.has(review.review_id)));
  }
}

async function hydrateReportMeta(reviews) {
  const knownDocs = new Set(state.docs.map((doc) => doc.doc_id));
  await Promise.all(reviews.map(async (review) => {
    if (state.reportMeta.has(review.review_id) || state.reportMetaFailed.has(review.review_id)) return;
    const row = Array.from(document.querySelectorAll('#reports-body tr')).find((node) => node.dataset.reviewId === review.review_id);
    if (!row) return;
    if (!knownDocs.has(review.doc_id)) {
      state.reportMetaFailed.add(review.review_id);
      fillReportMetaMissing(row);
      return;
    }
    try {
      const meta = await api(`/api/report/${encodeURIComponent(review.review_id)}/meta`, { timeout: 20000 });
      state.reportMeta.set(review.review_id, meta);
      fillReportMeta(row, meta);
    } catch (err) {
      state.reportMetaFailed.add(review.review_id);
      fillReportMetaError(row, err);
    }
  }));
}

function fillReportMeta(row, meta) {
  const total = row.querySelector('.meta-total');
  const numbers = row.querySelector('.meta-numbers');
  const files = row.querySelector('.meta-files');
  const nums = meta.numbers || {};
  if (total) {
    total.textContent = '';
    total.append(el('strong', '', fmtScore(nums.total)), document.createTextNode(` / ${fmtScore(nums.total_full)}`));
  }
  if (numbers) {
    const q = nums.qualification || {};
    const insufficient = q.insufficient ? ` · 不足 ${q.insufficient}` : '';
    const total = (q.provided || 0) + (q.insufficient || 0) + (q.missing || 0);
    numbers.textContent = `资格 提供 ${q.provided || 0} / 缺失 ${q.missing || 0}${insufficient} · 风险 ${nums.risk_count || 0}`;
    numbers.title = `共 ${total} 项｜细则指纹 ${nums.profile_digest || '—'}｜规则指纹 ${nums.rule_digest || '—'}`;
  }
  if (files) {
    files.textContent = '';
    for (const fmt of ['docx', 'pdf']) {
      const info = (meta.files || {})[fmt] || { exists: false, size: 0 };
      const line = el('div', 'report-file');
      line.append(el('span', info.exists ? 'file-ok' : 'file-none', info.exists ? '●' : '○'));
      line.append(document.createTextNode(` ${fmt.toUpperCase()} ${info.exists ? fmtSize(info.size) : '未生成'}`));
      files.append(line);
    }
  }
}

function fillReportMetaError(row, err) {
  const total = row.querySelector('.meta-total');
  const numbers = row.querySelector('.meta-numbers');
  const files = row.querySelector('.meta-files');
  if (total) total.textContent = '—';
  if (numbers) numbers.textContent = '元信息不可用';
  if (files) files.textContent = '报告不可用';
  setRowMessage(row, `报告未生成/不可用：${describeError(err, '读取报告元信息')}`, 'is-error');
}

function fillReportMetaMissing(row) {
  const total = row.querySelector('.meta-total');
  const numbers = row.querySelector('.meta-numbers');
  const files = row.querySelector('.meta-files');
  if (total) total.textContent = '—';
  if (numbers) numbers.textContent = '文档已不存在';
  if (files) files.textContent = '报告不可用';
  setRowMessage(row, '报告不可用：评审对应的文档已不存在', 'is-error');
}

function setRowMessage(row, text, cls) {
  const msg = row && row.querySelector('.report-msg');
  if (!msg) return;
  msg.className = `report-msg ${cls || ''}`.trim();
  msg.textContent = text;
}

async function exportCurrent(fmt) {
  if (!state.review) return;
  const button = fmt === 'docx' ? $('btn-export-docx') : $('btn-export-pdf');
  await downloadReport(state.review.review_id, fmt, { button, statusId: 'score-export-status' });
}

async function downloadReport(reviewId, fmt, opts = {}) {
  const { button = null, row = null, statusId = 'report-status' } = opts;
  const original = button ? button.textContent : '';
  if (button) { button.disabled = true; button.textContent = '生成中…'; }
  if (row) setRowMessage(row, `正在生成 ${fmt.toUpperCase()}…`, '');
  setNotice(statusId, 'info loading', `正在生成 ${reviewId} 的 ${fmt.toUpperCase()} 报告…`);
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 120000);
  try {
    const res = await fetch(`/api/report/${encodeURIComponent(reviewId)}?format=${encodeURIComponent(fmt)}`, {
      signal: ctrl.signal,
      cache: 'no-store',
    });
    if (!res.ok) {
      const text = await res.text();
      let data = null;
      try { data = JSON.parse(text); } catch { data = text; }
      const detail = data && typeof data === 'object' && data.detail !== undefined ? data.detail : data;
      const err = new Error(detailText(detail) || `HTTP ${res.status}`);
      err.status = res.status;
      throw err;
    }
    const blob = await res.blob();
    const filename = filenameFromDisposition(res.headers.get('Content-Disposition'), `${reviewId}.${fmt}`);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);

    const message = `已下载 ${fmt.toUpperCase()}：${filename}（${fmtSize(blob.size)}）`;
    setNotice(statusId, 'success', message);
    if (row) setRowMessage(row, message, 'is-ok');
    if (row && state.reportMeta.has(reviewId)) {
      const meta = state.reportMeta.get(reviewId);
      const info = ((meta.files || {})[fmt]) || { exists: false, size: 0 };
      const updated = {
        ...meta,
        files: { ...(meta.files || {}), [fmt]: { exists: true, size: blob.size || info.size } },
      };
      state.reportMeta.set(reviewId, updated);
      fillReportMeta(row, updated);
    } else if (row) {
      refreshRowMeta(reviewId, row);
    }
  } catch (err) {
    let message;
    if (err && err.name === 'AbortError') message = `生成 ${fmt.toUpperCase()} 超时（120 秒），请稍后重试。`;
    else if (err && err.status === 404) message = `报告未生成：${err.message}。请确认评审对应的文档仍存在。`;
    else message = describeError(err, `生成 ${fmt.toUpperCase()} 报告`);
    setNotice(statusId, 'error', message);
    if (row) setRowMessage(row, message, 'is-error');
  } finally {
    clearTimeout(timer);
    if (button) { button.disabled = false; button.textContent = original || `下载 ${fmt}`; }
  }
}

async function refreshRowMeta(reviewId, row) {
  try {
    const meta = await api(`/api/report/${encodeURIComponent(reviewId)}/meta`, { timeout: 20000 });
    state.reportMeta.set(reviewId, meta);
    fillReportMeta(row, meta);
  } catch (err) {
    fillReportMetaError(row, err);
  }
}

function filenameFromDisposition(header, fallback) {
  if (!header) return fallback;
  const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (star) {
    try { return decodeURIComponent(star[1].trim().replace(/^"|"$/g, '')); } catch { return star[1]; }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1].trim() : fallback;
}

async function openReview(reviewId) {
  try {
    setNotice('report-status', 'info loading', `正在读取评审 ${reviewId}…`);
    const review = await api(`/api/review/${encodeURIComponent(reviewId)}`, { timeout: 20000 });
    const profile = state.profiles.find((p) => p.id === (review.profile && review.profile.id));
    if (profile) {
      state.selectedProfileId = profile.id;
      renderProfiles();
    }
    state.selectedDocId = review.doc_id;
    state.review = review;
    state.compare = null;
    await selectDoc(review.doc_id);
    if (state.doc) {
      state.review = review;
      renderReview();
      setNotice('report-status', 'success', `已打开评审 ${reviewId}，可在「评审看板」查看分项与原文对照。`);
      setView('review');
    } else {
      setNotice('report-status', 'error', `评审 ${reviewId} 对应的文档已不存在，无法在页面打开；报告下载也会失败。`);
    }
  } catch (err) {
    setNotice('report-status', 'error', describeError(err, '读取评审'));
  }
}

/* ============================================================ 管理员入口 / 数据管理 */

async function refreshTopbar() {
  const chip = $('chip-health');
  const health = await safe(api('/api/health', { timeout: 6000 }));
  if (!chip) return;
  if (health.ok && health.data) {
    chip.classList.remove('is-fail');
    chip.classList.add('is-ok');
    chip.textContent = '';
    chip.append(el('span', 'live-dot'), document.createTextNode('服务正常'));
    $('chip-version').textContent = `v${health.data.version || '—'}`;
    $('chip-env').textContent = `env:${health.data.env || '—'}`;
  } else {
    chip.classList.remove('is-ok');
    chip.classList.add('is-fail');
    chip.textContent = '';
    chip.append(el('span', 'live-dot'), document.createTextNode('服务不可用'));
  }
}

function showAdminLock(message = '') {
  $('status-lock').hidden = false;
  $('status-content').hidden = true;
  $('admin-data-card').hidden = true;
  if ($('admin-data-locked')) $('admin-data-locked').hidden = false;
  $('btn-admin-logout').hidden = true;
  $('btn-refresh').hidden = true;
  if (message) setNotice('admin-status', 'warn', message);
  else setNotice('admin-status', '', '');
}

function showAdminContent() {
  $('status-lock').hidden = true;
  $('status-content').hidden = false;
  $('admin-data-card').hidden = false;
  if ($('admin-data-locked')) $('admin-data-locked').hidden = true;
  $('btn-admin-logout').hidden = false;
  $('btn-refresh').hidden = false;
}

async function enterReportsAdmin() {
  if (!state.adminAuthenticated) {
    const session = await safe(api('/api/admin/session', { timeout: 6000 }));
    if (session.ok && session.data && session.data.authenticated) {
      state.adminAuthenticated = true;
      state.adminUser = session.data.user || 'admin';
    }
  }
  const lock = $('admin-data-locked');
  const card = $('admin-data-card');
  if (state.adminAuthenticated) {
    if (lock) lock.hidden = true;
    if (card) card.hidden = false;
    await loadAdminData();
  } else {
    if (lock) lock.hidden = false;
    if (card) card.hidden = true;
  }
}

async function enterStatusView() {
  if (state.adminAuthenticated) {
    showAdminContent();
    await refreshStatus({ silent: true });
    await loadAdminData();
    return;
  }
  const session = await safe(api('/api/admin/session', { timeout: 6000 }));
  if (session.ok && session.data && session.data.authenticated) {
    state.adminAuthenticated = true;
    state.adminUser = session.data.user || 'admin';
    showAdminContent();
    await refreshStatus({ silent: true });
    await loadAdminData();
    return;
  }
  showAdminLock(session.ok ? '' : `读取管理员会话失败：${session.error.message}`);
}

async function adminLogin(event) {
  event.preventDefault();
  const user = ($('admin-user').value || '').trim();
  const password = $('admin-pass').value || '';
  const btn = $('btn-admin-login');
  if (!user || !password) {
    setNotice('admin-status', 'error', '请输入管理员账号和密码。');
    return;
  }
  btn.disabled = true;
  setNotice('admin-status', 'info loading', '正在验证管理员账号…');
  try {
    const data = await api('/api/admin/login', {
      method: 'POST',
      body: { username: user, password },
      timeout: 10000,
    });
    state.adminAuthenticated = true;
    state.adminUser = data.user || user;
    $('admin-pass').value = '';
    showAdminContent();
    setNotice('admin-action-status', 'success', `管理员 ${state.adminUser} 已登录。`);
    await refreshStatus({ silent: true });
    await loadAdminData();
  } catch (err) {
    if (err.status === 401) setNotice('admin-status', 'error', '账号或密码错误。');
    else if (err.status === 503) setNotice('admin-status', 'warn', err.message);
    else setNotice('admin-status', 'error', describeError(err, '管理员登录'));
  } finally {
    btn.disabled = false;
  }
}

async function adminLogout() {
  await safe(api('/api/admin/logout', { method: 'POST', timeout: 6000 }));
  state.adminAuthenticated = false;
  state.adminUser = null;
  state.adminData = null;
  state.adminLoadSeq += 1;
  $('admin-pass').value = '';
  showAdminLock('已退出管理员。');
}

async function loadAdminData() {
  if (!state.adminAuthenticated) return;
  const seq = ++state.adminLoadSeq;
  try {
    const data = await api('/api/admin/overview', { timeout: 20000 });
    if (seq !== state.adminLoadSeq || !state.adminAuthenticated) return;
    state.adminData = data;
    state.adminSelectedDocs.clear();
    state.adminSelectedReviews.clear();
    renderAdminData();
  } catch (err) {
    if (seq !== state.adminLoadSeq) return;
    if (err.status === 401) {
      state.adminAuthenticated = false;
      showAdminLock('管理员会话已过期，请重新登录。');
      return;
    }
    setNotice('admin-action-status', 'error', describeError(err, '读取数据管理概览'));
  }
}

function parseStatePill(status) {
  if (status === 'ok') return el('span', 'pill pill-ok', '正常');
  if (status === 'degraded') return el('span', 'pill pill-warn', '降级');
  if (status === 'failed') return el('span', 'pill pill-danger', '失败');
  return el('span', 'pill pill-neutral', status || '—');
}

function adminVisibleDocs() {
  const filter = (state.adminFilter || '').trim().toLowerCase();
  return (state.adminData?.docs || []).filter((doc) =>
    !filter || `${doc.file_name || ''} ${doc.doc_id || ''}`.toLowerCase().includes(filter));
}

function adminVisibleReviews() {
  const filter = (state.adminFilter || '').trim().toLowerCase();
  return (state.adminData?.reviews || []).filter((review) =>
    !filter || `${review.review_id || ''} ${review.file_name || ''} ${review.doc_id || ''}`.toLowerCase().includes(filter));
}

function makeAdminCheckbox(checked, onChange, label) {
  const cb = document.createElement('input');
  cb.type = 'checkbox';
  cb.checked = checked;
  cb.setAttribute('aria-label', label);
  cb.addEventListener('change', onChange);
  return cb;
}

function updateAdminSelection() {
  const docCount = state.adminSelectedDocs.size;
  const reviewCount = state.adminSelectedReviews.size;
  const docBtn = $('btn-batch-delete-docs');
  const reviewBtn = $('btn-batch-delete-reviews');
  if (docBtn) {
    docBtn.textContent = `删除所选文档 (${docCount})`;
    docBtn.disabled = docCount === 0;
  }
  if (reviewBtn) {
    reviewBtn.textContent = `删除所选评审 (${reviewCount})`;
    reviewBtn.disabled = reviewCount === 0;
  }
  const docs = adminVisibleDocs();
  const reviews = adminVisibleReviews();
  const docAll = $('admin-doc-select-all');
  const reviewAll = $('admin-review-select-all');
  if (docAll) {
    const picked = docs.filter((doc) => state.adminSelectedDocs.has(doc.doc_id));
    docAll.disabled = docs.length === 0;
    docAll.checked = docs.length > 0 && picked.length === docs.length;
    docAll.indeterminate = picked.length > 0 && picked.length < docs.length;
  }
  if (reviewAll) {
    const picked = reviews.filter((review) => state.adminSelectedReviews.has(review.review_id));
    reviewAll.disabled = reviews.length === 0;
    reviewAll.checked = reviews.length > 0 && picked.length === reviews.length;
    reviewAll.indeterminate = picked.length > 0 && picked.length < reviews.length;
  }
}

function renderAdminData() {
  const data = state.adminData;
  if (!data) return;
  const counts = data.counts || {};
  $('admin-summary').textContent =
    `文档 ${counts.docs || 0} · 评审 ${counts.reviews || 0} · 报告 ${counts.reports || 0} 个 / ${fmtSize(counts.report_bytes || 0)} · 上传文件 ${counts.uploads || 0}`;

  const docIds = new Set((data.docs || []).map((doc) => doc.doc_id));
  const reviewIds = new Set((data.reviews || []).map((review) => review.review_id));
  state.adminSelectedDocs = new Set([...state.adminSelectedDocs].filter((id) => docIds.has(id)));
  state.adminSelectedReviews = new Set([...state.adminSelectedReviews].filter((id) => reviewIds.has(id)));

  const docs = adminVisibleDocs();
  const docBody = $('admin-doc-body');
  docBody.textContent = '';
  $('admin-doc-count').textContent = `共 ${docs.length} 份`;
  if (!docs.length) {
    const tr = el('tr');
    const td = el('td', 'admin-empty', (state.adminFilter || '').trim() ? '没有匹配的文档' : '暂无文档');
    td.colSpan = 6;
    tr.append(td);
    docBody.append(tr);
  }
  for (const doc of docs) {
    const tr = el('tr');
    const selected = state.adminSelectedDocs.has(doc.doc_id);
    if (selected) tr.classList.add('is-selected');
    const tdCheck = el('td', 'check-cell');
    tdCheck.append(makeAdminCheckbox(selected, (event) => {
      if (event.target.checked) state.adminSelectedDocs.add(doc.doc_id);
      else state.adminSelectedDocs.delete(doc.doc_id);
      renderAdminData();
    }, `选择文档 ${doc.file_name || doc.doc_id}`));
    tr.append(tdCheck);
    tr.append(el('td', 'admin-file', doc.file_name || '—'));
    tr.append(el('td', '', doc.doc_id || '—'));
    tr.append(el('td', '', `${doc.page_count || '—'} 页`));
    const tdState = el('td');
    tdState.append(parseStatePill(doc.parse_status));
    tr.append(tdState);
    const tdAction = el('td');
    const del = el('button', 'btn btn-sm btn-danger', '删除');
    del.type = 'button';
    del.title = `删除文档 ${doc.file_name || doc.doc_id} 及其评审/报告`;
    del.addEventListener('click', () => adminDeleteDoc(doc));
    tdAction.append(del);
    tr.append(tdAction);
    docBody.append(tr);
  }

  const reviews = adminVisibleReviews();
  const reviewBody = $('admin-review-body');
  reviewBody.textContent = '';
  $('admin-review-count').textContent = `共 ${reviews.length} 份`;
  if (!reviews.length) {
    const tr = el('tr');
    const td = el('td', 'admin-empty', (state.adminFilter || '').trim() ? '没有匹配的评审' : '暂无评审');
    td.colSpan = 6;
    tr.append(td);
    reviewBody.append(tr);
  }
  for (const review of reviews) {
    const tr = el('tr');
    const selected = state.adminSelectedReviews.has(review.review_id);
    if (selected) tr.classList.add('is-selected');
    const tdCheck = el('td', 'check-cell');
    tdCheck.append(makeAdminCheckbox(selected, (event) => {
      if (event.target.checked) state.adminSelectedReviews.add(review.review_id);
      else state.adminSelectedReviews.delete(review.review_id);
      renderAdminData();
    }, `选择评审 ${review.review_id}`));
    tr.append(tdCheck);
    const tdId = el('td');
    tdId.append(el('code', 'report-id', review.review_id || '—'));
    tdId.append(el('span', 'cell-sub', fmtDateTime(review.created_at)));
    tr.append(tdId);
    tr.append(el('td', 'admin-file', review.file_name || '—'));
    tr.append(el('td', '', fmtScore(review.total)));
    const tdFiles = el('td');
    const reports = review.reports || {};
    const docx = reports.docx || { exists: false, size: 0 };
    const pdf = reports.pdf || { exists: false, size: 0 };
    tdFiles.append(el('div', `report-file ${docx.exists ? 'file-ok' : 'file-none'}`, `DOCX ${docx.exists ? fmtSize(docx.size) : '未生成'}`));
    tdFiles.append(el('div', `report-file ${pdf.exists ? 'file-ok' : 'file-none'}`, `PDF ${pdf.exists ? fmtSize(pdf.size) : '未生成'}`));
    tr.append(tdFiles);
    const tdActions = el('td');
    const actions = el('div', 'admin-actions');
    if (docx.exists || pdf.exists) {
      const delReport = el('button', 'btn btn-sm btn-danger', '删报告');
      delReport.type = 'button';
      delReport.title = '只删 docx/pdf，保留评审，可重新生成';
      delReport.addEventListener('click', () => adminDeleteReport(review));
      actions.append(delReport);
    }
    const delReview = el('button', 'btn btn-sm btn-danger', '删评审');
    delReview.type = 'button';
    delReview.title = '删除评审 JSON 及其报告，不可恢复';
    delReview.addEventListener('click', () => adminDeleteReview(review));
    actions.append(delReview);
    tdActions.append(actions);
    tr.append(tdActions);
    reviewBody.append(tr);
  }

  updateAdminSelection();
}

async function adminDeleteDoc(doc) {
  const label = doc.file_name || doc.doc_id;
  if (!window.confirm(`删除文档「${label}」（${doc.doc_id}）？\n相关评审与报告会一并删除，不可恢复。`)) return;
  await runAdminAction(`/api/admin/doc/${encodeURIComponent(doc.doc_id)}`, 'DELETE', `已删除文档 ${label}`, true);
}

async function adminDeleteReview(review) {
  const label = review.review_id || '';
  if (!window.confirm(`删除评审「${label}」及其 docx/pdf 报告？不可恢复。`)) return;
  await runAdminAction(`/api/admin/review/${encodeURIComponent(label)}`, 'DELETE', `已删除评审 ${label}`, false);
}

async function adminDeleteReport(review) {
  const label = review.review_id || '';
  if (!window.confirm(`只删除「${label}」的 docx/pdf 报告？评审结果保留，可重新生成。`)) return;
  await runAdminAction(`/api/admin/report/${encodeURIComponent(label)}`, 'DELETE', `已删除报告 ${label}`, false);
}

async function adminBatchDelete(kind) {
  const ids = kind === 'doc'
    ? [...state.adminSelectedDocs]
    : [...state.adminSelectedReviews];
  if (!ids.length) return;
  const label = kind === 'doc' ? `所选 ${ids.length} 份文档` : `所选 ${ids.length} 份评审`;
  const extra = kind === 'doc'
    ? '\n文档的评审与报告会一并删除，不可恢复。'
    : '\n评审的 docx/pdf 报告会一并删除，不可恢复。';
  if (!window.confirm(`批量删除${label}？${extra}`)) return;
  await runAdminAction(
    '/api/admin/batch-delete',
    'POST',
    `已批量删除${label}`,
    kind === 'doc',
    kind === 'doc' ? { doc_ids: ids } : { review_ids: ids },
  );
}

async function adminCleanup(mode) {
  const text = mode === 'duplicates'
    ? '按文件名分组，每组只保留最新 1 份文档，删除其余文档及其评审/报告。\n该操作不可恢复，确定继续？'
    : '删除所有「对应文档已不存在」的评审与其报告。\n该操作不可恢复，确定继续？';
  if (!window.confirm(text)) return;
  await runAdminAction('/api/admin/cleanup', 'POST', '清理完成', false, { mode });
}

async function runAdminAction(url, method, successText, refreshDocs, body) {
  const status = $('admin-action-status');
  setNotice('admin-action-status', 'info loading', '正在执行管理操作…');
  try {
    const data = await api(url, {
      method,
      body,
      timeout: 30000,
    });
    const details = [];
    if (data.deleted_docs !== undefined) details.push(`文档 ${data.deleted_docs}`);
    if (data.deleted_reviews !== undefined) details.push(`评审 ${data.deleted_reviews}`);
    if (data.deleted_reports !== undefined) details.push(`报告 ${data.deleted_reports}`);
    setNotice('admin-action-status', 'info loading', '管理操作完成，正在刷新列表…');
    if (refreshDocs) await loadDocs();
    await loadAdminData();
    await loadReports({ force: true });
    setNotice('admin-action-status', 'success', `${successText}${details.length ? `（${details.join(' / ')}）` : ''}。`);
    if (state.review && !state.reviews.some((r) => r.review_id === state.review.review_id)) {
      // 当前评审被删除时，避免继续展示旧结果
      const stillExists = await safe(api(`/api/review/${encodeURIComponent(state.review.review_id)}`, { timeout: 8000 }));
      if (!stillExists.ok) clearReviewDisplay();
    }
  } catch (err) {
    if (err.status === 401) {
      state.adminAuthenticated = false;
      showAdminLock('管理员会话已过期，请重新登录。');
      return;
    }
    setNotice('admin-action-status', 'error', describeError(err, '管理操作'));
  }
}

/* ============================================================ 系统状态 */

const STATUS_TEXT = { done: '已完成', doing: '进行中', planned: '计划中' };
const STATUS_CLASS = { done: 'badge-done', doing: 'badge-doing', planned: 'badge-plan' };

async function refreshStatus(opts = {}) {
  const btn = $('btn-refresh');
  if (btn && !opts.silent) btn.disabled = true;
  const [h, ah, info] = await Promise.all([
    safe(api('/health', { timeout: 6000 })),
    safe(api('/api/health', { timeout: 6000 })),
    safe(api('/api/info', { timeout: 6000 })),
  ]);

  const chip = $('chip-health');
  if (h.ok || ah.ok) {
    chip.classList.remove('is-fail');
    chip.classList.add('is-ok');
    chip.textContent = '';
    chip.append(el('span', 'live-dot'), document.createTextNode('服务正常'));
  } else {
    chip.classList.remove('is-ok');
    chip.classList.add('is-fail');
    chip.textContent = '';
    chip.append(el('span', 'live-dot'), document.createTextNode('服务不可用'));
  }

  const bodyH = h.ok ? h.data : {};
  const bodyAh = ah.ok ? ah.data : {};
  const bodyInfo = info.ok ? info.data : {};
  const app = bodyInfo.app || {};

  $('chip-version').textContent = `v${app.version || bodyAh.version || '—'}`;
  $('chip-env').textContent = `env:${app.env || bodyAh.env || '—'}`;

  const rows = [
    {
      name: 'GET /health 返回 200 且 status=ok',
      ok: h.ok && h.data && h.data.status === 'ok',
      detail: h.ok ? `HTTP 200 · ${h.data.service || '—'}` : `连接失败：${h.error.message}`,
    },
    {
      name: 'GET /api/health 返回 200 且含能力开关',
      ok: ah.ok && ah.data && ah.data.status === 'ok' && Boolean(ah.data.capabilities),
      detail: ah.ok ? `能力 ${Object.keys(ah.data.capabilities || {}).length} 项` : `连接失败：${ah.error.message}`,
    },
    {
      name: 'GET /api/info 返回版本、里程碑与免责声明',
      ok: info.ok && Boolean(app.version) && Boolean(bodyInfo.milestones),
      detail: info.ok ? `HTTP 200 · 错误 ${((bodyInfo.errors) || []).length} 项` : `连接失败：${info.error.message}`,
    },
    {
      name: '版本号单一来源一致（VERSION = 接口返回）',
      ok: Boolean(bodyAh.version) && bodyAh.version === app.version,
      detail: bodyAh.version ? `v${bodyAh.version}` : '无版本号',
    },
    {
      name: '配置文件可解析（agent.json / milestones.json）',
      ok: info.ok && Array.isArray(bodyInfo.errors) && bodyInfo.errors.length === 0,
      detail: info.ok && bodyInfo.errors && bodyInfo.errors.length ? bodyInfo.errors.join('；') : '无缺失',
    },
    {
      name: '免责声明在页面顶部逐字渲染',
      ok: ($('disclaimer-text')?.textContent || '') === DISCLAIMER,
      detail: '文案一致',
    },
  ];

  renderChecks(rows);
  renderRuntime(bodyAh, app);
  renderPlatform(bodyInfo.agent || {}, (bodyAh.capabilities) || {});
  renderMilestones(bodyInfo.milestones || null);
  $('check-stamp').textContent = rows.every((row) => row.ok)
    ? `最近检测 ${fmtDateTime(new Date().toISOString())} · 每 15 秒自动复检`
    : `自检未全部通过（${rows.filter((row) => row.ok).length}/${rows.length}）`;
  if (btn) btn.disabled = false;
}

function renderChecks(rows) {
  const list = $('check-list');
  list.textContent = '';
  for (const row of rows) {
    const li = el('li', `check-row ${row.ok ? 'is-pass' : 'is-fail'}`);
    li.append(el('span', 'dot'), el('span', 'check-name', row.name), el('span', 'check-detail', row.detail || ''));
    list.append(li);
  }
}

function renderRuntime(health, app) {
  $('k-service').textContent = health.service || '—';
  $('k-version').textContent = app.version || health.version || '—';
  $('k-env').textContent = app.env || health.env || '—';
  $('k-started').textContent = (health.started_at || '—').replace('T', ' ').slice(0, 19);
  $('k-uptime').textContent = fmtUptime(health.uptime_seconds);
  $('k-container').textContent = health.in_container ? '是（Docker）' : '否（本地直跑）';
}

function fmtUptime(sec) {
  const n = Number(sec);
  if (!Number.isFinite(n) || n < 0) return '—';
  if (n < 60) return `${n} 秒`;
  const m = Math.floor(n / 60);
  if (m < 60) return `${m} 分 ${n % 60} 秒`;
  const h = Math.floor(m / 60);
  return `${h} 小时 ${m % 60} 分`;
}

function renderPlatform(agent, caps = {}) {
  if (!agent || !agent.configured) {
    $('k-mcp-tools').textContent = '0';
    $('k-skill').textContent = '0';
    $('k-kb').textContent = 'agent.json 未就绪';
    $('mcp-value-label').textContent = '个已登记';
    $('badge-mcp').textContent = '待接入';
    $('badge-mcp').className = 'badge badge-todo';
    $('badge-skill').textContent = '待接入';
    $('badge-skill').className = 'badge badge-todo';
    $('badge-kb').textContent = '待接入';
    $('badge-kb').className = 'badge badge-todo';
    $('platform-hint').textContent = '配置未就绪';
    return;
  }
  const tools = agent.mcp_tools || [];
  const mcpLive = Boolean(caps.mcp) && tools.length > 0;
  $('k-mcp-tools').textContent = String(tools.length);
  $('mcp-value-label').textContent = mcpLive ? '个已接入' : '个已登记';
  $('badge-mcp').textContent = mcpLive
    ? `已接入 ${tools.length} 个工具`
    : (tools.length ? '已登记 · 待挂载' : '待接入');
  $('badge-mcp').className = mcpLive ? 'badge badge-done' : 'badge badge-todo';

  const skills = agent.skills || [];
  $('k-skill').textContent = String(skills.length);
  $('skill-value-label').textContent = caps.skills ? '个已挂载' : '个已登记';
  if (caps.skills) {
    $('badge-skill').textContent = `已挂载 ${skills.length} 个`;
    $('badge-skill').className = 'badge badge-done';
  } else {
    $('badge-skill').textContent = skills.length ? '已登记 · 待挂载' : '待接入';
    $('badge-skill').className = 'badge badge-todo';
  }
  if (agent.kb_index_ready) {
    $('k-kb').textContent = `索引已配置（${agent.kb_index_count} 个）`;
    $('badge-kb').textContent = '已就绪';
    $('badge-kb').className = 'badge badge-done';
  } else {
    $('k-kb').textContent = agent.kb_index_count ? `索引名待替换（${agent.kb_index_count} 个占位）` : '索引未配置';
    $('badge-kb').textContent = '待接入';
    $('badge-kb').className = 'badge badge-todo';
  }
  $('platform-hint').textContent = mcpLive
    ? `MCP 已接入 ${tools.length} 个工具${caps.skills ? ` · Skill 已挂载 ${skills.length} 个` : ''}`
    : '登记 ≠ 可用';
}

function renderMilestones(ms) {
  if (!ms || !Array.isArray(ms.items)) {
    $('ms-hint').textContent = '里程碑数据未就绪';
    $('ms-body').textContent = '';
    const tr = el('tr');
    const td = el('td', 'empty', '无法读取 milestones.json');
    td.colSpan = 5;
    tr.append(td);
    $('ms-body').append(tr);
    renderDeliverables([]);
    return;
  }
  $('ms-hint').textContent = `当前进度 ${ms.current || '—'} · 更新于 ${ms.updated || '—'}`;
  const body = $('ms-body');
  body.textContent = '';
  for (const item of ms.items) {
    const tr = el('tr');
    tr.append(el('td', '', item.id), el('td', '', item.name), el('td', 'col-day', item.day));
    const tdStatus = el('td');
    tdStatus.append(badge(STATUS_TEXT[item.status] || item.status, STATUS_CLASS[item.status] || 'badge-plan'));
    tr.append(tdStatus, el('td', 'col-target', item.target));
    body.append(tr);
  }
  renderDeliverables((ms.stage && ms.stage.items) || []);
  if (ms.stage && ms.stage.label) {
    $('stage-label').textContent = `${ms.stage.label} · 已完成 ${(ms.stage.items || []).length} 项`;
  }
}

function renderDeliverables(items) {
  const list = $('deliver-list');
  list.textContent = '';
  if (!items.length) {
    list.append(el('li', 'empty', '暂无交付记录'));
    return;
  }
  for (const item of items) {
    const li = el('li');
    li.append(el('span', 'tick', '✓'), el('span', '', item.item), el('code', '', item.path));
    list.append(li);
  }
}

/* ============================================================ 启动 */

function initGlobalActions() {
  $('btn-refresh').addEventListener('click', () => refreshStatus());
  $('btn-admin-logout').addEventListener('click', adminLogout);
  $('admin-login-form').addEventListener('submit', adminLogin);
  $('btn-admin-refresh').addEventListener('click', () => loadAdminData());
  $('admin-doc-filter').addEventListener('input', (event) => {
    state.adminFilter = event.target.value || '';
    state.adminSelectedDocs.clear();
    state.adminSelectedReviews.clear();
    renderAdminData();
  });
  $('admin-doc-select-all').addEventListener('change', (event) => {
    const docs = adminVisibleDocs();
    if (event.target.checked) docs.forEach((doc) => state.adminSelectedDocs.add(doc.doc_id));
    else docs.forEach((doc) => state.adminSelectedDocs.delete(doc.doc_id));
    renderAdminData();
  });
  $('admin-review-select-all').addEventListener('change', (event) => {
    const reviews = adminVisibleReviews();
    if (event.target.checked) reviews.forEach((review) => state.adminSelectedReviews.add(review.review_id));
    else reviews.forEach((review) => state.adminSelectedReviews.delete(review.review_id));
    renderAdminData();
  });
  $('btn-batch-delete-docs').addEventListener('click', () => adminBatchDelete('doc'));
  $('btn-batch-delete-reviews').addEventListener('click', () => adminBatchDelete('review'));
  $('btn-clean-duplicates').addEventListener('click', () => adminCleanup('duplicates'));
  $('btn-clean-orphans').addEventListener('click', () => adminCleanup('orphan_reviews'));
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && state.view === 'status' && state.adminAuthenticated) {
      refreshStatus({ silent: true });
    }
  });
}

document.addEventListener('DOMContentLoaded', () => {
  initNav();
  initUpload();
  initReview();
  initReports();
  initEvidenceTabs();
  initGlobalActions();

  const initial = (location.hash || '').replace(/^#/, '') || 'review';
  setView(initial, { updateHash: false });
  refreshTopbar(); // 顶栏健康状态先出，不阻塞文档列表
  (async () => {
    await Promise.all([loadProfiles(), loadDocs()]);
    await loadReports();
    if (state.view === 'reports') hydrateReportMeta(state.reviews.slice(0, MAX_REPORT_ROWS));
  })();

  setInterval(() => {
    if (state.view === 'status' && state.adminAuthenticated) refreshStatus({ silent: true });
  }, 15000);
});
