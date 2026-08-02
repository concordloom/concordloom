const copy = {
  en: {
    switchLanguage: "Switch to Russian",
    loading: "Loading accepted data…",
    loadingMap: "Loading the project map…",
    loadingAtlas: "Loading the accepted project map…",
    loadingDocs: "Loading the documentation index…",
    loadErrorMap: "The project map did not load. Reload the page. If the problem continues, inspect the source repository.",
    loadErrorDocs: "The documentation index did not load. Reload the page or open the source repository.",
    loadErrorContent: "This page did not load. Reload it or open the source document in the repository.",
    reload: "Reload the page",
    current: "Selected cycle",
    children: "Contained cycles",
    leaf: "No inner cycles. Select this cycle to see its input, result and run plan.",
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
    inspect: "View cycle details",
    openInside: "Open this cycle",
    selectedForDetails: "Selected for review",
    back: "Up one level",
    phaseBoundary: "Evolve stops here. Activation is a separate operator act.",
    docs: "Open document",
    revision: "Revision",
    acceptedSource: "From the accepted project map",
    bindingDigest: "Map fingerprint",
    identifier: "ID",
    childCount: "Contained cycles",
    noChildCount: "No contained cycles",
    path: "Path",
    level: "Level",
    whatItDoes: "What it does",
    needs: "Needs",
    produces: "Produces",
    resourcesOptional: "Models, skills and tools",
    closeInspector: "Close cycle details",
    openLoop: "Has inner cycles",
    terminalLoop: "No inner cycles",
    moreBelow: "More details below",
    routeRequired: "Describe the result you want first.",
    routeNoMatch: "No clear path yet. Name the concrete result, for example: “fix the Russian Quickstart” or “publish the verified site”.",
    routeAmbiguous: "This request may follow more than one path. Choose the closest result:",
    routeReady: "Suggested path found. Nothing has started.",
    routeTarget: "Result",
    routeArea: "Task area",
    routeActions: "What the work would actually do",
    routeAction: "Action",
    routeIncluded: "Included in the suggested path",
    routeEffectsNone: "Confirming this route creates an exact draft. A separate authorization is required before it can start. If authorized, it will use no network access and make no changes outside the repository. Nothing is running.",
    routeEffectsSome: "Confirming this route creates an exact draft. A separate authorization is required before it can start. If authorized, it may {network}. Possible changes outside the repository: {effects}. Nothing is running.",
    routeNetworkRead: "receive data from the network",
    routeNetworkWrite: "send data over the network",
  },
  ru: {
    switchLanguage: "Переключить на английский",
    loading: "Загружаются принятые данные…",
    loadingMap: "Загружаем карту проекта…",
    loadingAtlas: "Загружаем принятую карту проекта…",
    loadingDocs: "Загружаем список документов…",
    loadErrorMap: "Карта проекта не загрузилась. Обновите страницу. Если ошибка повторится, откройте данные в репозитории.",
    loadErrorDocs: "Список документов не загрузился. Обновите страницу или откройте документацию в репозитории.",
    loadErrorContent: "Страница не загрузилась. Обновите её или откройте исходный документ в репозитории.",
    reload: "Обновить страницу",
    current: "Выбранный цикл",
    children: "Вложенные циклы",
    leaf: "Внутри нет других циклов. Выберите этот цикл, чтобы увидеть вход, результат и план выполнения.",
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
    inspect: "Посмотреть сведения о цикле",
    openInside: "Перейти внутрь цикла",
    selectedForDetails: "Выбран для просмотра",
    back: "На уровень выше",
    phaseBoundary: "Предложение готово. Включение новой версии требует отдельного решения оператора.",
    docs: "Открыть документ",
    revision: "Редакция",
    acceptedSource: "Из принятой карты проекта",
    bindingDigest: "Отпечаток карты",
    identifier: "Идентификатор",
    childCount: "Вложенных циклов",
    noChildCount: "Нет вложенных циклов",
    path: "Путь",
    level: "Уровень",
    whatItDoes: "Что делает",
    needs: "Что нужно",
    produces: "Что получится",
    resourcesOptional: "Модели, инструкции и инструменты",
    closeInspector: "Закрыть сведения о цикле",
    openLoop: "Есть вложенные циклы",
    terminalLoop: "Без вложенных циклов",
    moreBelow: "Ниже — дополнительные сведения",
    routeRequired: "Сначала опишите, какой результат хотите получить.",
    routeNoMatch: "Пока не удалось подобрать точный путь. Назовите конкретный результат, например: «исправить русский быстрый старт» или «опубликовать проверенный сайт».",
    routeAmbiguous: "Запрос подходит к нескольким путям. Выберите ближайший результат:",
    routeReady: "Путь подобран. Ничего не запущено.",
    routeTarget: "Результат",
    routeArea: "Область задачи",
    routeActions: "Что будет сделано",
    routeAction: "Действие",
    routeIncluded: "Входит в предлагаемый путь",
    routeEffectsNone: "Подтверждение создаст точный черновик. Для запуска потребуется отдельная авторизация. После неё работа пройдёт без сети и изменений за пределами репозитория. Сейчас ничего не запущено.",
    routeEffectsSome: "Подтверждение создаст точный черновик. Для запуска потребуется отдельная авторизация. После неё работа сможет {network}. За пределами репозитория может произойти следующее: {effects}. Сейчас ничего не запущено.",
    routeNetworkRead: "получать данные из сети",
    routeNetworkWrite: "передавать данные по сети",
  },
};

const phaseCopy = {
  observe: {
    code: "O",
    en: "Gather facts",
    ru: "Собрать факты",
    enPurpose: "Record what is known and where it came from.",
    ruPurpose: "Зафиксировать, что известно и откуда это взято.",
  },
  negotiate: {
    code: "N",
    en: "Clarify intent",
    ru: "Уточнить намерение",
    enPurpose: "Resolve questions that can change the project map.",
    ruPurpose: "Разобрать вопросы, которые могут изменить карту проекта.",
  },
  bind: {
    code: "B",
    en: "Set the rules",
    ru: "Зафиксировать правила",
    enPurpose: "Turn accepted decisions into exact boundaries and permissions.",
    ruPurpose: "Превратить принятые решения в точные границы и разрешения.",
  },
  execute: {
    code: "X",
    en: "Do the work",
    ru: "Выполнить работу",
    enPurpose: "Create one result within the accepted boundaries.",
    ruPurpose: "Создать один результат в принятых границах.",
  },
  verify: {
    code: "V",
    en: "Check the result",
    ru: "Проверить результат",
    enPurpose: "Check the exact result against the agreed requirements.",
    ruPurpose: "Проверить точный результат по согласованным требованиям.",
  },
  publish: {
    code: "P",
    en: "Apply the result",
    ru: "Применить результат",
    enPurpose: "Perform only the separately authorized external action.",
    ruPurpose: "Выполнить только отдельно разрешённое внешнее действие.",
  },
  evolve: {
    code: "E",
    en: "Propose an improvement",
    ru: "Предложить улучшение",
    enPurpose: "Prepare a new version without activating it.",
    ruPurpose: "Подготовить новую версию, не включая её автоматически.",
  },
};

// Primary UI copy may explain stable machine terms in plain language.
// Exact IDs and accepted source values remain available under Technical details.
const loopPlainLanguageOverrides = {
  "prioritize-roadmap": {
    en: {
      output: "A list of next steps in execution order.",
      purpose: "Choose what to do first based on goals, time and available resources.",
    },
    ru: {
      output: "Список следующих шагов в порядке выполнения.",
      purpose: "Выбрать, что делать сначала, с учётом целей, сроков и доступных ресурсов.",
    },
  },
};

