# Быстрый старт Concord Loom

За 10 шагов вы проверите установку, исследуете свой репозиторий, утвердите
структуру циклов, запустите один управляемый проход и откроете Atlas. Все
основные команды работают с локальными файлами. Сайт только показывает
принятые данные и ничего не меняет.

## 1. Установите и проверьте

```bash
python3 -m pip install \
  "concordloom @ git+https://github.com/PullDakar/concordloom@v0.1.0"
concordloom --version
```

Для работы из клона:

```bash
python3 -m pip install -e .
./tools/check.sh
```

## 2. Изучите сайт и правила разработки Concord Loom

Общий сайт показывает универсальную грамматику изменений и генерируемую
проекцию собственной принятой системы Concord Loom:

```text
observe → negotiate → bind → execute → verify → publish → evolve
```

Активный корневой цикл называется `steward-concordloom`. Он раскрывается в
десять областей, которые вместе покрывают разработку продукта: от исследований
и протокола до документации, выпуска, обратной связи и эволюции.

Из локального клона проверьте и запустите те же статические файлы:

```bash
PYTHONPATH=src python3 tools/build_site.py --check
python3 -m http.server --directory site 8000
```

Откройте `http://localhost:8000/`. Страница не принимает решений о полномочиях.
Данные Atlas генерируются из активной принятой связки и не могут изменить её.
Перед следующими шагами остановите локальный сервер.

Проект использует Concord Loom для собственной разработки. Цикл
`propose-successor` может подготовить следующую версию правил, но включить её
может только отдельно назначенный оператор.

## 3. Исследуйте свой репозиторий

Запускайте команды из чистого Git-репозитория, который хотите понять.
Артефакты управления хранятся вне цели и не загрязняют инвентарь кандидата:

```bash
TARGET_REPOSITORY="$(git rev-parse --show-toplevel)"
WORK_DIR="$(mktemp -d /tmp/concordloom-quickstart-XXXXXX)"

concordloom inspect "$TARGET_REPOSITORY" \
  --output $WORK_DIR/observed-project-graph.json
concordloom questions \
  --graph $WORK_DIR/observed-project-graph.json \
  --output $WORK_DIR/questions.json
```

До интерпретации графа проверьте поля покрытия и усечения. Ребро `observed`
следует непосредственно из репозитория или истории Git. Ребро `inferred` —
гипотеза. Уверенность помогает ранжировать вопросы, но не даёт полномочий.

```bash
jq '.coverage, .hypotheses' \
  $WORK_DIR/observed-project-graph.json
jq '.questions[] | {id, prompt, why_it_matters, options}' \
  $WORK_DIR/questions.json
```

Используйте `--include-untracked`, только если нетрекаемые байты намеренно входят
в область наблюдения. Бюджеты файлов, истории, subprocess и co-change можно
настраивать; усечение остаётся видимым в результате.

## 4. Зафиксируйте решения оператора

Начните с политики, которая называет реальных принципалов, роли, полномочия,
правила доказательств, бюджеты и право эволюции. В помеченном тегом репозитории
есть исполнимый пример generic SDLC:

```bash
git clone --quiet --depth 1 --branch v0.1.0 \
  https://github.com/PullDakar/concordloom.git \
  "$WORK_DIR/concordloom-source"
cp "$WORK_DIR/concordloom-source/framework/generic-sdlc/policy.json" \
  "$WORK_DIR/policy.json"
```

Эта политика принадлежит одной связке поставки ПО, а не универсальному default.
Перед производственным применением сознательно отредактируйте копию. В локальном
примере принципал `example-operator` может ответить на первый вопрос:

```bash
QUESTION_ID="$(jq -r '.questions[0].id' \
  $WORK_DIR/questions.json)"

concordloom decide \
  --questions $WORK_DIR/questions.json \
  --question "$QUESTION_ID" \
  --verdict confirmed \
  --actor-id example-operator \
  --actor-kind operator \
  --authority-ref operator \
  --rationale "The operator confirms this proposed project intent." \
  --decided-at 2026-07-24T12:00:00Z \
  --output $WORK_DIR/decision-1.json
```

Повторите `decide` для каждого блокирующего вопроса. Исправление может передать
заменяющий JSON-массив через `--graph-delta`. Отказ остаётся в истории.

Примите набор решений. Для каждого файла решения добавьте отдельный аргумент
`--decision`; форма с одним вопросом выглядит так:

```bash
concordloom accept \
  --graph $WORK_DIR/observed-project-graph.json \
  --policy $WORK_DIR/policy.json \
  --decision $WORK_DIR/decision-1.json \
  --actor-id example-operator \
  --actor-kind operator \
  --authority-ref operator \
  --accepted-at 2026-07-24T12:05:00Z \
  --decision-log-output $WORK_DIR/decision-log.json \
  --output $WORK_DIR/accepted-project-graph.json
```

Приёмка завершается отказом, пока хотя бы один блокирующий вопрос не имеет
действительного решения.

## 5. Предложите и отдельно примите дизайн циклов

```bash
concordloom propose \
  --graph $WORK_DIR/accepted-project-graph.json \
  --decisions $WORK_DIR/decision-log.json \
  --policy $WORK_DIR/policy.json \
  --output $WORK_DIR/loop-design-proposal.json
```

Изучите предложение. Оно показывает вложенность, локальный поток, бюджеты,
доказательства, полномочия и терминальные исходы, но ещё не имеет права на
исполнение.

```bash
concordloom accept \
  --proposal $WORK_DIR/loop-design-proposal.json \
  --accepted-graph $WORK_DIR/accepted-project-graph.json \
  --decisions $WORK_DIR/decision-log.json \
  --policy $WORK_DIR/policy.json \
  --decision-id accept-loop-design-1 \
  --rationale "The operator accepts this exact loop-design proposal." \
  --actor-id example-operator \
  --actor-kind operator \
  --authority-ref operator \
  --accepted-at 2026-07-24T12:10:00Z \
  --output $WORK_DIR/loop-design.json
```

