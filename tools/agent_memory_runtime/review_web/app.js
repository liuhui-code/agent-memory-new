"use strict";

const $ = (id) => document.getElementById(id);
const kinds = {semantic: "语义事实", reflection: "反思经验", episode: "任务经历", "code-file": "代码文件", "code-symbol": "代码符号", "code-log": "日志索引"};
const statuses = {active: "有效", stale: "已过期", merged: "已合并", rejected: "已拒绝", archived: "已归档", indexed: "来源索引"};
const views = {library: ["记忆库", "记忆，有迹可循。", "把不断积累的知识，整理成值得信任的记忆。"], pending: ["待审查", "让记忆，值得信任。", "尚未人工审查的有效与过期记忆，等你逐条核对。"], archived: ["归档区", "给过时的记忆，一个去处。", "归档内容不参与常规记忆检索。可恢复为有效，或备份后永久删除。"]};
const labels = {fact: "事实内容", task: "任务", summary: "内容摘要", lesson: "经验教训", future_rule: "未来规则", mistake: "曾经的问题", source: "来源", scope: "适用范围", evidence: "依据", problem: "问题", outcome: "结果", file_path: "文件路径", symbol: "符号", symbol_type: "符号类型", signature: "签名", message_template: "日志模板", raw_statement: "原始语句", function: "所属函数", business_summary: "业务摘要", confidence: "置信度", created_at: "创建时间", updated_at: "更新时间", reviewed_at: "人工审查时间", stale_reason: "过期原因", use_count: "使用次数", last_used_at: "最近使用", importance: "重要性", category: "分类"};
const actionInfo = {review: ["标记已审查", "check"], archive: ["归档", "archive"], restore: ["恢复为有效", "restore"], delete: ["永久删除", "trash"]};
const state = {view: "library", kind: "all", filter: "all", page: 0, cursors: [""], next: null, items: [], selected: new Map(), token: "", active: null, load: 0, detailLoad: 0, busy: false, pendingAction: null};
let searchTimer, toastTimer, controller;
const inspectorEmpty = $("inspector").innerHTML;

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const use = document.createElementNS(svg.namespaceURI, "use");
  use.setAttribute("href", `#i-${name}`);
  svg.setAttribute("aria-hidden", "true");
  svg.append(use);
  return svg;
}
const keyOf = (item) => `${item.kind}:${item.id}`;
const number = (value) => Number(value).toLocaleString("zh-CN");
function date(value, full = false) {
  const parsed = new Date(value);
  return !value ? "—" : Number.isNaN(parsed.getTime()) ? String(value) : parsed.toLocaleString("zh-CN", full ? {hour12: false} : {year: "numeric", month: "2-digit", day: "2-digit"});
}
function toast(message, error = false) {
  clearTimeout(toastTimer);
  $("toast").textContent = message;
  $("toast").className = `toast${error ? " error" : ""}`;
  $("toast").hidden = false;
  toastTimer = setTimeout(() => { $("toast").hidden = true; }, 4500);
}
function notice(message, error = false) {
  $("notice").replaceChildren(node("span", "", message));
  if (message) {
    const close = node("button", "icon-button");
    close.setAttribute("aria-label", "关闭提示");
    close.append(icon("close"));
    close.addEventListener("click", () => { $("notice").hidden = true; });
    $("notice").append(close);
  }
  $("notice").className = `notice${error ? " error" : ""}`;
  $("notice").hidden = !message;
}
async function api(path, options = {}) {
  let response;
  try { response = await fetch(path, {cache: "no-store", ...options}); }
  catch (error) {
    if (error.name === "AbortError") throw error;
    throw new Error("无法连接本地工作台。请确认终端中的 review-ui 仍在运行。");
  }
  const payload = await response.json();
  if (!response.ok) {
    const error = new Error(payload.error || "操作失败，请刷新后重试。");
    error.status = response.status;
    throw error;
  }
  return payload;
}
function statusBadge(item) {
  const value = item.is_stale && item.status === "active" ? "stale" : item.status;
  return node("span", `status ${value}`, statuses[value] || value);
}
function renderTypes(counts) {
  $("type-nav").replaceChildren();
  if (!$("kind-filter").options.length) {
    for (const [kind, label] of Object.entries({all: "全部类型", ...kinds})) {
      const option = node("option", "", label);
      option.value = kind;
      $("kind-filter").append(option);
    }
  }
  for (const [kind, label] of Object.entries(kinds)) {
    const button = node("button", `type-item${state.kind === kind ? " active" : ""}`);
    button.append(node("i", "type-dot"), node("span", "", label), node("b", "", number(counts[kind] || 0)));
    button.dataset.kind = kind;
    button.addEventListener("click", () => changeKind(kind));
    $("type-nav").append(button);
  }
}
async function loadOverview() {
  const data = await api("/api/session");
  state.token = data.token;
  $("project-name").textContent = data.project_name;
  $("project-name").title = data.project_path;
  $("archive-path").textContent = data.db_path;
  $("archive-path").title = data.db_path;
  for (const [suffix, value] of Object.entries({total: data.total, pending: data.pending, archived: data.archived})) {
    $(`metric-${suffix}`).textContent = number(value);
    $(`nav-${suffix}`).textContent = number(value);
  }
  renderTypes(data.counts);
  $("connection").textContent = "已连接本地记忆库";
  $("connection").className = "connection";
}
function clearDetail() {
  state.detailLoad++;
  state.active = null;
  $("inspector").classList.remove("has-detail");
  $("inspector").innerHTML = inspectorEmpty;
  for (const row of document.querySelectorAll(".record-row.opened")) row.classList.remove("opened");
}
function resetPage() {
  state.page = 0;
  state.cursors = [""];
  state.selected.clear();
  clearDetail();
}
function listMessage(title, body, symbol = "search") {
  const message = node("div", "list-message");
  message.append(icon(symbol), node("strong", "", title), node("p", "", body));
  $("record-list").replaceChildren(message);
}
function syncSelection() {
  const eligible = state.items.filter((item) => item.editable);
  $("select-page").disabled = !eligible.length || state.busy;
  $("select-page").checked = eligible.length > 0 && state.selected.size === eligible.length;
  $("select-page").indeterminate = state.selected.size > 0 && state.selected.size < eligible.length;
  $("bulk-bar").hidden = !state.selected.size;
  $("selection-count").textContent = `已选 ${state.selected.size} 条`;
  $("bulk-actions").replaceChildren();
  const selected = [...state.selected.values()];
  if (selected.length) addActions($("bulk-actions"), selected, true);
  for (const row of document.querySelectorAll(".record-row")) row.classList.toggle("selected", state.selected.has(row.dataset.key));
}
function renderList() {
  $("record-list").replaceChildren();
  if (!state.items.length) {
    const archive = state.view === "archived";
    listMessage(archive ? "归档区，空空如也。" : "这里还没有匹配的记忆。", archive ? "归档后的记忆会出现在这里。调整筛选条件也许能找到你需要的记录。" : "试试其他关键词或筛选条件；新记忆由原有学习与反思流程写入。", archive ? "archive" : "search");
  }
  for (const item of state.items) {
    const row = node("article", `record-row${state.active === keyOf(item) ? " opened" : ""}`);
    row.dataset.key = keyOf(item);
    const checkbox = node("input");
    checkbox.type = "checkbox";
    checkbox.disabled = !item.editable;
    checkbox.setAttribute("aria-label", `选择${kinds[item.kind]} #${item.id}`);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) state.selected.set(keyOf(item), item);
      else state.selected.delete(keyOf(item));
      syncSelection();
    });
    const open = node("button", "record-open");
    const topline = node("div", "record-topline");
    topline.append(node("span", "kind-label", kinds[item.kind]), node("span", "record-id", `#${String(item.id).padStart(4, "0")}`));
    open.append(topline, node("div", "record-title", item.title));
    if (item.preview !== item.title) open.append(node("div", "record-preview", item.preview));
    if (item.source) open.append(node("div", "record-source", item.source));
    open.addEventListener("click", () => showDetail(item));
    const meta = node("div", "record-meta");
    meta.append(statusBadge(item), node("time", "record-time", date(item.timestamp)));
    if (typeof item.confidence === "number") meta.append(node("span", `status${item.confidence < .6 ? " low" : ""}`, `置信 ${Math.round(item.confidence * 100)}%`));
    if (item.reviewed_at) meta.append(node("span", "review-mark", "✓ 已审查"));
    row.append(checkbox, open, meta);
    $("record-list").append(row);
  }
  syncSelection();
}
async function loadList() {
  const load = ++state.load;
  if (controller) controller.abort();
  controller = new AbortController();
  state.selected.clear();
  state.items = [];
  syncSelection();
  $("record-list").setAttribute("aria-busy", "true");
  $("previous").disabled = $("next").disabled = true;
  $("record-list").replaceChildren(...[1, 2, 3].map(() => node("div", "skeleton")));
  const params = new URLSearchParams({kind: state.kind, view: state.view === "archived" ? "archived" : state.filter === "all" ? state.view : state.filter, q: $("search").value.trim(), status: $("status-filter").value, order: $("order").value, limit: $("page-size").value, cursor: state.cursors[state.page]});
  try {
    const data = await api(`/api/records?${params}`, {signal: controller.signal});
    if (load !== state.load) return;
    state.items = data.items;
    state.next = data.next_cursor;
    $("result-count").textContent = `${number(data.total)} 条匹配`;
    $("page-label").textContent = `第 ${state.page + 1} 页`;
    $("previous").disabled = state.page === 0;
    $("next").disabled = !state.next;
    renderList();
    $("record-list").scrollTop = 0;
  } catch (error) {
    if (error.name === "AbortError" || load !== state.load) return;
    $("result-count").textContent = "读取失败";
    listMessage("暂时无法读取记忆", error.message, "file");
    const retry = node("button", "button secondary", "重新加载");
    retry.addEventListener("click", () => refresh());
    $("record-list").firstChild.append(retry);
  } finally {
    if (load === state.load) $("record-list").setAttribute("aria-busy", "false");
  }
}
function changeView(view) {
  state.view = view;
  state.kind = "all";
  state.filter = "all";
  $("kind-filter").value = "all";
  $("search").value = "";
  $("status-filter").value = "all";
  $("status-filter").disabled = view === "archived";
  const [name, title, description] = views[view];
  $("breadcrumb").textContent = name;
  $("page-title").textContent = title;
  $("page-description").textContent = description;
  for (const button of document.querySelectorAll("[data-view]")) button.classList.toggle("active", button.dataset.view === view);
  syncFilters();
  resetPage();
  loadList();
}
function changeKind(kind) {
  state.kind = kind;
  $("kind-filter").value = kind;
  syncFilters();
  resetPage();
  loadList();
}
function syncFilters() {
  for (const button of document.querySelectorAll("[data-kind]")) button.classList.toggle("active", button.dataset.kind === state.kind);
  for (const button of document.querySelectorAll("[data-filter]")) {
    button.classList.toggle("active", button.dataset.filter === state.filter);
    button.disabled = state.view === "archived";
  }
}
function addSection(target, label, value, mono = false) {
  if (value === null || value === undefined || value === "") return;
  const section = node("section", "detail-section");
  section.append(node("h3", "detail-label", label), node("p", `detail-value${mono ? " mono" : ""}`, typeof value === "object" ? JSON.stringify(value, null, 2) : String(value)));
  target.append(section);
}
async function showDetail(item) {
  const request = ++state.detailLoad;
  state.active = keyOf(item);
  $("inspector").classList.add("has-detail");
  $("inspector").replaceChildren(node("div", "skeleton"));
  for (const row of document.querySelectorAll(".record-row")) row.classList.toggle("opened", row.dataset.key === state.active);
  try {
    const record = await api(`/api/records/${item.kind}/${item.id}`);
    if (request !== state.detailLoad) return;
    const header = node("div", "detail-header");
    const close = node("button", "icon-button");
    close.setAttribute("aria-label", "关闭详情");
    close.append(icon("close"));
    close.addEventListener("click", clearDetail);
    header.append(node("span", "", "记忆详情 / RECORD DETAIL"), close);
    const content = node("div", "detail-content");
    content.append(node("span", "eyebrow", `${kinds[record.kind]} · #${record.id}`), node("h2", "", record.title));
    const badges = node("div", "detail-badges");
    badges.append(statusBadge(record));
    if (typeof record.confidence === "number") badges.append(node("span", `status${record.confidence < .6 ? " low" : ""}`, `置信度 ${Math.round(record.confidence * 100)}%`));
    content.append(badges);
    const primary = ["fact", "summary", "lesson", "future_rule", "mistake", "problem", "evidence", "source", "scope", "file_path", "signature", "message_template", "raw_statement", "business_summary", "stale_reason"];
    for (const field of primary) addSection(content, labels[field] || field, record.fields[field], ["file_path", "signature", "raw_statement"].includes(field));
    addSection(content, "创建 / 索引时间", date(record.timestamp, true));
    addSection(content, "人工审查时间", record.reviewed_at ? date(record.reviewed_at, true) : "尚未人工审查");
    const extra = node("details", "detail-details");
    extra.append(node("summary", "", "查看全部原始字段"));
    for (const [field, value] of Object.entries(record.fields)) addSection(extra, labels[field] || field, value, true);
    content.append(extra);
    if (record.truncated_fields.length) content.append(node("p", "detail-value warning", `部分超长字段仅展示前 64,000 字：${record.truncated_fields.join("、")}`));
    const actions = node("div", "detail-actions");
    if (record.editable) addActions(actions, [record]);
    else actions.append(node("p", "detail-readonly", "此记录由源码学习生成，仅供查看。请通过原有 learn / refresh 流程更新索引。"));
    $("inspector").replaceChildren(header, content, actions);
    close.focus({preventScroll: true});
  } catch (error) {
    if (request !== state.detailLoad) return;
    clearDetail();
    toast(error.message, true);
  }
}
function addActions(target, records, compact = false) {
  const archived = records.every((item) => item.status === "archived");
  const names = archived ? ["restore", "delete"] : ["review", "archive"];
  for (const action of names) {
    if (action === "review" && records.some((item) => !["active", "stale"].includes(item.status))) continue;
    const [label, symbol] = actionInfo[action];
    const button = node("button", `button ${action === "delete" ? "subtle-danger" : action === "review" || action === "restore" ? "primary" : "secondary"}`);
    if (!compact) button.append(icon(symbol));
    button.append(document.createTextNode(label));
    button.disabled = state.busy;
    button.addEventListener("click", () => action === "review" ? perform(action, records) : confirmAction(action, records));
    target.append(button);
  }
}
function confirmAction(action, records) {
  state.pendingAction = {action, records: [...records]};
  const destructive = action === "delete";
  $("dialog-icon").replaceChildren(icon(actionInfo[action][1]));
  $("dialog-icon").className = `dialog-icon${destructive ? " destructive" : ""}`;
  $("dialog-title").textContent = `${actionInfo[action][0]}这 ${records.length} 条记忆？`;
  $("dialog-description").textContent = destructive ? "将先备份当前 SQLite，再从库中永久删除所选记录和直接图关系。此操作无法在界面中撤销；备份、历史引用及旧 Vault 镜像仍会保留。" : action === "archive" ? "归档后，这些记忆将退出常规记忆检索。内容仍然保留，你可以在归档区重新审查并恢复。" : "这些记忆将重新设为有效，并标记为已人工审查。恢复前请确认内容仍适用于当前项目。";
  $("dialog-records").replaceChildren(...records.map((item) => node("li", "", `${kinds[item.kind]} #${item.id} · ${item.title}`)));
  $("delete-confirmation").hidden = !destructive;
  $("confirmation").value = "";
  $("dialog-error").hidden = true;
  $("dialog-submit").textContent = actionInfo[action][0];
  $("dialog-submit").className = `button ${destructive ? "danger" : "primary"}`;
  $("dialog-submit").disabled = destructive;
  $("action-dialog").showModal();
  (destructive ? $("confirmation") : $("dialog-cancel")).focus();
}
async function perform(action, records, inDialog = false) {
  if (state.busy) return;
  state.busy = true;
  $("dialog-submit").disabled = true;
  $("dialog-cancel").disabled = $("dialog-close").disabled = true;
  for (const button of document.querySelectorAll(".detail-actions button, .bulk-bar button")) button.disabled = true;
  try {
    const result = await api("/api/actions", {method: "POST", headers: {"Content-Type": "application/json", "X-Review-Token": state.token}, body: JSON.stringify({action, records: records.map(({kind, id, version}) => ({kind, id, version})), confirmation: $("confirmation").value})});
    if (inDialog) $("action-dialog").close();
    resetPage();
    toast(`已${actionInfo[action][0]} ${result.changed} 条记忆`);
    if (result.vault_refresh_required) notice(`${result.backup_path ? `删除前备份：${result.backup_path}。` : ""}SQLite 已更新；现有 Obsidian 镜像需通过 vault-export 重新导出。`);
    await refresh(false);
  } catch (error) {
    const message = error.status === 409 ? `${error.message} 可点击右上角刷新后重试。` : error.message;
    if (inDialog) { $("dialog-error").textContent = message; $("dialog-error").hidden = false; }
    else toast(message, true);
  } finally {
    state.busy = false;
    $("dialog-cancel").disabled = $("dialog-close").disabled = false;
    $("dialog-submit").disabled = action === "delete" && $("confirmation").value !== "永久删除";
    for (const button of document.querySelectorAll(".detail-actions button, .bulk-bar button")) button.disabled = false;
    syncSelection();
  }
}
async function refresh(reset = true) {
  if (reset) resetPage();
  $("refresh").disabled = true;
  try { await loadOverview(); await loadList(); }
  catch (error) { notice(error.message, true); $("connection").textContent = "连接中断"; $("connection").className = "connection offline"; listMessage("无法连接记忆库", error.message, "file"); }
  finally { $("refresh").disabled = false; }
}

