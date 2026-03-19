/* =============================================
   RAG Assistant – frontend logic
   ============================================= */

const API = "";   // same origin; update if backend is on a different host

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------
function showTab(tabId, btnEl) {
  document.querySelectorAll(".tab-panel").forEach(p => (p.style.display = "none"));
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.getElementById(tabId).style.display = "block";
  btnEl.classList.add("active");

  if (tabId === "docs-tab") loadDocuments();
  if (tabId === "metrics-tab") loadMetrics();
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------
function handleChatKey(event) {
  if (event.key === "Enter" && event.ctrlKey) sendQuestion();
}

async function sendQuestion() {
  const input = document.getElementById("question-input");
  const question = input.value.trim();
  if (!question) return;

  appendUserMessage(question);
  input.value = "";

  const loadingEl = appendLoadingMessage();

  try {
    const res = await fetch(`${API}/rag/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: 5 }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }

    const data = await res.json();
    loadingEl.remove();
    appendBotMessage(data);
  } catch (err) {
    loadingEl.remove();
    appendErrorMessage(`Error: ${err.message}`);
  }
}

function appendUserMessage(text) {
  const box = document.getElementById("chat-messages");
  const el = document.createElement("div");
  el.className = "msg msg-user";
  el.textContent = text;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

function appendLoadingMessage() {
  const box = document.getElementById("chat-messages");
  const el = document.createElement("div");
  el.className = "msg msg-loading";
  el.textContent = "⏳ Thinking…";
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

function appendErrorMessage(text) {
  const box = document.getElementById("chat-messages");
  const el = document.createElement("div");
  el.className = "msg msg-bot";
  el.style.borderColor = "#e07070";
  el.style.background = "#fff5f5";
  el.textContent = "⚠️ " + text;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

function appendBotMessage(data) {
  const box = document.getElementById("chat-messages");

  const el = document.createElement("div");
  el.className = "msg msg-bot";

  // Answer text
  const answerEl = document.createElement("div");
  answerEl.className = "msg-answer";
  answerEl.textContent = data.answer;
  el.appendChild(answerEl);

  // Sources
  if (data.sources && data.sources.length > 0) {
    const details = document.createElement("details");
    details.className = "msg-sources";
    const summary = document.createElement("summary");
    summary.textContent = `📎 ${data.sources.length} source(s) used`;
    details.appendChild(summary);

    data.sources.forEach((src, i) => {
      const chip = document.createElement("span");
      chip.className = "source-chip";
      chip.textContent = `${src.filename} #${src.chunk_index + 1}`;
      details.appendChild(chip);

      const excerpt = document.createElement("div");
      excerpt.className = "source-excerpt";
      const preview = src.text.length > 200 ? src.text.slice(0, 200) + "…" : src.text;
      excerpt.textContent = preview;
      details.appendChild(excerpt);
    });
    el.appendChild(details);
  }

  // Feedback row
  el.appendChild(buildFeedbackRow(data.interaction_id));

  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
}

function buildFeedbackRow(interactionId) {
  const row = document.createElement("div");
  row.className = "msg-feedback";
  row.dataset.voted = "";

  const likeBtn = document.createElement("button");
  likeBtn.className = "btn-feedback";
  likeBtn.textContent = "👍 Like";
  likeBtn.onclick = () => handleVote(interactionId, "like", row);

  const dislikeBtn = document.createElement("button");
  dislikeBtn.className = "btn-feedback";
  dislikeBtn.textContent = "👎 Dislike";
  dislikeBtn.onclick = () => handleVote(interactionId, "dislike", row);

  const commentToggle = document.createElement("button");
  commentToggle.className = "btn-feedback";
  commentToggle.textContent = "💬 Comment";
  commentToggle.onclick = () => toggleCommentArea(row);

  row.appendChild(likeBtn);
  row.appendChild(dislikeBtn);
  row.appendChild(commentToggle);

  // Comment area (hidden by default)
  const commentArea = document.createElement("div");
  commentArea.className = "feedback-comment-area";

  const textarea = document.createElement("textarea");
  textarea.placeholder = "Add a comment about this response…";
  commentArea.appendChild(textarea);

  const submitBtn = document.createElement("button");
  submitBtn.className = "btn-comment-submit";
  submitBtn.textContent = "Submit comment";
  submitBtn.onclick = () => submitComment(interactionId, textarea, row);
  commentArea.appendChild(submitBtn);

  // Append comment area after the row (we'll place it inside the parent msg)
  row.dataset.interactionId = interactionId;
  row._commentArea = commentArea;  // store reference

  return row;
}

function toggleCommentArea(row) {
  // Insert comment area after row if not already in DOM
  const area = row._commentArea;
  if (!area) return;
  if (!area.parentElement) {
    row.parentElement.insertBefore(area, row.nextSibling);
  }
  const visible = area.style.display === "block";
  area.style.display = visible ? "none" : "block";
}

