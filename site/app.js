const stageCopy = {
  observe: {
    code: "O",
    en: "Record provenance before inferring intent.",
    ru: "Зафиксировать происхождение фактов до вывода о намерении.",
  },
  negotiate: {
    code: "N",
    en: "Turn consequential ambiguity into an operator decision.",
    ru: "Превратить значимую неоднозначность в решение оператора.",
  },
  bind: {
    code: "B",
    en: "Pin accepted intent to exact loops, policy, and scope.",
    ru: "Привязать принятое намерение к точным циклам, политике и области.",
  },
  execute: {
    code: "X",
    en: "Produce a candidate inside the authorized boundary.",
    ru: "Создать candidate внутри разрешённой границы.",
  },
  verify: {
    code: "V",
    en: "Let an independent reviewer test the declared evidence contract.",
    ru: "Дать независимому reviewer проверить заявленный контракт доказательств.",
  },
  publish: {
    code: "P",
    en: "Perform one authorized external effect — or explicitly perform none.",
    ru: "Выполнить один разрешённый внешний эффект — либо явно не выполнять его.",
  },
  evolve: {
    code: "E",
    en: "Propose a successor from repeated signals. Never activate it yourself.",
    ru: "Предложить преемника по повторяющимся сигналам. Никогда не активировать его самостоятельно.",
  },
};

const fallbackAtlas = {
  binding: {
    id: "concordloom-self-binding",
    digest: "unavailable-offline",
    rootLoopIds: ["concord-change"],
  },
  loops: Object.entries(stageCopy).map(([id, copy]) => ({
    id,
    label: id.replace("-", " "),
    purpose: copy.en,
    input: "Bound input",
    output: "Declared outcome",
  })),
};

let language = localStorage.getItem("concordloom-language") || "en";
let atlasData = fallbackAtlas;

function applyLanguage(nextLanguage) {
  language = nextLanguage;
  document.documentElement.lang = language;
  localStorage.setItem("concordloom-language", language);
  document.querySelectorAll("[data-en][data-ru]").forEach((element) => {
    element.textContent = element.dataset[language];
  });
  document.querySelector("[data-lang-label]").textContent = language === "en" ? "RU" : "EN";
  renderAtlas();
}

function setView(viewName) {
  const safeView = viewName === "atlas" ? "atlas" : "concept";
  document.querySelectorAll("[data-view]").forEach((view) => {
    const active = view.dataset.view === safeView;
    view.hidden = !active;
    view.classList.toggle("is-active", active);
  });
  document.querySelectorAll("[data-view-link]").forEach((link) => {
    const active = link.dataset.viewLink === safeView;
    link.classList.toggle("is-active", active);
    if (active) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
  if (safeView === "atlas") {
    requestAnimationFrame(() => revealVisible());
  }
}

function revealVisible() {
  document.querySelectorAll(".reveal:not(.is-visible)").forEach((element) => {
    const bounds = element.getBoundingClientRect();
    if (bounds.top < window.innerHeight * 0.92) {
      element.classList.add("is-visible");
    }
  });
}

function renderAtlasContract(loop) {
  const contract = document.querySelector("[data-atlas-contract]");
  if (!contract || !loop) return;
  contract.innerHTML = "";

  const label = document.createElement("span");
  label.textContent = language === "en" ? "OUTCOME CONTRACT" : "КОНТРАКТ РЕЗУЛЬТАТА";
  const title = document.createElement("h3");
  title.textContent = loop.label || loop.id;
  const purpose = document.createElement("p");
  purpose.textContent = loop.purpose;

  contract.append(label, title, purpose);
}

function renderAtlas() {
  const binding = atlasData.binding || fallbackAtlas.binding;
  const bindingElement = document.querySelector("[data-atlas-binding]");
  const rootElement = document.querySelector("[data-atlas-root]");
  if (bindingElement) {
    bindingElement.textContent = binding.id;
    bindingElement.title = binding.digest;
  }
  if (rootElement) rootElement.textContent = binding.rootLoopIds?.[0] || "—";

  const container = document.querySelector("[data-atlas-nodes]");
  if (!container) return;
  container.innerHTML = "";
  const loops = (atlasData.loops || fallbackAtlas.loops).filter(
    (loop) => !binding.rootLoopIds?.includes(loop.id),
  );
  loops.forEach((loop, index) => {
    const angle = -Math.PI / 2 + (index / loops.length) * Math.PI * 2;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "atlas-node";
    button.style.setProperty("--x", (Math.cos(angle) * 43).toFixed(2));
    button.style.setProperty("--y", (Math.sin(angle) * 43).toFixed(2));
    button.textContent = loop.label || loop.id;
    button.setAttribute("aria-label", `Inspect ${loop.label || loop.id}`);
    button.addEventListener("click", () => {
      container.querySelectorAll(".atlas-node").forEach((node) => node.classList.remove("is-active"));
      button.classList.add("is-active");
      renderAtlasContract(loop);
    });
    container.append(button);
    if (index === 0) {
      button.classList.add("is-active");
      renderAtlasContract(loop);
    }
  });
}

document.querySelector(".language-switch").addEventListener("click", () => {
  applyLanguage(language === "en" ? "ru" : "en");
});

document.querySelectorAll("[data-stage]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-stage]").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    const copy = stageCopy[button.dataset.stage];
    document.querySelector("[data-stage-code]").textContent = copy.code;
    document.querySelector("[data-stage-copy]").textContent = copy[language];
  });
});

window.addEventListener("hashchange", () => setView(location.hash.slice(1)));

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) entry.target.classList.add("is-visible");
    });
  },
  { threshold: 0.08 },
);
document.querySelectorAll(".reveal").forEach((element) => observer.observe(element));

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

fetch("data/atlas.json")
  .then((response) => {
    if (!response.ok) throw new Error(`Atlas data request failed: ${response.status}`);
    return response.json();
  })
  .then((data) => {
    atlasData = data;
    renderAtlas();
  })
  .catch(() => renderAtlas());

applyLanguage(language);
setView(location.hash.slice(1));
revealVisible();
