# Карта команд Concord Loom v0.1

Используйте этот справочник только после проверки встроенного launcher и
справки нужной subcommand. Флаги команд — версионированные контракты; не
придумывайте параметры.

## Поддерживаемый путь зависимости CLI

Из каталога этого skill запускайте команды так:

```bash
python3 scripts/concordloom_cli.py <command> ...
```

Launcher сначала использует source distribution v0.1 из того же репозитория.
Если плагин установлен без дерева исходников, он использует установленную
команду `concordloom`. Определить маршрут без исполнения команды проекта:

```bash
python3 scripts/concordloom_cli.py --resolve
```

Если зависимости нет, launcher и preflight выводят `install_argv` для
соответствующего source release v0.1. Выполните этот точный вектор аргументов,
затем снова запустите `--resolve`; не устанавливайте незакреплённый пакет и не
копируйте исходники в целевой репозиторий.

## Новый репозиторий

Отсутствующая binding не является ошибкой CLI. Preflight сообщает
`mode=bootstrap-discovery`. Храните outputs во временном каталоге и используйте
только `inspect` и `questions`, пока не представлен bootstrap packet.
Repository mutation, authority claims, network access, external mutations,
run-card authorization и binding activation запрещены, пока оператор не примет
точные записи первой binding.

| Этап | Семейство команд | Требуемый результат |
|---|---|---|
| Observe | `concordloom inspect` | Привязанный к revision observed/inferred graph |
| Interview | `concordloom questions` | Ранжированные вопросы с answer delta |
| Decide | `concordloom decide` | Append-only решение actor с rationale |
| Accept | `concordloom accept` | Принятый graph или blocking failure |
| Propose | `concordloom propose` | Проверяемая delta дизайна циклов |
| Compile | `concordloom compile` | Registry и неавторитетный binding proposal |
| Activate | `concordloom activate` | Binding, принятая из точного proposal digest |
| Validate | `concordloom validate` | Проверки schema и cross-artifact |
| Identify | `concordloom candidate` | Канонические candidate manifest и digest |
| Catalog | `concordloom catalog` | Новое значение append-only active-binding chain |
| Execute | `concordloom run` | Жизненный цикл управляемой run card |
| Visualize | `concordloom atlas` | Детерминированная офлайн HTML projection |
| Evolve | `concordloom evolve` | Предложенная successor delta без activation |

Семейство `run` содержит `new`, `authorize`, `attempt`, `evidence`, `guard` и
`complete`. Перед использованием всегда смотрите вложенную справку. Запускайте
`guard` до task-scoped чтения или изменения и перечисляйте каждый
предполагаемый path. Attempt records включают фактические model/provider, data
egress, network/external mutation, elapsed time и cost. Для evidence и
completion нужен `--payload-root`, чтобы заявленный payload digest можно было
сверить с реальными байтами.

Если `--help` отличается от этой карты, остановитесь и сообщите о несовпадении
версии. Не переходите к ручному редактированию канонических артефактов.

Команды и флаги в этом русском справочнике намеренно не переводятся. Русский
текст не создаёт отдельного контракта CLI и не меняет границы полномочий.
