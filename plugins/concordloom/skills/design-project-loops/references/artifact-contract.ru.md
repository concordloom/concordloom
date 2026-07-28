# Контракт артефактов и полномочий Concord Loom

Используйте этот справочник при принятии намерения, компиляции binding,
управлении run или предложении эволюции.

## Цепочка артефактов

Сохраняйте направленную контентно-адресуемую цепочку:

```text
snapshot репозитория
  -> наблюдаемый граф проекта
  -> ранжированные вопросы
  -> append-only решения
  -> принятый граф проекта
  -> предложенная delta дизайна циклов
  -> принятие дизайна циклов
  -> скомпилированные registry и binding proposal
  -> отдельное решение активации
  -> активные binding и append-only запись catalog
  -> run card и Atlas
  -> сигналы эволюции
  -> successor proposal
```

Не перезаписывайте ранний артефакт, чтобы поздний вывод выглядел наблюдаемым.
Изменяемые display metadata храните вне канонических digest payload.

Язык общения и представления относится к display metadata. Храните его вне
канонических graph, policy, binding, candidate и evidence payload, если
принятая schema явно не включает locale в артефакт. Переведённая projection
обязана сохранять machine identifiers, точные значения и digest.

## Эпистемические состояния

| Состояние | Основание | Даёт полномочия |
|---|---|---|
| `observed` | Байты репозитория или записи Git | Нет |
| `inferred` | Детерминированная эвристика | Нет |
| `confirmed` | Явное решение полномочного оператора | Только после binding |
| `rejected` | Явное решение оператора | Нет |
| `runtime_verified` | Контракт evidence, привязанный к кандидату | Только в своей области |

Confidence ранжирует вопросы. Он не может повысить `inferred` до `confirmed`.

## Представление graph delta

Перед запросом решения показывайте каждый ответ как операции:

```json
{
  "answer_id": "confirm-test-ownership",
  "operations": [
    {
      "op": "confirm_edge",
      "edge_id": "owns:quality:tests"
    },
    {
      "op": "add_loop_candidate",
      "loop_id": "verification"
    }
  ]
}
```

Укажите добавленные, удалённые, исправленные и нерешённые nodes/edges. Назовите
source references и затронутые downstream loops или authority grants. Вместе
с решением запишите actor и rationale.

## Два типа графов

Containment описывает конечную иерархию контрактов циклов и обязан быть DAG:
ребёнок не может содержать предка.

Local control flow описывает состояния и переходы внутри одного цикла.
Feedback edges допустимы, только если каждая циклическая strongly connected
component расходует конечный монотонный budget, а исчерпание приводит к
terminal или escalation.

Не используйте «рекурсивный» в значении неограниченной runtime recursion.
Термин означает, что один шаблон loop contract и навигации Atlas применяется
на нескольких уровнях.

## Planned, actual и verified

- Planned route: намерение, записанное до исполнения.
- Actual route: фактические principal, model/reasoning, skill, subagents,
  tools и policy.
- Verified result: структурированное evidence, совпадающее с digest кандидата
  и policy и предикатом gate.
- Drift: видимая разница между planned и actual facts.

Не объединяйте эти состояния. Child receipt — input решения родителя, но не
автоматическое принятие родителя.

## Границы полномочий

Разрешайте capabilities через bound policy, а не через свободный текст.
Разделяйте как минимум:

- принятие намерения проекта;
- принятие предложенного дизайна циклов;
- авторизацию исполнения;
- авторство содержимого кандидата;
- независимый review закреплённого кандидата;
- объявление готовности релиза;
- внешнюю публикацию;
- принятие и активацию successor binding.

Runner может иметь узкую control-plane capability для добавления run events,
пока кандидат остаётся read-only. Это не даёт candidate write или publication
authority.

## Эволюция

Evolution reducer может собрать повторяющиеся контентно-адресуемые сигналы в
proposal. Proposal должен содержать:

- точный base binding digest;
- digest участвующих сигналов;
- graph operations;
- precondition digest каждой операции;
- требование решения под base binding.

Не позволяйте proposer принимать или активировать собственное изменение.
Отклоняйте stale preconditions и сохраняйте исторические bindings. Public
projection, Pages workflow или social artwork не могут подменять отдельные
решения acceptance и activation.
