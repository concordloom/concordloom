const copy = {
  en: {
    switchLanguage: "Switch to Russian",
    loading: "Loading accepted data",
    loadError: "The accepted projection could not be loaded. Reload the page or inspect the source repository.",
    current: "Current cycle",
    children: "Contained cycles",
    leaf: "This cycle has no smaller responsibility cycles. Open its shared run grammar and resources in the inspector.",
    purpose: "Purpose",
    responsibility: "Responsible role",
    contract: "Outcome contract",
    resources: "Planned resources",
    model: "Model intent",
    skills: "Skills",
    mcp: "MCP",
    tools: "Tools",
    evidence: "Evidence",
    input: "Input",
    output: "Output",
    source: "Source",
    notDeclared: "Not declared",
    noSkills: "No required skill",
    bindingPlan: "Accepted binding plan",
    actualNote: "Exact model, skills and tools become facts only when a run records them.",
    open: "Open cycle",
    back: "Up one level",
    phaseBoundary: "Evolve stops here. Activation is a separate operator act.",
    docs: "Open document",
  },
  ru: {
    switchLanguage: "Переключить на английский",
    loading: "Загружаются принятые данные",
    loadError: "Не удалось загрузить принятую проекцию. Перезагрузите страницу или откройте исходные данные в репозитории.",
    current: "Текущий цикл",
    children: "Вложенные циклы",
    leaf: "У этого цикла нет более мелких циклов ответственности. Общая схема запуска и ресурсы показаны справа.",
    purpose: "Задача",
    responsibility: "Ответственный",
    contract: "Результат цикла",
    resources: "Запланированные ресурсы",
    model: "Требования к модели",
    skills: "Скиллы",
    mcp: "MCP",
    tools: "Инструменты",
    evidence: "Проверка",
    input: "Вход",
    output: "Выход",
    source: "Источник",
    notDeclared: "Не задан",
    noSkills: "Обязательный скилл не задан",
    bindingPlan: "Принятый план",
    actualNote: "Точная модель, скиллы и инструменты становятся фактом только после записи запуска.",
    open: "Открыть цикл",
    back: "На уровень выше",
    phaseBoundary: "На этом Evolve заканчивается. Включение новой версии является отдельным решением оператора.",
    docs: "Открыть документ",
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
let language = (["en", "ru"].includes(requestedLanguage) ? requestedLanguage : null) || storedLanguage || (
  (navigator.languages || [navigator.language]).some((item) => item?.startsWith("ru"))
    ? "ru"
    : "en"
);
let atlasData = null;
let contentData = null;
let selectedLoopId = null;

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
  const switcher = document.querySelector(".language-switch");
  switcher.querySelector("[data-lang-label]").textContent = language === "en" ? "RU" : "EN";
  switcher.setAttribute("aria-label", text("switchLanguage"));
  renderGrammar();
  renderReading();
  renderDocs();
  renderAtlas();
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
      <span>${documentData.id}</span>
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
  link.className = className;
  link.href = `#atlas/${encodeURIComponent(loop.id)}`;
  link.dataset.loopId = loop.id;
  link.innerHTML = `
    <span>${loop.children.length ? String(loop.children.length).padStart(2, "0") : "•"}</span>
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
  breadcrumbs.innerHTML = "";
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
  });
}

function renderInspector(loop) {
  const profile = atlasData.profiles[loop.profile];
  const inspector = document.querySelector("[data-atlas-inspector]");
  const skills = profile.skills.length
    ? profile.skills.map((skill) => `<li><code>${skill}</code></li>`).join("")
    : `<li>${text("noSkills")}</li>`;
  const tools = profile.tools.map((tool) => `<li><code>${tool}</code></li>`).join("");
  inspector.innerHTML = `
    <p class="section-label">${text("current")}</p>
    <h2>${loopCopy(loop).label}</h2>
    <code class="loop-id">${loop.id}</code>
    <p class="inspector-purpose">${loopCopy(loop).purpose}</p>
    <dl class="contract-grid">
      <div><dt>${text("responsibility")}</dt><dd>${loop.role[language]}</dd></div>
      <div><dt>${text("input")}</dt><dd>${loop.contract[language].input}</dd></div>
      <div><dt>${text("output")}</dt><dd>${loop.contract[language].output}</dd></div>
      <div><dt>${language === "en" ? "Artifacts" : "Артефакты"}</dt><dd>${loop.artifacts.map((item) => `<code>${item}</code>`).join(" ")}</dd></div>
      <div><dt>${text("evidence")}</dt><dd>${loop.requiredClaims.join(", ")}</dd></div>
    </dl>
    <section class="resource-panel">
      <div>
        <p class="section-label">${text("resources")} / ${text("bindingPlan")}</p>
        <strong>${loop.profile}</strong>
      </div>
      <dl>
        <div><dt>${text("model")}</dt><dd>${profile.model_intent[language]}</dd></div>
        <div><dt>${text("skills")}</dt><dd><ul>${skills}</ul></dd></div>
        <div><dt>${text("mcp")}</dt><dd>${profile.mcp.status === "not-declared" ? text("notDeclared") : profile.mcp.status}</dd></div>
        <div><dt>${text("tools")}</dt><dd><ul>${tools}</ul></dd></div>
        <div><dt>${text("source")}</dt><dd>${profile.truth_layer} / active binding</dd></div>
      </dl>
      <p>${text("actualNote")}</p>
    </section>
    <section class="inner-grammar">
      <p class="section-label">${language === "en" ? "SHARED INNER RUN" : "ОБЩАЯ СХЕМА ЗАПУСКА"}</p>
      <ol>${atlasData.sharedRunGrammar.map((phase) => `<li><span>${phaseCopy[phase.id].code}</span>${phase.copy[language].label}</li>`).join("")}</ol>
    </section>
  `;
}

function renderAtlas() {
  if (!atlasData) return;
  const rootId = atlasData.binding.rootLoopIds[0];
  const requested = currentRoute().view === "atlas" ? currentRoute().detail : null;
  selectedLoopId = atlasLoop(requested) ? requested : (selectedLoopId && atlasLoop(selectedLoopId) ? selectedLoopId : rootId);
  const loop = atlasLoop(selectedLoopId);
  document.querySelector("[data-atlas-binding]").textContent = atlasData.binding.id;
  document.querySelector("[data-atlas-binding]").title = atlasData.binding.digest;
  document.querySelector("[data-atlas-root]").textContent = loopCopy(atlasLoop(rootId)).label;
  document.querySelector("[data-atlas-count]").textContent = atlasData.loops.length;
  document.querySelector("[data-atlas-provenance]").textContent =
    `${language === "en" ? "accepted binding" : "принятая версия"} / ${atlasData.binding.digest.slice(0, 19)}...`;

  renderBreadcrumbs(loop);
  renderInspector(loop);

  const parent = document.querySelector("[data-atlas-parent]");
  parent.innerHTML = "";
  parent.append(atlasLink(loop, "atlas-current"));

  const children = document.querySelector("[data-atlas-children]");
  children.innerHTML = "";
  loop.children.map(atlasLoop).forEach((child) => children.append(atlasLink(child, "atlas-child")));
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
    if (element.getBoundingClientRect().top < window.innerHeight * 0.94) {
      element.classList.add("is-visible");
    }
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
  requestAnimationFrame(revealVisible);
}

document.querySelector(".language-switch").addEventListener("click", () => {
  applyLanguage(language === "en" ? "ru" : "en");
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
window.addEventListener("scroll", revealVisible, { passive: true });

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const heroArt = document.querySelector(".hero-art");
if (heroArt && !reducedMotion.matches) {
  heroArt.addEventListener("pointermove", (event) => {
    const bounds = heroArt.getBoundingClientRect();
    const x = ((event.clientX - bounds.left) / bounds.width - 0.5) * -10;
    const y = ((event.clientY - bounds.top) / bounds.height - 0.5) * -8;
    heroArt.style.setProperty("--hero-x", `${x}px`);
    heroArt.style.setProperty("--hero-y", `${y}px`);
  });
  heroArt.addEventListener("pointerleave", () => {
    heroArt.style.setProperty("--hero-x", "0px");
    heroArt.style.setProperty("--hero-y", "0px");
  });
}

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
revealVisible();