async function handleVote(interactionId, vote, rowEl) {
  if (rowEl.dataset.voted) return;  // already voted

  try {
    await fetch(`${API}/rag/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ interaction_id: interactionId, vote }),
    });

    rowEl.dataset.voted = vote;
    rowEl.querySelectorAll(".btn-feedback").forEach(b => {
      if (b.textContent.includes("Like")) b.classList.toggle("voted-like", vote === "like");
      if (b.textContent.includes("Dislike")) b.classList.toggle("voted-dislike", vote === "dislike");
    });
  } catch (err) {
    console.error("Feedback error:", err);
  }
}

async function submitComment(interactionId, textareaEl, rowEl) {
  const comment = textareaEl.value.trim();
  if (!comment) return;

  const vote = rowEl.dataset.voted;
  if (!vote) {
    alert("Please 👍 Like or 👎 Dislike the response before adding a comment.");
    return;
  }

  try {
    await fetch(`${API}/rag/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ interaction_id: interactionId, vote, comment }),
    });
    textareaEl.value = "";
    textareaEl.placeholder = "✅ Comment submitted. Thank you!";
    textareaEl.disabled = true;
  } catch (err) {
    console.error("Comment error:", err);
  }
}

// ---------------------------------------------------------------------------
// Documents
// ---------------------------------------------------------------------------
async function uploadDocument() {
  const fileInput = document.getElementById("doc-file-input");
  const file = fileInput.files[0];
  if (!file) return;

  const status = document.getElementById("upload-status");
  status.style.display = "block";
  status.className = "upload-status loading";
  status.textContent = `⏳ Uploading "${file.name}"…`;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API}/rag/upload`, { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) throw new Error(data.detail || res.statusText);

    status.className = "upload-status success";
    status.textContent = `✅ "${data.filename}" uploaded — ${data.chunk_count} chunks indexed.`;
    loadDocuments();
  } catch (err) {
    status.className = "upload-status error";
    status.textContent = `❌ Upload failed: ${err.message}`;
  } finally {
    fileInput.value = "";
  }
}

async function loadDocuments() {
  const listEl = document.getElementById("doc-list");
  listEl.innerHTML = "<p class='empty-state'>Loading…</p>";

  try {
    const res = await fetch(`${API}/rag/documents`);
    const docs = await res.json();

    if (!docs.length) {
      listEl.innerHTML = "<p class='empty-state'>No documents uploaded yet.</p>";
      return;
    }

    listEl.innerHTML = "";
    docs.slice().reverse().forEach(doc => {
      listEl.appendChild(buildDocCard(doc));
    });
  } catch (err) {
    listEl.innerHTML = `<p class='empty-state' style='color:#c0392b'>Error loading documents: ${err.message}</p>`;
  }
}

function buildDocCard(doc) {
  const iconMap = { PDF: "📕", DOCX: "📘", TXT: "📄" };
  const icon = iconMap[doc.file_type] || "📄";
  const date = new Date(doc.uploaded_at).toLocaleString();

  const card = document.createElement("div");
  card.className = "doc-card";
  card.innerHTML = `
    <span class="doc-icon">${icon}</span>
    <div class="doc-info">
      <div class="doc-name">${escapeHtml(doc.filename)}</div>
      <div class="doc-meta">${doc.file_type} · ${doc.chunk_count} chunks · Uploaded ${date}</div>
    </div>
    <button class="btn-delete" onclick="deleteDocument('${doc.doc_id}', this)">🗑 Delete</button>
  `;
  return card;
}

async function deleteDocument(docId, btnEl) {
  if (!confirm("Delete this document and its embeddings?")) return;
  btnEl.disabled = true;
  btnEl.textContent = "⏳";

  try {
    const res = await fetch(`${API}/rag/documents/${docId}`, { method: "DELETE" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail);
    }
    loadDocuments();
  } catch (err) {
    alert(`Error deleting document: ${err.message}`);
    btnEl.disabled = false;
    btnEl.textContent = "🗑 Delete";
  }
}

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------
async function loadMetrics() {
  const grid = document.getElementById("metrics-grid");
  grid.innerHTML = "<p class='empty-state'>Loading…</p>";

  try {
    const res = await fetch(`${API}/rag/metrics`);
    const m = await res.json();

    grid.innerHTML = `
      <div class="metric-card">
        <div class="metric-value">${m.total_interactions}</div>
        <div class="metric-label">Total Interactions</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">${m.total_documents}</div>
        <div class="metric-label">Documents Indexed</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">${m.total_chunks}</div>
        <div class="metric-label">Total Chunks</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">${m.total_likes}</div>
        <div class="metric-label">👍 Likes</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">${m.total_dislikes}</div>
        <div class="metric-label">👎 Dislikes</div>
      </div>
      <div class="metric-card">
        <div class="metric-value">${(m.like_ratio * 100).toFixed(0)}%</div>
        <div class="metric-label">Like Ratio</div>
      </div>
    `;
  } catch (err) {
    grid.innerHTML = `<p class='empty-state' style='color:#c0392b'>Error loading metrics: ${err.message}</p>`;
  }
}

// ---------------------------------------------------------------------------
// Drag-and-drop
// ---------------------------------------------------------------------------
(function initDragDrop() {
  const zone = document.getElementById("upload-drop-zone");
  if (!zone) return;

  zone.addEventListener("dragover", e => {
    e.preventDefault();
    zone.classList.add("drag-over");
  });

  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));

  zone.addEventListener("drop", e => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const input = document.getElementById("doc-file-input");
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    uploadDocument();
  });
})();

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------
function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
