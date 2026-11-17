// Model browser: a tree of the schema's documents (left) and the details of the
// selected class or field (right). Reads data/model.json, written by docs/build.py.
(function () {
  const root = document.getElementById("schema-browser");
  if (!root) return;
  const base = root.dataset.base || "../";

  const el = (tag, attrs = {}, ...children) => {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (key === "class") node.className = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value);
    }
    for (const child of children.flat()) {
      if (child !== null && child !== undefined && child !== false)
        node.append(child.nodeType ? child : document.createTextNode(String(child)));
    }
    return node;
  };
  const badge = (text, kind) => el("span", { class: `mb-badge mb-${kind}` }, text);
  const mifa = (list) => list.filter((t) => t.startsWith("mifa:")).map((t) => t.slice(5));

  fetch(base + "data/model.json")
    .then((r) => r.json())
    .then(render)
    .catch((err) => (root.textContent = "Could not load the model: " + err));

  function render(model) {
    const search = el("input", { class: "mb-search", type: "search", placeholder: "Search fields…" });
    const tree = el("div", { class: "mb-tree", role: "tree" });
    const details = el("div", { class: "mb-details" });
    root.append(el("div", { class: "mb-controls" }, search), el("div", { class: "mb-layout" }, tree, details));
    let selected = null;

    const select = (row, show) => {
      if (selected) selected.classList.remove("mb-selected");
      selected = row;
      row.classList.add("mb-selected");
      details.replaceChildren(...show());
    };

    function fieldRow(cls, field, path) {
      const isClass = field.kind === "class" && model.classes[field.range] && field.range !== "Any";
      const label = el(
        "span",
        { class: "mb-label" },
        el("span", { class: "mb-name" }, field.name),
        el("span", { class: "mb-range" }, field.multivalued ? `${field.range}[]` : field.range),
        field.required ? badge("required", "req") : null,
        mifa([...field.exact, ...field.close]).length ? badge("MIFA", "mifa") : null,
      );
      const row = el("div", { class: "mb-row", role: "treeitem", "data-path": path.join(".") });
      const node = el("div", { class: "mb-node" }, row);
      const toggle = el("span", { class: "mb-toggle" }, isClass ? "▸" : "");
      row.append(toggle, label);
      let children = null;
      const open = (force) => {
        if (!isClass) return;
        const want = force ?? (!children || children.hidden);
        if (!children) {
          children = el("div", { class: "mb-children" });
          for (const f of model.classes[field.range].fields) children.append(fieldRow(field.range, f, [...path, f.name]));
          node.append(children);
        }
        children.hidden = !want;
        toggle.textContent = want ? "▾" : "▸";
      };
      toggle.addEventListener("click", (e) => (e.stopPropagation(), open()));
      row.addEventListener("click", () => {
        open(true);
        select(row, () => fieldDetails(cls, field, path));
      });
      node.open = open;
      return node;
    }

    function classNode(name) {
      const row = el("div", { class: "mb-row mb-root", role: "treeitem" },
        el("span", { class: "mb-toggle" }, "▾"),
        el("span", { class: "mb-label" }, el("span", { class: "mb-name" }, name)));
      const children = el("div", { class: "mb-children" },
        model.classes[name].fields.map((f) => fieldRow(name, f, [name, f.name])));
      row.addEventListener("click", () => {
        children.hidden = !children.hidden;
        row.firstChild.textContent = children.hidden ? "▸" : "▾";
        select(row, () => classDetails(name));
      });
      return el("div", { class: "mb-node" }, row, children);
    }

    const refLink = (kind, name) => el("a", { href: `${base}reference/${kind}/${name}/` }, name);
    const typeLink = (field) =>
      field.kind === "class" ? refLink("classes", field.range)
      : field.kind === "enum" ? refLink("enums", field.range)
      : el("code", {}, field.range);

    function mappings(item) {
      const rows = [];
      for (const [kind, list] of [["exact", item.exact], ["close", item.close]]) {
        for (const t of list) rows.push(el("li", {}, `${kind}: `, el("code", {}, t)));
      }
      return rows.length ? [el("h4", {}, "Mappings"), el("ul", {}, rows)] : [];
    }

    function classDetails(name) {
      const cls = model.classes[name];
      return [
        el("h3", {}, name),
        el("p", {}, cls.description || "No description."),
        cls.uri ? el("p", {}, "Class URI: ", el("code", {}, cls.uri)) : null,
        ...mappings(cls),
        cls.rules.length ? el("h4", {}, "Rules") : null,
        cls.rules.length ? el("ul", {}, cls.rules.map((r) => el("li", {}, r))) : null,
        el("p", {}, refLink("classes", name), " — full reference page"),
      ];
    }

    function fieldDetails(cls, field, path) {
      const facts = [
        ["Path", el("code", {}, path.join("."))],
        ["Type", typeLink(field)],
        ["Required", field.required ? "yes" : "no"],
        ["List", field.multivalued ? "yes" : "no"],
        field.pattern ? ["Pattern", el("code", {}, field.pattern)] : null,
        field.minimum !== null ? ["Minimum", String(field.minimum)] : null,
        field.maximum !== null ? ["Maximum", String(field.maximum)] : null,
        field.uri ? ["Field URI", el("code", {}, field.uri)] : null,
      ].filter(Boolean);
      const out = [
        el("h3", {}, field.name),
        el("p", {}, field.description || "No description."),
        el("table", { class: "mb-facts" }, facts.map(([k, v]) => el("tr", {}, el("th", {}, k), el("td", {}, v)))),
        ...mappings(field),
      ];
      const en = field.kind === "enum" && model.enums[field.range];
      if (en) {
        out.push(el("h4", {}, `Values of ${field.range}`),
          el("table", { class: "mb-facts" }, en.values.map((v) =>
            el("tr", {}, el("th", {}, el("code", {}, v.value)), el("td", {}, v.description)))));
      }
      out.push(el("p", {}, "Declared in ", refLink("classes", cls)));
      return out;
    }

    for (const name of model.roots) tree.append(classNode(name));
    details.append(el("p", { class: "mb-hint" },
      `${model.title} ${model.version}. Click a class or field to see its details; ▸ opens the fields of a nested class.`));

    // Search: list every field path whose name or description matches.
    const paths = [];
    const walk = (cls, path, seen) => {
      for (const f of model.classes[cls].fields) {
        paths.push({ cls, field: f, path: [...path, f.name] });
        if (f.kind === "class" && f.range !== "Any" && !seen.includes(f.range))
          walk(f.range, [...path, f.name], [...seen, f.range]);
      }
    };
    for (const name of model.roots) walk(name, [name], [name]);
    const treeChildren = [...tree.children];
    search.addEventListener("input", () => {
      const q = search.value.trim().toLowerCase();
      if (!q) return tree.replaceChildren(...treeChildren);
      const hits = paths.filter(({ field }) =>
        field.name.toLowerCase().includes(q) || field.description.toLowerCase().includes(q));
      tree.replaceChildren(...(hits.length ? hits.map(({ cls, field, path }) => {
        const row = el("div", { class: "mb-row" },
          el("span", { class: "mb-label" }, el("span", { class: "mb-path" }, path.slice(0, -1).join(".") + "."),
            el("span", { class: "mb-name" }, field.name), el("span", { class: "mb-range" }, field.range)));
        row.addEventListener("click", () => select(row, () => fieldDetails(cls, field, path)));
        return row;
      }) : [el("p", { class: "mb-hint" }, "No field matches.")]));
    });
  }
})();
