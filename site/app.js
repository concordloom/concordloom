const copy = {
  en: {
    switchLanguage: "Switch to Russian",
    loading: "Loading accepted data…",
    loadError: "The accepted projection could not be loaded. Reload the page or inspect the source repository.",
    current: "Current cycle",
    children: "Contained cycles",
    leaf: "This cycle has no smaller responsibility cycles. Open its shared run grammar and resources in the inspector.",
    purpose: "Purpose",
    responsibility: "Responsible role",
    contract: "Outcome contract",
    resources: "Planned resources",
    provider: "Provider",
    model: "Planned model",
    reasoning: "Reasoning",
    skills: "Bound skills",
    guidance: "Profile guidance",
    mcp: "MCP",
    tools: "Tools",
    evidence: "Evidence",
    input: "Input",
    output: "Output",
    source: "Source",
    technicalDetails: "Technical details",
    executionPlan: "How this cycle is planned to run",
    profile: "Execution profile",
    claims: "Required checks",
    artifacts: "Artifacts",
    notDeclared: "Not declared",
    noSkills: "No required skill",
    bindingPlan: "Accepted binding plan",
    actualNote: "This is the accepted plan. Actual use and token counts appear only after a recorded run.",
    open: "Open cycle",
    back: "Up one level",
    phaseBoundary: "Evolve stops here. Activation is a separate operator act.",
    docs: "Open document",
    revision: "Revision",
    acceptedSource: "Accepted development rules",
    identifier: "ID",
    childCount: "Contained cycles",
    noChildCount: "No contained cycles",
    path: "Path",
    level: "Level",
    whatItDoes: "What it does",
    needs: "Needs",
    produces: "Produces",
    resourcesOptional: "Models, skills and tools",
  },
  ru: {
    switchLanguage: "Переключить на английский",
    loading: "Загружаются принятые данные…",
    loadError: "Не удалось загрузить принятую проекцию. Перезагрузите страницу или откройте исходные данные в репозитории.",
    current: "Текущий цикл",
    children: "Вложенные циклы",
    leaf: "У этого цикла нет более мелких циклов ответственности. Общая схема запуска и ресурсы показаны справа.",
    purpose: "Задача",
    responsibility: "Ответственный",
    contract: "Результат цикла",
    resources: "Как планируется выполнять цикл",
    provider: "Провайдер",
    model: "Запланированная модель",
    reasoning: "Глубина рассуждения",
    skills: "Подключённые инструкции",
    guidance: "Рекомендуемые инструкции",
    mcp: "Подключения MCP",
    tools: "Инструменты",
    evidence: "Проверка",
    input: "Вход",
    output: "Выход",
    source: "Источник",
    technicalDetails: "Технические данные",
    executionPlan: "Как планируется выполнять этот цикл",
    profile: "Профиль исполнения",
    claims: "Обязательные проверки",
    artifacts: "Артефакты",
    notDeclared: "Не используется",
    noSkills: "Специальная инструкция не требуется",
    bindingPlan: "Утверждённый план",
    actualNote: "Это утверждённый план. Фактическое использование и расход токенов появятся только после записанного запуска.",
    open: "Открыть цикл",
    back: "На уровень выше",
    phaseBoundary: "Предложение готово. Включение новой версии требует отдельного решения оператора.",
    docs: "Открыть документ",
    revision: "Редакция",
    acceptedSource: "Утверждённые правила разработки",
    identifier: "Идентификатор",
    childCount: "Вложенных циклов",
    noChildCount: "Нет вложенных циклов",
    path: "Путь",
    level: "Уровень",
    whatItDoes: "Что делает",
    needs: "Что нужно",
    produces: "Что получится",
    resourcesOptional: "Модели, инструкции и инструменты",
  },
};