const documentGroups = [
  {
    en: "Start here",
    ru: "Начать",
    ids: ["quickstart", "atlas", "codex-plugin"],
  },
  {
    en: "Understand",
    ru: "Разобраться",
    ids: ["concepts", "article", "writing"],
  },
  {
    en: "Build",
    ru: "Собрать",
    ids: ["architecture", "spec-v0.1", "design-system"],
  },
  {
    en: "Govern",
    ru: "Управлять",
    ids: ["trust-model", "decisions", "release", "frontend-cycle-proposal"],
  },
  {
    en: "Research",
    ru: "Исследовать",
    ids: ["research-landscape"],
  },
];

const initialLanguage = document.documentElement.dataset.initialLanguage;
let language =
  (["en", "ru"].includes(initialLanguage) ? initialLanguage : null)
  || "en";
let atlasData = null;
let contentData = null;
let selectedLoopId = null;
let inspectedLoopId = null;
let previousLoopId = null;
let inspectorRequested = false;
let inspectorTrigger = null;
let pendingInspectorFocusFrame = null;
let pendingInspectorOpenFrame = null;
let focusGraphAfterRoute = false;
let dataLoadState = "loading";
let routePreview = null;
let routePreviewRequest = "";

function text(key) {
  return copy[language][key];
}

function renderDataLoadState() {
  const ready = dataLoadState === "ready";
  const failed = dataLoadState === "error";
  const routeSubmit = document.querySelector("[data-route-preview-submit]");
  if (routeSubmit) routeSubmit.disabled = !ready;
  const statuses = [
    ["[data-hero-status]", "loadingMap", "loadErrorMap"],
    ["[data-atlas-status]", "loadingAtlas", "loadErrorMap"],
    ["[data-docs-status]", "loadingDocs", "loadErrorDocs"],
  ];
  statuses.forEach(([selector, loadingKey, errorKey]) => {
    const status = document.querySelector(selector);
    if (!status) return;
    status.hidden = ready;
    const message = status.querySelector("p");
    if (message) message.textContent = failed ? text(errorKey) : text(loadingKey);
    const reload = status.querySelector("[data-reload-site]");
    if (reload) {
      reload.hidden = !failed;
      reload.textContent = text("reload");
    }
  });
  document.querySelectorAll("[data-content-status]").forEach((status) => {
    const needsLocalizedData = language === "ru" && !contentData;
    status.hidden = !needsLocalizedData;
    const message = status.querySelector("p");
    if (message) {
      message.textContent = failed ? text("loadErrorContent") : text("loading");
    }
    const reload = status.querySelector("[data-reload-site]");
    if (reload) {
      reload.hidden = !failed;
      reload.textContent = text("reload");
    }
  });
  document.querySelectorAll("[data-content-body]").forEach((body) => {
    body.hidden = language === "ru" && !contentData;
    body.closest(".reading-shell")
      ?.querySelector(".reading-toc")
      ?.toggleAttribute("hidden", language === "ru" && !contentData);
  });
  document.querySelectorAll("[data-atlas-entry]").forEach((entry) => {
    entry.setAttribute("aria-disabled", String(!ready));
    entry.tabIndex = ready ? 0 : -1;
  });
  if (!ready) {
    const count = failed ? "—" : "…";
    document.querySelectorAll("[data-loop-count], [data-atlas-count]").forEach((entry) => {
      entry.textContent = count;
    });
  }
}

function humanizeRuText(value) {
  if (language !== "ru") return value;
  return value
    .replace(
      /Детерминированная проекция Atlas только для чтения/g,
      "Детерминированная проекция Атласа только для чтения",
    )
    .replace(
      /Ограниченный плагин, скилл или набор проверок/g,
      "Плагин, инструкция для помощника или набор проверок с явными ограничениями",
    )
    .replace(
      /Зафиксированный набор Playwright и axe/g,
      "Зафиксированный набор браузерных проверок доступности",
    )
    .replace(
      /Данные HTTP, DOM и снимки экрана/g,
      "Данные о сетевом ответе и структуре страницы, а также снимки экрана",
    )
    .replace(
      /Локальная мастерская с обычным, длинным, загружаемым, пустым, ошибочным и устаревшим состояниями/g,
      "Локальная мастерская с компонентами в обычном состоянии, с длинным текстом, при загрузке, без данных, с ошибкой и с устаревшими данными",
    )
    .replace(/\bAtlas\b/g, "Атлас")
    .replace(/\bCLI\b/g, "командный интерфейс")
    .replace(/\brunner\b/gi, "средство запуска")
    .replace(/\bPlaywright и axe\b/g, "браузерные проверки доступности")
    .replace(/\bHTTP, DOM\b/g, "сетевого ответа и структуры страницы");
}

function loopCopy(loop) {
  const source = loop.copy[language];
  const override = loopPlainLanguageOverrides[loop.id]?.[language] ?? {};
  return {
    ...source,
    ...override,
    label: humanizeRuText(override.label ?? source.label),
    purpose: humanizeRuText(override.purpose ?? source.purpose),
  };
}

function loopContractCopy(loop, field) {
  const override = loopPlainLanguageOverrides[loop.id]?.[language]?.[field];
  return humanizeRuText(override ?? loop.contract[language][field]);
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
    view.querySelectorAll("[data-content-body]").forEach((body) => {
      body.classList.toggle("prose", active);
    });
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
  document.documentElement.dataset.languageReady = language;
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
  document.querySelectorAll("[data-en-placeholder][data-ru-placeholder]").forEach((element) => {
    element.setAttribute("placeholder", element.dataset[`${language}Placeholder`]);
  });
  const switcher = document.querySelector(".language-switch");
  switcher.querySelector("[data-lang-label]").textContent = language === "en" ? "RU" : "EN";
  switcher.setAttribute("aria-label", text("switchLanguage"));
  document.querySelector("[data-stage-code]").textContent = phaseCopy.observe.code;
  document.querySelector("[data-stage-copy]").textContent =
    phaseCopy.observe[`${language}Purpose`];
  renderGrammar();
  renderHeroPreview();
  renderReading();
  renderDocs();
  renderAtlas();
  if (routePreviewRequest && !routePreview && atlasData) {
    resolveRoutePreview(routePreviewRequest);
  } else {
    renderRoutePreview();
  }
  renderDataLoadState();
}

function persistLanguageInUrl() {
  const url = new URL(location.href);
  url.searchParams.set("lang", language);
  history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}

function renderGrammar() {
  if (!atlasData) return;
  const list = document.querySelector("[data-run-grammar]");
  const selectedStage =
    list.querySelector("button[aria-pressed='true']")?.dataset.stage
    || atlasData.sharedRunGrammar[0].id;
  list.innerHTML = "";
  list.setAttribute(
    "aria-label",
    language === "en" ? "Shared run stages" : "Общие этапы выполнения",
  );
  const buttons = [];

  function selectStage(index, focus = false) {
    const phase = atlasData.sharedRunGrammar[index];
    const button = buttons[index];
    buttons.forEach((entry, entryIndex) => {
      const selected = entryIndex === index;
      entry.setAttribute("aria-pressed", String(selected));
      entry.tabIndex = selected ? 0 : -1;
    });
    document.querySelector("[data-stage-code]").textContent = phaseCopy[phase.id].code;
    document.querySelector("[data-stage-copy]").textContent =
      phaseCopy[phase.id][`${language}Purpose`];
    if (focus) button.focus();
  }

  atlasData.sharedRunGrammar.forEach((phase, index) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.stage = phase.id;
    button.setAttribute("aria-controls", "stage-readout");
    button.innerHTML = `
      <b aria-hidden="true">${phaseCopy[phase.id].code}</b>
      <span>${phaseCopy[phase.id][language]}</span>
    `;
    button.addEventListener("click", () => selectStage(index));
    button.addEventListener("keydown", (event) => {
      const keyTargets = {
        ArrowLeft: (index - 1 + buttons.length) % buttons.length,
        ArrowUp: (index - 1 + buttons.length) % buttons.length,
        ArrowRight: (index + 1) % buttons.length,
        ArrowDown: (index + 1) % buttons.length,
        Home: 0,
        End: buttons.length - 1,
      };
      if (!(event.key in keyTargets)) return;
      event.preventDefault();
      selectStage(keyTargets[event.key], true);
    });
    buttons.push(button);
    item.append(button);
    list.append(item);
  });
  const selectedIndex = Math.max(
    atlasData.sharedRunGrammar.findIndex((phase) => phase.id === selectedStage),
    0,
  );
  selectStage(selectedIndex);
}

