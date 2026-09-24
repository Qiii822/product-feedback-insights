const $ = (sel) => document.querySelector(sel);

const SEVERITY_LABEL = { low: "低", medium: "中", high: "高", critical: "严重" };
const TREND_LABEL = { rising: "上升", falling: "下降", stable: "稳定", new: "新增" };
const FACTOR_LABEL = { severity: "严重度", volume: "量", growth: "增长", breadth: "广度" };

function setStatus(msg, isError = false, loading = false) {
  const el = $("#status");
  el.textContent = msg;
  el.className = "status" + (isError ? " error" : "") + (loading ? " loading" : "");
  const banner = $("#errorBanner");
  banner.hidden = !isError;
  if (isError) banner.textContent = "⚠️ " + msg;
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
    setStatus(`已重置并摄取 ${result.added} 条反馈${result.invalid ? `（${result.invalid} 条无效）` : ""}`);
    await loadFeedback();
  } catch (e) {
    setStatus("摄取失败：" + e.message, true);
  }
}

async function handleSample() {
  setStatus("正在载入示例数据…", false, true);
  try {
    const result = await postJSON("/api/load_sample", {});
    setStatus(`已重置并载入示例数据：${result.added} 条反馈`);
    await loadFeedback();
  } catch (e) {
    setStatus("载入失败：" + e.message, true);
  }
}

