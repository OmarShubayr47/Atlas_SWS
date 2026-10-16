// Viewer for files the assistant shows on the projector (T-004 phase 3).
//
// One transform (scale + translate) is driven two ways:
//   - voice: "view_control" events (zoom in/out, scroll, next page, ...)
//   - pointer input: wheel = zoom at the cursor, one-pointer drag = pan,
//     two-pointer pinch = zoom + pan around the fingers' midpoint.
// Pointer Events cover mouse, pen and touch alike, so the PCAP foil needs no
// new code here once it is mapped to the projector with mouseEmulation="no"
// (the Pi's autotouch default of "yes" would turn touches into a mouse and
// make pinch impossible — see T-004 phase 5).
//
// File text is only ever inserted with textContent, never as HTML, and
// images (including SVG) are loaded through <img>, where scripts cannot run.
"use strict";

const Viewer = (() => {
  const MIN_SCALE = 0.2, MAX_SCALE = 8, STEP = 1.25;
  const el = (id) => document.getElementById(id);
  let st = { kind: null };
  const pointers = new Map();

  function apply() {
    el("vcontent").style.transform = `translate(${st.tx}px, ${st.ty}px) scale(${st.scale})`;
  }
  function port() {
    const r = el("vport").getBoundingClientRect();
    return { w: r.width, h: r.height, x: r.left, y: r.top };
  }
  function contentSize() {
    const c = el("vcontent").firstElementChild;
    return c ? { w: c.offsetWidth, h: c.offsetHeight } : { w: 0, h: 0 };
  }

  // Images and pages: fit whole. Text and lists: fit the width, start at top.
  function fit() {
    const p = port(), c = contentSize();
    if (!c.w || !c.h) { st.scale = 1; st.tx = 0; st.ty = 0; apply(); return; }
    if (st.kind === "text" || st.kind === "list") {
      st.scale = Math.min(1, p.w / c.w);
      st.tx = (p.w - c.w * st.scale) / 2;
      st.ty = 0;
    } else {
      // 4 % margin so nothing (a ground symbol, a page edge) touches the frame.
      st.scale = 0.96 * Math.min(p.w / c.w, p.h / c.h, 4);
      st.tx = (p.w - c.w * st.scale) / 2;
      st.ty = (p.h - c.h * st.scale) / 2;
    }
    apply();
  }

  // Zoom keeping the point (px, py) of the viewport fixed under the
  // finger/cursor: the standard "zoom about a point" transform.
  function zoomAt(px, py, factor) {
    const s = Math.min(MAX_SCALE, Math.max(MIN_SCALE, st.scale * factor));
    const k = s / st.scale;
    st.tx = px - (px - st.tx) * k;
    st.ty = py - (py - st.ty) * k;
    st.scale = s;
    apply();
  }
  function scrollBy(dy) { st.ty += dy; apply(); }

  function url(kind, path, page) {
    const q = "path=" + encodeURIComponent(path);
    return kind === "pdf" ? `/pdfpage?${q}&page=${page}` : `/file?${q}`;
  }
  function setContent(node) { el("vcontent").replaceChildren(node); }
  function message(text) {
    const d = document.createElement("div");
    d.className = "vempty";
    d.textContent = text;
    setContent(d);
    fit();
  }
  function showImage(src, invert) {
    const img = new Image();
    img.className = "vimg" + (invert ? " invert" : "");
    img.alt = "";
    img.draggable = false;
    img.onload = fit;
    img.onerror = () => message("Could not load this file.");
    img.src = src;
    setContent(img);
  }
  function info() {
    el("vinfo").textContent =
      st.kind === "pdf" ? `page ${st.page} / ${st.pages}` :
      st.kind === "list" ? `${st.count} item${st.count === 1 ? "" : "s"}` : "";
  }

  function list(items) {
    st.count = items.length;
    if (!items.length) { message("Nothing here yet."); return; }
    const ol = document.createElement("ol");
    ol.className = "vlist";
    for (const it of items) {
      const li = document.createElement("li");
      const n = document.createElement("span");
      n.className = "n";
      n.textContent = it.n;
      const name = document.createElement("span");
      name.className = "name";
      name.textContent = it.name;
      const path = document.createElement("span");
      path.className = "path";
      path.textContent = it.path;
      name.appendChild(path);
      const when = document.createElement("span");
      when.className = "when";
      when.textContent = it.when || "";
      li.append(n, name, when);
      ol.appendChild(li);
    }
    setContent(ol);
    fit();
  }

  async function open(ev) {
    st = { kind: ev.kind, path: ev.path, page: 1, pages: Math.max(1, ev.pages || 1),
           scale: 1, tx: 0, ty: 0, count: 0 };
    document.body.dataset.view = "open";
    el("viewer").hidden = false;
    el("vtitle").textContent = ev.title || ev.path || "";
    if (ev.kind === "text") {
      const wanted = ev.path;
      try {
        const r = await fetch(url("text", wanted), { cache: "no-store" });
        if (!r.ok) throw new Error(String(r.status));
        const pre = document.createElement("pre");
        pre.className = "vtext";
        pre.textContent = await r.text();
        if (st.path !== wanted) return;     // another file opened meanwhile
        setContent(pre);
        fit();
      } catch (_) {
        if (st.path === wanted) message("Could not load this file.");
      }
    } else if (ev.kind === "image") {
      showImage(url("image", ev.path), !!ev.invert);
    } else if (ev.kind === "pdf") {
      showImage(url("pdf", ev.path, 1), false);
    } else if (ev.kind === "list") {
      list(ev.items || []);
    }
    info();
  }

  function close() {
    st = { kind: null };
    document.body.dataset.view = "closed";
    el("viewer").hidden = true;
    el("vcontent").replaceChildren();
  }

  function page(delta) {
    const p = Math.min(st.pages, Math.max(1, st.page + delta));
    if (p === st.page) return;
    st.page = p;
    showImage(url("pdf", st.path, p), false);
    info();
  }

  function control(op) {
    if (!st.kind) return;
    const p = port();
    switch (op) {
      case "zoom_in":     zoomAt(p.w / 2, p.h / 2, STEP); break;
      case "zoom_out":    zoomAt(p.w / 2, p.h / 2, 1 / STEP); break;
      case "reset_zoom":  fit(); break;
      case "scroll_down": scrollBy(-0.4 * p.h); break;
      case "scroll_up":   scrollBy(0.4 * p.h); break;
      case "next_page":     if (st.kind === "pdf") page(+1); else scrollBy(-0.9 * p.h); break;
      case "previous_page": if (st.kind === "pdf") page(-1); else scrollBy(0.9 * p.h); break;
    }
  }

  // --- pointer input: the mouse today, the touch foil later ------------------
  function local(e) {
    const p = port();
    return { x: e.clientX - p.x, y: e.clientY - p.y };
  }
  function init() {
    const vp = el("vport");
    vp.addEventListener("pointerdown", (e) => {
      vp.setPointerCapture(e.pointerId);
      pointers.set(e.pointerId, local(e));
    });
    vp.addEventListener("pointermove", (e) => {
      if (!pointers.has(e.pointerId) || !st.kind) return;
      const prev = pointers.get(e.pointerId), cur = local(e);
      if (pointers.size === 1) {
        st.tx += cur.x - prev.x;
        st.ty += cur.y - prev.y;
        apply();
      } else if (pointers.size === 2) {
        const other = [...pointers.entries()].find(([id]) => id !== e.pointerId)[1];
        const d0 = Math.hypot(prev.x - other.x, prev.y - other.y);
        const d1 = Math.hypot(cur.x - other.x, cur.y - other.y);
        const m0 = { x: (prev.x + other.x) / 2, y: (prev.y + other.y) / 2 };
        const m1 = { x: (cur.x + other.x) / 2, y: (cur.y + other.y) / 2 };
        if (d0 > 0) zoomAt(m0.x, m0.y, d1 / d0);
        st.tx += m1.x - m0.x;
        st.ty += m1.y - m0.y;
        apply();
      }
      pointers.set(e.pointerId, cur);
    });
    const end = (e) => pointers.delete(e.pointerId);
    vp.addEventListener("pointerup", end);
    vp.addEventListener("pointercancel", end);
    vp.addEventListener("wheel", (e) => {
      if (!st.kind) return;
      e.preventDefault();
      const p = local(e);
      zoomAt(p.x, p.y, e.deltaY < 0 ? 1.15 : 1 / 1.15);
    }, { passive: false });
    window.addEventListener("resize", () => { if (st.kind) fit(); });
  }

  return { init, open, close, control };
})();
