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
  document.body.dataset.activeView = viewName;
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

function hasAtlasAncestor(loopId, ancestorId) {
  if (!atlasData || !loopId) return false;
  let current = atlasLoop(loopId);
  while (current) {
    if (current.id === ancestorId) return true;
    current = current.parentId ? atlasLoop(current.parentId) : null;
  }
  return false;
}

function renderSystemRail(routeState) {
  let active = "map";
  if (routeState.view === "quickstart") active = "build";
  if (routeState.view === "theory" || routeState.view === "docs") active = "verify";
  if (routeState.view === "atlas" && atlasData) {
    const loopId = routeState.detail || atlasData.binding.rootLoopIds[0];
    if (hasAtlasAncestor(loopId, "system-evolution")) active = "evolve";
    else if (hasAtlasAncestor(loopId, "release-distribution")) active = "publish";
    else if (hasAtlasAncestor(loopId, "trust-assurance")) active = "verify";
    else if (hasAtlasAncestor(loopId, "runtime-tooling")) active = "build";
  }
  document.querySelectorAll("[data-system-stage]").forEach((item) => {
    const selected = item.dataset.systemStage === active;
    item.classList.toggle("is-active", selected);
    if (selected) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  });
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
  const loopIndex = atlasData.loops.findIndex((entry) => entry.id === loop.id) + 1;
  const loopCode = `LOOP ${String(loopIndex).padStart(2, "0")}.${loop.children.length ? "A" : "T"}`;
  const glyph = loopGlyph(loop);
  const boundSkills = route.skills.length
    ? route.skills
        .map((skill) => `<li><code translate="no">${skill.id}@${skill.version}</code></li>`)
        .join("")
    : `<li>${text("notDeclared")}</li>`;
  const skills = profile.skills.length
    ? profile.skills.map((skill) => `<li><code translate="no">${skill}</code></li>`).join("")
    : `<li>${text("noSkills")}</li>`;
  const tools = route.tool_capabilities.length
    ? route.tool_capabilities.map((tool) => `<li><code translate="no">${tool}</code></li>`).join("")
    : `<li>${text("notDeclared")}</li>`;
  const mcp = route.mcp_servers.length
    ? route.mcp_servers.map((server) => `<code translate="no">${server}</code>`).join(" ")
    : text("notDeclared");
  const provider = route.model === "none" ? text("notDeclared") : route.model_provider;
  const technical = `
    <details class="technical-details">
      <summary>${text("technicalDetails")}</summary>
      <dl class="contract-grid">
        <div><dt>${text("identifier")}</dt><dd><code translate="no">${loop.id}</code></dd></div>
        <div><dt>${text("profile")}</dt><dd><code translate="no">${loop.profile}</code></dd></div>
        <div><dt>${text("artifacts")}</dt><dd>${loop.artifacts.map((item) => `<code translate="no">${item}</code>`).join(" ")}</dd></div>
        <div><dt>${text("claims")}</dt><dd>${loop.requiredClaims.map((item) => `<code translate="no">${item}</code>`).join(" ")}</dd></div>
        <div><dt>${text("source")}</dt><dd>${text("acceptedSource")}</dd></div>
      </dl>
    </details>
  `;
  inspector.innerHTML = `
    <div class="inspector-status">
      <i aria-hidden="true"></i>
      <span>${loop.children.length ? (language === "ru" ? "Открытый цикл" : "Open loop") : (language === "ru" ? "Конечный цикл" : "Terminal loop")}</span>
    </div>
    <p class="inspector-code" translate="no">${loopCode}</p>
    <h2>${loopCopy(loop).label}</h2>
    <div class="inspector-dial" aria-hidden="true">
      <img src="assets/signal-dial-core.png" width="1254" height="1254" alt="">
      <span>${glyph}</span>
    </div>
    <p class="inspector-purpose">${loopCopy(loop).purpose}</p>
    <dl class="inspector-contract">
      <div><dt>${text("needs")}</dt><dd>${loop.contract[language].input}</dd></div>
      <div><dt>${text("produces")}</dt><dd>${loop.contract[language].output}</dd></div>
    </dl>
    <details class="resource-panel">
      <summary>${text("resourcesOptional")}</summary>
      <dl>
        <div><dt>${text("provider")}</dt><dd><code translate="no">${provider}</code></dd></div>
        <div><dt>${text("model")}</dt><dd><code translate="no">${route.model}</code></dd></div>
        <div><dt>${text("reasoning")}</dt><dd><code translate="no">${route.reasoning}</code></dd></div>
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
    ${loop.parentId ? `<a class="atlas-back" href="#atlas/${encodeURIComponent(loop.parentId)}">← ${text("back")}: ${loopCopy(atlasLoop(loop.parentId)).label}</a>` : ""}
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
  if (words.length < 2 || textValue.length < 19) return [textValue];
  let first = "";
  let second = "";
  words.forEach((word) => {
    if (!first) {
      first = word;
    } else if (!second && `${first} ${word}`.length <= Math.ceil(textValue.length / 2)) {
      first = `${first} ${word}`.trim();
    } else {
      second = `${second} ${word}`.trim();
    }
  });
  return second ? [first, second] : [first];
}

const LOOP_GLYPHS = ["◉", "⌬", "⊕", "◇", "⧉", "⌁", "⊙", "✣", "⟲", "◌", "⌘", "⦿"];

function loopGlyph(loop) {
  let hash = 0;
  for (const character of loop.id) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  return LOOP_GLYPHS[hash % LOOP_GLYPHS.length];
}

function appendGraphDefs(svg) {
  const defs = svgElement("defs");
  const metal = svgElement("radialGradient", { id: "node-metal", cx: "42%", cy: "34%" });
  [
    ["0%", "#5b5d58"],
    ["18%", "#242622"],
    ["62%", "#0c0e0c"],
    ["84%", "#2d302b"],
    ["100%", "#050605"],
  ].forEach(([offset, color]) => metal.append(svgElement("stop", { offset, "stop-color": color })));
  defs.append(metal);

  const core = svgElement("radialGradient", { id: "node-core", cx: "50%", cy: "40%" });
  [
    ["0%", "#1e211c"],
    ["65%", "#0b0d0b"],
    ["100%", "#030403"],
  ].forEach(([offset, color]) => core.append(svgElement("stop", { offset, "stop-color": color })));
  defs.append(core);

  const signal = svgElement("filter", {
    id: "signal-glow",
    x: "-80%",
    y: "-80%",
    width: "260%",
    height: "260%",
  });
  signal.append(svgElement("feGaussianBlur", { stdDeviation: "4", result: "blur" }));
  const merge = svgElement("feMerge");
  merge.append(svgElement("feMergeNode", { in: "blur" }));
  merge.append(svgElement("feMergeNode", { in: "SourceGraphic" }));
  signal.append(merge);
  defs.append(signal);

  const shadow = svgElement("filter", {
    id: "node-shadow",
    x: "-60%",
    y: "-60%",
    width: "220%",
    height: "220%",
  });
  shadow.append(svgElement("feDropShadow", {
    dx: "4",
    dy: "9",
    stdDeviation: "8",
    "flood-color": "#000000",
    "flood-opacity": ".9",
  }));
  defs.append(shadow);
  svg.append(defs);
}

function appendGraphNode(
  svg,
  loop,
  x,
  y,
  radius,
  current = false,
  labelOffset = 0,
  labelYOffset = 0,
) {
  const group = svgElement("g", {
    class: `node-assembly${current ? " is-current" : ""}`,
    transform: `translate(${x} ${y})`,
  });
  const link = svgElement("a", {
    href: `#atlas/${encodeURIComponent(loop.id)}`,
    class: `graph-node${current ? " is-current" : ""}`,
    "data-loop-id": loop.id,
    "aria-label": `${loopCopy(loop).label}. ${
      loop.children.length ? `${text("childCount")}: ${loop.children.length}` : text("noChildCount")
    }`,
  });
  const title = svgElement("title");
  title.textContent = `${loopCopy(loop).label}. ${loopCopy(loop).purpose}`;
  link.append(title);
  link.append(svgElement("circle", { class: "node-shadow", cx: 0, cy: 0, r: radius + 14 }));
  link.append(svgElement("circle", { class: "node-outer", cx: 0, cy: 0, r: radius + 12 }));
  link.append(svgElement("circle", { class: "node-case", cx: 0, cy: 0, r: radius + 7 }));
  link.append(svgElement("circle", { class: "node-inner", cx: 0, cy: 0, r: radius }));
  link.append(svgElement("circle", {
    class: "node-bezel",
    cx: 0,
    cy: 0,
    r: Math.max(radius - 8, 12),
  }));
  link.append(svgElement("circle", {
    class: "node-etch",
    cx: 0,
    cy: 0,
    r: Math.max(radius - 15, 8),
  }));

  const boltRadius = radius + 8;
  const boltCount = current ? 12 : 6;
  for (let index = 0; index < boltCount; index += 1) {
    const angle = (Math.PI * 2 * index) / boltCount;
    link.append(svgElement("circle", {
      class: "node-bolt",
      cx: Math.cos(angle) * boltRadius,
      cy: Math.sin(angle) * boltRadius,
      r: current ? 2.4 : 1.7,
    }));
  }

  const count = svgElement("text", {
    class: "node-count",
    x: 0,
    y: current ? -31 : -radius - 19,
    "text-anchor": "middle",
  });
  count.textContent = String(loop.children.length).padStart(current ? 2 : 1, "0");
  link.append(count);

  const glyph = svgElement("text", {
    class: "node-glyph",
    x: 0,
    y: current ? 13 : 8,
    "text-anchor": "middle",
  });
  glyph.textContent = loopGlyph(loop);
  link.append(glyph);

  group.append(link);
  svg.append(group);
}