function renderReading() {
  if (!contentData) return;
  ["article", "quickstart"].forEach((section) => {
    const source = contentData[section][language];
    const body = document.querySelector(`[data-content-body="${section}"]`);
    const toc = document.querySelector(`[data-content-toc="${section}"]`);
    body.innerHTML = source.html;
    toc.innerHTML = "";
    source.toc.slice(1).forEach((entry) => {
      const link = document.createElement("a");
      const viewName = section === "article" ? "theory" : "quickstart";
      link.href = `#${viewName}/${entry.id}`;
      link.textContent = entry.title;
      toc.append(link);
    });
    const shell = toc.closest(".reading-toc");
    const toggle = shell?.querySelector(".reading-toc-toggle");
    if (toggle) {
      toggle.querySelector("span").textContent =
        language === "en" ? "On this page" : "На этой странице";
      toggle.setAttribute(
        "aria-label",
        language === "en" ? "Show sections on this page" : "Показать разделы страницы",
      );
    }
  });
}

function renderDocs() {
  if (!contentData) return;
  const grid = document.querySelector("[data-docs-grid]");
  grid.innerHTML = "";
  const documentsById = new Map(
    contentData.documents.map((documentData) => [documentData.id, documentData]),
  );
  let documentIndex = 0;
  documentGroups.forEach((group) => {
    const section = document.createElement("section");
    section.className = "docs-group";
    const heading = document.createElement("h2");
    heading.textContent = group[language];
    const list = document.createElement("div");
    list.className = "docs-list";
    group.ids.forEach((id) => {
      const documentData = documentsById.get(id);
      if (!documentData) return;
      documentIndex += 1;
      const article = document.createElement("article");
      const title = language === "en" ? documentData.enTitle : documentData.ruTitle;
      const url = language === "en" ? documentData.enUrl : documentData.ruUrl;
      article.innerHTML = `
        <span class="doc-index" aria-hidden="true">${String(documentIndex).padStart(2, "0")}</span>
        <h3>${title}</h3>
        <a href="${url}" aria-label="${text("docs")}: ${title}">
          <span>${text("docs")}</span><span class="ui-icon ui-icon-external" aria-hidden="true"></span>
        </a>
      `;
      list.append(article);
    });
    section.append(heading, list);
    grid.append(section);
  });
}

function atlasLoop(id) {
  return atlasData?.loops.find((loop) => loop.id === id);
}

const routeStopwords = new Set([
  "about", "after", "again", "also", "and", "are", "change", "could", "for",
  "from", "have", "into", "make", "need", "please", "that", "the", "this",
  "want", "with", "would", "а", "бы", "в", "во", "для", "ещё", "из", "и",
  "как", "мне", "мы", "на", "надо", "не", "но", "по", "с", "сделать", "то",
  "у", "хочу", "чтобы", "это",
]);

const routeKeywordHints = {
  "accept-source-change": ["merge", "pull request", "pr", "мерж", "пул реквест"],
  "assure-compatibility": ["compatibility", "backward compatible", "совместимость"],
  "author-documentation": ["documentation", "docs", "guide", "quickstart", "readme", "документация", "инструкция", "ридми", "быстрый старт"],
  "collect-friction": ["friction", "confusing", "stuck", "problem report", "непонятно", "застрял", "проблема пользователя"],
  "decide-product": ["product decision", "scope decision", "new feature", "продуктовое решение", "решить направление", "новая функция"],
  "distribute-package": ["package", "pypi", "wheel", "installable", "пакет", "установочный"],
  "evolve-schemas": ["schema", "json schema", "protocol field", "схема", "поле протокола"],
  "formalize-theory": ["theory", "formal model", "definition", "теория", "формальная модель", "определение"],
  "implement-frontend-surface": ["site", "website", "frontend", "interface", "layout", "typography", "mobile", "phone", "css", "html", "responsive", "сайт", "фронтенд", "интерфейс", "вёрстка", "верстка", "типографика", "мобильный", "телефон", "адаптив"],
  "localize-content": ["translate", "translation", "localize", "localization", "russian", "english", "перевод", "локализация", "русский", "английский"],
  "maintain-article": ["article", "paper", "research paper", "статья", "публикация"],
  "maintain-automation": ["automation", "agent workflow", "ci automation", "автоматизация", "агент"],
  "maintain-cli": ["cli", "command line", "terminal command", "командная строка", "терминал", "команда"],
  "maintain-compiler-core": ["compiler", "compile binding", "компилятор", "компиляция"],
  "maintain-evidence-adapters": ["inspect repository", "git history", "evidence adapter", "анализ репозитория", "история git", "адаптер наблюдения"],
  "maintain-execution-adapters": ["execution adapter", "external tool", "адаптер исполнения", "внешний инструмент"],
  "maintain-frontend-verification": ["playwright", "browser test", "visual regression", "accessibility", "браузерная проверка", "скриншот", "доступность"],
  "maintain-product-boundary": ["product boundary", "universal kernel", "граница продукта", "универсальное ядро"],
  "maintain-reference-bindings": ["example binding", "reference binding", "пример конфигурации", "эталонная конфигурация"],
  "maintain-repository-presence": ["repository avatar", "about link", "social preview", "branch protection", "repository security settings", "аватар репозитория", "ссылка about", "превью репозитория", "защита ветки", "настройки безопасности репозитория"],
  "model-threats": ["security", "threat", "attack", "secret", "безопасность", "угроза", "атака", "секрет"],
  "observe-onboarding": ["onboarding", "first use", "installation journey", "онбординг", "первый запуск", "установка пользователем"],
  "project-atlas": ["atlas", "project map", "cycle map", "атлас", "карта проекта", "карта циклов"],
  "plan-release": ["new release", "ship release", "release plan", "новый релиз", "новый выпуск", "план выпуска"],
  "propose-successor": ["propose evolution", "propose successor", "new binding", "предложить новую версию правил", "предложить преемника"],
  "review-successor": ["review proposed rules", "review successor", "проверить предложенную версию правил", "проверить преемника"],
  "activate-successor": ["activate reviewed rules", "activate successor", "включить проверенную версию правил", "активировать преемника"],
  "publish-site": ["publish site", "deploy site", "github pages", "опубликовать сайт", "задеплоить сайт", "pages"],
  "publish-source-change": ["open pull request", "push branch", "опубликовать ветку", "создать pull request"],
  "review-candidate": ["code review", "review candidate", "проверить изменение", "ревью кода"],
  "review-comprehension": ["clear text", "jargon", "copy review", "readable", "понятный текст", "жаргон", "нейрослоп", "вычитка"],
  "validate-invariants": ["invariant", "unit test", "security test", "инвариант", "юнит тест", "проверка правил"],
  "validate-use-cases": ["real repository", "use case", "field test", "реальный репозиторий", "сценарий применения", "полевой тест"],
  "verify-frontend-candidate": ["verify frontend", "cross browser", "browser matrix", "проверить интерфейс", "разные браузеры"],
  "verify-live-release": ["live site", "production check", "published release", "живой сайт", "проверка продакшена", "опубликованный выпуск"],
};

function routeTokens(value) {
  return (value || "")
    .normalize("NFKC")
    .toLocaleLowerCase()
    .match(/[\p{L}\p{N}]+/gu)
    ?.filter((token) => token.length > 1 && !routeStopwords.has(token))
    ?? [];
}

