const phases = {
  en: {
    map: { label: "Map", short: "Map" },
    build: { label: "Build", short: "Build" },
    verify: { label: "Verify", short: "Verify" },
    publish: { label: "Publish", short: "Publish" },
    evolve: { label: "Evolve", short: "Evolve" },
  },
  ru: {
    map: { label: "Карта", short: "Карта" },
    build: { label: "Сборка", short: "Сборка" },
    verify: { label: "Проверка", short: "Контроль" },
    publish: { label: "Публикация", short: "Релиз" },
    evolve: { label: "Эволюция", short: "Эволюция" },
  },
};

function selectPhase(phase) {
  document.querySelectorAll(".system-rail li").forEach((item) => {
    const active = item.dataset.phase === phase;
    item.classList.toggle("is-active", active);
    if (active) item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  });
  document.querySelectorAll("[data-phase-control]").forEach((button) => {
    button.setAttribute(
      "aria-pressed",
      String(button.dataset.phaseControl === phase),
    );
  });
}

function selectLanguage(language) {
  document.documentElement.lang = language;
  document.title = language === "ru"
    ? "Стенд Patch Panel"
    : "Patch Panel Workshop";
  document.querySelector(".workshop-language").setAttribute(
    "aria-label",
    language === "ru" ? "Язык стенда" : "Fixture language",
  );
  const rail = document.querySelector(".system-rail");
  rail.setAttribute("aria-label", rail.dataset[`${language}AriaLabel`]);
  document.querySelectorAll("[data-language]").forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.language === language));
  });
  document.querySelectorAll(".system-rail [data-phase]").forEach((item) => {
    const copy = phases[language][item.dataset.phase];
    const label = item.querySelector("span");
    label.textContent = copy.label;
    label.dataset.short = copy.short;
    item.setAttribute("aria-label", copy.label);
  });
  document.querySelectorAll("[data-en][data-ru]").forEach((element) => {
    element.textContent = element.dataset[language];
  });
}

document.querySelectorAll("[data-phase-control]").forEach((button) => {
  button.addEventListener("click", () => selectPhase(button.dataset.phaseControl));
});
document.querySelectorAll("[data-language]").forEach((button) => {
  button.addEventListener("click", () => selectLanguage(button.dataset.language));
});

selectLanguage(document.documentElement.lang === "ru" ? "ru" : "en");