function appendConstellationRings(svg, x, y, radii, className) {
  radii.forEach((radius, index) => {
    svg.append(svgElement("circle", {
      class: `${className}${index === radii.length - 2 ? " is-signal" : ""}`,
      cx: x,
      cy: y,
      r: radius,
    }));
  });
}

function appendContextConstellation(svg, loop, selected, x, y) {
  const constellation = svgElement("g", { class: "parent-constellation" });
  const context = loop.parentId ? atlasLoop(loop.parentId) : loop;
  const items = context.children.map(atlasLoop);
  appendConstellationRings(constellation, x, y, [216, 166, 108], "context-ring");

  items.forEach((item, index) => {
    const count = Math.max(items.length, 1);
    const radius = items.length > 8 && index % 2 ? 190 : 148;
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count;
    const nodeX = x + Math.cos(angle) * radius;
    const nodeY = y + Math.sin(angle) * radius * 0.88;
    constellation.append(svgElement("line", {
      class: item.id === selected.id ? "context-thread is-active" : "context-thread",
      x1: x,
      y1: y,
      x2: nodeX,
      y2: nodeY,
    }));
    appendGraphNode(constellation, item, nodeX, nodeY, item.id === selected.id ? 26 : 20);
  });
  appendGraphNode(
    constellation,
    context,
    x,
    y,
    50,
    Boolean(loop.parentId && context.id === selected.id),
  );
  svg.append(constellation);
}

