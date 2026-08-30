const $ = (sel) => document.querySelector(sel);

const SEVERITY_LABEL = { low: "低", medium: "中", high: "高", critical: "严重" };

function setStatus(msg, isError = false) {
  const el = $("#status");
  el.textContent = msg;
  el.className = "status" + (isError ? " error" : "");
}

async function postJSON(url, body) {
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.detail || resp.statusText);
  return data;
}

async function handleIngest() {
  const file = $("#fileInput").files[0];
  if (!file) {
    setStatus("请先选择一个 CSV / JSON 文件", true);
    return;
  }
  setStatus("正在摄取…");
  try {
    const content = await file.text();
    const result = await postJSON("/api/ingest", { filename: file.name, content });
    setStatus(`摄取完成：${result.added} 新增 / ${result.skipped_duplicates} 去重 / ${result.invalid} 无效`);
    await loadFeedback();
  } catch (e) {
    setStatus("摄取失败：" + e.message, true);
  }
}

async function handleRun() {
  setStatus("正在运行完整分析（含 LLM 调用，约需 30~60 秒）…");
  $("#runBtn").disabled = true;
  try {
    const data = await postJSON("/api/run", {});
    render(data);
    setStatus("分析完成 ✓");
  } catch (e) {
    setStatus("分析失败：" + e.message, true);
  } finally {
    $("#runBtn").disabled = false;
  }
}

async function loadFeedback() {
  try {
    const items = await (await fetch("/api/feedback")).json();
    $("#feedbackList").innerHTML = items
      .map(
        (i) =>
          `<div class="feedback-item"><span class="fb-platform">${i.platform || "?"}</span>` +
          `<span class="fb-text">${escapeHtml(i.raw_text)}</span></div>`
      )
      .join("");
  } catch (e) {
    /* ignore */
  }
}

function render(data) {
  renderSummary(data);
  renderOpportunity(data.opportunity);
  renderProblems(data.problems);
  renderCandidates(data.candidates);
  if (data.feedback_count) loadFeedback();
}

function renderSummary(data) {
  const cards = [
    { label: "反馈总数", value: data.feedback_count },
    { label: "已确认问题", value: data.problems.length },
    { label: "候选问题", value: data.candidates.length },
    { label: "other（不参与聚类）", value: `${data.other.count}（${data.other.percentage.toFixed(1)}%）` },
  ];
  const el = $("#summary");
  el.hidden = false;
  const run = data.run
    ? `<div class="run-info">run ${data.run.run_id.slice(0, 8)} · ${data.run.latency_ms}ms · ${data.run.total_tokens} tokens · ${data.run.model}</div>`
    : "";
  el.innerHTML = cards
    .map((c) => `<div class="stat"><div class="stat-value">${c.value}</div><div class="stat-label">${c.label}</div></div>`)
    .join("") + run;
}

function renderOpportunity(opp) {
  const el = $("#opportunity");
  if (!opp) {
    el.hidden = true;
    return;
  }
  el.hidden = false;
  el.innerHTML = `
    <div class="opp-title">💡 Top 产品机会</div>
    <h3>${escapeHtml(opp.title)}</h3>
    <div class="opp-reco">${escapeHtml(opp.recommendation)}</div>
    ${opp.expected_impact ? `<div class="opp-impact">预期影响：${escapeHtml(opp.expected_impact)}</div>` : ""}
    <div class="opp-meta">引用证据 ${opp.evidence_count} 条</div>`;
}

function renderProblems(problems) {
  const section = $("#problems");
  if (!problems.length) {
    section.hidden = true;
    return;
  }
  section.hidden = false;
  $("#problemList").innerHTML = problems.map(problemCard).join("");
}

function renderCandidates(candidates) {
  const section = $("#candidates");
  if (!candidates.length) {
    section.hidden = true;
    return;
  }
  section.hidden = false;
  $("#candidateList").innerHTML = candidates.map(problemCard).join("");
}

function problemCard(p) {
  const sev = p.severity || "unknown";
  return `
    <div class="card">
      <div class="card-head">
        ${p.rank ? `<span class="rank">#${p.rank}</span>` : `<span class="rank review">复核</span>`}
        <h3 class="card-title">${escapeHtml(p.title)}</h3>
        <span class="badge severity-${sev}">${SEVERITY_LABEL[sev] || sev}</span>
        <span class="badge category">${p.category || "?"}</span>
      </div>
      <div class="card-meta">
        <span>证据 ${p.evidence_count} 条</span>
        <span>cohesion ${p.cohesion.toFixed(2)}</span>
        ${p.priority_score ? `<span>score ${p.priority_score.toFixed(3)}</span>` : ""}
        ${p.affected_segments && p.affected_segments.length ? `<span>平台 ${p.affected_segments.join(", ")}</span>` : ""}
      </div>
      <ul class="evidence">
        ${p.evidence.slice(0, 6).map((e) => `<li>${escapeHtml(e)}</li>`).join("")}
        ${p.evidence.length > 6 ? `<li class="more">… 共 ${p.evidence.length} 条</li>` : ""}
      </ul>
    </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

$("#ingestBtn").addEventListener("click", handleIngest);
$("#runBtn").addEventListener("click", handleRun);
loadFeedback();