function routeTokenAffinity(requestToken, sourceToken) {
  if (requestToken === sourceToken) return 1;
  const shortest = Math.min(requestToken.length, sourceToken.length);
  if (shortest < 4) return 0;
  if (requestToken.startsWith(sourceToken) || sourceToken.startsWith(requestToken)) {
    return shortest / Math.max(requestToken.length, sourceToken.length) >= 0.55 ? 0.68 : 0;
  }
  let sharedPrefix = 0;
  while (
    sharedPrefix < shortest
    && requestToken[sharedPrefix] === sourceToken[sharedPrefix]
  ) {
    sharedPrefix += 1;
  }
  if (sharedPrefix >= 4 && sharedPrefix / shortest >= 0.65) return 0.58;
  return 0;
}

function routeHasAny(requestTokens, terms) {
  const termTokens = terms.flatMap((term) => routeTokens(term));
  return requestTokens.some((requestToken) => termTokens.some(
    (termToken) => routeTokenAffinity(requestToken, termToken) >= 0.58,
  ));
}

function routeIntentOverride(requestTokens) {
  const has = (terms) => routeHasAny(requestTokens, terms);
  const site = has(["site", "website", "page", "pages", "сайт", "страница"]);
  const publish = has(["publish", "deploy", "host", "опубликовать", "задеплоить", "развернуть"]);
  const frontendAction = has([
    "fix", "repair", "redesign", "design", "layout", "typography", "responsive",
    "исправить", "починить", "переделать", "дизайн", "вёрстка", "верстка",
    "типографика", "адаптивный",
  ]);
  const frontendObject = site || has([
    "frontend", "interface", "mobile", "phone", "ui", "css", "html",
    "фронтенд", "интерфейс", "мобильный", "телефон",
  ]);
  const branch = has(["main", "branch", "repository", "ветка", "репозиторий"]);
  const protect = has(["protect", "secure", "security setting", "защитить", "безопасность", "настройка"]);
  const release = has(["release", "version", "выпуск", "релиз", "версия"]);
  const releaseAction = has(["ship", "create", "prepare", "make", "выпустить", "создать", "подготовить", "сделать"]);
  const evolution = has([
    "successor", "binding", "rules", "преемник", "привязка", "правила",
  ]);
  const activate = has(["activate", "enable", "apply", "включить", "активировать", "применить"]);
  const review = has(["review", "verify", "assess", "проверить", "оценить", "ревью"]);
  const propose = has(["propose", "evolve", "предложить", "эволюция"]);
  const tokenCost = has(["token", "cost", "usage", "токен", "расход", "стоимость"])
    && has(["model", "route", "модель", "маршрут"]);
  const feature = has(["feature", "functionality", "функция", "фича"]);
  const add = has(["add", "create", "implement", "добавить", "создать", "реализовать"]);

  if (tokenCost) return { blocked: true };
  if (branch && protect) return { targetId: "maintain-repository-presence" };
  if (evolution && activate) return { targetId: "activate-successor" };
  if (evolution && review) return { targetId: "review-successor" };
  if (evolution && propose) return { targetId: "propose-successor" };
  if (site && publish) return { targetId: "publish-site" };
  if (frontendObject && frontendAction) {
    return {
      targetId: "implement-frontend-surface",
      executionRootId: "design-site-experience",
    };
  }
  if (release && (releaseAction || publish)) {
    return { targetId: "plan-release", executionRootId: "release-distribution" };
  }
  if (feature && add) return { targetId: "decide-product" };
  return null;
}

function routeTargetAllowed(loopId, requestTokens) {
  const has = (terms) => routeHasAny(requestTokens, terms);
  if (loopId === "publish-site") {
    return has(["publish", "deploy", "host", "опубликовать", "задеплоить", "развернуть"]);
  }
  if (loopId === "publish-source-change") {
    return has(["push", "pull request", "open pr", "опубликовать ветку", "создать pull request"]);
  }
  if (loopId === "activate-successor") {
    return has(["activate", "enable", "apply", "включить", "активировать", "применить"]);
  }
  return true;
}

function routeSourceScore(requestTokens, source, weight) {
  const sourceTokens = routeTokens(source);
  return requestTokens.reduce((score, token) => {
    const affinity = sourceTokens.reduce(
      (best, sourceToken) => Math.max(best, routeTokenAffinity(token, sourceToken)),
      0,
    );
    return score + affinity * weight;
  }, 0);
}

function scoreRouteTarget(loop, requestTokens) {
  const hints = routeKeywordHints[loop.id] ?? [];
  const fields = [
    [loop.id.replaceAll("-", " "), 7],
    [loop.copy.en.label, 6],
    [loop.copy.ru.label, 6],
    [loop.copy.en.purpose, 3],
    [loop.copy.ru.purpose, 3],
    [loop.contract.en.input, 2],
    [loop.contract.en.output, 2],
    [loop.contract.ru.input, 2],
    [loop.contract.ru.output, 2],
    [loop.artifacts.join(" "), 4],
    [hints.join(" "), 8],
  ];
  return fields.reduce(
    (score, [source, weight]) => score + routeSourceScore(requestTokens, source, weight),
    0,
  );
}

function routePath(targetId) {
  const path = [];
  let cursor = atlasLoop(targetId);
  while (cursor) {
    path.unshift(cursor.id);
    cursor = cursor.parentId ? atlasLoop(cursor.parentId) : null;
  }
  return path;
}

function routeCandidates(request) {
  const requestTokens = routeTokens(request);
  if (!requestTokens.length) return [];
  const override = routeIntentOverride(requestTokens);
  if (override?.blocked) return [];
  if (override?.targetId && atlasLoop(override.targetId)) {
    return [{ ...override, id: override.targetId, score: Number.POSITIVE_INFINITY }];
  }
  return atlasData.loops
    .filter((loop) => loop.children.length === 0)
    .filter((loop) => routeTargetAllowed(loop.id, requestTokens))
    .map((loop) => ({ id: loop.id, score: scoreRouteTarget(loop, requestTokens) }))
    .filter((candidate) => candidate.score >= 6)
    .sort((left, right) => right.score - left.score || left.id.localeCompare(right.id))
    .slice(0, 5);
}

function proposedRouteIds() {
  return new Set(routePreview?.loopIds ?? []);
}

const externalEffectCopy = {
  "github-organization-profile": {
    en: "update the organization profile",
    ru: "обновить профиль организации",
  },
  "github-pages": {
    en: "publish the site to GitHub Pages",
    ru: "опубликовать сайт в GitHub Pages",
  },
  "github-pull-request": {
    en: "open a pull request",
    ru: "открыть запрос на слияние",
  },
  "github-pull-request-merge": {
    en: "merge an approved pull request",
    ru: "слить одобренный запрос",
  },
  "github-release-assets": {
    en: "publish the release files",
    ru: "опубликовать файлы выпуска",
  },
  "github-repository-homepage": {
    en: "update the repository website link",
    ru: "обновить ссылку на сайт репозитория",
  },
  "github-repository-security-settings": {
    en: "update the repository security settings",
    ru: "обновить настройки безопасности репозитория",
  },
  "github-repository-social-preview": {
    en: "update the repository preview image",
    ru: "обновить картинку-превью репозитория",
  },
  "github-repository-source": {
    en: "push source changes to GitHub",
    ru: "отправить изменения исходников в GitHub",
  },
  "github-version-tag": {
    en: "create a version tag",
    ru: "создать метку версии",
  },
};

function routeProspectiveEffects(loopIds) {
  const networkOrder = { none: 0, read: 1, write: 2 };
  let network = "none";
  const externalMutations = new Set();
  loopIds.forEach((loopId) => {
    const effects = atlasLoop(loopId)?.prospectiveEffects ?? {};
    const candidateNetwork = effects.network ?? "none";
    if ((networkOrder[candidateNetwork] ?? 0) > networkOrder[network]) {
      network = candidateNetwork;
    }
    (effects.externalMutations ?? []).forEach((effect) => externalMutations.add(effect));
  });
  return { network, externalMutations: [...externalMutations].sort() };
}

function externalEffectLabel(effect) {
  return externalEffectCopy[effect]?.[language] ?? effect;
}

