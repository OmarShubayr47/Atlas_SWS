// Status panel: subscribes to the UI server and redraws on each event.
// Text is always set via textContent, never innerHTML — replies come from an
// LLM and must never be able to inject markup into the page.
"use strict";
const $ = (id) => document.getElementById(id);

const LABEL = { idle: "Idle", listening: "Listening", thinking: "Thinking",
                speaking: "Speaking", error: "Error" };
const DETAIL = { idle: "Say “Hey Atlas” or press the button",
                 listening: "Go ahead — I’m listening",
                 thinking: "Working on it…", speaking: "", error: "" };

// Two separate things can be down: this page's link to the UI server, and the
// assistant behind it. The assistant sends a heartbeat every 5 s; with none
// for 15 s the panel says so, rather than showing a confident but stale state.
const BEAT_STALE_MS = 15000;
let serverUp = false;
let lastBeat = 0;
const LINKTEXT = { offline: "UI server offline", online: "assistant ready",
                   noassistant: "assistant offline" };

function updateLink() {
  const link = !serverUp ? "offline"
             : (Date.now() - lastBeat < BEAT_STALE_MS ? "online" : "noassistant");
  if (document.body.dataset.link !== link) {
    document.body.dataset.link = link;
    $("linktext").textContent = LINKTEXT[link];
  }
}

let bannerTimer = null;
function showBanner(title, text, ms) {
  $("bannertitle").textContent = title;
  $("bannertext").textContent = text;
  $("banner").hidden = false;
  clearTimeout(bannerTimer);
  if (ms) bannerTimer = setTimeout(() => { $("banner").hidden = true; }, ms);
}
function hideBanner() { clearTimeout(bannerTimer); $("banner").hidden = true; }

// Restart button (software/restart_button.py): tell the user what letting go
// will do at each moment of the hold.
function showRestart(ev) {
  switch (ev.stage) {
    case "holding":
      showBanner("Restart button",
                 ev.reboot_s ? `Hold ${ev.soft_s} s: restart the software · ${ev.reboot_s} s: reboot`
                             : `Hold ${ev.soft_s} s: restart the software`, 12000);
      break;
    case "armed":
      showBanner("Release to restart the software", "Keep holding to reboot the Pi", 12000);
      break;
    case "software": showBanner("Restarting the software…", "Back in a few seconds", 30000); break;
    case "reboot":   showBanner("Rebooting…", "Back in about a minute", 0); break;
    case "cancelled": hideBanner(); break;
  }
}

function setState(state, detail) {
  if (!(state in LABEL)) return;
  document.body.dataset.state = state;
  $("state").textContent = LABEL[state];
  $("chiptext").textContent = LABEL[state];
  $("detail").textContent = detail ?? DETAIL[state];
}

function handle(ev) {
  switch (ev.type) {
    case "state":      setState(ev.state, ev.detail); break;
    case "transcript": $("you").textContent = ev.text || "—"; break;
    case "reply":      $("ai").textContent = ev.text || "—";
                       $("ticker").textContent = ev.text || ""; break;
    case "view":
      if (ev.action === "open") Viewer.open(ev); else Viewer.close();
      break;
    case "view_control": Viewer.control(ev.op); break;
    case "tool":
      if (document.body.dataset.state === "thinking")
        $("detail").textContent = `Checking the project: ${ev.name}`;
      break;
    case "volume": {
      const pct = Math.max(0, Math.min(100, Number(ev.percent) || 0));
      $("volfill").style.width = (ev.muted ? 0 : pct) + "%";
      $("volpct").textContent = ev.muted ? "muted" : pct + "%";
      break;
    }
    case "error": setState("error", ev.message || "Something went wrong"); break;
    // ts is the assistant's clock (same Pi), so a replayed old heartbeat is
    // correctly treated as stale rather than as "alive now".
    case "heartbeat": lastBeat = (ev.ts ? ev.ts * 1000 : Date.now()); updateLink(); break;
    case "restart": showRestart(ev); break;
  }
}

function connect() {
  const es = new EventSource("/events");   // reconnects by itself
  es.onopen = () => { serverUp = true; updateLink(); };
  es.onerror = () => { serverUp = false; updateLink(); };
  es.onmessage = (m) => { try { handle(JSON.parse(m.data)); } catch (_) {} };
}
setInterval(updateLink, 1000);

function tick() {
  const now = new Date();
  $("clock").textContent = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  $("date").textContent = now.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" });
}

tick(); setInterval(tick, 1000);
Viewer.init();
connect();
