(function startAtlasConcept() {
  "use strict";

  const concept = window.ATLAS_CONCEPT;
  const mount = document.querySelector("#atlas-root");
  const defaultVariants = [
    { index: 1, name: "Systems Index", path: "../01-launchboard/" },
    { index: 2, name: "Dependency Flow", path: "../02-ribbon/" },
    { index: 3, name: "Research Map", path: "../03-bloom/" },
    { index: 4, name: "Control Plane", path: "../04-switchyard/" },
    { index: 5, name: "Architecture Field", path: "../05-loopshift/" },
  ];
  const variants = Array.isArray(window.ATLAS_VARIANTS)
    ? window.ATLAS_VARIANTS
    : defaultVariants;
  const interfaceCopy = {
    back: "Все 5 вариантов",
    eyebrow: "НАПРАВЛЕНИЕ",
    versionCaption: "ВЕРСИЯ СТРУКТУРЫ",
    current: "ТЕКУЩИЙ",
    contains: "СОДЕРЖИТ",
    terminal: "КОНЕЧНЫЙ",
    terminalMeta: "Нет вложенных циклов",
    detail: "ОПИСАНИЕ",
    loading: "Загружаем принятую структуру...",
    titleSuffix: "Concord Loom Atlas",
    ...window.ATLAS_INTERFACE_COPY,
    ...concept?.copy,
  };

  if (!concept || !mount || !window.ConcordData) {
    throw new Error("Atlas concept configuration is missing");
  }

  let atlasData = null;
  let activeRevisionId = null;
  let pathIds = [];
  let selectedId = null;
  let renderFrame = 0;
  let resizeObserver = null;
  const pendingNodeRemovals = new WeakMap();

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) {
      node.className = className;
    }
    if (text !== undefined) {
      node.textContent = text;
    }
    return node;
  }

  function button(className, text, action) {
    const node = element("button", className, text);
    node.type = "button";
    node.addEventListener("click", action);
    return node;
  }

  function model() {
    return atlasData.models.get(activeRevisionId);
  }

  function currentLoop() {
    const currentModel = model();
    const candidate = currentModel.loops.get(pathIds.at(-1));
    return candidate || currentModel.loops.get(currentModel.rootId);
  }

  function pluralCycles(count) {
    const lastTwo = count % 100;
    const last = count % 10;
    if (lastTwo >= 11 && lastTwo <= 14) {
      return `${count} циклов`;
    }
    if (last === 1) {
      return `${count} цикл`;
    }
    if (last >= 2 && last <= 4) {
      return `${count} цикла`;
    }
    return `${count} циклов`;
  }

  function buildShell() {
    document.documentElement.dataset.concept = concept.slug;
    document.title = `${concept.name} | ${interfaceCopy.titleSuffix}`;

    const skip = element("a", "skip-link", "К карте");
    skip.href = "#graph-viewport";

    const atlas = element("main", "atlas");
    const chrome = element("header", "chrome");
    const topbar = element("div", "topbar");
    const identity = element("div", "identity");
    const brand = element("a", "brand");
    brand.href = concept.sitePath || "../../../../site/";
    brand.setAttribute("aria-label", "Concord Loom");
    const brandMark = element("span", "brand-mark");
    brandMark.setAttribute("aria-hidden", "true");
    brand.append(brandMark, element("span", "brand-name", "CONCORD LOOM"));
    const back = element("a", "concept-back", interfaceCopy.back);
    back.href = concept.galleryPath || "../";
    identity.append(brand, back);

    const intro = element("section", "intro-copy");
    intro.append(
      element("p", "eyebrow", interfaceCopy.eyebrow),
      element("h1", "concept-title", concept.headline),
      element("p", "concept-deck", concept.deck),
    );

    const versionShell = element("nav", "version-shell");
    versionShell.setAttribute("aria-label", "Редакции системы");
    versionShell.append(
      element("span", "version-caption", interfaceCopy.versionCaption),
      element("div", "version-rail"),
    );

    const switcher = element("nav", "variant-switcher");
    switcher.setAttribute("aria-label", "Варианты дизайна");
    variants.forEach((variant) => {
      const link = element("a", "variant-link", String(variant.index));
      link.href = variant.path;
      link.title = variant.name;
      if (variant.index === concept.index) {
        link.setAttribute("aria-current", "page");
      }
      switcher.append(link);
    });

    topbar.append(identity, intro, versionShell, switcher);
    chrome.append(topbar);

    const workspace = element("section", "workspace");
    workspace.setAttribute("aria-label", "Карта циклов");
    const breadcrumbs = element("nav", "breadcrumbs");
    breadcrumbs.setAttribute("aria-label", "Путь по циклам");
    const viewport = element("div", "graph-viewport");
    viewport.id = "graph-viewport";
    viewport.tabIndex = -1;
    const plane = element("div", "graph-plane");
    const edges = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    edges.classList.add("edge-layer");
    edges.setAttribute("aria-hidden", "true");
    const nodes = element("div", "node-layer");
    plane.append(edges, nodes);
    viewport.append(plane);

    const detail = element("aside", "detail");
    detail.hidden = true;
    detail.setAttribute("aria-live", "polite");
    detail.setAttribute("aria-label", "Описание цикла");
    detail.append(
      button("detail-close", "Закрыть", closeDetail),
      element("p", "detail-kicker", interfaceCopy.detail),
      element("h2", "detail-title"),
      element("p", "detail-purpose"),
      element("p", "detail-meta"),
    );

    const loading = element(
      "div",
      "loading",
      interfaceCopy.loading,
    );
    loading.setAttribute("role", "status");
    workspace.append(breadcrumbs, viewport, detail, loading);
    atlas.append(chrome, workspace);
    mount.replaceChildren(skip, atlas);
  }

  function renderVersions() {
    const rail = document.querySelector(".version-rail");
    rail.style.setProperty("--revision-count", String(atlasData.sources.length));
    rail.replaceChildren();
    atlasData.sources.forEach((source) => {
      const item = button("revision", `v${source.label}`, () => {
        if (source.id !== activeRevisionId) {
          selectRevision(source.id, true);
        }
      });
      item.dataset.revision = source.id;
      item.setAttribute("aria-pressed", String(source.id === activeRevisionId));
      item.setAttribute(
        "aria-label",
        source.latest
          ? `Редакция ${source.label}, актуальная`
          : `Редакция ${source.label}`,
      );
      if (source.latest) {
        item.dataset.latest = "true";
      }
      rail.append(item);
    });
  }

  function pathTo(targetId, currentModel) {
    if (!currentModel.loops.has(targetId)) {
      return [currentModel.rootId];
    }
    const queue = [[currentModel.rootId]];
    const visited = new Set();
    while (queue.length) {
      const candidate = queue.shift();
      const id = candidate.at(-1);
      if (id === targetId) {
        return candidate;
      }
      if (visited.has(id)) {
        continue;
      }
      visited.add(id);
      const loop = currentModel.loops.get(id);
      loop.children.forEach((childId) => {
        if (!visited.has(childId)) {
          queue.push([...candidate, childId]);
        }
      });
    }
    return [currentModel.rootId];
  }

  function validPath(ids, currentModel) {
    if (!ids.length || ids[0] !== currentModel.rootId) {
      return false;
    }
    return ids.every((id, index) => {
      if (!currentModel.loops.has(id)) {
        return false;
      }
      return index === 0 ||
        currentModel.loops.get(ids[index - 1]).children.includes(id);
    });
  }

  function readRoute() {
    const raw = window.location.hash.replace(/^#/, "");
    if (!raw) {
      return null;
    }
    const [revisionId, ...encodedPath] = raw.split("/");
    return {
      revisionId,
      ids: encodedPath.map((part) => decodeURIComponent(part)),
    };
  }

  function writeRoute(mode) {
    const hash = [
      activeRevisionId,
      ...pathIds.map((id) => encodeURIComponent(id)),
    ].join("/");
    const url = `${window.location.pathname}${window.location.search}#${hash}`;
    window.history[mode]({ atlas: true }, "", url);
  }

  function restoreRoute() {
    const route = readRoute();
    const fallback = atlasData.sources.find((source) => source.latest).id;
    activeRevisionId = atlasData.models.has(route?.revisionId)
      ? route.revisionId
      : fallback;
    const currentModel = model();
    pathIds = validPath(route?.ids || [], currentModel)
      ? route.ids
      : [currentModel.rootId];
    selectedId = null;
    renderAll(false);
  }

  function selectRevision(revisionId, remember) {
    const previousId = pathIds.at(-1);
    activeRevisionId = revisionId;
    const currentModel = model();
    pathIds = pathTo(previousId, currentModel);
    selectedId = null;
    if (remember) {
      writeRoute("pushState");
    }
    renderAll(true);
  }

  function openLoop(loopId) {
    const current = currentLoop();
    if (loopId === current.id) {
      openDetail(loopId);
      return;
    }
    if (!current.children.includes(loopId)) {
      return;
    }
    pathIds.push(loopId);
    selectedId = currentLoop().children.length ? null : loopId;
    writeRoute("pushState");
    renderAll(true);
  }

  function goToPath(index) {
    if (index === pathIds.length - 1) {
      return;
    }
    pathIds = pathIds.slice(0, index + 1);
    selectedId = null;
    writeRoute("pushState");
    renderAll(true);
  }

  function goBack() {
    if (selectedId !== null) {
      closeDetail();
      return true;
    }
    if (pathIds.length > 1) {
      pathIds.pop();
      writeRoute("pushState");
      renderAll(true);
      return true;
    }
    return false;
  }

  function renderBreadcrumbs() {
    const breadcrumbs = document.querySelector(".breadcrumbs");
    breadcrumbs.replaceChildren();
    pathIds.forEach((id, index) => {
      const loop = model().loops.get(id);
      const crumb = button("crumb", loop.label, () => goToPath(index));
      if (index === pathIds.length - 1) {
        crumb.setAttribute("aria-current", "page");
        crumb.disabled = true;
      }
      breadcrumbs.append(crumb);
      if (index < pathIds.length - 1) {
        const separator = element("span", "crumb-separator", "/");
        separator.setAttribute("aria-hidden", "true");
        breadcrumbs.append(separator);
      }
    });
  }

  function compactLayout(width) {
    return width < (concept.compactAt || 860);
  }

  function calculateLayout(loop, viewportWidth, viewportHeight) {
    const childCount = loop.children.length;
    const compact = compactLayout(viewportWidth);
    const width = compact ? Math.max(viewportWidth, 320) : Math.max(viewportWidth, 820);
    const colors = concept.branchColors || [concept.accent || "#3156a3"];

    if (compact) {
      const columns = width < 480 ? 1 : 2;
      const rows = Math.ceil(childCount / columns);
      const height = Math.max(viewportHeight, 260 + rows * 136);
      const positions = [{ id: loop.id, x: width / 2, y: 118, role: "focus" }];
      loop.children.forEach((id, index) => {
        const column = index % columns;
        const row = Math.floor(index / columns);
        positions.push({
          id,
          x: columns === 1 ? width / 2 : width * (column ? 0.73 : 0.27),
          y: 290 + row * 136,
          role: "child",
          branch: colors[index % colors.length],
        });
      });
      return { width, height, positions, edgeKind: "vertical", compact };
    }

    if (concept.layout === "rail") {
      const columns =
        childCount > 8
          ? width >= 1360
            ? 4
            : width >= 960
              ? 3
              : 2
          : childCount > 5 && width >= 960
            ? 3
            : 2;
      const rows = Math.max(1, Math.ceil(childCount / columns));
      const height = Math.max(viewportHeight, 180 + rows * 132);
      const positions = [{
        id: loop.id,
        x: width * 0.19,
        y: height * 0.52,
        role: "focus",
      }];
      loop.children.forEach((id, index) => {
        const column = index % columns;
        const row = Math.floor(index / columns);
        const railStart = 0.48;
        const railEnd = Math.min(0.9, 1 - 125 / width);
        positions.push({
          id,
          x:
            width *
            (railStart +
              column *
                ((railEnd - railStart) / Math.max(columns - 1, 1))),
          y: 116 + row * ((height - 236) / Math.max(rows - 1, 1)),
          role: "child",
          branch: colors[index % colors.length],
        });
      });
      return { width, height, positions, edgeKind: "orthogonal" };
    }

    if (concept.layout === "ribbon") {
      const columns = childCount > 7 ? 2 : 1;
      const rows = Math.max(1, Math.ceil(childCount / columns));
      const height = Math.max(viewportHeight, 170 + rows * 108);
      const positions = [{
        id: loop.id,
        x: width * 0.22,
        y: height * 0.5,
        role: "focus",
      }];
      loop.children.forEach((id, index) => {
        const column = index % columns;
        const row = Math.floor(index / columns);
        positions.push({
          id,
          x: width * (column ? 0.77 : 0.56),
          y: 112 + row * ((height - 184) / Math.max(rows - 1, 1)),
          role: "child",
          branch: colors[index % colors.length],
        });
      });
      return { width, height, positions, edgeKind: "ribbon" };
    }

    if (concept.layout === "bloom") {
      const rings = childCount > 10 ? 2 : 1;
      const widthNeeded = Math.max(width, childCount > 12 ? 1180 : width);
      const height = Math.max(viewportHeight, rings === 2 ? 820 : 680);
      const centerX = widthNeeded * 0.5;
      const centerY = height * 0.54;
      const positions = [{
        id: loop.id,
        x: centerX,
        y: centerY,
        role: "focus",
      }];
      loop.children.forEach((id, index) => {
        const ring = rings === 2 && index >= Math.ceil(childCount / 2) ? 2 : 1;
        const ringStart = ring === 2 ? Math.ceil(childCount / 2) : 0;
        const ringCount = rings === 1
          ? childCount
          : ring === 2
            ? childCount - ringStart
            : Math.ceil(childCount / 2);
        const localIndex = index - ringStart;
        const angle = (-Math.PI * 0.83) + (localIndex / Math.max(ringCount - 1, 1)) * Math.PI * 1.66;
        const radiusX = widthNeeded * (ring === 2 ? 0.43 : 0.31);
        const radiusY = height * (ring === 2 ? 0.42 : 0.32);
        positions.push({
          id,
          x: centerX + Math.cos(angle) * radiusX,
          y: centerY + Math.sin(angle) * radiusY,
          role: "child",
          branch: colors[index % colors.length],
        });
      });
      return { width: widthNeeded, height, positions, edgeKind: "curve" };
    }

    if (concept.layout === "switchyard") {
      const columns = Math.min(4, Math.max(2, Math.ceil(Math.sqrt(childCount))));
      const rows = Math.max(1, Math.ceil(childCount / columns));
      const height = Math.max(viewportHeight, 220 + rows * 142);
      const positions = [{
        id: loop.id,
        x: width * 0.13,
        y: height * 0.5,
        role: "focus",
      }];
      loop.children.forEach((id, index) => {
        const column = index % columns;
        const row = Math.floor(index / columns);
        positions.push({
          id,
          x: width * 0.38 + column * ((width * 0.54) / Math.max(columns - 1, 1)),
          y: 130 + row * ((height - 230) / Math.max(rows - 1, 1)),
          role: "child",
          branch: colors[index % colors.length],
        });
      });
      return { width, height, positions, edgeKind: "orthogonal" };
    }

    const height = Math.max(viewportHeight, childCount > 12 ? 820 : 680);
    const widthNeeded = Math.max(width, childCount > 12 ? 1180 : width);
    const centerX = widthNeeded * 0.5;
    const centerY = height * 0.5;
    const positions = [{
      id: loop.id,
      x: centerX,
      y: centerY,
      role: "focus",
    }];
    loop.children.forEach((id, index) => {
      const angle = (-Math.PI / 2) + (index / Math.max(childCount, 1)) * Math.PI * 2;
      const radiusX = widthNeeded * 0.39;
      const radiusY = height * 0.38;
      positions.push({
        id,
        x: centerX + Math.cos(angle) * radiusX,
        y: centerY + Math.sin(angle) * radiusY,
        role: "child",
        branch: colors[index % colors.length],
      });
    });
    return { width: widthNeeded, height, positions, edgeKind: "curve" };
  }

  function edgePath(from, to, kind) {
    if (kind === "vertical") {
      const middleY = from.y + Math.max(54, (to.y - from.y) * 0.48);
      return `M ${from.x} ${from.y} V ${middleY} H ${to.x} V ${to.y}`;
    }
    if (kind === "orthogonal") {
      const middleX = from.x + (to.x - from.x) * 0.48;
      return `M ${from.x} ${from.y} H ${middleX} V ${to.y} H ${to.x}`;
    }
    if (kind === "ribbon") {
      const bend = Math.max(76, Math.abs(to.x - from.x) * 0.44);
      return `M ${from.x} ${from.y} C ${from.x + bend} ${from.y}, ${to.x - bend} ${to.y}, ${to.x} ${to.y}`;
    }
    const bendX = (to.x - from.x) * 0.42;
    const bendY = (to.y - from.y) * 0.22;
    return `M ${from.x} ${from.y} C ${from.x + bendX} ${from.y + bendY}, ${to.x - bendX} ${to.y - bendY}, ${to.x} ${to.y}`;
  }

  function renderEdges(layout) {
    const svg = document.querySelector(".edge-layer");
    svg.replaceChildren();
    svg.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
    svg.setAttribute("width", String(layout.width));
    svg.setAttribute("height", String(layout.height));
    const focus = layout.positions[0];
    layout.positions.slice(1).forEach((position, index) => {
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.classList.add("edge");
      path.dataset.branch = String(index);
      path.style.setProperty("--branch", position.branch);
      path.setAttribute("d", edgePath(focus, position, layout.edgeKind));
      svg.append(path);
    });
  }

  function previousModel() {
    const index = atlasData.sources.findIndex(
      (source) => source.id === activeRevisionId,
    );
    if (index <= 0) {
      return null;
    }
    return atlasData.models.get(atlasData.sources[index - 1].id);
  }

  function createNode(position, loop, origin) {
    const item = button(
      `node is-${position.role} is-entering`,
      "",
      () => openLoop(loop.id),
    );
    item.dataset.nodeId = loop.id;
    item.style.setProperty("--x", `${position.x}px`);
    item.style.setProperty("--y", `${position.y}px`);
    item.style.setProperty("--origin-x", `${origin.x}px`);
    item.style.setProperty("--origin-y", `${origin.y}px`);
    if (position.branch) {
      item.style.setProperty("--branch", position.branch);
    }
    const before = previousModel();
    if (before && !before.loops.has(loop.id)) {
      item.classList.add("is-new");
    }
    item.setAttribute(
      "aria-label",
      loop.children.length
        ? `${loop.label}. Содержит ${pluralCycles(loop.children.length)}.`
        : `${loop.label}. Вложенных циклов нет.`,
    );
    item.append(
      element(
        "span",
        "node-kicker",
        position.role === "focus"
          ? interfaceCopy.current
          : loop.children.length
            ? interfaceCopy.contains
            : interfaceCopy.terminal,
      ),
      element("span", "node-label", loop.label),
      element(
        "span",
        "node-meta",
        loop.children.length
          ? pluralCycles(loop.children.length)
          : interfaceCopy.terminalMeta,
      ),
    );
    return item;
  }

  function updateNode(item, position, loop) {
    item.className = `node is-${position.role}`;
    if (previousModel() && !previousModel().loops.has(loop.id)) {
      item.classList.add("is-new");
    }
    item.style.setProperty("--x", `${position.x}px`);
    item.style.setProperty("--y", `${position.y}px`);
    if (position.branch) {
      item.style.setProperty("--branch", position.branch);
    }
    item.querySelector(".node-kicker").textContent =
      position.role === "focus"
        ? interfaceCopy.current
        : loop.children.length
          ? interfaceCopy.contains
          : interfaceCopy.terminal;
    item.querySelector(".node-label").textContent = loop.label;
    item.querySelector(".node-meta").textContent = loop.children.length
      ? pluralCycles(loop.children.length)
      : interfaceCopy.terminalMeta;
  }

  function renderGraph(animated) {
    cancelAnimationFrame(renderFrame);
    const viewport = document.querySelector(".graph-viewport");
    const plane = document.querySelector(".graph-plane");
    const layer = document.querySelector(".node-layer");
    const loop = currentLoop();
    const layout = calculateLayout(
      loop,
      viewport.clientWidth,
      viewport.clientHeight,
    );
    plane.style.width = `${layout.width}px`;
    plane.style.height = `${layout.height}px`;
    viewport.classList.toggle(
      "is-scrollable",
      layout.width > viewport.clientWidth || layout.height > viewport.clientHeight,
    );
    renderEdges(layout);

    const wanted = new Set(layout.positions.map((position) => position.id));
    layer.querySelectorAll(".node").forEach((item) => {
      if (!wanted.has(item.dataset.nodeId)) {
        if (animated) {
          const pendingRemoval = pendingNodeRemovals.get(item);
          if (pendingRemoval) {
            window.clearTimeout(pendingRemoval);
          }
          item.classList.add("is-leaving");
          const removal = window.setTimeout(() => {
            pendingNodeRemovals.delete(item);
            if (item.classList.contains("is-leaving")) {
              item.remove();
            }
          }, 170);
          pendingNodeRemovals.set(item, removal);
        } else {
          item.remove();
        }
      }
    });

    const origin = layout.positions[0];
    layout.positions.forEach((position) => {
      const loopData = model().loops.get(position.id);
      let item = [...layer.querySelectorAll(".node")].find(
        (candidate) => candidate.dataset.nodeId === position.id,
      );
      if (item) {
        const pendingRemoval = pendingNodeRemovals.get(item);
        if (pendingRemoval) {
          window.clearTimeout(pendingRemoval);
          pendingNodeRemovals.delete(item);
        }
        updateNode(item, position, loopData);
      } else {
        item = createNode(position, loopData, origin);
        layer.append(item);
        renderFrame = requestAnimationFrame(() => {
          requestAnimationFrame(() => item.classList.remove("is-entering"));
        });
      }
    });
  }

  function renderDetail() {
    const detail = document.querySelector(".detail");
    if (!selectedId || !model().loops.has(selectedId)) {
      detail.classList.remove("is-open");
      detail.hidden = true;
      return;
    }
    const loop = model().loops.get(selectedId);
    detail.querySelector(".detail-title").textContent = loop.label;
    detail.querySelector(".detail-purpose").textContent = loop.purpose;
    detail.querySelector(".detail-meta").textContent = loop.children.length
      ? `На следующем уровне: ${pluralCycles(loop.children.length)}.`
      : "У этого цикла нет вложенных циклов.";
    detail.hidden = false;
    requestAnimationFrame(() => detail.classList.add("is-open"));
  }

  function openDetail(loopId) {
    selectedId = loopId;
    renderDetail();
    document.querySelector(".detail-close").focus({ preventScroll: true });
  }

  function closeDetail() {
    selectedId = null;
    renderDetail();
    document
      .querySelector(`[data-node-id="${CSS.escape(currentLoop().id)}"]`)
      ?.focus({ preventScroll: true });
  }

  function renderAll(animated) {
    renderVersions();
    renderBreadcrumbs();
    renderGraph(animated);
    renderDetail();
    document.querySelector(".loading")?.remove();
  }

  function showFailure(error) {
    const workspace = document.querySelector(".workspace");
    const fatal = element("div", "fatal");
    fatal.setAttribute("role", "alert");
    fatal.append(
      element("strong", "", "Карта не загрузилась."),
      element(
        "span",
        "",
        "Запустите локальный сервер из корня репозитория и обновите страницу.",
      ),
      button("retry", "Попробовать снова", () => window.location.reload()),
    );
    fatal.title = error.message;
    workspace.append(fatal);
    document.querySelector(".loading")?.remove();
  }

  function bindGlobalEvents() {
    window.addEventListener("popstate", restoreRoute);
    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        goBack();
      }
      if (
        /^[1-5]$/.test(event.key) &&
        !event.ctrlKey &&
        !event.metaKey &&
        !event.altKey
      ) {
        const target = variants.find(
          (variant) => variant.index === Number(event.key),
        );
        if (target && target.index !== concept.index) {
          window.location.href = target.path;
        }
      }
    });
    resizeObserver = new ResizeObserver(() => {
      if (atlasData) {
        renderGraph(false);
      }
    });
    resizeObserver.observe(document.querySelector(".graph-viewport"));
  }

  async function boot() {
    buildShell();
    bindGlobalEvents();
    try {
      atlasData = await window.ConcordData.load();
      restoreRoute();
    } catch (error) {
      showFailure(error);
    }
  }

  boot();
})();
