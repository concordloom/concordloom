#!/usr/bin/env python3
"""Activate the complete Concord Loom development system as self-binding v5."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from concordloom.canonical import digest, load, save
from concordloom.catalog import append_binding
from concordloom.compiler import (
    accept_loop_design,
    activate_binding,
    compile_registry,
    create_binding_proposal,
    propose_loop_design,
)
from concordloom.evolution import propose_evolution
from concordloom.loops import validate_policy, validate_registry


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "framework" / "concordloom"
PREDECESSOR_DIR = SOURCE / "v4"
GRAPH_DIR = SOURCE / "v3"
TARGET = SOURCE / "v5"
STAMP = "2026-07-27T13:00:00Z"
OPERATOR = {
    "id": "example-operator",
    "kind": "operator",
    "display_name": "Operator",
}
EXTERNAL_MUTATIONS = [
    "github-pages",
    "github-repository-homepage",
    "github-repository-social-preview",
]


# Stable responsibility classes. Tools, models and providers are deliberately
# kept in execution profiles below: they change faster than the product model.
# id, parent, EN label, RU label, EN purpose, RU purpose, role, profile
NODES = [
    (
        "steward-concordloom", None,
        "Steward Concord Loom", "Развивать Concord Loom",
        "Keep the whole product useful, trustworthy and coherent.",
        "Сохранять продукт полезным, надёжным и цельным.",
        "operator", "strategy",
    ),
    (
        "product-direction", "steward-concordloom",
        "Product Direction", "Направление продукта",
        "Decide what Concord Loom is and what it should do next.",
        "Определять границы продукта и его следующие задачи.",
        "product steward", "strategy",
    ),
    (
        "research-theory", "steward-concordloom",
        "Research and Theory", "Исследования и теория",
        "Build and challenge the conceptual basis.",
        "Создавать и проверять теоретическую основу.",
        "researcher", "research",
    ),
    (
        "protocol-design", "steward-concordloom",
        "Protocol Design", "Проектирование протокола",
        "Define portable machine semantics and compatibility.",
        "Задавать переносимые машинные правила и совместимость.",
        "protocol designer", "protocol",
    ),
    (
        "runtime-tooling", "steward-concordloom",
        "Runtime and Tooling", "Исполнение и инструменты",
        "Make the protocol executable and practical.",
        "Делать протокол исполнимым и удобным.",
        "implementer", "engineering",
    ),
    (
        "trust-assurance", "steward-concordloom",
        "Trust and Assurance", "Доверие и проверка",
        "Independently challenge claims, authority and candidates.",
        "Независимо проверять утверждения, полномочия и результаты.",
        "independent reviewer", "assurance",
    ),
    (
        "bindings-adapters", "steward-concordloom",
        "Bindings and Adapters", "Привязки и адаптеры",
        "Connect the neutral kernel to real domains and environments.",
        "Соединять нейтральное ядро с предметными областями и средами.",
        "integration author", "integration",
    ),
    (
        "knowledge-experience", "steward-concordloom",
        "Knowledge and Experience", "Знания и опыт",
        "Make the system understandable and navigable.",
        "Делать систему понятной и удобной для изучения.",
        "editor", "editorial",
    ),
    (
        "release-distribution", "steward-concordloom",
        "Release and Distribution", "Выпуск и распространение",
        "Deliver verified bytes and authorized external effects.",
        "Публиковать проверенные файлы и разрешённые внешние изменения.",
        "publisher", "release",
    ),
    (
        "adoption-feedback", "steward-concordloom",
        "Adoption and Feedback", "Применение и обратная связь",
        "Test usefulness in real work and collect friction.",
        "Проверять пользу в реальной работе и собирать проблемы.",
        "adoption analyst", "insight",
    ),
    (
        "system-evolution", "steward-concordloom",
        "System Evolution", "Эволюция системы",
        "Propose, review and explicitly activate successor bindings.",
        "Предлагать, проверять и отдельно включать новые версии правил.",
        "evolution steward", "evolution-analysis",
    ),
    # Product direction
    ("discover-product-needs", "product-direction", "Discover Needs", "Выявлять потребности",
     "Find valuable problems without prescribing a solution.", "Находить важные проблемы, не навязывая решение.",
     "product researcher", "strategy"),
    ("maintain-product-boundary", "product-direction", "Maintain Product Boundary", "Удерживать границы продукта",
     "Keep domain assumptions out of the universal kernel.", "Не допускать предметные допущения в универсальное ядро.",
     "product steward", "strategy"),
    ("decide-product", "product-direction", "Make Product Decisions", "Принимать продуктовые решения",
     "Resolve consequential product choices.", "Принимать важные продуктовые решения.",
     "operator", "strategy"),
    ("prioritize-roadmap", "product-direction", "Prioritize Roadmap", "Определять приоритеты",
     "Order bounded outcomes under real constraints.", "Упорядочивать ограниченные результаты с учётом ограничений.",
     "product steward", "strategy"),
    # Research and theory
    ("observe-landscape", "research-theory", "Observe the Landscape", "Исследовать ландшафт",
     "Collect attributable primary evidence.", "Собирать проверяемые первичные источники.",
     "researcher", "research"),
    ("formalize-theory", "research-theory", "Formalize Theory", "Формализовать теорию",
     "Turn claims into definitions and falsifiable propositions.", "Превращать идеи в определения и проверяемые утверждения.",
     "theorist", "research"),
    ("test-applicability", "research-theory", "Test Applicability", "Проверять применимость",
     "Search for counterexamples across domains.", "Искать контрпримеры в разных предметных областях.",
     "independent researcher", "research"),
    ("maintain-article", "research-theory", "Maintain the Article", "Развивать статью",
     "Keep the long-form theory accurate and readable.", "Поддерживать точность и понятность научного текста.",
     "research editor", "research"),
    # Protocol
    ("define-artifact-semantics", "protocol-design", "Define Artifact Semantics", "Определять семантику артефактов",
     "Define fact states and artifact relationships.", "Определять состояния фактов и связи артефактов.",
     "protocol designer", "protocol"),
    ("design-graphs-policies", "protocol-design", "Design Graphs and Policies", "Проектировать графы и правила",
     "Define containment, flow, scope and authority.", "Задавать вложенность, переходы, область действий и полномочия.",
     "protocol designer", "protocol"),
    ("evolve-schemas", "protocol-design", "Evolve Schemas", "Развивать схемы",
     "Introduce compatible protocol changes.", "Вносить совместимые изменения протокола.",
     "schema maintainer", "protocol"),
    ("assure-compatibility", "protocol-design", "Assure Compatibility", "Проверять совместимость",
     "Prove how older artifacts are handled.", "Доказывать, как обрабатываются старые артефакты.",
     "protocol reviewer", "assurance"),
    # Runtime
    ("maintain-compiler-core", "runtime-tooling", "Maintain Compiler Core", "Развивать компилятор",
     "Compile accepted inputs deterministically.", "Детерминированно собирать принятые входные данные.",
     "implementer", "engineering"),
    ("operate-run-lifecycle", "runtime-tooling", "Operate Run Lifecycle", "Исполнять жизненный цикл запуска",
     "Guard scope, collect evidence and complete runs.", "Проверять область действий, собирать данные и завершать запуски.",
     "executor", "engineering"),
    ("maintain-cli", "runtime-tooling", "Maintain CLI", "Развивать CLI",
     "Expose kernel operations safely.", "Безопасно предоставлять операции ядра.",
     "implementer", "engineering"),
    ("maintain-automation", "runtime-tooling", "Maintain Automation", "Развивать автоматизацию",
     "Integrate agents without hidden authority.", "Подключать агентов без скрытых полномочий.",
     "automation author", "engineering"),
    # Trust
    ("model-threats", "trust-assurance", "Model Threats", "Моделировать угрозы",
     "Find authority, provenance and isolation failures.", "Находить ошибки полномочий, происхождения и изоляции.",
     "security reviewer", "assurance"),
    ("validate-invariants", "trust-assurance", "Validate Invariants", "Проверять инварианты",
     "Exercise graph, scope, digest and authority rules.", "Проверять правила графа, области действий, хешей и полномочий.",
     "test author", "assurance"),
    ("review-candidate", "trust-assurance", "Review Candidate", "Проверять результат",
     "Independently judge one pinned candidate.", "Независимо оценивать одну точно зафиксированную версию результата.",
     "independent reviewer", "assurance"),
    ("assure-release", "trust-assurance", "Assure Release", "Проверять готовность выпуска",
     "Confirm verified bytes match the publication plan.", "Подтверждать соответствие проверенных файлов плану публикации.",
     "release reviewer", "assurance"),
    # Bindings
    ("maintain-self-binding", "bindings-adapters", "Maintain Self-Binding", "Развивать правила самоизменения",
     "Describe how Concord Loom governs its own changes.", "Описывать правила, по которым Concord Loom меняет сам себя.",
     "binding author", "integration"),
    ("maintain-evidence-adapters", "bindings-adapters", "Maintain Evidence Adapters", "Развивать адаптеры наблюдения",
     "Observe environments without making them universal.", "Наблюдать среды, не превращая их особенности в общие правила.",
     "integration author", "integration"),
    ("maintain-execution-adapters", "bindings-adapters", "Maintain Execution Adapters", "Развивать адаптеры исполнения",
     "Perform explicitly scoped environment effects.", "Выполнять только явно разрешённые изменения среды.",
     "integration author", "integration"),
    ("maintain-reference-bindings", "bindings-adapters", "Maintain Reference Bindings", "Развивать эталонные конфигурации",
     "Demonstrate the grammar in real domains.", "Показывать применение общей схемы в реальных областях.",
     "domain author", "integration"),
    # Knowledge
    ("design-information-architecture", "knowledge-experience", "Design Information Architecture", "Проектировать структуру знаний",
     "Keep content discoverable by task and concept.", "Делать материалы доступными по задачам и понятиям.",
     "information architect", "editorial"),
    ("author-documentation", "knowledge-experience", "Author Documentation", "Писать документацию",
     "Explain accepted behavior in direct human language.", "Объяснять принятое поведение прямым человеческим языком.",
     "technical writer", "editorial"),
    ("localize-content", "knowledge-experience", "Localize Content", "Локализовать материалы",
     "Preserve meaning across English and Russian.", "Сохранять смысл в английской и русской версиях.",
     "bilingual editor", "localization"),
    ("review-comprehension", "knowledge-experience", "Review Human Comprehension", "Проверять понятность",
     "Catch jargon, literal translation and empty prose.", "Находить жаргон, буквальный перевод и бессодержательный текст.",
     "independent language reviewer", "comprehension"),
    ("design-site-experience", "knowledge-experience", "Design Site Experience", "Проектировать сайт",
     "Turn knowledge into a distinctive accessible interface.", "Превращать знания в выразительный и доступный интерфейс.",
     "experience designer", "experience"),
    ("project-atlas", "knowledge-experience", "Project the Atlas", "Строить Atlas",
     "Render accepted facts without becoming their source.", "Показывать принятые факты, не становясь их источником.",
     "projection builder", "experience"),
    # Release
    ("plan-release", "release-distribution", "Plan Release", "Планировать выпуск",
     "Pin the candidate, route and authority.", "Фиксировать результат, маршрут и полномочия.",
     "release manager", "release"),
    ("distribute-package", "release-distribution", "Distribute Package", "Публиковать пакет",
     "Publish immutable installable artifacts.", "Публиковать неизменяемые устанавливаемые артефакты.",
     "publisher", "release"),
    ("publish-site", "release-distribution", "Publish Site", "Публиковать сайт",
     "Deploy exact checked static bytes.", "Развёртывать точные проверенные файлы сайта.",
     "publisher", "release"),
    ("maintain-repository-presence", "release-distribution", "Maintain Repository Presence", "Оформлять репозиторий",
     "Publish the About URL, mark and social preview.", "Публиковать ссылку About, знак и социальное превью.",
     "publisher", "release"),
    ("verify-live-release", "release-distribution", "Verify Live Release", "Проверять опубликованный выпуск",
     "Prove the public endpoint serves the pinned candidate.", "Доказывать, что публичный адрес отдаёт зафиксированную версию.",
     "release verifier", "assurance"),
    # Adoption
    ("observe-onboarding", "adoption-feedback", "Observe Onboarding", "Наблюдать за первым использованием",
     "Find where new users succeed or get stuck.", "Находить места, где новые пользователи справляются или застревают.",
     "adoption researcher", "insight"),
    ("validate-use-cases", "adoption-feedback", "Validate Use Cases", "Проверять сценарии применения",
     "Test the framework outside its self-binding.", "Проверять фреймворк за пределами его собственной разработки.",
     "domain researcher", "insight"),
    ("collect-friction", "adoption-feedback", "Collect Friction", "Собирать проблемы",
     "Record defects and confusion with provenance.", "Фиксировать ошибки и непонимание вместе с источником.",
     "triager", "insight"),
    ("synthesize-feedback", "adoption-feedback", "Synthesize Feedback", "Обобщать обратную связь",
     "Turn repeated observations into evidence, not intent.", "Превращать повторяющиеся наблюдения в данные, а не решения.",
     "analyst", "insight"),
    # Evolution
    ("collect-evolution-signals", "system-evolution", "Collect Evolution Signals", "Собирать сигналы эволюции",
     "Pin multiple attributable signals to the active binding.", "Привязывать несколько проверяемых сигналов к действующей версии.",
     "evolution analyst", "evolution-analysis"),
    ("propose-successor", "system-evolution", "Propose Successor", "Предлагать новую версию",
     "Describe exact bounded changes without granting authority.", "Описывать точные изменения, не выдавая им полномочий.",
     "evolution proposer", "evolution-proposal"),
    ("review-successor", "system-evolution", "Review Successor", "Проверять новую версию",
     "Independently verify need, exactness and boundaries.", "Независимо проверять необходимость, точность и границы.",
     "evolution reviewer", "evolution-review"),
    ("activate-successor", "system-evolution", "Activate Successor", "Включать новую версию",
     "Make a reviewed successor active through a separate operator act.", "Включать проверенную версию отдельным решением оператора.",
     "operator only", "operator"),
    ("observe-migration", "system-evolution", "Observe Migration", "Наблюдать за переходом",
     "Detect regressions after activation without rewriting history.", "Находить регрессии после включения, не переписывая историю.",
     "evolution analyst", "evolution-analysis"),
]


PROFILES = {
    "strategy": {
        "model_intent": "high-reasoning synthesis and trade-offs",
        "skills": ["writing-clearly-and-concisely"],
        "tools": ["repository", "decision-log"],
    },
    "research": {
        "model_intent": "source-critical research reasoning",
        "skills": ["writing-clearly-and-concisely"],
        "tools": ["primary-sources", "citation-checks"],
    },
    "protocol": {
        "model_intent": "schema and invariant reasoning",
        "skills": ["writing-clearly-and-concisely"],
        "tools": ["json-schema", "tests", "repository"],
    },
    "engineering": {
        "model_intent": "coding and debugging",
        "skills": [],
        "tools": ["shell", "tests", "github"],
    },
    "assurance": {
        "model_intent": "fresh independent review context",
        "skills": ["web-design-guidelines"],
        "tools": ["validators", "browser", "test-runner"],
    },
    "integration": {
        "model_intent": "environment-specific implementation reasoning",
        "skills": [],
        "tools": ["contract-fixtures"],
    },
    "editorial": {
        "model_intent": "precise technical editing",
        "skills": ["writing-clearly-and-concisely"],
        "tools": ["terminology-check", "link-check"],
    },
    "localization": {
        "model_intent": "bilingual editorial reasoning",
        "skills": ["writing-clearly-and-concisely"],
        "tools": ["glossary", "parity-check", "comprehension-check"],
    },
    "comprehension": {
        "model_intent": "independent reader review, preferably human-backed",
        "skills": ["writing-clearly-and-concisely"],
        "tools": ["task-based-reading-test"],
    },
    "experience": {
        "model_intent": "visual and frontend implementation",
        "skills": [
            "design-taste-frontend", "frontend-design",
            "web-design-guidelines", "imagegen",
        ],
        "tools": ["browser", "accessibility-checks"],
    },
    "release": {
        "model_intent": "deterministic publisher",
        "skills": ["github"],
        "tools": ["github", "pages"],
    },
    "insight": {
        "model_intent": "qualitative synthesis without inventing intent",
        "skills": ["writing-clearly-and-concisely"],
        "tools": ["issues", "interviews"],
    },
    "evolution-analysis": {
        "model_intent": "high-reasoning signal analysis",
        "skills": ["writing-clearly-and-concisely"],
        "tools": ["digest-validator", "cas-validator"],
    },
    "evolution-proposal": {
        "model_intent": "high-reasoning bounded proposal",
        "skills": ["writing-clearly-and-concisely"],
        "tools": ["digest-validator", "cas-validator"],
    },
    "evolution-review": {
        "model_intent": "independent successor review",
        "skills": ["writing-clearly-and-concisely"],
        "tools": ["digest-validator", "cas-validator"],
    },
    "operator": {
        "model_intent": "human decision; a model may explain but cannot decide",
        "skills": [],
        "tools": ["recorded-operator-decision"],
    },
}

ROLE_RU = {
    "operator": "оператор",
    "product steward": "ответственный за продукт",
    "researcher": "исследователь",
    "protocol designer": "проектировщик протокола",
    "implementer": "разработчик",
    "independent reviewer": "независимый проверяющий",
    "integration author": "автор интеграции",
    "editor": "редактор",
    "publisher": "публикатор",
    "adoption analyst": "аналитик применения",
    "evolution steward": "ответственный за эволюцию",
    "product researcher": "исследователь продукта",
    "theorist": "теоретик",
    "independent researcher": "независимый исследователь",
    "research editor": "научный редактор",
    "schema maintainer": "ответственный за схемы",
    "protocol reviewer": "проверяющий протокола",
    "executor": "исполнитель",
    "automation author": "автор автоматизации",
    "security reviewer": "проверяющий безопасность",
    "test author": "автор проверок",
    "release reviewer": "проверяющий выпуска",
    "binding author": "автор конфигурации",
    "domain author": "эксперт предметной области",
    "information architect": "архитектор информации",
    "technical writer": "технический писатель",
    "bilingual editor": "двуязычный редактор",
    "independent language reviewer": "независимый редактор понятности",
    "experience designer": "дизайнер интерфейса",
    "projection builder": "разработчик проекции",
    "release manager": "ответственный за выпуск",
    "release verifier": "проверяющий публикации",
    "adoption researcher": "исследователь применения",
    "domain researcher": "исследователь предметной области",
    "triager": "ответственный за разбор сигналов",
    "analyst": "аналитик",
    "evolution analyst": "аналитик эволюции",
    "evolution proposer": "автор предложения",
    "evolution reviewer": "проверяющий новой версии",
    "operator only": "только оператор",
}

MODEL_INTENT_RU = {
    "strategy": "глубокий анализ вариантов и компромиссов",
    "research": "исследование с критической проверкой источников",
    "protocol": "проектирование схем и инвариантов",
    "engineering": "разработка и отладка",
    "assurance": "независимая проверка в новом контексте",
    "integration": "разработка с учётом конкретной среды",
    "editorial": "точное техническое редактирование",
    "localization": "двуязычное редактирование смысла",
    "comprehension": "независимая читательская проверка, желательно с участием человека",
    "experience": "визуальная и интерфейсная разработка",
    "release": "детерминированная публикация",
    "insight": "обобщение наблюдений без выдумывания намерений",
    "evolution-analysis": "глубокий анализ сигналов",
    "evolution-proposal": "подготовка ограниченного предложения",
    "evolution-review": "независимая проверка новой версии",
    "operator": "решение человека; модель может объяснить, но не решать",
}

RUN_GRAMMAR = [
    ("observe", "Observe", "Наблюдать", "Collect attributable facts.", "Собрать факты с указанием источника."),
    ("negotiate", "Negotiate", "Согласовать", "Turn ambiguity into accepted intent.", "Превратить неоднозначность в принятое решение."),
    ("bind", "Bind", "Зафиксировать правила", "Compile exact scope and authority.", "Зафиксировать точные границы и полномочия."),
    ("execute", "Execute", "Выполнить", "Produce one bounded candidate.", "Создать один результат в разрешённых границах."),
    ("verify", "Verify", "Проверить", "Independently evaluate that candidate.", "Независимо проверить этот результат."),
    ("publish", "Publish", "Опубликовать", "Perform an explicitly authorized effect.", "Выполнить только явно разрешённое внешнее изменение."),
    ("evolve", "Evolve", "Предложить изменение", "Draft a non-activating successor.", "Подготовить новую версию без её включения."),
]

# Real contracts used by the compiler and Atlas. They stay short enough to scan
# in the inspector, but name the actual material moving through each cycle.
DETAILS = {
    "steward-concordloom": ("Mission, evidence and operator decisions.", "An accepted product, release or successor decision.", "Цель, данные проверки и решения оператора.", "Принятый продукт, выпуск или решение о новой версии.", ["charter", "catalog", "receipts"]),
    "product-direction": ("Needs, research and adoption signals.", "Accepted product intent and priorities.", "Потребности, исследования и сигналы применения.", "Принятые цели продукта и приоритеты.", ["product-boundary", "decisions", "roadmap"]),
    "research-theory": ("Questions, sources and counterexamples.", "Supported claims, models and article revisions.", "Вопросы, источники и контрпримеры.", "Обоснованные утверждения, модели и новая версия статьи.", ["observation-corpus", "claim-ledger", "article"]),
    "protocol-design": ("Accepted theory and protocol requirements.", "Schemas, invariants and compatibility rules.", "Принятая теория и требования к протоколу.", "Схемы, инварианты и правила совместимости.", ["schemas", "graph-contracts", "compatibility-matrix"]),
    "runtime-tooling": ("Accepted protocol semantics.", "Tested compiler, runner, CLI and automation.", "Принятые правила протокола.", "Проверенные компилятор, runner, CLI и автоматизация.", ["source", "tests", "cli", "plugin"]),
    "trust-assurance": ("A pinned claim, candidate or release.", "An independent verdict with evidence.", "Зафиксированное утверждение, результат или выпуск.", "Независимый вердикт с данными проверки.", ["threat-model", "tests", "review-receipts"]),
    "bindings-adapters": ("Kernel contracts and environment needs.", "Tested bindings and adapter contracts.", "Контракты ядра и требования среды.", "Проверенные конфигурации циклов и адаптеры.", ["bindings", "adapters", "fixtures"]),
    "knowledge-experience": ("Accepted facts and reader tasks.", "Clear bilingual documentation and interfaces.", "Принятые факты и задачи читателя.", "Понятная двуязычная документация и интерфейсы.", ["markdown", "glossary", "site", "atlas"]),
    "release-distribution": ("A verified candidate and publication authority.", "Published bytes, external state and provenance.", "Проверенная версия и право на публикацию.", "Опубликованные файлы, внешнее состояние и отчёт о происхождении.", ["release-manifest", "checksums", "deployment-receipts"]),
    "adoption-feedback": ("A released system and real usage.", "Classified friction and normalized signals.", "Опубликованная система и реальное использование.", "Разобранные проблемы и нормализованные сигналы.", ["onboarding-studies", "case-reports", "signals"]),
    "system-evolution": ("Repeated signals pinned to the active binding.", "A rejected proposal or separately activated successor.", "Повторяющиеся сигналы, привязанные к действующей версии.", "Отклонённое предложение или отдельно включённая новая версия.", ["signals", "proposal", "review", "activation-receipt"]),
    "discover-product-needs": ("User observations and unresolved work.", "Prioritized problem statements.", "Наблюдения за пользователями и нерешённые задачи.", "Упорядоченные формулировки проблем.", ["interviews", "need-records"]),
    "maintain-product-boundary": ("Features and domain assumptions under consideration.", "A boundary verdict and cut list.", "Предлагаемые функции и предметные допущения.", "Решение о границе продукта и список исключений.", ["charter", "cut-list"]),
    "decide-product": ("Alternatives, evidence and consequences.", "One recorded product decision.", "Варианты, данные и последствия.", "Одно зафиксированное продуктовое решение.", ["decision-record"]),
    "prioritize-roadmap": ("Accepted decisions and constraints.", "An ordered set of bounded outcomes.", "Принятые решения и ограничения.", "Упорядоченный набор ограниченных результатов.", ["roadmap", "outcome-cards"]),
    "observe-landscape": ("Research questions and primary sources.", "An attributable observation corpus.", "Исследовательские вопросы и первичные источники.", "Корпус наблюдений с указанием источников.", ["sources", "provenance"]),
    "formalize-theory": ("Observations and candidate claims.", "Definitions, invariants and falsifiable propositions.", "Наблюдения и проверяемые идеи.", "Определения, инварианты и опровержимые утверждения.", ["definitions", "claim-ledger"]),
    "test-applicability": ("A formal model and cases from different domains.", "Counterexamples and an applicability report.", "Формальная модель и случаи из разных областей.", "Контрпримеры и отчёт о применимости.", ["case-matrix", "counterexamples"]),
    "maintain-article": ("Accepted claims, citations and reader findings.", "Matched English and Russian article candidates.", "Принятые утверждения, ссылки и замечания читателей.", "Согласованные английская и русская версии статьи.", ["article-en", "article-ru", "citations"]),
    "define-artifact-semantics": ("Accepted concepts and fact-state requirements.", "Canonical artifact types and vocabulary.", "Принятые понятия и требования к состояниям факта.", "Канонические типы артефактов и словарь.", ["schemas", "vocabulary"]),
    "design-graphs-policies": ("Containment, flow, scope and authority needs.", "Graph and policy contracts.", "Требования к вложенности, переходам, действиям и полномочиям.", "Контракты графов и правил.", ["registry-schema", "policy-schema"]),
    "evolve-schemas": ("An accepted protocol change.", "Successor schemas and migration rules.", "Принятое изменение протокола.", "Новые схемы и правила перехода.", ["schemas", "migration-rules"]),
    "assure-compatibility": ("Old and new artifact versions.", "A compatibility verdict backed by fixtures.", "Старые и новые версии артефактов.", "Вердикт о совместимости, подтверждённый примерами.", ["fixtures", "compatibility-matrix"]),
    "maintain-compiler-core": ("Accepted graph, design and policy.", "A deterministic content-addressed binding.", "Принятые граф, дизайн и правила.", "Детерминированная конфигурация с точным хешем.", ["compiler", "binding", "digest-tests"]),
    "operate-run-lifecycle": ("An authorized card and exact candidate.", "Attempts, evidence and a completion receipt.", "Разрешённая карточка запуска и точная версия результата.", "Попытки, данные проверки и отчёт о завершении.", ["run-card", "attempts", "evidence", "receipt"]),
    "maintain-cli": ("Kernel operations and user tasks.", "Safe commands, help and contract tests.", "Операции ядра и задачи пользователя.", "Безопасные команды, справка и контрактные тесты.", ["cli", "help", "tests"]),
    "maintain-automation": ("Explicit automation contracts.", "A bounded plugin, skill or harness.", "Явные контракты автоматизации.", "Ограниченный плагин, скилл или набор проверок.", ["plugin", "skills", "harness"]),
    "model-threats": ("System model, assets and trust assumptions.", "Threats, mitigations and open risks.", "Модель системы, активы и допущения о доверии.", "Угрозы, меры защиты и открытые риски.", ["threat-model"]),
    "validate-invariants": ("Implementation and declared invariants.", "Deterministic and adversarial test evidence.", "Реализация и заявленные инварианты.", "Данные детерминированных и атакующих тестов.", ["tests", "test-evidence"]),
    "review-candidate": ("An exact candidate manifest and evidence contract.", "A pass, fail or indeterminate review receipt.", "Точное описание версии и требования к проверке.", "Отчёт с результатом: пройдено, ошибка или недостаточно данных.", ["candidate-manifest", "review-receipt"]),
    "assure-release": ("A verified candidate and publication route.", "A release-readiness verdict.", "Проверенная версия и маршрут публикации.", "Вердикт о готовности выпуска.", ["release-evidence", "readiness-verdict"]),
    "maintain-self-binding": ("The accepted development process of this repository.", "A new self-binding proposal and catalog entry.", "Принятый процесс разработки этого репозитория.", "Предложение новых правил самоизменения и запись каталога.", ["registry", "policy", "binding", "catalog"]),
    "maintain-evidence-adapters": ("An environment and observation contract.", "Observed facts with provenance.", "Среда и контракт наблюдения.", "Наблюдаемые факты с указанием источника.", ["adapter", "provenance-fixtures"]),
    "maintain-execution-adapters": ("A scoped grant and environment contract.", "An external effect and exact receipt.", "Ограниченное разрешение и контракт среды.", "Внешнее изменение и точный отчёт.", ["adapter", "effect-receipt"]),
    "maintain-reference-bindings": ("A domain model and kernel grammar.", "A tested example binding.", "Модель предметной области и общая схема ядра.", "Проверенная примерная конфигурация циклов.", ["example", "fixtures"]),
    "design-information-architecture": ("Content inventory and reader tasks.", "A route, navigation and section map.", "Список материалов и задачи читателя.", "Карта маршрутов, навигации и разделов.", ["content-map", "route-map"]),
    "author-documentation": ("Accepted behavior and concrete user tasks.", "Direct source documentation with examples.", "Принятое поведение и конкретные задачи пользователя.", "Прямая исходная документация с примерами.", ["markdown", "examples"]),
    "localize-content": ("Source text, glossary and semantic section map.", "Equivalent English and Russian peers.", "Исходный текст, словарь и смысловая карта разделов.", "Равнозначные английская и русская версии.", ["locale-peers", "glossary"]),
    "review-comprehension": ("A text candidate and representative reader tasks.", "A comprehension verdict and actionable findings.", "Версия текста и типовые задачи читателя.", "Вердикт о понятности и конкретные замечания.", ["terminology-findings", "task-answers", "review-receipt"]),
    "design-site-experience": ("Information architecture, content and accessibility needs.", "A distinctive checked static interface.", "Структура знаний, материалы и требования доступности.", "Выразительный проверенный статический интерфейс.", ["html", "css", "javascript", "visual-assets"]),
    "project-atlas": ("The active catalog, binding and recorded runs.", "A deterministic read-only Atlas projection.", "Действующий каталог, конфигурация и записанные запуски.", "Детерминированная проекция Atlas только для чтения.", ["atlas-json", "static-ui"]),
    "plan-release": ("A verified change and release constraints.", "An exact candidate, version, route and authority plan.", "Проверенное изменение и ограничения выпуска.", "Точный план версии, маршрута и полномочий.", ["candidate-manifest", "release-card"]),
    "distribute-package": ("An authorized immutable release.", "A package, checksum and registry receipt.", "Разрешённый неизменяемый выпуск.", "Пакет, контрольная сумма и отчёт реестра.", ["package", "checksum", "registry-receipt"]),
    "publish-site": ("A checked site artifact and Pages authority.", "A Pages deployment and provenance receipt.", "Проверенный сайт и право публикации в Pages.", "Развёртывание Pages и отчёт о происхождении.", ["site-artifact", "deployment-receipt"]),
    "maintain-repository-presence": ("Approved brand assets and repository metadata.", "An About URL and social preview settings receipt.", "Принятые материалы бренда и данные репозитория.", "Отчёт о ссылке About и социальном превью.", ["mark", "social-preview", "settings-receipt"]),
    "verify-live-release": ("A deployment URL and pinned site digest.", "HTTP, DOM and screenshot evidence.", "Адрес развёртывания и точный хеш сайта.", "Данные HTTP, DOM и снимки экрана.", ["http-evidence", "dom-evidence", "screenshots"]),
    "observe-onboarding": ("A new user task and session.", "Friction points and task outcomes.", "Задача нового пользователя и наблюдаемая сессия.", "Проблемные места и результаты задач.", ["session-notes", "task-outcomes"]),
    "validate-use-cases": ("A real case outside the self-binding.", "Utility evidence and reusable binding needs.", "Реальный случай вне разработки самого Concord Loom.", "Данные о пользе и требования к повторному применению.", ["case-report", "binding-needs"]),
    "collect-friction": ("Issues, support reports and confusion.", "Classified observations with provenance.", "Ошибки, обращения и непонимание.", "Разобранные наблюдения с указанием источника.", ["issues", "support-signals"]),
    "synthesize-feedback": ("Repeated attributable observations.", "Normalized signals without automatic intent.", "Повторяющиеся наблюдения с известным источником.", "Нормализованные сигналы без автоматического решения.", ["signal-set"]),
    "collect-evolution-signals": ("Run, adoption and research evidence.", "Multiple signals pinned to the active binding.", "Данные запусков, применения и исследований.", "Несколько сигналов, привязанных к действующей версии.", ["normalized-signals", "provenance"]),
    "propose-successor": ("The active binding, pinned signals and CAS preconditions.", "A non-activating exact evolution proposal.", "Действующая версия, сигналы и условия сравнения.", "Точное предложение новой версии без права включения.", ["evolution-proposal"]),
    "review-successor": ("A proposal and reproduced successor artifacts.", "An independent acceptance or rejection decision.", "Предложение и воспроизведённые артефакты новой версии.", "Независимое решение о принятии или отклонении.", ["review", "acceptance-decision"]),
    "activate-successor": ("An accepted proposal and exact binding proposal.", "An activation receipt and catalog head update.", "Принятое предложение и точная новая конфигурация.", "Отчёт о включении и новая вершина каталога.", ["activation-receipt", "catalog-append"]),
    "observe-migration": ("The new active binding and subsequent runs.", "A migration report and regression signals.", "Новая действующая версия и последующие запуски.", "Отчёт о переходе и сигналы регрессии.", ["migration-report", "regression-signals"]),
}


def loop_specs() -> list[dict[str, object]]:
    basis = [{"kind": "decision", "ref": "accepted-project-graph"}]
    return [
        {
            "id": node_id,
            "purpose": purpose_en,
            "input_outcome": DETAILS[node_id][0],
            "output_outcome": DETAILS[node_id][1],
            "basis": basis,
            "decision_ids": ["accept-universal-loop-system"],
        }
        for (
            node_id, _parent, label_en, _label_ru, purpose_en, _purpose_ru,
            _role, _profile,
        ) in NODES
    ]


def containment() -> list[dict[str, str]]:
    return [
        {
            "id": f"{parent}.{node_id}",
            "parent_loop_id": parent,
            "child_loop_id": node_id,
            "decision_id": "accept-universal-loop-system",
        }
        for node_id, parent, *_rest in NODES
        if parent is not None
    ]


def development_model(binding_base_digest: str) -> dict[str, object]:
    children: dict[str, list[str]] = {node[0]: [] for node in NODES}
    for node_id, parent, *_rest in NODES:
        if parent is not None:
            children[parent].append(node_id)
    return {
        "kind": "concordloom.development-model",
        "schema_version": "0.1",
        "id": "concordloom-development-system-v5",
        "base_binding_digest": binding_base_digest,
        "root_loop_id": "steward-concordloom",
        "resource_semantics": {
            "profiles_are": "planned binding metadata, not timeless loop identity",
            "actual_resources_come_from": "a pinned run route or attempt",
            "mcp_default": "not-declared",
        },
        "nodes": [
            {
                "id": node_id,
                "parent_id": parent,
                "children": children[node_id],
                "copy": {
                    "en": {
                        "label": label_en,
                        "purpose": purpose_en,
                    },
                    "ru": {
                        "label": label_ru,
                        "purpose": purpose_ru,
                    },
                },
                "responsible_role": {
                    "en": role,
                    "ru": ROLE_RU[role],
                },
                "execution_profile": profile,
                "contract": {
                    "en": {
                        "input": DETAILS[node_id][0],
                        "output": DETAILS[node_id][1],
                    },
                    "ru": {
                        "input": DETAILS[node_id][2],
                        "output": DETAILS[node_id][3],
                    },
                },
                "artifacts": DETAILS[node_id][4],
            }
            for (
                node_id, parent, label_en, label_ru, purpose_en, purpose_ru,
                role, profile,
            ) in NODES
        ],
        "profiles": {
            profile_id: {
                **{key: value for key, value in profile.items() if key != "model_intent"},
                "model_intent": {
                    "en": profile["model_intent"],
                    "ru": MODEL_INTENT_RU[profile_id],
                },
                "mcp": {
                    "status": "not-declared",
                    "source": "active binding",
                },
                "truth_layer": "planned",
            }
            for profile_id, profile in PROFILES.items()
        },
        "shared_run_grammar": [
            {
                "id": phase_id,
                "copy": {
                    "en": {"label": label_en, "purpose": purpose_en},
                    "ru": {"label": label_ru, "purpose": purpose_ru},
                },
            }
            for phase_id, label_en, label_ru, purpose_en, purpose_ru in RUN_GRAMMAR
        ],
        "evolution_circuit": [
            "collect-evolution-signals",
            "propose-successor",
            "review-successor",
            "activate-successor",
            "observe-migration",
        ],
        "activation_boundary": {
            "evolve_phase_terminates_at": "propose-successor",
            "activation_loop_id": "activate-successor",
            "authority": "operator only",
            "self_activation_allowed": False,
        },
    }


def main() -> None:
    graph = load(GRAPH_DIR / "accepted-project-graph.json")
    decisions = load(GRAPH_DIR / "decision-log.json")
    old_policy = load(PREDECESSOR_DIR / "policy.json")
    predecessor = load(PREDECESSOR_DIR / "binding.json")
    base_digest = predecessor["binding_digest"]

    policy = deepcopy(old_policy)
    policy["id"] = "concordloom-self-policy-v5"
    policy["authority"]["separation_rules"][0]["applies_to_loop_ids"] = [
        "review-candidate",
        "assure-release",
        "review-comprehension",
        "review-successor",
    ]
    validate_policy(policy)

    design_proposal = propose_loop_design(
        graph,
        decisions,
        policy,
        proposal_id="concordloom-development-system-v5-proposal",
        loop_specs=loop_specs(),
        containment=containment(),
    )
    design = accept_loop_design(
        design_proposal,
        decisions,
        policy,
        accepted_graph=graph,
        decision_id="accept-concordloom-development-system-v5",
        actor=OPERATOR,
        accepted_at=STAMP,
        authority_ref="operator",
        rationale=(
            "Accept the complete repository development system requested by "
            "the operator, including comprehension review and explicit "
            "successor activation."
        ),
    )
    registry = compile_registry(
        graph,
        decisions,
        design,
        policy,
        loop_design_proposal=design_proposal,
        registry_id="concordloom-development-registry-v5",
    )
    special_capabilities = {
        "publish-site": "publish-release",
        "maintain-repository-presence": "publish-release",
        "distribute-package": "publish-release",
        "activate-successor": "activate-binding",
    }
    loops_by_id = {loop["id"]: loop for loop in registry["loops"]}
    contracts_by_id = {
        contract["id"]: contract for contract in registry["evidence_contracts"]
    }
    for loop_id, capability in special_capabilities.items():
        loops_by_id[loop_id]["authority"]["execute_capability"] = capability
        contracts_by_id[f"{loop_id}-acceptance"]["producer_capability"] = capability
    for edge in registry["containment_graph"]["edges"]:
        capability = special_capabilities.get(edge["child_loop_id"])
        if capability and capability not in edge["grant"]["capabilities"]:
            edge["grant"]["capabilities"].append(capability)
            edge["grant"]["capabilities"].sort()

    local_scope = deepcopy(policy["execution"]["default_scope"])
    local_scope["network"] = "none"
    local_scope["external_mutations"] = []
    read_only_scope = deepcopy(local_scope)
    read_only_scope["write_paths"] = []
    release_scope = {
        "read_paths": ["."],
        "write_paths": [],
        "network": "write",
        "external_mutations": EXTERNAL_MUTATIONS,
    }
    pages_scope = {
        **release_scope,
        "external_mutations": ["github-pages"],
    }
    presence_scope = {
        **release_scope,
        "external_mutations": [
            "github-repository-homepage",
            "github-repository-social-preview",
        ],
    }
    live_scope = {
        "read_paths": ["."],
        "write_paths": [],
        "network": "read",
        "external_mutations": [],
    }
    writable_profiles = {
        "strategy", "research", "protocol", "engineering", "integration",
        "editorial", "localization", "experience", "insight",
        "evolution-analysis", "evolution-proposal",
    }
    profile_by_node = {node[0]: node[7] for node in NODES}
    for edge in registry["containment_graph"]["edges"]:
        child_id = edge["child_loop_id"]
        if child_id == "release-distribution":
            edge["grant"]["scope"] = deepcopy(release_scope)
        elif child_id == "publish-site":
            edge["grant"]["scope"] = deepcopy(pages_scope)
        elif child_id == "maintain-repository-presence":
            edge["grant"]["scope"] = deepcopy(presence_scope)
        elif child_id == "verify-live-release":
            edge["grant"]["scope"] = deepcopy(live_scope)
        elif profile_by_node[child_id] in writable_profiles:
            edge["grant"]["scope"] = deepcopy(local_scope)
        else:
            edge["grant"]["scope"] = deepcopy(read_only_scope)
    validate_registry(registry, policy)

    model = development_model(base_digest)
    signals = [
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "operator-requested-complete-development-system",
            "base_binding_digest": base_digest,
            "category": "coverage",
            "severity": "warning",
            "occurrences": 1,
            "summary": (
                "The operator requested every cycle that develops Concord Loom, "
                "not only the website or one generic change."
            ),
            "source_digest": digest(
                {"source": "conversation:2026-07-27:complete-cycle-system"}
            ),
            "provenance": [{"kind": "evidence", "ref": "operator-request"}],
        },
        {
            "kind": "concordloom.evolution-signal",
            "schema_version": "0.1",
            "id": "atlas-hides-development-and-activation",
            "base_binding_digest": base_digest,
            "category": "friction",
            "severity": "warning",
            "occurrences": 2,
            "summary": (
                "The active Atlas exposes eight generic phases, but not the "
                "repository development responsibilities or activation boundary."
            ),
            "source_digest": digest(
                {"source": "audit:2026-07-27:atlas-development-coverage"}
            ),
            "provenance": [{"kind": "evidence", "ref": "atlas-coverage-audit"}],
        },
    ]
    evolution = propose_evolution(
        base_digest,
        signals,
        [
            {
                "op": "add",
                "target_kind": "loop",
                "target_id": "concordloom-development-system-v5",
                "value": {
                    "root_loop_id": "steward-concordloom",
                    "node_count": len(NODES),
                    "comprehension_cycle": "review-comprehension",
                    "activation_loop": "activate-successor",
                },
            }
        ],
        proposed_by={"id": "example-orchestrator", "kind": "orchestrator"},
        decision_authority_ref="operator",
        expected_effect=(
            "Replace the shallow self-development projection with a complete "
            "finite hierarchy and make the evolution authority boundary visible."
        ),
        risk={
            "level": "medium",
            "failure_modes": [
                "A responsibility could be placed under the wrong parent.",
                "Execution metadata could be mistaken for timeless semantics.",
            ],
            "rollback": (
                "Reactivate the v4 predecessor if the v5 hierarchy fails "
                "independent review."
            ),
        },
        generated_at=STAMP,
        policy=old_policy,
        proposal_id="complete-concordloom-development-system",
    )

    paths = {
        "accepted_project_graph": (
            "framework/concordloom/v3/accepted-project-graph.json"
        ),
        "decision_log": "framework/concordloom/v3/decision-log.json",
        "loop_design_proposal": (
            "framework/concordloom/v5/loop-design-proposal.json"
        ),
        "accepted_loop_design": "framework/concordloom/v5/loop-design.json",
        "cycle_registry": "framework/concordloom/v5/cycle-registry.json",
        "policy": "framework/concordloom/v5/policy.json",
    }
    extras = {
        "atlas_input": (
            "framework/concordloom/v5/development-model.json", model,
        ),
        "evolution_history": (
            "framework/concordloom/v5/evolution-proposal.json", evolution,
        ),
    }
    proposal = create_binding_proposal(
        graph,
        decisions,
        design,
        registry,
        policy,
        loop_design_proposal=design_proposal,
        artifact_paths=paths,
        proposal_id="concordloom-self-binding-v5-proposal",
        created_at=STAMP,
        predecessor_binding_digest=base_digest,
        extra_artifacts=extras,
    )
    binding = activate_binding(
        proposal,
        graph,
        decisions,
        design_proposal,
        design,
        registry,
        policy,
        activation_decision={
            "decision_id": "activate-concordloom-self-binding-v5",
            "actor": OPERATOR,
            "authority_ref": "operator",
            "accepted_at": "2026-07-27T13:01:00Z",
            "rationale": (
                "Activate the exact complete development system accepted by "
                "the operator. The evolution proposal did not activate itself."
            ),
        },
        binding_id="concordloom-self-binding-v5",
        extra_artifacts=extras,
    )

    publication_route = [
        {
            "node_id": "steward-concordloom",
            "loop_id": "steward-concordloom",
            "role": "executor",
            "skill_intent": "coordinate exact publication without external effects",
            "model_intent": "none",
            "reasoning_intent": "verify the publisher handoff",
            "subagent_intent": [],
            "scope": deepcopy(read_only_scope),
        },
        {
            "node_id": "publish-site",
            "loop_id": "publish-site",
            "role": "publisher",
            "skill_intent": "publish the pinned static site",
            "model_intent": "none",
            "reasoning_intent": "perform only the Pages effect",
            "subagent_intent": [],
            "scope": deepcopy(pages_scope),
        },
        {
            "node_id": "maintain-repository-presence",
            "loop_id": "maintain-repository-presence",
            "role": "publisher",
            "skill_intent": "publish the pinned repository brand metadata",
            "model_intent": "none",
            "reasoning_intent": "perform only the repository presence effects",
            "subagent_intent": [],
            "scope": deepcopy(presence_scope),
        },
    ]

    current_catalog = load(SOURCE / "catalog.json")
    predecessor_index = next(
        index
        for index, entry in enumerate(current_catalog["entries"])
        if entry["binding_digest"] == base_digest
    )
    base_catalog = deepcopy(current_catalog)
    base_catalog["entries"] = base_catalog["entries"][: predecessor_index + 1]
    base_catalog["active_binding_digest"] = base_digest
    catalog = append_binding(
        base_catalog,
        binding,
        path="framework/concordloom/v5/binding.json",
    )

    documents = {
        "loop-design-proposal.json": design_proposal,
        "loop-design.json": design,
        "cycle-registry.json": registry,
        "policy.json": policy,
        "development-model.json": model,
        "evolution-proposal.json": evolution,
        "binding-proposal.json": proposal,
        "binding.json": binding,
        "publication-route.json": publication_route,
    }
    for name, document in documents.items():
        save(TARGET / name, document)
    save(SOURCE / "catalog.json", catalog)
    print(
        "FULL_DEVELOPMENT_GRAPH_AUTHORIZED "
        f"nodes={len(NODES)} binding={binding['binding_digest']}"
    )


if __name__ == "__main__":
    main()
