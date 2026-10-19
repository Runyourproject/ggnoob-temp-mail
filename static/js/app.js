/**
 * GGNoob Temp Mail – client-side inbox logic
 */
(function () {
  "use strict";

  const POLL_INTERVAL = 12000; // 12 seconds
  let pollTimer = null;
  let currentEmail = null;

  function $(sel, ctx) {
    return (ctx || document).querySelector(sel);
  }
  function $$(sel, ctx) {
    return Array.from((ctx || document).querySelectorAll(sel));
  }

  function showToast(msg) {
    let t = $(".toast");
    if (!t) {
      t = document.createElement("div");
      t.className = "toast";
      document.body.appendChild(t);
    }
    t.textContent = msg;
    t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 2200);
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(() => {
        showToast("Copied to clipboard");
      });
    }
    // Fallback
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand("copy");
      showToast("Copied to clipboard");
    } catch (e) {
      showToast("Copy failed");
    }
    document.body.removeChild(ta);
  }

  /* ---------- Copy / Random / Custom ---------- */
  function initHomeActions() {
    const emailEl = $("#email-address");
    if (!emailEl) return;

    currentEmail = emailEl.dataset.email || emailEl.textContent.trim();

    const copyBtn = $("#btn-copy");
    if (copyBtn) {
      copyBtn.addEventListener("click", () => copyText(currentEmail));
    }

    const randomBtn = $("#btn-random");
    if (randomBtn) {
      randomBtn.addEventListener("click", () => {
        fetch("/api/random")
          .then((r) => r.json())
          .then((data) => {
            window.location.href = "/mailbox/" + encodeURIComponent(data.name);
          })
          .catch(() => {
            // Fallback: just reload with random
            window.location.href = "/";
          });
      });
    }

    const form = $("#custom-form");
    if (form) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        const input = $("#custom-name");
        let name = (input.value || "").trim().toLowerCase();
        name = name.replace(/[^a-z0-9._+-]/g, "");
        if (!name) {
          showToast("Enter a valid name");
          return;
        }
        window.location.href = "/mailbox/" + encodeURIComponent(name);
      });
    }
  }

  /* ---------- Inbox polling ---------- */
  function renderMessages(messages) {
    const list = $("#message-list");
    const empty = $("#empty-state");
    const totalEl = $("#msg-total");
    if (!list) return;

    if (totalEl) totalEl.textContent = messages.length;

    if (!messages.length) {
      list.innerHTML = "";
      if (empty) empty.style.display = "block";
      return;
    }
    if (empty) empty.style.display = "none";

    list.innerHTML = messages
      .map(
        (m) => `
      <li class="message-item" data-id="${escapeAttr(m.id)}" role="button" tabindex="0">
        <div class="msg-from">${escapeHtml(m.from)}</div>
        <div class="msg-subject">${escapeHtml(m.subject)}</div>
        <div class="msg-date">${formatDate(m.date)}</div>
      </li>`
      )
      .join("");

    $$(".message-item", list).forEach((el) => {
      el.addEventListener("click", () => openMessage(el.dataset.id));
      el.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openMessage(el.dataset.id);
        }
      });
    });
  }

  function fetchMessages() {
    if (!currentEmail) return;
    const status = $("#inbox-status");
    fetch("/api/messages?email=" + encodeURIComponent(currentEmail))
      .then((r) => {
        if (!r.ok) throw new Error("fetch failed");
        return r.json();
      })
      .then((data) => {
        if (data.error) {
          if (status) status.textContent = data.error;
          return;
        }
        renderMessages(data.messages || []);
        if (status) {
          status.textContent = "Live · last checked just now";
          status.classList.add("live");
        }
      })
      .catch(() => {
        if (status) {
          status.textContent = "Connection issue – retrying…";
          status.classList.remove("live");
        }
      });
  }

  function startPolling() {
    fetchMessages();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(fetchMessages, POLL_INTERVAL);
  }

  /* ---------- Message detail ---------- */
  function openMessage(id) {
    const overlay = $("#modal-overlay");
    const title = $("#modal-title");
    const meta = $("#modal-meta");
    const body = $("#modal-body");
    if (!overlay) return;

    title.textContent = "Loading…";
    meta.textContent = "";
    body.innerHTML = "<p style='color:var(--text-muted)'>Fetching message…</p>";
    overlay.classList.add("open");

    fetch(
      "/api/message/" +
        encodeURIComponent(id) +
        "?email=" +
        encodeURIComponent(currentEmail)
    )
      .then((r) => {
        if (!r.ok) throw new Error("not found");
        return r.json();
      })
      .then((data) => {
        title.textContent = data.subject || "(no subject)";
        meta.innerHTML =
          "<strong>From:</strong> " +
          escapeHtml(data.from) +
          " · <strong>Date:</strong> " +
          formatDate(data.date);

        if (data.html && data.html.trim()) {
          // Sandboxed iframe for HTML
          body.className = "modal-body html-content";
          body.innerHTML = "";
          const iframe = document.createElement("iframe");
          iframe.sandbox = "allow-same-origin";
          iframe.srcdoc =
            '<base target="_blank"><style>body{font-family:system-ui,sans-serif;padding:12px;color:#111;background:#fff;margin:0}</style>' +
            data.html;
          body.appendChild(iframe);
        } else if (data.text) {
          body.className = "modal-body";
          body.textContent = data.text;
        } else {
          body.className = "modal-body";
          body.textContent = "(No message body)";
        }
      })
      .catch(() => {
        title.textContent = "Error";
        body.textContent = "Could not load this message. It may have expired.";
      });
  }

  function closeModal() {
    const overlay = $("#modal-overlay");
    if (overlay) overlay.classList.remove("open");
  }

  function initModal() {
    const overlay = $("#modal-overlay");
    if (!overlay) return;
    const closeBtn = $("#modal-close");
    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeModal();
    });
  }

  /* ---------- Helpers ---------- */
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function escapeAttr(str) {
    return escapeHtml(str).replace(/'/g, "&#39;");
  }
  function formatDate(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch {
      return iso;
    }
  }

  /* ---------- Boot ---------- */
  document.addEventListener("DOMContentLoaded", () => {
    initHomeActions();
    initModal();

    // Mailbox page
    const emailEl = $("#email-address");
    if (emailEl && document.body.dataset.page === "mailbox") {
      currentEmail = emailEl.dataset.email || emailEl.textContent.trim();
      const copyBtn = $("#btn-copy");
      if (copyBtn) copyBtn.addEventListener("click", () => copyText(currentEmail));
      const refreshBtn = $("#btn-refresh");
      if (refreshBtn) refreshBtn.addEventListener("click", fetchMessages);
      const changeBtn = $("#btn-change");
      if (changeBtn) {
        changeBtn.addEventListener("click", () => {
          window.location.href = "/";
        });
      }
      startPolling();
    }
  });
})();
