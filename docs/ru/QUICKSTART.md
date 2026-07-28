# Быстрый старт Concord Loom

Сначала вы получите полезный результат, затем разберётесь с полной цепочкой
управления. Начните с безопасного исследования одного репозитория. Переходите к
управляемому запуску, когда потребуется исполнение, независимая проверка или
публикация.

## Что получится

Примерно за 5 минут вы:

1. установите командную программу;
2. исследуете репозиторий без изменений;
3. отделите найденные факты от гипотез;
4. откроете интерактивный Атлас.

Следующие разделы объясняют, как превратить наблюдение в принятую и исполнимую
систему циклов.

## Рекомендуемый путь: первичная настройка через навык Codex

Если вы используете Codex, установите плагин по
[инструкции](CODEX_PLUGIN.md), откройте целевой репозиторий и попросите:

```text
Use $design-project-loops to onboard this repository safely, inspect it
read-only, and show me the highest-impact unresolved loop decision.
```

Навык выполнит предварительную проверку. Если CLI отсутствует, он покажет один
безопасный план установки и попросит разрешение перед изменением окружения
пользователя. Следующие команды нужны только для ручной или автоматической
настройки без Codex.

## 1. Установите CLI

```bash
pipx install \
  "concordloom @ git+https://github.com/concordloom/concordloom@v0.1.5"
concordloom --version
```

Если `pipx` недоступен, но вы уже используете `uv`:

```bash
uv tool install \
  "concordloom @ git+https://github.com/concordloom/concordloom@v0.1.5"
```

Не используйте `--break-system-packages` и не устанавливайте пакет в системный
Python с внешним управлением.

Для работы из клона:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
./tools/check.sh
```

Ожидаемый результат: команда версии печатает `concordloom 0.1.5`, а проверка
заканчивается строкой `CHECK_OK`.

## 2. Исследуйте репозиторий

Выполните команды в чистом Git-репозитории:

```bash
TARGET_REPOSITORY="$(git rev-parse --show-toplevel)"
WORK_DIR="$(mktemp -d /tmp/concordloom-quickstart-XXXXXX)"

concordloom inspect "$TARGET_REPOSITORY" \
  --output "$WORK_DIR/observed-project-graph.json"
concordloom questions \
  --graph "$WORK_DIR/observed-project-graph.json" \
  --output "$WORK_DIR/questions.json"
```

Ожидаемый результат: `observed-project-graph.json` содержит найденные файлы и
связи, а `questions.json` — решения, которые нельзя безопасно угадать.

Посмотрите сводку:

```bash
jq '.coverage, .hypotheses' "$WORK_DIR/observed-project-graph.json"
jq '.questions[] | {prompt, why_it_matters, options}' "$WORK_DIR/questions.json"
```

Связь `observed` подтверждена данными репозитория. Связь `inferred` остаётся
гипотезой. Ни одна из них не становится принятым намерением без решения
оператора.

## 3. Откройте Атлас

[Публичный Атлас](https://concordloom.github.io/concordloom/?lang=ru#atlas/steward-concordloom)
показывает полную систему разработки этого репозитория. Это представление
только для просмотра: оно объясняет принятые правила и записанные запуски, но
не выдаёт полномочия и ничего не меняет.

Из локального клона:

```bash
PYTHONPATH=src python3 tools/build_site.py --check
python3 -m http.server --directory site 8000
```

Откройте `http://localhost:8000/?lang=ru#atlas/steward-concordloom`.

Страница отдельно показывает выпуск продукта и внутреннюю редакцию правил
разработки:

```text
Concord Loom 0.1.5
Правила разработки: редакция 9
```

## 4. Решите, что означает наблюдение

Результат исследования — это данные, а не разрешение. Управляемая настройка
называет:

- оператора, который принимает намерение;
- исполнителя, который создаёт проверяемую версию результата;
- проверяющего, который оценивает её точные байты;
- издателя, который может выполнить внешнее изменение;
- бюджеты и конечные исходы каждой обратной связи.

Ответьте на блокирующие вопросы командой `concordloom decide`, затем создайте
принятый граф проекта командой `concordloom accept`. Точные входные файлы
покажут `concordloom decide --help` и `concordloom accept --help`. Если
обязательного решения нет, команды завершаются отказом.

Решение оператора явно указывает источник полномочий:

```bash
concordloom decide \
  --questions "$WORK_DIR/questions.json" \
  --question question-id \
  --verdict confirmed \
  --actor-id project-operator \
  --actor-kind operator \
  --authority-ref operator \
  --rationale "Confirmed by the responsible operator." \
  --decided-at 2026-07-24T12:00:00Z \
  --output "$WORK_DIR/decision.json"
```

## 5. Соберите исполнимую систему циклов

Дальнейшая цепочка намеренно разделяет предложение и принятие:

```text
принятый граф проекта
  → предложение дизайна циклов
  → принятый оператором дизайн
  → реестр и предложение конфигурации
  → отдельно включённая конфигурация
```

Команды каждого этапа:

```bash
concordloom propose --help
concordloom accept --help
concordloom compile --help
concordloom activate --help
concordloom catalog --help
```

В `framework/generic-sdlc/` находится полный пример для поставки программного
обеспечения. Это пример, а не обязательный процесс Concord Loom.

## 6. Выполните одно управляемое изменение

Создайте описание точных байтов проверяемой версии, затем карточку запуска:

```bash
concordloom candidate "$TARGET_REPOSITORY" \
  --generated-at 2026-07-24T12:25:00Z \
  --output "$WORK_DIR/candidate.json"

concordloom run new \
  --binding "$WORK_DIR/binding.json" \
  --registry "$WORK_DIR/cycle-registry.json" \
  --policy "$WORK_DIR/policy.json" \
  --candidate "$WORK_DIR/candidate.json" \
  --run-id first-governed-run \
  --root-loop project-root \
  --target-loop chosen-leaf-loop \
  --candidate-author project-executor \
  --output "$WORK_DIR/run-card.json"
```

Настоящие идентификаторы корневого цикла и участников задаёт принятая
конфигурация. `--target-loop` включает только выбранную задачу и её родительские
циклы; несвязанные ветви выпуска и эволюции в запуск не попадут. Без этого
параметра создаётся запуск только для координации корневого цикла.
`--portfolio` нужен лишь для намеренной проверки всей доступной системы.
Продвигайте карточку командами:

```bash
concordloom run authorize --help
concordloom run attempt --help
concordloom run evidence --help
concordloom run complete --help
```

План становится фактом только после записи попытки. Запись показывает, кто
выполнял работу, какую модель и инструкции использовал, какими инструментами
пользовался, обращался ли к сети, какие внешние изменения сделал, сколько
времени потратил и чем закончил. Запуск завершён только после успешной команды
`run complete`.

## 7. Разберитесь с эволюцией

Повторяющиеся сигналы с точными хешами могут обосновать предложение новой
конфигурации:

```bash
concordloom evolve --help
```

Предложение всегда содержит `activation_allowed: false`. Действующая
конфигурация определяет, кто проверяет и включает следующую версию. Система
может подготовить себе замену, но не может сама разрешить её включение.

## Что читать дальше

- [Основные понятия](CONCEPTS.md) объясняют два графа и состояния сведений.
- [Модель доверия](TRUST_MODEL.md) объясняет полномочия и независимую проверку.
- [Руководство по Атласу](ATLAS.md) объясняет интерактивное и автономное
  представления.
- [Архитектура](ARCHITECTURE.md) описывает ядро и адаптеры.
