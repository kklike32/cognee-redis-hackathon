const state = {
  pending: [],
  wiki: "",
};

const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").split("\n");
  return lines
    .map((line) => {
      if (line.startsWith("# ")) return `<h1>${escapeHtml(line.slice(2))}</h1>`;
      if (line.startsWith("## ")) return `<h2>${escapeHtml(line.slice(3))}</h2>`;
      if (line.startsWith("### ")) return `<h3>${escapeHtml(line.slice(4))}</h3>`;
      if (line.startsWith("- ")) return `<li>${escapeHtml(line.slice(2))}</li>`;
      if (!line.trim()) return "<br />";
      return `<p>${escapeHtml(line)}</p>`;
    })
    .join("");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || payload.message || "Request failed");
  }
  return payload;
}

async function loadState() {
  const payload = await api("/api/state");
  state.pending = payload.pending || [];
  state.wiki = payload.wiki || "";
  renderRedis(payload.redis || {});
  renderPending();
  renderWiki();
}

function renderRedis(redis) {
  const node = $("#redisStatus");
  node.textContent = redis.ok ? "Redis connected" : "Redis unavailable: no-cache mode";
  node.className = `status ${redis.ok ? "ok" : "warn"}`;
}

function renderMetrics(payload) {
  $("#briefMetrics").innerHTML = `
    <div class="metric"><strong>Cache</strong>${escapeHtml(payload.cache_status || "unknown")}</div>
    <div class="metric"><strong>Latency</strong>${escapeHtml(payload.latency_ms || 0)} ms</div>
    <div class="metric"><strong>Sources</strong>${(payload.sources || []).length}</div>
    <div class="metric"><strong>Owner</strong>${escapeHtml((payload.metadata || {}).Owner || "CI")}</div>
  `;
}

function renderPending() {
  const list = $("#pendingList");
  if (!state.pending.length) {
    list.innerHTML = `<p class="markdown empty">No pending changes. Run Wiki Intake to generate proposals.</p>`;
    return;
  }

  list.innerHTML = state.pending
    .map((change) => {
      const disabled = change.status !== "pending" ? "disabled" : "";
      return `
        <article class="pendingCard" data-id="${escapeHtml(change.id)}">
          <h3>${escapeHtml(change.id)}</h3>
          <div class="pendingMeta">
            <span class="pill">${escapeHtml(change.competitor)}</span>
            <span class="pill ${escapeHtml(change.priority)}">${escapeHtml(change.priority)}</span>
            <span class="pill">${escapeHtml(change.proposed_section)}</span>
            <span class="pill ${escapeHtml(change.status)}">${escapeHtml(change.status)}</span>
          </div>
          <p><strong>Source:</strong> <code>${escapeHtml(change.source_citation)}</code></p>
          <textarea ${disabled}>${escapeHtml(change.proposed_text)}</textarea>
          <div class="actions">
            <button class="primary approveBtn" ${disabled}>Approve</button>
            <button class="rejectBtn" ${disabled}>Reject</button>
          </div>
        </article>
      `;
    })
    .join("");

  document.querySelectorAll(".approveBtn").forEach((button) => {
    button.addEventListener("click", approveSelected);
  });
  document.querySelectorAll(".rejectBtn").forEach((button) => {
    button.addEventListener("click", rejectSelected);
  });
}

function renderWiki() {
  $("#wikiOutput").innerHTML = renderMarkdown(state.wiki);
}

async function generateBrief() {
  const payload = await api("/api/brief", {
    method: "POST",
    body: JSON.stringify({
      competitor: $("#competitorSelect").value,
      deal_context: $("#dealContext").value,
    }),
  });
  renderMetrics(payload);
  $("#briefOutput").classList.remove("empty");
  $("#briefOutput").innerHTML = renderMarkdown(payload.brief);
}

async function generatePending() {
  const payload = await api("/api/pending/generate", {
    method: "POST",
    body: JSON.stringify({ competitor: $("#competitorSelect").value }),
  });
  $("#intakeResult").textContent = JSON.stringify(payload, null, 2);
  await loadState();
}

async function approveSelected(event) {
  const card = event.target.closest(".pendingCard");
  const id = card.dataset.id;
  const editedText = card.querySelector("textarea").value;
  await api(`/api/pending/${encodeURIComponent(id)}/approve`, {
    method: "POST",
    body: JSON.stringify({ edited_text: editedText }),
  });
  await loadState();
}

async function rejectSelected(event) {
  const card = event.target.closest(".pendingCard");
  const id = card.dataset.id;
  await api(`/api/pending/${encodeURIComponent(id)}/reject`, { method: "POST" });
  await loadState();
}

async function resetDemo() {
  await api("/api/reset", { method: "POST" });
  $("#briefOutput").classList.add("empty");
  $("#briefOutput").textContent = "Generate a brief to see AE guidance.";
  $("#briefMetrics").innerHTML = "";
  $("#intakeResult").textContent = "No intake run yet.";
  await loadState();
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((item) => item.classList.remove("active"));
    tab.classList.add("active");
    $(`#${tab.dataset.panel}`).classList.add("active");
  });
});

$("#generateBriefBtn").addEventListener("click", () => generateBrief().catch(alert));
$("#generatePendingBtn").addEventListener("click", () => generatePending().catch(alert));
$("#refreshBtn").addEventListener("click", () => loadState().catch(alert));
$("#resetBtn").addEventListener("click", () => resetDemo().catch(alert));

loadState().catch((error) => {
  $("#redisStatus").textContent = error.message;
});