function renderRoutePreview() {
  const feedback = document.querySelector("[data-route-preview-feedback]");
  const message = document.querySelector("[data-route-preview-message]");
  const choices = document.querySelector("[data-route-preview-choices]");
  const result = document.querySelector("[data-route-preview-result]");
  const area = document.querySelector("[data-route-preview-area]");
  const list = document.querySelector("[data-route-preview-list]");
  const effects = document.querySelector("[data-route-preview-effects]");
  if (!feedback || !message || !choices || !result || !area || !list || !effects) return;

  if (!routePreview) {
    result.hidden = true;
    area.innerHTML = "";
    list.innerHTML = "";
    effects.textContent = "";
    if (!message.textContent) feedback.hidden = true;
    return;
  }

  choices.innerHTML = "";
  feedback.hidden = false;
  feedback.dataset.state = "success";
  message.textContent = text("routeReady");
  result.hidden = false;
  area.innerHTML = "";
  const areaLabel = document.createElement("strong");
  areaLabel.textContent = text("routeArea");
  const areaPath = document.createElement("span");
  routePreview.areaIds.forEach((loopId, index) => {
    if (index) {
      const separator = document.createElement("span");
      separator.className = "ui-icon ui-icon-arrow-right route-preview-separator";
      separator.setAttribute("aria-hidden", "true");
      areaPath.append(separator);
    }
    const loop = atlasLoop(loopId);
    const link = document.createElement("a");
    link.href = `#atlas/${encodeURIComponent(loopId)}`;
    link.textContent = loopCopy(loop).label;
    areaPath.append(link);
  });
  area.append(areaLabel, areaPath);
  list.innerHTML = "";
  routePreview.actionIds.forEach((loopId, index) => {
    const loop = atlasLoop(loopId);
    const item = document.createElement("li");
    if (loopId === routePreview.targetId) item.dataset.routeTarget = "true";
    const link = document.createElement("a");
    link.href = `#atlas/${encodeURIComponent(loopId)}`;
    const step = document.createElement("span");
    step.textContent = `${text("routeAction")} ${String(index + 1).padStart(2, "0")}`;
    const label = document.createElement("strong");
    label.textContent = loopCopy(loop).label;
    link.append(step, label);
    if (loopId === routePreview.targetId) {
      link.setAttribute("aria-current", "step");
      link.setAttribute("aria-label", `${text("routeTarget")}: ${loopCopy(loop).label}`);
    }
    item.append(link);
    list.append(item);
  });
  const prospective = routeProspectiveEffects(routePreview.actionIds);
  if (prospective.network === "none" && !prospective.externalMutations.length) {
    effects.textContent = text("routeEffectsNone");
  } else {
    const network = prospective.network === "write"
      ? text("routeNetworkWrite")
      : text("routeNetworkRead");
    const effectLabels = prospective.externalMutations.length
      ? prospective.externalMutations.map(externalEffectLabel).join(", ")
      : text("notDeclared");
    effects.textContent = text("routeEffectsSome")
      .replace("{network}", network)
      .replace("{effects}", effectLabels);
  }
}

function clearRoutePreview({ keepFeedback = false } = {}) {
  routePreview = null;
  routePreviewRequest = "";
  const request = document.querySelector("[data-route-preview-request]");
  const feedback = document.querySelector("[data-route-preview-feedback]");
  const message = document.querySelector("[data-route-preview-message]");
  const choices = document.querySelector("[data-route-preview-choices]");
  if (request) request.value = "";
  if (message && !keepFeedback) message.textContent = "";
  if (choices) choices.innerHTML = "";
  if (feedback && !keepFeedback) feedback.hidden = true;
  if (feedback && !keepFeedback) delete feedback.dataset.state;
  renderRoutePreview();
  if (atlasData) renderGraph(atlasLoop(selectedLoopId || atlasData.binding.rootLoopIds[0]));
}

function routeExecutionIds(targetId, executionRootId = null) {
  if (!executionRootId) return [targetId];
  const root = atlasLoop(executionRootId);
  if (!root?.children?.length || !root.children.includes(targetId)) return [targetId];
  return [...root.children];
}

function selectRouteTarget(
  targetId,
  { executionRootId = null, focusResult = false } = {},
) {
  const areaIds = routePath(executionRootId || targetId);
  const actionIds = routeExecutionIds(targetId, executionRootId);
  routePreview = {
    areaIds,
    actionIds,
    loopIds: [...new Set([...areaIds, ...actionIds])],
    targetId,
  };
  renderRoutePreview();
  renderGraph(atlasLoop(selectedLoopId || atlasData.binding.rootLoopIds[0]));
  if (focusResult) document.getElementById("route-preview-result-title")?.focus();
}

function resolveRoutePreview(request) {
  const feedback = document.querySelector("[data-route-preview-feedback]");
  const message = document.querySelector("[data-route-preview-message]");
  const choices = document.querySelector("[data-route-preview-choices]");
  routePreview = null;
  routePreviewRequest = request.trim();
  choices.innerHTML = "";
  feedback.hidden = false;
  feedback.dataset.state = "needs-attention";

  if (!routePreviewRequest) {
    message.textContent = text("routeRequired");
    renderRoutePreview();
    return;
  }

  const candidates = routeCandidates(routePreviewRequest);
  if (!candidates.length) {
    message.textContent = text("routeNoMatch");
    renderRoutePreview();
    return;
  }

  const top = candidates[0];
  const close = candidates.filter(
    (candidate) => candidate.score >= top.score * 0.93,
  );
  if (close.length > 1) {
    message.textContent = text("routeAmbiguous");
    close.slice(0, 3).forEach((candidate) => {
      const loop = atlasLoop(candidate.id);
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = loopCopy(loop).label;
      button.addEventListener("click", () => selectRouteTarget(candidate.id, {
        executionRootId: candidate.executionRootId ?? null,
        focusResult: true,
      }));
      choices.append(button);
    });
    renderRoutePreview();
    return;
  }
  selectRouteTarget(top.id, { executionRootId: top.executionRootId ?? null });
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
  const upLink = document.querySelector("[data-atlas-up]");
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
  const parent = loop.parentId ? atlasLoop(loop.parentId) : null;
  upLink.hidden = !parent;
  if (parent) {
    upLink.href = `#atlas/${encodeURIComponent(parent.id)}`;
    upLink.querySelector("span:last-child").textContent = text("back");
    upLink.setAttribute(
      "aria-label",
      `${text("back")}: ${loopCopy(parent).label}`,
    );
  } else {
    upLink.removeAttribute("href");
    upLink.removeAttribute("aria-label");
  }
}