Это первая явная граница принятия. `propose` не может принять собственный
результат.

## 6. Соберите и отдельно включите конфигурацию

Компиляция создаёт реестр циклов и предложение конфигурации:

```bash
concordloom compile \
  --graph $WORK_DIR/accepted-project-graph.json \
  --decisions $WORK_DIR/decision-log.json \
  --design-proposal $WORK_DIR/loop-design-proposal.json \
  --design $WORK_DIR/loop-design.json \
  --policy $WORK_DIR/policy.json \
  --created-at 2026-07-24T12:15:00Z \
  --artifact-root "$WORK_DIR" \
  --registry-output $WORK_DIR/cycle-registry.json \
  --proposal-output $WORK_DIR/binding-proposal.json
```

Активация — второе решение над точным предложением:

```bash
concordloom activate \
  --proposal $WORK_DIR/binding-proposal.json \
  --graph $WORK_DIR/accepted-project-graph.json \
  --decisions $WORK_DIR/decision-log.json \
  --design-proposal $WORK_DIR/loop-design-proposal.json \
  --design $WORK_DIR/loop-design.json \
  --registry $WORK_DIR/cycle-registry.json \
  --policy $WORK_DIR/policy.json \
  --binding-id project-binding-v1 \
  --decision-id activate-binding-v1 \
  --actor-id example-operator \
  --actor-kind operator \
  --authority-ref operator \
  --accepted-at 2026-07-24T12:20:00Z \
  --rationale "Activate this exact compiled proposal." \
  --output $WORK_DIR/binding.json
```

Добавьте конфигурацию в каталог:

```bash
concordloom catalog \
  --binding $WORK_DIR/binding.json \
  --artifact-root "$WORK_DIR" \
  --output $WORK_DIR/catalog.json
```

Ни компиляция, ни создание каталога не могут молча заменить действующую
конфигурацию.

## 7. Закрепите кандидат и создайте запуск

В этом примере кандидатом служит дерево репозитория, потому что предметная
связка относится к поставке ПО. Другая связка может определить набор данных,
действие по восстановлению, творческий мастер или нормативный пакет. Явно
укажите нетрекаемый путь, если он входит в кандидат:

```bash
concordloom candidate "$TARGET_REPOSITORY" \
  --generated-at 2026-07-24T12:25:00Z \
  --output $WORK_DIR/candidate.json
```

Создайте запуск для корневого цикла собранного реестра:

```bash
ROOT_LOOP="$(jq -r '.containment_graph.roots[0]' \
  $WORK_DIR/cycle-registry.json)"

concordloom run new \
  --binding $WORK_DIR/binding.json \
  --registry $WORK_DIR/cycle-registry.json \
  --policy $WORK_DIR/policy.json \
  --candidate $WORK_DIR/candidate.json \
  --run-id first-governed-run \
  --root-loop "$ROOT_LOOP" \
  --candidate-author example-executor \
  --output $WORK_DIR/run-card.json
```

Продвигайте его командами `concordloom run authorize`, `attempt`, `guard`,
`evidence` и `complete`. Каждая команда требует текущую карточку и точные
конфигурации, реестра, правил, версии результата, репозитория, участника и
данных проверки, необходимых
этому переходу:

```bash
concordloom run authorize --help
concordloom run attempt --help
concordloom run evidence --help
concordloom run complete --help
```

Явные файлы нужны намеренно. Запланированный маршрут становится фактом только
после записи реального принципала, агента, модели, навыка, субагентов,
инструментов, сети, вывода данных, изменений, времени и стоимости.
Доказательство связывается с попыткой и фактическими байтами payload.

## 8. Создайте автономный Atlas

```bash
concordloom atlas \
  --binding $WORK_DIR/binding.json \
  --registry $WORK_DIR/cycle-registry.json \
  --policy $WORK_DIR/policy.json \
  --run-card $WORK_DIR/run-card.json \
  --output $WORK_DIR/atlas.html
```

Откройте `atlas.html` прямо в браузере: сетевых зависимостей нет. Atlas
показывает принятую структуру этой конфигурации и записанные факты запуска. Он не
превращает generic SDLC в требование фреймворка. В автоматизации используйте
`--check`, чтобы отклонять устаревший результат.

## 9. Предложите эволюцию

Повторяющиеся адресуемые по содержимому сигналы могут поддержать предложение
преемника:

```bash
concordloom evolve --help
```

Команде нужны действующая конфигурация, правила, сигналы, явные операции, риск, автор
предложения, действующее право решения и время генерации. Результат всегда имеет
`activation_allowed: false`. Преемника принимает и активирует власть,
закреплённая текущей версией. Это правило одинаково для исследовательского
протокола, процесса инцидента, творческого производства, управления, поставки
ПО и правила разработки самого Concord Loom.

## 10. Проверьте готовый пример поставки ПО

Помеченный тегом снимок содержит все артефакты примера поставки ПО в согласованной
цепочке точных дайджестов:

```bash
cd "$WORK_DIR/concordloom-source"
concordloom validate \
  --input framework/generic-sdlc/catalog.json \
  --artifact-root .

python3 tools/generate_generic_example.py --check
```

Изучайте этот каталог при создании политики и входов запуска для поставки ПО.
Замените демонстрационные идентичности и предположения. В другой предметной
области сохраните правила артефактов и полномочий, но спроектируйте собственные
контракты, кандидаты, доказательства и исходы. Не принимайте топологию примера
за default и не выводите принятое намерение из наблюдений.
