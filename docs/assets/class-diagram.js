// Class diagram: renders <base>data/classes.mmd (written by scripts/build_docs.py) with
// Mermaid and lets the reader pan (drag) and zoom (wheel, buttons) by moving the
// SVG's viewBox. Redraws when the colour scheme changes.
(function () {
  const root = document.getElementById("diagram-view");
  if (!root) return;
  const MERMAID = "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs";

  const button = (label, title, onclick) => {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.title = title;
    b.addEventListener("click", onclick);
    return b;
  };
  const stage = document.createElement("div");
  stage.className = "cd-stage";
  stage.textContent = "Drawing the diagram…";
  const tools = document.createElement("div");
  tools.className = "cd-tools";
  root.append(tools, stage);

  let svg = null, view = null, full = null;
  const apply = () => svg.setAttribute("viewBox", view.join(" "));
  const fit = () => { view = [...full]; apply(); };
  // Zoom by `factor` around a point given as fractions of the stage (0..1).
  const zoom = (factor, fx = 0.5, fy = 0.5) => {
    const [x, y, w, h] = view;
    const nw = Math.min(Math.max(w * factor, full[2] / 40), full[2] * 4);
    const nh = (nw / w) * h;
    view = [x + (w - nw) * fx, y + (h - nh) * fy, nw, nh];
    apply();
  };
  tools.append(
    button("+", "Zoom in", () => svg && zoom(0.8)),
    button("−", "Zoom out", () => svg && zoom(1.25)),
    button("⤢", "Fit the whole diagram", () => svg && fit()),
  );

  stage.addEventListener("wheel", (e) => {
    if (!svg) return;
    e.preventDefault();
    const r = stage.getBoundingClientRect();
    zoom(e.deltaY < 0 ? 0.85 : 1 / 0.85, (e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
  }, { passive: false });

  let drag = null;
  stage.addEventListener("pointerdown", (e) => {
    if (!svg) return;
    drag = { x: e.clientX, y: e.clientY, view: [...view] };
    stage.setPointerCapture(e.pointerId);
    stage.classList.add("cd-dragging");
  });
  stage.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const r = stage.getBoundingClientRect();
    // The SVG keeps its aspect ratio, so one screen pixel is the larger of the two scales.
    const scale = Math.max(drag.view[2] / r.width, drag.view[3] / r.height);
    view = [drag.view[0] - (e.clientX - drag.x) * scale, drag.view[1] - (e.clientY - drag.y) * scale, drag.view[2], drag.view[3]];
    apply();
  });
  const stop = () => { drag = null; stage.classList.remove("cd-dragging"); };
  stage.addEventListener("pointerup", stop);
  stage.addEventListener("pointercancel", stop);

  const dark = () => document.body.getAttribute("data-md-color-scheme") === "slate";
  let source = null, mermaid = null, count = 0;
  async function draw() {
    mermaid.initialize({ startOnLoad: false, theme: dark() ? "dark" : "default", er: { useMaxWidth: false } });
    const { svg: markup } = await mermaid.render(`class-diagram-svg-${count++}`, source);
    stage.innerHTML = markup;
    svg = stage.querySelector("svg");
    svg.removeAttribute("style");
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", "100%");
    full = svg.getAttribute("viewBox").split(/[\s,]+/).map(Number);
    fit();
  }

  Promise.all([
    fetch((root.dataset.base || "../") + "data/classes.mmd").then((r) => r.text()),
    import(MERMAID).then((m) => m.default),
  ])
    .then(([text, m]) => { source = text; mermaid = m; return draw(); })
    .catch((err) => (stage.textContent = "Could not draw the diagram: " + err));

  new MutationObserver(() => mermaid && draw())
    .observe(document.body, { attributes: true, attributeFilter: ["data-md-color-scheme"] });
})();
