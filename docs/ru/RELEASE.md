# Проверка релиза и публичного сайта

Релизы Concord Loom v0.1 связывают исходники, пакет, независимые проверки и
долговечную bootstrap-квитанцию.

Инструкции для `v0.1.0` ниже относятся к исторической проверке неизменяемого
тега. Текущая разработка также содержит принятую предметно-нейтральную
self-binding Concord Loom и двуязычный кандидат Pages. Нельзя использовать
файлы текущего рабочего дерева, чтобы пересматривать утверждения о теге.

## Проверка исходников

```bash
git clone https://github.com/PullDakar/concordloom.git
cd concordloom
git fetch --tags
git checkout --detach v0.1.0
git status --short
./tools/check.sh
```

Checkout должен быть чистым, а проверка должна закончиться `CHECK_OK`.

## Проверка артефактов релиза

Скачайте wheel, архив исходников, `SHA256SUMS` и bootstrap receipt bundle из
GitHub-релиза `v0.1.0`, затем выполните:

```bash
sha256sum --check SHA256SUMS
python3 -m venv /tmp/concordloom-release-check
/tmp/concordloom-release-check/bin/python -m pip install \
  --no-deps concordloom-0.1.0-py3-none-any.whl
/tmp/concordloom-release-check/bin/concordloom --version
/tmp/concordloom-release-check/bin/python -m pip check
```

У wheel не должно быть runtime-зависимостей Python. Его состав включает
переносимый пакет, семнадцать публичных схем и цепочку артефактов generic SDLC.

## Проверка bootstrap-квитанции

В receipt bundle входят:

- завершённая bootstrap run card;
- точный bootstrap cycle и compute policy;
- закреплённые commit и tree digest кандидата;
- фактические попытки узлов;
- независимые доказательства R, L, Q и M;
- собственный канонический SHA-256 digest.

Runner экспортирует bundle только из завершённого run и повторно проверяет
кандидата, все узлы, привязки review и разделение автора с ревьюером.
`SHA256SUMS` релиза закрепляет экспортированные байты рядом с кандидатом тега.

Собственный digest не является аутентификацией. Проверяйте происхождение
релиза/тега подходящим для среды способом и добавляйте подписанные attestations,
если нужна криптографическая идентичность.

## Уровни доказательств

Не объединяйте следующие утверждения:

- Unit- и integration-тесты доказывают детерминированные пути кода.
- Smoke установленного wheel доказывает упаковку и доступность команды.
- Browser inspection доказывает только просмотренные состояния и viewport Atlas.
- Независимый quality review оценивает точного закреплённого кандидата.
- Smoke публичного clone доказывает доступность опубликованного тега и assets.

Ни одно из них само по себе не доказывает ценность продукта, полноту тестовых
оракулов или криптографическую идентичность ревьюера.

## Проверка принятой self-binding

Текущий переход репозитория фиксирует преемника примера generic SDLC.
Проверяйте точные binding, registry, policy, predecessor link и append-only
catalog, а не полагайтесь на слово «current». Принятый корень —
`concord-change`; его дети — observe, negotiate, bind, execute, verify,
publish и evolve.

Binding активирован решением, отдельным от предложения эволюции. В предложении
остаётся `activation_allowed: false`, а predecessor binding доступен в
каталоге. Это и есть доказательство управляемой self-binding; сгенерированный
Atlas или текст сайта им не являются.

## Проверка двуязычного кандидата Pages

В checkout с текущим кандидатом выполните:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/build_site.py --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/check_site.py
```

Проверки привязывают `site/data/atlas.json` к активной принятой binding,
требуют достаточный объём английского и русского текста, проверяют локальные
assets и accessibility hooks, а также точный размер social preview
1280 × 640 пикселей. Hero и social preview в `docs/assets/` — исходные
коммуникационные assets; копии в `site/assets/` должны совпадать с
детерминированной сборкой.

Workflow Pages — механизм публикации с ограниченной областью. Проверьте trigger,
путь артефакта, разрешения `contents: read`, `pages: write`,
`id-token: write` и отдельную среду `github-pages`. Успешная локальная проверка
или workflow build не доказывает ни разрешение публикации, ни наличие живого
URL.

Для live-проверки нужны deployment record и URL точного кандидата, после чего
свежий запрос должен проверить переключение языка, локальные assets, social
metadata и digest принятого Atlas. Пока таких доказательств нет, называйте
сайт кандидатом Pages, а не развёрнутым сайтом.

## Последовательность релиза для сопровождающего

Для неизменяемого релиза v0.1:

1. Завершить код и документацию.
2. Сгенерировать и проверить офлайн-Atlas.
3. Закоммитить чистого кандидата и один раз закрепить его.
4. Выполнить независимые reference-, visual-, quality- и release-review.
5. Опубликовать точный commit и аннотированный тег `v0.1.0`.
6. Выполнить smoke свежего публичного clone и установленного wheel.
7. Записать proposal-only сигналы эволюции.
8. Завершить bootstrap run и экспортировать receipt bundle.
9. Приложить bundle и итоговые checksums к GitHub-релизу.

Для преемника и публикации Pages:

1. Закрепить кандидата под активной predecessor binding.
2. Проверить двуязычные docs, site output, social assets и происхождение Atlas.
3. Получить независимую проверку точного кандидата.
4. Для активации преемника записать отдельное решение полномочного оператора.
5. Добавить активированную binding без замены истории predecessor.
6. Разрешить scoped publisher развернуть только проверенный артефакт `site/`.
7. Сохранить deployment receipt и выполнить smoke живого URL.
8. Записать последующее трение как сигналы; не активировать их proposal
   автоматически.

Если байты исходников изменились после закрепления кандидата, начните новый run.