async function handleRun() {
  setStatus("正在运行完整分析（含 LLM 调用，约需 30~60 秒）…", false, true);
  ["#runBtn", "#ingestBtn", "#sampleBtn"].forEach((s) => ($(s).disabled = true));
  try {
    const data = await postJSON("/api/run", {});
    if (data.feedback_count === 0) {
      setStatus("还没有反馈数据，请先上传或载入示例数据", true);
      return;
    }
    render(data);
    setStatus("分析完成 ✓");
  } catch (e) {
    setStatus("分析失败：" + e.message, true);
  } finally {
    ["#runBtn", "#ingestBtn", "#sampleBtn"].forEach((s) => ($(s).disabled = false));
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
  const steps = opp.action_items && opp.action_items.length
    ? `<div class="opp-block"><h4>建议步骤</h4><ol class="opp-list">${opp.action_items.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ol></div>`
    : "";
  const metrics = opp.success_metrics && opp.success_metrics.length
    ? `<div class="opp-block"><h4>如何验证</h4><ul class="opp-list">${opp.success_metrics.map((s) => `<li>${escapeHtml(s)}</li>`).join("")}</ul></div>`
    : "";
  el.innerHTML = `
    <div class="opp-title">💡 Top 产品机会</div>
    <h3>${escapeHtml(opp.title)}</h3>
    ${opp.summary ? `<p class="opp-summary">${escapeHtml(opp.summary)}</p>` : ""}
    <div class="opp-reco">${escapeHtml(opp.recommendation)}</div>
    ${steps}
    ${metrics}
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
  const evidence = countEvidence(p.evidence || []);
  const trend = p.trend || {};
  const trendBadge = trend.direction
    ? `<span class="badge trend-${trend.direction}">${TREND_LABEL[trend.direction] || trend.direction}${trend.direction === "rising" || trend.direction === "falling" ? ` ${trend.growth_pct > 0 ? "+" : ""}${trend.growth_pct}%` : ""}</span>`
    : "";
  const s = p.sentiment || {};
  const rated = s.negative + s.neutral + s.positive;
  const sentimentText = rated
    ? `<div class="card-sentiment">情绪：负 ${s.negative} · 中 ${s.neutral} · 正 ${s.positive}${s.unknown ? ` · 未知 ${s.unknown}` : ""}</div>`
    : "";
  const versions = p.affected_versions && p.affected_versions.length
    ? `<span>版本 ${p.affected_versions.join(", ")}</span>`
    : "";
  const factors = p.priority_factors || [];
  const breakdown = factors.length && p.priority_score
    ? `<div class="card-score">为什么排这里：${factors.map((f) => `${FACTOR_LABEL[f.name] || f.name} ${f.contribution.toFixed(2)}`).join(" + ")} = ${p.priority_score.toFixed(2)}</div>`
    : "";
  const diag = p.diagnosis;
  const diagHtml = diag
    ? `<div class="card-diagnosis">
        ${diag.facts && diag.facts.length ? `<div class="diag-row diag-facts"><span class="diag-label">事实</span><ul>${diag.facts.map((f) => `<li>${escapeHtml(f)}</li>`).join("")}</ul></div>` : ""}
        ${diag.hypotheses && diag.hypotheses.length ? `<div class="diag-row diag-hypo"><span class="diag-label">假设</span><ul>${diag.hypotheses.map((h) => `<li>${escapeHtml(h)}</li>`).join("")}</ul></div>` : ""}
        ${diag.unknowns && diag.unknowns.length ? `<div class="diag-row diag-unknown"><span class="diag-label">未知</span><ul>${diag.unknowns.map((u) => `<li>${escapeHtml(u)}</li>`).join("")}</ul></div>` : ""}
      </div>`
    : "";
  return `
    <div class="card">
      <div class="card-head">
        ${p.rank ? `<span class="rank">#${p.rank}</span>` : `<span class="rank review">复核</span>`}
        <h3 class="card-title">${escapeHtml(p.title)}</h3>
        <span class="badge severity-${sev}">${SEVERITY_LABEL[sev] || sev}</span>
        <span class="badge category">${p.category || "?"}</span>
        ${trendBadge}
      </div>
      ${p.description ? `<p class="card-desc">${escapeHtml(p.description)}</p>` : ""}
      <div class="card-meta">
        <span>证据 ${p.evidence_count} 条 · 占比 ${p.volume_pct != null ? p.volume_pct : "—"}%</span>
        <span>cohesion ${p.cohesion.toFixed(2)}</span>
        ${p.priority_score ? `<span>score ${p.priority_score.toFixed(3)}</span>` : ""}
        ${p.affected_segments && p.affected_segments.length ? `<span>平台 ${p.affected_segments.join(", ")}</span>` : ""}
        ${versions}
      </div>
      ${sentimentText}
      ${breakdown}
      ${diagHtml}
      ${evidence.length ? `<div class="evidence-label">证据表现</div><ul class="evidence">${evidence.map((e) => `<li>${escapeHtml(e.text)}${e.count > 1 ? `<span class="count">×${e.count}</span>` : ""}</li>`).join("")}</ul>` : ""}
    </div>`;
}

function countEvidence(texts) {
  const counts = {};
  texts.forEach((t) => (counts[t] = (counts[t] || 0) + 1));
  return Object.entries(counts)
    .map(([text, count]) => ({ text, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 6);
}

async function handleEvaluate() {
  const btn = $("#evalBtn");
  const status = $("#evalStatus");
  btn.disabled = true;
  status.textContent = "正在运行分类评估（真实 LLM 约 30~60 秒）…";
  status.className = "status loading";
  try {
    const data = await postJSON("/api/evaluate", {});
    renderQuality(data);
    status.textContent = `评估完成 · model ${data.model} · ${data.n} 条用例`;
    status.className = "status";
  } catch (e) {
    status.textContent = "评估失败：" + e.message;
    status.className = "status error";
  } finally {
    btn.disabled = false;
  }
}

function renderQuality(r) {
  const el = $("#qualityResult");
  el.hidden = false;
  const recall = r.needs_review_recall == null ? "—" : r.needs_review_recall.toFixed(3);
  const stats = [
    { label: "Accuracy", value: (r.accuracy * 100).toFixed(1) + "%" },
    { label: "Macro F1", value: r.macro_f1.toFixed(3) },
    { label: "Issue Type Acc", value: (r.issue_type_accuracy * 100).toFixed(1) + "%" },
    { label: "Needs Review Rate", value: (r.needs_review_rate * 100).toFixed(1) + "%" },
    { label: "Needs Review 召回", value: recall },
    { label: "ECE", value: r.calibration.ece.toFixed(3) },
  ];
  const statHtml = stats
    .map((s) => `<div class="stat"><div class="stat-value">${s.value}</div><div class="stat-label">${s.label}</div></div>`)
    .join("");

  const rows = Object.entries(r.per_category)
    .map(([cat, prf]) => {
      const [p, rec, f1] = prf;
      return `<tr><td>${cat}</td><td>${p.toFixed(2)}</td><td>${rec.toFixed(2)}</td><td>${f1.toFixed(2)}</td></tr>`;
    })
    .join("");

  const rel = (r.calibration.reliability || [])
    .filter((b) => b.n > 0)
    .map((b) => {
      const accPct = (b.accuracy * 100).toFixed(0);
      const confPct = (b.confidence * 100).toFixed(0);
      return `<div class="rel-row">
        <div class="rel-label">${b.range}<span class="rel-n">n=${b.n}</span></div>
        <div class="rel-bar">
          <div class="rel-fill" style="width:${accPct}%"></div>
          <div class="rel-marker" style="left:${confPct}%" title="confidence ${b.confidence}"></div>
        </div>
        <div class="rel-values">acc ${b.accuracy.toFixed(2)} · conf ${b.confidence.toFixed(2)}</div>
      </div>`;
    })
    .join("");

  el.innerHTML = `
    <div class="summary">${statHtml}</div>
    <div class="q-block">
      <h3>每类表现（precision / recall / F1）</h3>
      <table class="q-table"><thead><tr><th>category</th><th>P</th><th>R</th><th>F1</th></tr></thead><tbody>${rows}</tbody></table>
    </div>
    <div class="q-block">
      <h3>可靠性曲线（置信度分桶 vs 实际准确率）</h3>
      <div class="rel">${rel}</div>
      <p class="q-note">绿色条 = 实际准确率，竖线 = 模型自评置信度。竖线在条右 → 过度自信；在条左 → 过于谨慎。</p>
    </div>`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

$("#ingestBtn").addEventListener("click", handleIngest);
$("#sampleBtn").addEventListener("click", handleSample);
$("#runBtn").addEventListener("click", handleRun);
$("#evalBtn").addEventListener("click", handleEvaluate);
loadFeedback();