function renderInspector(loop) {
  const profile = atlasData.profiles[loop.profile];
  const route = loop.route_materialization;
  const inspector = document.querySelector("[data-atlas-inspector]");
  const loopIndex = atlasData.loops.findIndex((entry) => entry.id === loop.id) + 1;
  const loopCode = `LOOP ${String(loopIndex).padStart(2, "0")}.${loop.children.length ? "A" : "T"}`;
  const iconClass = loopIconClass(loop);
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
        <div><dt>${text("bindingDigest")}</dt><dd><code translate="no">${atlasData.binding.digest}</code></dd></div>
      </dl>
    </details>
  `;
  const openAction = loop.id !== selectedLoopId && loop.children.length
    ? `
      <a class="inspector-open-cycle" href="#atlas/${encodeURIComponent(loop.id)}">
        <span>${text("openInside")}</span>
        <span class="ui-icon ui-icon-arrow-right" aria-hidden="true"></span>
      </a>
    `
    : "";
  inspector.innerHTML = `
    <button class="inspector-close" data-atlas-inspector-close type="button"
      aria-label="${text("closeInspector")}">×</button>
    <div class="inspector-status">
      <i aria-hidden="true"></i>
      <span>${loop.children.length ? text("openLoop") : text("terminalLoop")}</span>
    </div>
    <p class="inspector-code" translate="no">${loopCode}</p>
    <h2 id="atlas-inspector-title" tabindex="-1">${loopCopy(loop).label}</h2>
    <div class="inspector-dial" aria-hidden="true">
      <span class="ui-icon ${iconClass}"></span>
    </div>
    <p class="inspector-purpose">${loopCopy(loop).purpose}</p>
    <dl class="inspector-contract">
      <div><dt>${text("needs")}</dt><dd>${loopContractCopy(loop, "input")}</dd></div>
      <div><dt>${text("produces")}</dt><dd>${loopContractCopy(loop, "output")}</dd></div>
    </dl>
    ${openAction}
    <p class="inspector-more-cue">${text("moreBelow")} <span class="ui-icon ui-icon-arrow-down" aria-hidden="true"></span></p>
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
    ${loop.parentId ? `<a class="atlas-back" href="#atlas/${encodeURIComponent(loop.parentId)}"><span class="ui-icon ui-icon-arrow-left" aria-hidden="true"></span> ${text("back")}: ${loopCopy(atlasLoop(loop.parentId)).label}</a>` : ""}
  `;
  inspector.querySelector("[data-atlas-inspector-close]")
    .addEventListener("click", () => setInspectorOpen(false, true));
  inspector.querySelector(".inspector-open-cycle")?.addEventListener("click", () => {
    focusGraphAfterRoute = true;
    inspectorRequested = false;
    inspectedLoopId = null;
    setInspectorOpen(false);
  });
}

function setInspectorOpen(open, restoreFocus = false) {
  const inspector = document.querySelector("[data-atlas-inspector]");
  const scrim = document.querySelector("[data-atlas-inspector-scrim]");
  const background = document.querySelectorAll(
    ".site-header, .atlas-commandbar, .atlas-navigation, "
      + "[data-atlas-stage], .evolution-circuit, .full-outline, .site-footer",
  );
  if (!open && pendingInspectorOpenFrame !== null) {
    cancelAnimationFrame(pendingInspectorOpenFrame);
    pendingInspectorOpenFrame = null;
  }
  if (pendingInspectorFocusFrame !== null) {
    cancelAnimationFrame(pendingInspectorFocusFrame);
    pendingInspectorFocusFrame = null;
  }
  inspectorRequested = open;
  inspector.classList.toggle("is-open", open);
  inspector.setAttribute("aria-hidden", String(!open));
  inspector.toggleAttribute("inert", !open);
  scrim.hidden = !open;
  background.forEach((element) => element.toggleAttribute("inert", open));
  document.body.classList.toggle("is-inspector-open", open);
  if (open) {
    pendingInspectorFocusFrame = requestAnimationFrame(() => {
      pendingInspectorFocusFrame = null;
      if (inspectorRequested) {
        inspector.querySelector("[data-atlas-inspector-close]")?.focus({ preventScroll: true });
      }
    });
  }
  if (!open && restoreFocus && inspectorTrigger?.isConnected) {
    inspectorTrigger.focus({ preventScroll: true });
  }
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

function loopIconClass(loop) {
  return loop.children.length ? "ui-icon-plus" : "ui-icon-dot";
}

function renderHeroPreview() {
  if (!atlasData) return;
  const svg = document.querySelector("[data-hero-atlas]");
  if (!svg) return;
  svg.innerHTML = "";
  const root = atlasLoop(atlasData.binding.rootLoopIds[0]);
  const children = root.children.map(atlasLoop).slice(0, 4);
  const positions = [
    { x: 148, y: 118 },
    { x: 472, y: 112 },
    { x: 488, y: 378 },
    { x: 132, y: 382 },
  ];

  children.forEach((child, index) => {
    const position = positions[index];
    svg.append(svgElement("path", {
      class: "preview-link",
      d: `M 310 250 C ${310 + (position.x - 310) * 0.45} ${250 + (position.y - 250) * 0.15}, ${310 + (position.x - 310) * 0.72} ${position.y}, ${position.x} ${position.y}`,
    }));
  });

  function appendPreviewNode(loop, x, y, current = false) {
    const link = svgElement("a", {
      class: `preview-node${current ? " is-current" : ""}`,
      href: `#atlas/${encodeURIComponent(loop.id)}`,
      "aria-label": `${text("open")}: ${loopCopy(loop).label}`,
    });
    link.append(svgElement("rect", {
      class: "preview-hit",
      x: current ? -114 : -86,
      y: current ? -62 : -50,
      width: current ? 228 : 172,
      height: current ? 124 : 100,
      rx: current ? 24 : 18,
    }));
    link.append(svgElement("rect", {
      x: current ? -106 : -78,
      y: current ? -56 : -40,
      width: current ? 212 : 156,
      height: current ? 112 : 80,
      rx: current ? 22 : 16,
    }));
    const label = svgElement("text", {
      class: "preview-node-label",
      x: 0,
      y: graphLabel(loopCopy(loop).label).length > 1 ? -5 : 5,
      "text-anchor": "middle",
    });
    graphLabel(loopCopy(loop).label).slice(0, 2).forEach((line, index) => {
      const part = svgElement("tspan", {
        x: 0,
        dy: index === 0 ? 0 : 18,
      });
      part.textContent = line;
      label.append(part);
    });
    link.append(label);
    if (current) {
      const hint = svgElement("text", {
        class: "preview-node-hint",
        x: 0,
        y: 37,
        "text-anchor": "middle",
      });
      hint.setAttribute("x", "-8");
      hint.textContent = language === "en" ? "OPEN THE ATLAS" : "ОТКРЫТЬ АТЛАС";
      link.append(hint);
      link.append(svgElement("path", {
        class: "preview-node-hint-icon",
        d: "M 68 37 H 84 M 79 32 L 84 37 L 79 42",
      }));
    }
    const group = svgElement("g", { transform: `translate(${x} ${y})` });
    group.append(link);
    svg.append(group);
  }

  children.forEach((child, index) => {
    appendPreviewNode(child, positions[index].x, positions[index].y);
  });
  appendPreviewNode(root, 310, 250, true);
}

function appendGraphDefs(svg) {
  const defs = svgElement("defs");
  svg.append(defs);
}

function appendGraphNode(
  svg,
  loop,
  x,
  y,
  current = false,
  variant = "desktop",
) {
  const mobile = variant === "mobile";
  const tablet = variant === "tablet";
  const landscape = variant === "landscape";
  const proposed = proposedRouteIds().has(loop.id);
  const nodeWidth = current
    ? (mobile ? 326 : (landscape ? 200 : (tablet ? 360 : 320)))
    : (mobile ? 310 : (landscape ? 148 : (tablet ? 300 : 220)));
  const nodeHeight = current
    ? (mobile ? 136 : (landscape ? 96 : (tablet ? 144 : 156)))
    : (mobile ? 92 : (landscape ? 64 : (tablet ? 98 : 104)));
  const corner = current ? 22 : 17;
  const group = svgElement("g", {
    class: `node-assembly${current ? " is-current" : ""}${proposed ? " is-proposed-route" : ""} is-${variant}`,
    transform: `translate(${x} ${y})`,
  });
  const link = svgElement("a", {
    href: `#atlas/${encodeURIComponent(loop.id)}`,
    class: `graph-node${current ? " is-current" : ""}${proposed ? " is-proposed-route" : ""}`,
    "data-loop-id": loop.id,
    "aria-label": `${loopCopy(loop).label}. ${
      loop.children.length ? `${text("childCount")}: ${loop.children.length}.` : `${text("noChildCount")}.`
    }${proposed ? ` ${text("routeIncluded")}.` : ""} ${text("inspect")}`,
  });
  const title = svgElement("title");
  title.textContent = `${loopCopy(loop).label}. ${loopCopy(loop).purpose}`;
  link.append(title);
  link.append(svgElement("rect", {
    class: "node-hit",
    x: -(nodeWidth / 2) - 8,
    y: -(nodeHeight / 2) - 8,
    width: nodeWidth + 16,
    height: nodeHeight + 16,
    rx: corner,
  }));
  link.append(svgElement("rect", {
    class: "node-shadow",
    x: -(nodeWidth / 2) + 6,
    y: -(nodeHeight / 2) + 7,
    width: nodeWidth,
    height: nodeHeight,
    rx: corner,
  }));
  link.append(svgElement("rect", {
    class: "node-case",
    x: -(nodeWidth / 2),
    y: -(nodeHeight / 2),
    width: nodeWidth,
    height: nodeHeight,
    rx: corner,
  }));
  link.append(svgElement("rect", {
    class: "node-inner",
    x: -(nodeWidth / 2) + 7,
    y: -(nodeHeight / 2) + 7,
    width: nodeWidth - 14,
    height: nodeHeight - 14,
    rx: Math.max(corner - 6, 8),
  }));

  const count = svgElement("text", {
    class: "node-count",
    x: -(nodeWidth / 2) + 20,
    y: -(nodeHeight / 2) + (landscape ? 18 : 28),
    "text-anchor": "start",
  });
  count.textContent = loop.children.length
    ? String(loop.children.length).padStart(2, "0")
    : "•";
  link.append(count);

  const state = svgElement("text", {
    class: "node-state",
    x: (nodeWidth / 2) - 20,
    y: -(nodeHeight / 2) + (landscape ? 18 : 28),
    "text-anchor": "end",
  });
  state.textContent = loop.children.length
    ? (language === "en" ? "OPEN" : "ВНУТРИ")
    : (language === "en" ? "LEAF" : "ФИНАЛ");
  link.append(state);

  const label = svgElement("text", {
    class: "node-label",
    x: 0,
    y: current ? 1 : (landscape ? 3 : 9),
    "text-anchor": "middle",
  });
  graphLabel(loopCopy(loop).label).slice(0, 2).forEach((line, index) => {
    const part = svgElement("tspan", {
      x: 0,
      dy: index === 0
        ? 0
        : (current ? (landscape ? 20 : 22) : (landscape ? 17 : 19)),
    });
    part.textContent = line;
    label.append(part);
  });
  link.append(label);

  group.append(link);
  svg.append(group);
}

