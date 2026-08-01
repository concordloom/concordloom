const phases = {
  en: {
    map: { short: "Map", label: "Map" },
    build: { short: "Build", label: "Build" },
    verify: { short: "Check", label: "Verify" },
    publish: { short: "Release", label: "Publish" },
    evolve: { short: "Evolve", label: "Evolve" },
  },
  ru: {
    map: { short: "Карта", label: "Карта" },
    build: { short: "Сборка", label: "Сборка" },
    verify: { short: "Пров.", label: "Проверка" },
    publish: { short: "Релиз", label: "Публикация" },
    evolve: { short: "Эвол.", label: "Эволюция" },
  },
};

const state = {
  language: "en",
  expandedCopy: false,
  drawerTrigger: null,
};

const localizeAttributes = (language) => {
  document.querySelectorAll("[data-en-aria-label][data-ru-aria-label]")
    .forEach((element) => {
      element.setAttribute("aria-label", element.dataset[`${language}AriaLabel`]);
    });
};

const localizeCopy = (language) => {
  document.querySelectorAll("[data-en][data-ru]").forEach((element) => {
    const longKey = `long${language === "en" ? "En" : "Ru"}`;
    const value = state.expandedCopy && element.dataset[longKey]
      ? element.dataset[longKey]
      : element.dataset[language];
    element.textContent = value;
  });
};

function selectLanguage(language) {
  state.language = language;
  document.documentElement.lang = language;
  document.title = language === "ru"
    ? "Мастерская Signal Canvas"
    : "Signal Canvas workshop";
  const languageSwitch = document.querySelector("[data-workshop-language-switch]");
  languageSwitch.querySelector("[data-lang-label]").textContent =
    language === "en" ? "RU" : "EN";
  languageSwitch.setAttribute(
    "aria-label",
    language === "en" ? "Switch to Russian" : "Переключить на английский",
  );
  document.querySelectorAll(".workshop-rail [data-phase]").forEach((item) => {
    const copy = phases[language][item.dataset.phase];
    item.querySelector("span").textContent = copy.short;
    item.setAttribute("aria-label", copy.label);
  });
  localizeCopy(language);
  localizeAttributes(language);
}

function selectPhase(phase, announce = true) {
  document.querySelectorAll(".workshop-rail [data-phase]").forEach((item) => {
    const active = item.dataset.phase === phase;
    item.classList.toggle("is-active", active);
    if (active) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  });
  document.querySelectorAll("[data-phase-control]").forEach((button) => {
    const active = button.dataset.phaseControl === phase;
    button.setAttribute("aria-pressed", String(active));
    button.setAttribute("tabindex", active ? "0" : "-1");
  });
  if (announce) {
    const copy = state.language === "ru"
      ? `Текущий этап: ${phases.ru[phase].label}`
      : `Current step: ${phases.en[phase].label}`;
    document.querySelector(".workshop-announcer").textContent = copy;
  }
}

function setCopyExpansion(expanded) {
  state.expandedCopy = expanded;
  const control = document.querySelector("[data-copy-expansion]");
  control.setAttribute("aria-pressed", String(expanded));
  control.dataset.en = expanded ? "Use regular copy" : "Add 30% text";
  control.dataset.ru = expanded ? "Вернуть обычный текст" : "Увеличить текст на 30%";
  localizeCopy(state.language);
  document.querySelector(".workshop-announcer").textContent =
    state.language === "ru"
      ? expanded
        ? "Текст увеличен примерно на 30 процентов"
        : "Обычная длина текста восстановлена"
      : expanded
        ? "Copy expanded by about 30 percent"
        : "Regular copy length restored";
}

function setDrawer(open, trigger = null) {
  const drawer = document.querySelector("#workshop-drawer");
  const scrim = document.querySelector("[data-drawer-scrim]");
  if (open) {
    state.drawerTrigger = trigger || document.activeElement;
    scrim.hidden = false;
    drawer.classList.add("is-open");
    drawer.setAttribute("aria-hidden", "false");
    document.body.classList.add("is-inspector-open");
    drawer.querySelector("[data-drawer-close]").focus();
    return;
  }
  drawer.classList.remove("is-open");
  drawer.setAttribute("aria-hidden", "true");
  document.body.classList.remove("is-inspector-open");
  scrim.hidden = true;
  if (state.drawerTrigger instanceof HTMLElement) state.drawerTrigger.focus();
  state.drawerTrigger = null;
}

function movePressedButton(event, selector, valueKey, select) {
  if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End"]
    .includes(event.key)) return;
  const buttons = [...document.querySelectorAll(selector)];
  const current = buttons.indexOf(event.currentTarget);
  if (current < 0) return;
  event.preventDefault();
  let next = current;
  if (event.key === "Home") next = 0;
  else if (event.key === "End") next = buttons.length - 1;
  else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
    next = (current - 1 + buttons.length) % buttons.length;
  } else {
    next = (current + 1) % buttons.length;
  }
  buttons[next].focus();
  select(buttons[next].dataset[valueKey]);
}

document.querySelector("[data-workshop-language-switch]").addEventListener(
  "click",
  () => selectLanguage(state.language === "en" ? "ru" : "en"),
);

document.querySelectorAll("[data-phase-control]").forEach((button) => {
  button.addEventListener("click", () => selectPhase(button.dataset.phaseControl));
  button.addEventListener("keydown", (event) => {
    movePressedButton(
      event,
      "[data-phase-control]",
      "phaseControl",
      selectPhase,
    );
  });
});

const menuButton = document.querySelector(".menu-switch");
const workshopNav = document.querySelector("#workshop-nav");

function setMenu(open) {
  menuButton.setAttribute("aria-expanded", String(open));
  workshopNav.classList.toggle("is-open", open);
  if (open) workshopNav.querySelector("a").focus();
}

menuButton.addEventListener("click", () => {
  setMenu(menuButton.getAttribute("aria-expanded") !== "true");
});
workshopNav.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => setMenu(false));
});

document.querySelectorAll("button.workshop-node:not(:disabled)")
  .forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("button.workshop-node").forEach((node) => {
        node.classList.remove("is-current");
        node.setAttribute("aria-pressed", "false");
      });
      button.classList.add("is-current");
      button.setAttribute("aria-pressed", "true");
    });
  });

document.querySelector("[data-copy-expansion]").addEventListener("click", (event) => {
  setCopyExpansion(event.currentTarget.getAttribute("aria-pressed") !== "true");
});
document.querySelector("[data-drawer-open]").addEventListener("click", (event) => {
  setDrawer(true, event.currentTarget);
});
document.querySelector("[data-drawer-close]").addEventListener("click", () => {
  setDrawer(false);
});
document.querySelector("[data-drawer-scrim]").addEventListener("click", () => {
  setDrawer(false);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && workshopNav.classList.contains("is-open")) {
    event.preventDefault();
    setMenu(false);
    menuButton.focus();
    return;
  }
  const drawer = document.querySelector("#workshop-drawer");
  if (!drawer.classList.contains("is-open")) return;
  if (event.key === "Escape") {
    event.preventDefault();
    setDrawer(false);
    return;
  }
  if (event.key !== "Tab") return;
  const controls = [...drawer.querySelectorAll(
    'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
  )];
  if (!controls.length) return;
  const first = controls[0];
  const last = controls[controls.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
});

selectLanguage("en");
selectPhase("map", false);