for (const button of document.querySelectorAll("[data-view]")) button.addEventListener("click", () => changeView(button.dataset.view));
for (const button of document.querySelectorAll("[data-metric]")) button.addEventListener("click", () => changeView(button.dataset.metric));
for (const button of document.querySelectorAll("[data-filter]")) button.addEventListener("click", () => { state.filter = button.dataset.filter; syncFilters(); resetPage(); loadList(); });
$("kind-filter").addEventListener("change", () => changeKind($("kind-filter").value));
$("search").addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => { resetPage(); loadList(); }, 280); });
for (const id of ["status-filter", "order", "page-size"]) $(id).addEventListener("change", () => { resetPage(); loadList(); });
$("refresh").addEventListener("click", () => refresh());
$("select-page").addEventListener("change", () => { for (const item of state.items.filter((item) => item.editable)) { if ($("select-page").checked) state.selected.set(keyOf(item), item); else state.selected.delete(keyOf(item)); } renderList(); for (const input of $("record-list").querySelectorAll("input")) input.checked = state.selected.has(input.closest("article").dataset.key); });
$("clear-selection").addEventListener("click", () => { state.selected.clear(); renderList(); });
$("next").addEventListener("click", () => { if (!state.next) return; state.cursors[++state.page] = state.next; clearDetail(); loadList(); });
$("previous").addEventListener("click", () => { if (state.page === 0) return; state.page--; clearDetail(); loadList(); });
for (const id of ["dialog-cancel", "dialog-close"]) $(id).addEventListener("click", () => $("action-dialog").close());
$("action-dialog").addEventListener("cancel", (event) => { if (state.busy) event.preventDefault(); });
$("confirmation").addEventListener("input", () => { $("dialog-submit").disabled = state.busy || $("confirmation").value !== "永久删除"; });
$("dialog-submit").addEventListener("click", () => { if (state.pendingAction) perform(state.pendingAction.action, state.pendingAction.records, true); });
document.addEventListener("keydown", (event) => {
  if (event.key === "/" && !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName) && !$("action-dialog").open) { event.preventDefault(); $("search").focus(); }
  if (event.key === "Escape" && !$("action-dialog").open) clearDetail();
});
refresh();
