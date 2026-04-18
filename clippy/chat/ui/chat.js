(function () {
  "use strict";

  const transcript = document.getElementById("transcript");
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("send-btn");
  const newChatBtn = document.getElementById("new-chat-btn");

  // ── Helpers ──────────────────────────────────────────────────────────────

  function appendBubble(text, role) {
    const row = document.createElement("div");
    row.className = `bubble-row ${role}`;

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;

    row.appendChild(bubble);
    transcript.appendChild(row);
    transcript.scrollTop = transcript.scrollHeight;
  }

  function appendStatus(text) {
    const el = document.createElement("div");
    el.className = "status-msg";
    el.id = "status-msg";
    el.textContent = text;
    transcript.appendChild(el);
    transcript.scrollTop = transcript.scrollHeight;
    return el;
  }

  function removeStatus() {
    const el = document.getElementById("status-msg");
    if (el) el.remove();
  }

  function setUiBusy(busy) {
    input.disabled = busy;
    sendBtn.disabled = busy;
  }

  function autoResize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 120) + "px";
  }

  async function startNewChat() {
    let api;
    try {
      api = await waitForBridge();
    } catch (_err) {
      return;
    }
    try {
      await api.new_chat();
      while (transcript.firstChild) {
        transcript.removeChild(transcript.firstChild);
      }
    } catch (err) {
      console.error("New chat error:", err);
    }
  }

  // ── Bridge readiness ──────────────────────────────────────────────────────

  /**
   * Resolves once window.pywebview.api is available.
   * Polls every 100 ms; gives up after 10 seconds.
   */
  function waitForBridge() {
    return new Promise((resolve, reject) => {
      const deadline = Date.now() + 10_000;

      function check() {
        if (window.pywebview && window.pywebview.api) {
          resolve(window.pywebview.api);
        } else if (Date.now() > deadline) {
          reject(new Error("pywebview bridge not available"));
        } else {
          setTimeout(check, 100);
        }
      }

      check();
    });
  }

  // ── Send logic ────────────────────────────────────────────────────────────

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    input.value = "";
    input.style.height = "auto";
    appendBubble(text, "user");
    setUiBusy(true);

    const connectingEl = appendStatus("Connecting…");

    let api;
    try {
      api = await waitForBridge();
      removeStatus();
    } catch (_err) {
      connectingEl.textContent = "⚠️ Could not connect to Clippy bridge.";
      setUiBusy(false);
      return;
    }

    try {
      const response = await api.send_message(text);
      appendBubble(response, "assistant");
    } catch (err) {
      appendBubble("⚠️ Something went wrong. Please try again.", "assistant");
      console.error("Bridge error:", err);
    } finally {
      setUiBusy(false);
      input.focus();
    }
  }

  // ── Event wiring ──────────────────────────────────────────────────────────

  sendBtn.addEventListener("click", sendMessage);

  input.addEventListener("input", autoResize);

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  newChatBtn.addEventListener("click", startNewChat);

  input.focus();

  window.injectAssistantMessage = function (payload) {
    let text, buttons = [];
    try {
      const parsed = JSON.parse(payload);
      text = parsed.message || payload;
      buttons = parsed.buttons || [];
    } catch (_) {
      text = payload;
    }

    const row = document.createElement("div");
    row.className = "bubble-row assistant";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;

    // Reminder action buttons
    if (text.startsWith("⏰")) {
      const match = text.match(/^⏰\s+([^—–]+?)\s*[—–]/);
      const label = match ? match[1].trim() : "";
      const btnRow = document.createElement("div");
      btnRow.className = "action-btn-row";

      function disableRow() {
        btnRow.querySelectorAll("button").forEach(b => b.disabled = true);
      }

      const doneBtn = document.createElement("button");
      doneBtn.className = "ack-btn";
      doneBtn.textContent = "✓ Done";
      doneBtn.addEventListener("click", async function () {
        disableRow();
        doneBtn.textContent = "✓";
        try {
          const api = await waitForBridge();
          await api.acknowledge_reminder(label);
        } catch (e) {
          console.error("Ack error:", e);
        }
      });

      const notTodayBtn = document.createElement("button");
      notTodayBtn.className = "action-btn";
      notTodayBtn.textContent = "Not today";
      notTodayBtn.addEventListener("click", async function () {
        disableRow();
        notTodayBtn.textContent = "dismissed";
        try {
          const api = await waitForBridge();
          await api.dismiss_reminder(label);
        } catch (e) {
          console.error("Dismiss error:", e);
        }
      });

      const snoozeBtn = document.createElement("button");
      snoozeBtn.className = "action-btn";
      snoozeBtn.textContent = "Snooze 1h";
      snoozeBtn.addEventListener("click", async function () {
        disableRow();
        snoozeBtn.textContent = "snoozed";
        try {
          const api = await waitForBridge();
          await api.snooze_reminder(label, 1);
        } catch (e) {
          console.error("Snooze error:", e);
        }
      });

      btnRow.appendChild(doneBtn);
      btnRow.appendChild(notTodayBtn);
      btnRow.appendChild(snoozeBtn);
      bubble.appendChild(btnRow);
    }

    // Action buttons (e.g. Full / Lazy)
    if (buttons.length > 0) {
      const btnRow = document.createElement("div");
      btnRow.className = "action-btn-row";
      buttons.forEach(function (btnDef) {
        const btn = document.createElement("button");
        btn.className = "action-btn";
        btn.textContent = btnDef.label;
        btn.addEventListener("click", async function () {
          btnRow.querySelectorAll(".action-btn").forEach(b => b.disabled = true);
          try {
            const api = await waitForBridge();
            await api.handle_action(btnDef.action);
          } catch (e) {
            console.error("Action error:", e);
          }
        });
        btnRow.appendChild(btn);
      });
      bubble.appendChild(btnRow);
    }

    row.appendChild(bubble);
    transcript.appendChild(row);
    transcript.scrollTop = transcript.scrollHeight;
  };

  window.updateHeaderFace = function (emoji) {
    const el = document.getElementById("header-face");
    if (el) el.textContent = emoji;
  };
})();