const phaseCopy = {
  observe: { code: "O", ru: "Собрать факты с указанием источника." },
  negotiate: { code: "N", ru: "Превратить неоднозначность в принятое решение." },
  bind: { code: "B", ru: "Зафиксировать точные границы и полномочия." },
  execute: { code: "X", ru: "Создать один результат в разрешённых границах." },
  verify: { code: "V", ru: "Независимо проверить этот результат." },
  publish: { code: "P", ru: "Выполнить только явно разрешённое внешнее изменение." },
  evolve: { code: "E", ru: "Подготовить новую версию без её включения." },
};

const storedLanguage = localStorage.getItem("concordloom-language");
const requestedLanguage = new URLSearchParams(location.search).get("lang");
let language =
  (["en", "ru"].includes(requestedLanguage) ? requestedLanguage : null)
  || (["en", "ru"].includes(storedLanguage) ? storedLanguage : null)
  || "en";
let atlasData = null;
let contentData = null;
let selectedLoopId = null;
let previousLoopId = null;

function text(key) {
  return copy[language][key];
}

function loopCopy(loop) {
  return loop.copy[language];
}

function currentRoute() {
  const raw = location.hash.replace(/^#/, "");
  const [candidate, detail] = raw.split("/");
  const views = new Set(["concept", "theory", "quickstart", "atlas", "docs"]);
  return {
    view: views.has(candidate) ? candidate : "concept",
    detail: detail ? decodeURIComponent(detail) : null,
  };
}

function setView(viewName) {
  document.querySelectorAll("[data-view]").forEach((view) => {
    const active = view.dataset.view === viewName;
    view.hidden = !active;
    view.classList.toggle("is-active", active);
  });
  document.querySelectorAll("[data-view-link]").forEach((link) => {
    const active = link.dataset.viewLink === viewName;
    link.classList.toggle("is-active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  document.querySelector(".view-tabs").classList.remove("is-open");
  document.querySelector(".menu-switch").setAttribute("aria-expanded", "false");
}

function applyLanguage(nextLanguage) {
  language = nextLanguage;
  document.documentElement.lang = language;
  localStorage.setItem("concordloom-language", language);
  document.querySelectorAll("[data-en][data-ru]").forEach((element) => {
    element.textContent = element.dataset[language];
  });
  document.querySelectorAll("[data-en-content][data-ru-content]").forEach((element) => {
    element.setAttribute("content", element.dataset[`${language}Content`]);
  });
  document.querySelectorAll("[data-en-aria-label][data-ru-aria-label]").forEach((element) => {
    element.setAttribute("aria-label", element.dataset[`${language}AriaLabel`]);
  });
  document.querySelectorAll("[data-en-alt][data-ru-alt]").forEach((element) => {
    element.setAttribute("alt", element.dataset[`${language}Alt`]);
  });
  const switcher = document.querySelector(".language-switch");
  switcher.querySelector("[data-lang-label]").textContent = language === "en" ? "RU" : "EN";
  switcher.setAttribute("aria-label", text("switchLanguage"));
  renderGrammar();
  renderReading();
  renderDocs();
  renderAtlas();
}

function persistLanguageInUrl() {
  const url = new URL(location.href);
  url.searchParams.set("lang", language);
  history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}

function renderGrammar() {
  if (!atlasData) return;
  const list = document.querySelector("[data-run-grammar]");
  list.innerHTML = "";
  atlasData.sharedRunGrammar.forEach((phase, index) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    const localized = phase.copy[language];
    button.type = "button";
    button.dataset.stage = phase.id;
    button.setAttribute("aria-pressed", index === 0 ? "true" : "false");
    button.innerHTML = `<b>${phaseCopy[phase.id].code}</b><span>${localized.label}</span>`;
    button.addEventListener("click", () => {
      list.querySelectorAll("button").forEach((entry) => entry.setAttribute("aria-pressed", "false"));
      button.setAttribute("aria-pressed", "true");
      document.querySelector("[data-stage-code]").textContent = phaseCopy[phase.id].code;
      document.querySelector("[data-stage-copy]").textContent =
        language === "ru" ? phaseCopy[phase.id].ru : localized.purpose;
    });
    item.append(button);
    list.append(item);
  });
  const first = atlasData.sharedRunGrammar[0];
  document.querySelector("[data-stage-code]").textContent = phaseCopy[first.id].code;
  document.querySelector("[data-stage-copy]").textContent =
    language === "ru" ? phaseCopy[first.id].ru : first.copy.en.purpose;
}

function renderReading() {
  if (!contentData) return;
  ["article", "quickstart"].forEach((section) => {
    const source = contentData[section][language];
    const body = document.querySelector(`[data-content-body="${section}"]`);
    const toc = document.querySelector(`[data-content-toc="${section}"]`);
    body.innerHTML = source.html;
    toc.innerHTML = "";
    const heading = document.createElement("strong");
    heading.textContent = language === "en" ? "On this page" : "На этой странице";
    toc.append(heading);
    source.toc.slice(1).forEach((entry) => {
      const link = document.createElement("a");
      const viewName = section === "article" ? "theory" : "quickstart";
      link.href = `#${viewName}/${entry.id}`;
      link.textContent = entry.title;
      toc.append(link);
    });
  });
}

function renderDocs() {
  if (!contentData) return;
  const grid = document.querySelector("[data-docs-grid]");
  grid.innerHTML = "";
  contentData.documents.forEach((documentData) => {
    const article = document.createElement("article");
    const title = language === "en" ? documentData.enTitle : documentData.ruTitle;
    const url = language === "en" ? documentData.enUrl : documentData.ruUrl;
    article.innerHTML = `
      <h2>${title}</h2>
      <a href="${url}">${text("docs")} ↗</a>
    `;
    grid.append(article);
  });
}

function atlasLoop(id) {
  return atlasData?.loops.find((loop) => loop.id === id);
}

function atlasLink(loop, className = "") {
  const link = document.createElement("a");
  const childCount = loop.children.length;
  link.className = className;
  link.href = `#atlas/${encodeURIComponent(loop.id)}`;
  link.dataset.loopId = loop.id;
  link.setAttribute(
    "aria-label",
    `${loopCopy(loop).label}. ${
      childCount ? `${text("childCount")}: ${childCount}` : text("noChildCount")
    }`,
  );
  link.innerHTML = `
    <span aria-hidden="true">${childCount ? String(childCount).padStart(2, "0") : "•"}</span>
    <strong>${loopCopy(loop).label}</strong>
    <small>${loopCopy(loop).purpose}</small>
  `;
  return link;
}

function renderBreadcrumbs(loop) {
  const path = [];
  let cursor = loop;
  while (cursor) {
    path.unshift(cursor);
    cursor = cursor.parentId ? atlasLoop(cursor.parentId) : null;
  }
  const breadcrumbs = document.querySelector("[data-atlas-breadcrumbs]");
  const history = document.querySelector("[data-atlas-history]");
  breadcrumbs.innerHTML = "";
  history.innerHTML = "";
  path.forEach((entry, index) => {
    if (index) {
      const separator = document.createElement("span");
      separator.textContent = "/";
      separator.setAttribute("aria-hidden", "true");
      breadcrumbs.append(separator);
    }
    const link = document.createElement("a");
    link.href = `#atlas/${encodeURIComponent(entry.id)}`;
    link.textContent = loopCopy(entry).label;
    if (index === path.length - 1) link.setAttribute("aria-current", "page");
    breadcrumbs.append(link);

    const item = document.createElement("li");
    const historyLink = document.createElement("a");
    historyLink.href = `#atlas/${encodeURIComponent(entry.id)}`;
    historyLink.innerHTML = `
      <strong>${loopCopy(entry).label}</strong>
      <small>${text("level")} ${String(index + 1).padStart(2, "0")}</small>
    `;
    if (index === path.length - 1) historyLink.setAttribute("aria-current", "page");
    item.append(historyLink);
    history.append(item);
  });
}

function renderInspector(loop) {
  const profile = atlasData.profiles[loop.profile];
  const route = loop.route_materialization;
  const inspector = document.querySelector("[data-atlas-inspector]");
  const boundSkills = route.skills.length
    ? route.skills
        .map((skill) => `<li><code>${skill.id}@${skill.version}</code></li>`)
        .join("")
    : `<li>${text("notDeclared")}</li>`;
  const skills = profile.skills.length
    ? profile.skills.map((skill) => `<li><code>${skill}</code></li>`).join("")
    : `<li>${text("noSkills")}</li>`;
  const tools = route.tool_capabilities.length
    ? route.tool_capabilities.map((tool) => `<li><code>${tool}</code></li>`).join("")
    : `<li>${text("notDeclared")}</li>`;
  const mcp = route.mcp_servers.length
    ? route.mcp_servers.map((server) => `<code>${server}</code>`).join(" ")
    : text("notDeclared");
  const provider = route.model === "none" ? text("notDeclared") : route.model_provider;
  const technical = `
    <details class="technical-details">
      <summary>${text("technicalDetails")}</summary>
      <dl class="contract-grid">
        <div><dt>${text("identifier")}</dt><dd><code>${loop.id}</code></dd></div>
        <div><dt>${text("profile")}</dt><dd><code>${loop.profile}</code></dd></div>
        <div><dt>${text("artifacts")}</dt><dd>${loop.artifacts.map((item) => `<code>${item}</code>`).join(" ")}</dd></div>
        <div><dt>${text("claims")}</dt><dd>${loop.requiredClaims.map((item) => `<code>${item}</code>`).join(" ")}</dd></div>
        <div><dt>${text("source")}</dt><dd>${text("acceptedSource")}</dd></div>
      </dl>
    </details>
  `;
  inspector.innerHTML = `
    <p class="instrument-label">${text("current")}</p>
    <h2>${loopCopy(loop).label}</h2>
    <p class="inspector-purpose">${loopCopy(loop).purpose}</p>
    <dl class="contract-grid">
      <div><dt>${text("whatItDoes")}</dt><dd>${loopCopy(loop).purpose}</dd></div>
      <div><dt>${text("needs")}</dt><dd>${loop.contract[language].input}</dd></div>
      <div><dt>${text("produces")}</dt><dd>${loop.contract[language].output}</dd></div>
    </dl>
    <details class="resource-panel">
      <summary>${text("resourcesOptional")}</summary>
      <dl>
        <div><dt>${text("provider")}</dt><dd><code>${provider}</code></dd></div>
        <div><dt>${text("model")}</dt><dd><code>${route.model}</code></dd></div>
        <div><dt>${text("reasoning")}</dt><dd><code>${route.reasoning}</code></dd></div>
        <div><dt>${text("skills")}</dt><dd><ul>${boundSkills}</ul></dd></div>
        <div><dt>${text("guidance")}</dt><dd><ul>${skills}</ul></dd></div>
        <div><dt>${text("mcp")}</dt><dd>${mcp}</dd></div>
        <div><dt>${text("tools")}</dt><dd><ul>${tools}</ul></dd></div>
      </dl>
      <p>${text("actualNote")}</p>
    </details>
    ${technical}
    <section class="inner-grammar">
      <p class="section-label">${language === "en" ? "SHARED INNER RUN" : "ОБЩАЯ СХЕМА ЗАПУСКА"}</p>
      <ol>${atlasData.sharedRunGrammar.map((phase) => `<li><span>${phaseCopy[phase.id].code}</span>${phase.copy[language].label}</li>`).join("")}</ol>
    </section>
  `;
}

const SVG_NS = "http://www.w3.org/2000/svg";

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(SVG_NS, name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function graphLabel(textValue) {
  const words = textValue.split(/\s+/);
  if (words.length < 3 || textValue.length < 19) return [textValue];
  let first = "";
  let second = "";
  words.forEach((word) => {
    if (!second && `${first} ${word}`.trim().length <= Math.ceil(textValue.length / 2)) {
      first = `${first} ${word}`.trim();
    } else {
      second = `${second} ${word}`.trim();
    }
  });
  return second ? [first, second] : [first];
}

function appendGraphNode(svg, loop, x, y, radius, current = false) {
  const link = svgElement("a", {
    href: current ? `#atlas/${encodeURIComponent(loop.id)}` : `#atlas/${encodeURIComponent(loop.id)}`,
    class: `graph-node${current ? " is-current" : ""}`,
    "data-loop-id": loop.id,
    "aria-label": `${loopCopy(loop).label}. ${
      loop.children.length ? `${text("childCount")}: ${loop.children.length}` : text("noChildCount")
    }`,
  });
  const title = svgElement("title");
  title.textContent = `${loopCopy(loop).label}. ${loopCopy(loop).purpose}`;
  link.append(title);
  link.append(svgElement("circle", { class: "node-outer", cx: x, cy: y, r: radius + 10 }));
  link.append(svgElement("circle", { class: "node-inner", cx: x, cy: y, r: radius }));
  link.append(svgElement("circle", {
    class: "node-bezel",
    cx: x,
    cy: y,
    r: Math.max(radius - 8, 12),
  }));

  const count = svgElement("text", {
    class: "node-count",
    x,
    y: current ? y - 25 : y + 4,
    "text-anchor": "middle",
  });
  count.textContent = String(loop.children.length).padStart(current ? 2 : 1, "0");
  link.append(count);

  const label = svgElement("text", {
    class: "node-label",
    x,
    y: current ? y - 2 : y + radius + 35,
    "text-anchor": "middle",
  });
  graphLabel(loopCopy(loop).label).slice(0, current ? 3 : 2).forEach((line, index) => {
    const span = svgElement("tspan", { x, dy: index ? 19 : 0 });
    span.textContent = line;
    label.append(span);
  });
  link.append(label);
  svg.append(link);
}

function appendParentConstellation(svg, parent, selectedChild, x, y) {
  const group = svgElement("g", { class: "parent-constellation" });
  const parentLink = svgElement("a", {
    href: `#atlas/${encodeURIComponent(parent.id)}`,
    "aria-label": `${text("back")}: ${loopCopy(parent).label}`,
  });
  const title = svgElement("title");
  title.textContent = `${text("back")}: ${loopCopy(parent).label}`;
  parentLink.append(title);
  parentLink.append(svgElement("circle", {
    class: "parent-housing",
    cx: x,
    cy: y,
    r: 52,
  }));
  parentLink.append(svgElement("circle", {
    class: "parent-core",
    cx: x,
    cy: y,
    r: 34,
  }));
  group.append(parentLink);

  const siblings = parent.children.map(atlasLoop);
  siblings.forEach((sibling, index) => {
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / Math.max(siblings.length, 1);
    const nodeX = x + Math.cos(angle) * 92;
    const nodeY = y + Math.sin(angle) * 78;
    group.append(svgElement("line", {
      class: sibling.id === selectedChild.id ? "parent-thread is-active" : "parent-thread",
      x1: x,
      y1: y,
      x2: nodeX,
      y2: nodeY,
    }));
    group.append(svgElement("circle", {
      class: sibling.id === selectedChild.id ? "parent-node is-active" : "parent-node",
      cx: nodeX,
      cy: nodeY,
      r: sibling.id === selectedChild.id ? 10 : 6,
    }));
  });
  svg.append(group);
}

function renderGraph(loop) {
  const svg = document.querySelector("[data-atlas-graph]");
  const stage = document.querySelector("[data-atlas-stage]");
  svg.innerHTML = "";
  const compact = window.matchMedia("(max-width: 560px)").matches;
  svg.setAttribute("viewBox", compact ? "180 70 640 600" : "0 0 1000 760");

  const previous = previousLoopId ? atlasLoop(previousLoopId) : null;
  let motion = "none";
  if (previous && loop.parentId === previous.id) motion = "forward";
  else if (previous && previous.parentId === loop.id) motion = "back";
  else if (previous && previous.id !== loop.id) motion = "side";

  stage.removeAttribute("data-motion");
  if (motion !== "none" && !reducedMotion.matches) {
    requestAnimationFrame(() => {
      stage.dataset.motion = motion;
    });
  }

  const parent = !compact && loop.parentId ? atlasLoop(loop.parentId) : null;
  const centerX = parent ? 625 : 500;
  const centerY = 370;
  [parent ? 285 : 310, parent ? 215 : 225, 118].forEach((radius, index) => {
    svg.append(svgElement("circle", {
      class: `graph-ring${index === 1 ? " is-signal" : ""}`,
      cx: centerX,
      cy: centerY,
      r: radius,
    }));
  });

  if (parent) {
    appendParentConstellation(svg, parent, loop, 132, centerY);
    svg.append(svgElement("path", {
      class: "level-thread",
      d: `M 236 ${centerY} C 330 ${centerY}, 390 ${centerY}, ${centerX - 118} ${centerY}`,
    }));
    [0.25, 0.5, 0.75].forEach((progress) => {
      svg.append(svgElement("circle", {
        class: "level-thread-marker",
        cx: 236 + (centerX - 118 - 236) * progress,
        cy: centerY,
        r: 3,
      }));
    });
  }

  const children = loop.children.map(atlasLoop);
  const positions = children.map((child, index) => {
    const count = Math.max(children.length, 1);
    const ring = children.length > 8 && index % 2 ? 248 : 208;
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count;
    return {
      child,
      x: centerX + Math.cos(angle) * ring,
      y: centerY + Math.sin(angle) * ring * 0.82,
    };
  });

  positions.forEach(({ x, y }) => {
    svg.append(svgElement("path", {
      class: "graph-link",
      d: `M ${centerX} ${centerY} C ${centerX} ${(centerY + y) / 2}, ${x} ${(centerY + y) / 2}, ${x} ${y}`,
    }));
    const dotX = centerX + (x - centerX) * 0.56;
    const dotY = centerY + (y - centerY) * 0.56;
    svg.append(svgElement("circle", { class: "graph-link-dot", cx: dotX, cy: dotY, r: 3 }));
  });

  positions.forEach(({ child, x, y }) => appendGraphNode(svg, child, x, y, 34));
  appendGraphNode(svg, loop, centerX, centerY, 78, true);
  previousLoopId = loop.id;
}

function renderAtlas() {
  if (!atlasData) return;
  const rootId = atlasData.binding.rootLoopIds[0];
  const requested = currentRoute().view === "atlas" ? currentRoute().detail : null;
  selectedLoopId = atlasLoop(requested) ? requested : (selectedLoopId && atlasLoop(selectedLoopId) ? selectedLoopId : rootId);
  const loop = atlasLoop(selectedLoopId);
  const revision = atlasData.binding.id.match(/-v(\d+)$/)?.[1] || "?";
  document.querySelector("[data-product-release]").textContent = atlasData.product.release;
  document.querySelector("[data-atlas-binding]").textContent = `${text("revision")} ${revision}`;
  document.querySelector("[data-atlas-binding]").title = atlasData.binding.digest;
  document.querySelector("[data-atlas-root]").textContent = loopCopy(atlasLoop(rootId)).label;
  document.querySelector("[data-atlas-count]").textContent = atlasData.loops.length;
  document.querySelector("[data-atlas-provenance]").textContent =
    `${text("acceptedSource")} / ${atlasData.binding.digest.slice(0, 19)}…`;

  renderBreadcrumbs(loop);
  renderInspector(loop);
  renderGraph(loop);
  const empty = document.querySelector("[data-atlas-empty]");
  empty.hidden = loop.children.length > 0;
  empty.textContent = text("leaf");

  const circuit = document.querySelector("[data-evolution-circuit]");
  circuit.innerHTML = "";
  atlasData.evolutionCircuit.forEach((id, index) => {
    const circuitLoop = atlasLoop(id);
    const item = document.createElement("li");
    item.append(atlasLink(circuitLoop, "circuit-link"));
    if (index === 1) {
      const boundary = document.createElement("p");
      boundary.className = "activation-stop";
      boundary.textContent = text("phaseBoundary");
      item.append(boundary);
    }
    circuit.append(item);
  });

  const outline = document.querySelector("[data-atlas-outline]");
  outline.innerHTML = "";
  const tree = document.createElement("ul");
  function appendBranch(parentElement, node) {
    const item = document.createElement("li");
    const link = document.createElement("a");
    link.href = `#atlas/${encodeURIComponent(node.id)}`;
    link.textContent = loopCopy(node).label;
    item.append(link);
    if (node.children.length) {
      const nested = document.createElement("ul");
      node.children.map(atlasLoop).forEach((child) => appendBranch(nested, child));
      item.append(nested);
    }
    parentElement.append(item);
  }
  appendBranch(tree, atlasLoop(rootId));
  outline.append(tree);
}

function renderError() {
  document.querySelectorAll("[data-atlas-binding], [data-atlas-root]").forEach((element) => {
    element.textContent = text("loadError");
  });
  document.querySelectorAll("[data-content-body]").forEach((element) => {
    element.innerHTML = `<p class="load-error">${text("loadError")}</p>`;
  });
}

function revealVisible() {
  document.querySelectorAll(".reveal:not(.is-visible)").forEach((element) => {
    element.classList.add("is-visible");
  });
}

const revealObserver = "IntersectionObserver" in window
  ? new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        revealObserver.unobserve(entry.target);
      });
    }, { rootMargin: "0px 0px -6% 0px" })
  : null;