function renderGraph(loop) {
  const svg = document.querySelector("[data-atlas-graph]");
  const stage = document.querySelector("[data-atlas-stage]");
  svg.innerHTML = "";
  const children = loop.children.map(atlasLoop);
  const landscape = compactLandscapeAtlas.matches;
  const mobile = !landscape && window.matchMedia("(max-width: 640px)").matches;
  const tablet = !landscape && !mobile
    && window.matchMedia("(max-width: 1199px)").matches;
  const layout = landscape
    ? "landscape"
    : (mobile ? "mobile" : (tablet ? "tablet" : "desktop"));
  stage.toggleAttribute("data-has-proposed-route", Boolean(routePreview));
  const rows = mobile ? children.length : Math.ceil(children.length / 2);
  const viewWidth = landscape
    ? 844
    : (mobile ? 360 : (tablet ? 960 : 1600));
  const viewHeight = landscape
    ? 248
    : (mobile
      ? Math.max(480, 280 + Math.max(rows, 1) * 122)
      : (tablet ? Math.max(650, 280 + Math.max(rows, 1) * 132) : 760));
  svg.setAttribute("viewBox", `0 0 ${viewWidth} ${viewHeight}`);
  svg.setAttribute(
    "preserveAspectRatio",
    mobile ? "xMidYMin meet" : "xMidYMid meet",
  );
  stage.dataset.layout = layout;
  if (landscape) {
    stage.style.removeProperty("--atlas-graph-height");
    stage.style.removeProperty("--atlas-graph-width");
  } else if (mobile || tablet) {
    const renderedHeight = Math.ceil(viewHeight * (stage.clientWidth / viewWidth));
    stage.style.setProperty("--atlas-graph-height", `${renderedHeight}px`);
    stage.style.removeProperty("--atlas-graph-width");
  } else {
    stage.style.removeProperty("--atlas-graph-height");
    stage.style.removeProperty("--atlas-graph-width");
  }
  appendGraphDefs(svg);
  const level = svgElement("g", { class: "level-constellation" });
  const routeIds = proposedRouteIds();
  const proposedConnection = (child) =>
    routeIds.has(loop.id) && routeIds.has(child.id) ? " is-proposed-route" : "";

  const previous = previousLoopId ? atlasLoop(previousLoopId) : null;
  let motion = "none";
  if (previous && loop.parentId === previous.id) motion = "forward";
  else if (previous && previous.parentId === loop.id) motion = "back";
  else if (previous && previous.id !== loop.id) motion = "side";

  stage.removeAttribute("data-motion");
  if (motion !== "none" && !reducedMotion.matches && !landscape) {
    requestAnimationFrame(() => {
      stage.dataset.motion = motion;
    });
  }

  const centerX = landscape ? 422 : (mobile ? 180 : (tablet ? 480 : 800));
  const centerY = landscape ? 124 : (mobile ? 108 : (tablet ? 104 : 380));

  const positions = children.map((child, index) => {
    if (landscape) {
      const topCount = Math.ceil(children.length / 2);
      const topRow = index < topCount;
      const rowSize = topRow ? topCount : children.length - topCount;
      const rowIndex = topRow ? index : index - topCount;
      return {
        child,
        index,
        x: rowSize <= 1 ? centerX : 86 + rowIndex * (672 / (rowSize - 1)),
        y: topRow ? 44 : 204,
      };
    }
    if (mobile) {
      return {
        child,
        index,
        x: 197,
        y: 292 + index * 122,
      };
    }
    if (tablet) {
      return {
        child,
        index,
        x: index % 2 === 0 ? 250 : 710,
        y: 286 + Math.floor(index / 2) * 132,
      };
    }
    const count = Math.max(children.length, 1);
    const ringX = children.length > 8 ? 620 : 560;
    const ringY = children.length > 8 ? 278 : 252;
    const angle = -Math.PI / 2 + (Math.PI * 2 * index) / count;
    return {
      child,
      index,
      x: centerX + Math.cos(angle) * ringX,
      y: centerY + Math.sin(angle) * ringY,
    };
  });

  if (positions.length && landscape) {
    positions.forEach(({ child, x, y }) => {
      level.append(svgElement("path", {
        class: `graph-link${proposedConnection(child)}`,
        d: `M ${centerX} ${centerY} L ${x} ${y}`,
      }));
      level.append(svgElement("circle", {
        class: `graph-link-dot${proposedConnection(child)}`,
        cx: centerX + (x - centerX) * 0.58,
        cy: centerY + (y - centerY) * 0.58,
        r: 3,
      }));
    });
  } else if (positions.length && mobile) {
    const trunkX = 24;
    const rootBottom = centerY + 68;
    const lastY = positions.at(-1).y;
    level.append(svgElement("path", {
      class: "graph-link graph-trunk",
      d: `M ${centerX} ${rootBottom} H ${trunkX} V ${lastY}`,
    }));
    positions.forEach(({ child, x, y }) => {
      level.append(svgElement("path", {
        class: `graph-link graph-branch${proposedConnection(child)}`,
        d: `M ${trunkX} ${y} H ${x - 155}`,
      }));
      level.append(svgElement("circle", {
        class: `graph-link-dot${proposedConnection(child)}`,
        cx: trunkX,
        cy: y,
        r: 3,
      }));
    });
  } else if (positions.length && tablet) {
    const rootBottom = centerY + 72;
    const lastY = positions.at(-1).y;
    level.append(svgElement("path", {
      class: "graph-link graph-trunk",
      d: `M ${centerX} ${rootBottom} V ${lastY}`,
    }));
    positions.forEach(({ child, x, y }) => {
      const cardEdge = x < centerX ? x + 150 : x - 150;
      level.append(svgElement("path", {
        class: `graph-link graph-branch${proposedConnection(child)}`,
        d: `M ${centerX} ${y} H ${cardEdge}`,
      }));
      level.append(svgElement("circle", {
        class: `graph-link-dot${proposedConnection(child)}`,
        cx: centerX,
        cy: y,
        r: 3,
      }));
    });
  } else {
    positions.forEach(({ child, x, y }) => {
      level.append(svgElement("path", {
        class: `graph-link${proposedConnection(child)}`,
        d: `M ${centerX} ${centerY} L ${x} ${y}`,
      }));
      level.append(svgElement("circle", {
        class: `graph-link-dot${proposedConnection(child)}`,
        cx: centerX + (x - centerX) * 0.56,
        cy: centerY + (y - centerY) * 0.56,
        r: 3,
      }));
    });
  }

  positions.forEach(({ child, index, x, y }) => appendGraphNode(
    level,
    child,
    x,
    y,
    false,
    layout,
  ));
  appendGraphNode(
    level,
    loop,
    centerX,
    centerY,
    true,
    layout,
  );
  svg.append(level);
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
  document.querySelector("[data-atlas-binding]").removeAttribute("title");
  document.querySelector("[data-atlas-root]").textContent = loopCopy(atlasLoop(rootId)).label;
  document.querySelector("[data-atlas-count]").textContent = atlasData.loops.length;
  document.querySelector("[data-loop-count]").textContent = atlasData.loops.length;
  const outlineSummary = document.querySelector("[data-outline-summary]");
  outlineSummary.textContent = language === "ru"
    ? `Показать полную схему из ${atlasData.loops.length} циклов`
    : `Show the complete ${atlasData.loops.length}-cycle outline`;
  document.querySelector("[data-atlas-provenance]").textContent =
    text("acceptedSource");

  renderBreadcrumbs(loop);
  const inspectedLoop = inspectedLoopId ? atlasLoop(inspectedLoopId) : null;
  renderInspector(inspectedLoop || loop);
  renderGraph(loop);
  setInspectorOpen(inspectorRequested);
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
    element.textContent = text("loadErrorMap");
  });
  document.querySelectorAll("[data-content-body]").forEach((element) => {
    element.innerHTML = `<p class="load-error">${text("loadErrorContent")}</p>`;
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
    ".graph-node, .atlas-up, .atlas-history a, .atlas-breadcrumbs a",
  );
  if (next.view === "atlas" && !next.detail && atlasData) {
    next.detail = atlasData.binding.rootLoopIds[0];
    const url = new URL(location.href);
    url.hash = `atlas/${encodeURIComponent(next.detail)}`;
    history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  }
  const restoreAtlasFocus =
    next.view === "atlas" &&
    ((lastRoutedView === "atlas" && atlasNavigationHadFocus) || focusGraphAfterRoute);
  setView(next.view);
  if (next.view === "atlas") {
    const requestedLoopId = next.detail || atlasData?.binding.rootLoopIds[0];
    if (requestedLoopId && requestedLoopId !== selectedLoopId) {
      inspectorRequested = false;
      inspectedLoopId = null;
    }
    selectedLoopId = next.detail;
    renderAtlas();
    if (restoreAtlasFocus) {
      requestAnimationFrame(() => {
        document
          .querySelector(".graph-node.is-current")
          ?.focus({ preventScroll: true });
        focusGraphAfterRoute = false;
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
  lastRoutedView = next.view;
  requestAnimationFrame(observeReveals);
}

document.querySelector(".language-switch").addEventListener("click", () => {
  applyLanguage(language === "en" ? "ru" : "en");
  persistLanguageInUrl();
});

const menuSwitch = document.querySelector(".menu-switch");
const primaryNav = document.querySelector(".view-tabs");

function closePrimaryMenu({ restoreFocus = false } = {}) {
  primaryNav.classList.remove("is-open");
  menuSwitch.setAttribute("aria-expanded", "false");
  if (restoreFocus) menuSwitch.focus();
}

menuSwitch.addEventListener("click", (event) => {
  const nav = primaryNav;
  const open = !nav.classList.contains("is-open");
  nav.classList.toggle("is-open", open);
  event.currentTarget.setAttribute("aria-expanded", String(open));
});

document.addEventListener("pointerdown", (event) => {
  if (!primaryNav.classList.contains("is-open")) return;
  if (event.target.closest(".site-header")) return;
  closePrimaryMenu();
});

document.querySelectorAll(".reading-toc-toggle").forEach((toggle) => {
  toggle.addEventListener("click", () => {
    const toc = toggle.closest(".reading-toc");
    const open = toc.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", String(open));
    const icon = toggle.querySelector(".ui-icon");
    icon.classList.toggle("ui-icon-plus", !open);
    icon.classList.toggle("ui-icon-minus", open);
  });
});

const routePreviewForm = document.querySelector("[data-route-preview-form]");
const routePreviewInput = document.querySelector("[data-route-preview-request]");
routePreviewInput.value = "";
routePreviewForm.addEventListener("submit", (event) => {
  event.preventDefault();
  if (!atlasData) return;
  resolveRoutePreview(routePreviewInput.value);
});
routePreviewInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" || !(event.ctrlKey || event.metaKey)) return;
  event.preventDefault();
  routePreviewForm.requestSubmit();
});
document.querySelector("[data-route-preview-clear]").addEventListener("click", () => {
  clearRoutePreview();
  routePreviewInput.focus();
});
window.addEventListener("pageshow", (event) => {
  if (event.persisted) clearRoutePreview();
});

document.querySelector("[data-atlas-graph]").addEventListener("click", (event) => {
  const node = event.target.closest(".graph-node");
  if (!node) return;
  event.preventDefault();
  inspectorTrigger = node;
  inspectedLoopId = node.dataset.loopId;
  inspectorRequested = true;
  renderInspector(atlasLoop(inspectedLoopId));
  if (pendingInspectorOpenFrame !== null) {
    cancelAnimationFrame(pendingInspectorOpenFrame);
  }
  pendingInspectorOpenFrame = requestAnimationFrame(() => {
    pendingInspectorOpenFrame = null;
    if (inspectorRequested) setInspectorOpen(true);
  });
});

document.querySelector("[data-atlas-inspector-scrim]").addEventListener("click", () => {
  setInspectorOpen(false, true);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Tab" && primaryNav.classList.contains("is-open")) {
    const menuFocusables = [
      menuSwitch,
      ...primaryNav.querySelectorAll("a[href], button:not([disabled])"),
      document.querySelector(".language-switch"),
    ].filter((element) => element && element.getClientRects().length);
    const first = menuFocusables[0];
    const last = menuFocusables.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
  if (event.key === "Tab" && inspectorRequested) {
    const inspector = document.querySelector("[data-atlas-inspector]");
    const focusable = [...inspector.querySelectorAll(
      "a[href], button:not([disabled]), summary, [tabindex]:not([tabindex='-1'])",
    )].filter((element) => !element.hidden && element.getClientRects().length);
    if (focusable.length) {
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }
  if (event.key === "Tab" && !event.shiftKey && document.activeElement === document.body) {
    event.preventDefault();
    document.querySelector(".skip-link").focus();
    return;
  }
  if (event.key === "Escape") {
    if (inspectorRequested) {
      setInspectorOpen(false, true);
      return;
    }
    closePrimaryMenu({ restoreFocus: true });
  }
});

window.addEventListener("hashchange", route);
if ("scrollRestoration" in history) history.scrollRestoration = "manual";

const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const compactAtlas = window.matchMedia("(max-width: 640px)");
const tabletAtlas = window.matchMedia("(max-width: 1199px)");
const compactLandscapeAtlas = window.matchMedia(
  "(max-height: 520px) and (orientation: landscape)",
);
[compactAtlas, tabletAtlas, compactLandscapeAtlas].forEach((query) => query.addEventListener?.("change", () => {
  if (atlasData && currentRoute().view === "atlas") renderAtlas();
}));
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
    dataLoadState = "ready";
    applyLanguage(language);
    route();
  })
  .catch(() => {
    dataLoadState = "error";
    applyLanguage(language);
    renderError();
    route();
  });

document.querySelectorAll("[data-reload-site]").forEach((button) => {
  button.addEventListener("click", () => location.reload());
});
applyLanguage(language);
route();
delete document.documentElement.dataset.languagePending;
observeReveals();
document.body.focus({ preventScroll: true });