function renderGraph(loop) {
  const svg = document.querySelector("[data-atlas-graph]");
  const stage = document.querySelector("[data-atlas-stage]");
  svg.innerHTML = "";
  const compact = window.matchMedia("(max-width: 560px)").matches;
  svg.setAttribute("viewBox", compact ? "0 0 760 760" : "0 0 1600 760");
  appendGraphDefs(svg);

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

  const centerX = compact ? 380 : 1110;
  const centerY = compact ? 370 : 380;
  appendConstellationRings(
    svg,
    centerX,
    centerY,
    compact ? [320, 260, 198, 108] : [330, 275, 208, 112],
    "graph-ring",
  );

  if (!compact) {
    appendContextConstellation(svg, loop, loop, 315, centerY);
    svg.append(svgElement("path", {
      class: "level-thread",
      d: `M 535 ${centerY} C 650 ${centerY}, 770 ${centerY}, ${centerX - 112} ${centerY}`,
    }));
    [0.18, 0.36, 0.56, 0.76].forEach((progress) => {
      svg.append(svgElement("circle", {
        class: "level-thread-marker",
        cx: 535 + (centerX - 112 - 535) * progress,
        cy: centerY,
        r: progress === 0.56 ? 7 : 3,
      }));
    });
    const arrow = svgElement("text", {
      class: "level-thread-arrow",
      x: 810,
      y: centerY + 7,
      "text-anchor": "middle",
    });
    arrow.textContent = "▶";
    svg.append(arrow);
  }

  const children = loop.children.map(atlasLoop);
  const compactLabelOffsets = children.length > 8
    ? [0, 24, -24, -20, 0, 0, 0, 24, 0, -24]
    : [];
  const positions = children.map((child, index) => {
    const count = Math.max(children.length, 1);
    const ring = compact
      ? (children.length > 8 && index % 2 ? 272 : 220)
      : (children.length > 8 && index % 2 ? 272 : 218);
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count;
    return {
      child,
      index,
      x: centerX + Math.cos(angle) * ring,
      y: centerY + Math.sin(angle) * ring * 0.9,
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

  positions.forEach(({ child, index, x, y }) => appendGraphNode(
    svg,
    child,
    x,
    y,
    compact ? 28 : 30,
    false,
    compact ? (compactLabelOffsets[index] || 0) : 0,
    compact && index === 0 ? -28 : 0,
  ));
  appendGraphNode(svg, loop, centerX, centerY, compact ? 76 : 82, true);
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
  document.querySelector("[data-loop-count]").textContent = atlasData.loops.length;
  const outlineSummary = document.querySelector("[data-outline-summary]");
  outlineSummary.textContent = language === "ru"
    ? `Показать полную схему из ${atlasData.loops.length} циклов`
    : `Show the complete ${atlasData.loops.length}-cycle outline`;
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

let lastRoutedView = null;

function route() {
  const next = currentRoute();
  const atlasNavigationHadFocus = document.activeElement?.matches(
    ".graph-node, .atlas-back, .atlas-history a",
  );
  const restoreAtlasFocus =
    next.view === "atlas" &&
    lastRoutedView === "atlas" &&
    atlasNavigationHadFocus;
  setView(next.view);
  if (next.view === "atlas") {
    selectedLoopId = next.detail;
    renderAtlas();
    if (restoreAtlasFocus) {
      requestAnimationFrame(() => {
        document
          .querySelector(".graph-node.is-current")
          ?.focus({ preventScroll: true });
      });
    }
  }
  if (["theory", "quickstart"].includes(next.view) && next.detail) {
    requestAnimationFrame(() => {
      document.getElementById(next.detail)?.scrollIntoView({ block: "start" });
    });
  } else {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }
  renderSystemRail(next);
  lastRoutedView = next.view;
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
  if (event.key === "Tab" && !event.shiftKey && document.activeElement === document.body) {
    event.preventDefault();
    document.querySelector(".skip-link").focus();
    return;
  }
  if (event.key === "Escape") {
    document.querySelector(".view-tabs").classList.remove("is-open");
    document.querySelector(".menu-switch").setAttribute("aria-expanded", "false");
    document.querySelector(".menu-switch").focus();
  }
});

window.addEventListener("hashchange", route);
if ("scrollRestoration" in history) history.scrollRestoration = "manual";

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
document.body.focus({ preventScroll: true });