function observeReveals() {
  if (!revealObserver) {
    revealVisible();
    return;
  }
  document.querySelectorAll(".reveal:not(.is-visible)").forEach((element) => {
    revealObserver.observe(element);
  });
}

function route() {
  const next = currentRoute();
  setView(next.view);
  if (next.view === "atlas") {
    selectedLoopId = next.detail;
    renderAtlas();
  }
  if (["theory", "quickstart"].includes(next.view) && next.detail) {
    requestAnimationFrame(() => document.getElementById(next.detail)?.scrollIntoView());
  }
  requestAnimationFrame(observeReveals);
}

document.querySelector(".language-switch").addEventListener("click", () => {
  applyLanguage(language === "en" ? "ru" : "en");
  persistLanguageInUrl();
});

document.querySelector(".menu-switch").addEventListener("click", (event) => {
  const nav = document.querySelector(".view-tabs");
  const open = !nav.classList.contains("is-open");
  nav.classList.toggle("is-open", open);
  event.currentTarget.setAttribute("aria-expanded", String(open));
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    document.querySelector(".view-tabs").classList.remove("is-open");
    document.querySelector(".menu-switch").setAttribute("aria-expanded", "false");
    document.querySelector(".menu-switch").focus();
  }
});

window.addEventListener("hashchange", route);

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const compactAtlas = window.matchMedia("(max-width: 560px)");
compactAtlas.addEventListener?.("change", () => {
  if (atlasData && currentRoute().view === "atlas") renderAtlas();
});
Promise.all([
  fetch("data/atlas.json").then((response) => {
    if (!response.ok) throw new Error(`Atlas ${response.status}`);
    return response.json();
  }),
  fetch("data/content.json").then((response) => {
    if (!response.ok) throw new Error(`Content ${response.status}`);
    return response.json();
  }),
])
  .then(([atlas, content]) => {
    atlasData = atlas;
    contentData = content;
    applyLanguage(language);
    route();
  })
  .catch(() => {
    applyLanguage(language);
    renderError();
    route();
  });

applyLanguage(language);
route();
observeReveals();
