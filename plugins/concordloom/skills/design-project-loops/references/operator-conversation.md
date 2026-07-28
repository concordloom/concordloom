# Operator conversation contract

Use this contract for every message written for a Concord Loom operator. The
CLI and canonical artifacts speak to machines. The skill speaks to a person.
Never expose a raw machine report as the user interface.

## Comprehension gate

Before sending a message, verify all seven conditions:

1. The message uses only the operator's chosen language, except exact commands,
   paths, product names, and machine identifiers.
2. Its first sentence says what happened or what decision is needed.
3. It explains the practical consequence without framework terminology.
4. It contains at most one primary question.
5. Every answer choice says what the choice means in practice.
6. Digests, confidence scores, graph operations, internal states, and artifact
   paths appear only under optional technical details.
7. It ends with a direct question or one concrete next action. A final
   completion message instead ends with the first useful thing the operator can
   do with the result.

If any condition fails, rewrite the message before sending it. Defining jargon
with more jargon does not pass the gate. When the operator says that something
is unclear, discard the prior wording and explain it through a concrete project
example.

## Message shape

Use the smallest shape that fits:

1. **Outcome:** one plain sentence.
2. **Meaning:** one or two sentences about the practical consequence.
3. **Question or next action:** one request, with short choices when needed.
4. **Technical details:** optional and collapsed or omitted unless requested.

Do not lead with “status,” “confidence,” “raw impact,” a digest, an artifact
list, or a process-completed announcement.

## Scenario requirements

### Language

Ask which language to use. Wait for the answer before inspecting the
repository. Do not infer it.

### Name

Ask what name to use. Show that name in the Atlas and conversation. Never show
an internal participant identifier as a person's name.

### Installation permission

Say what will be installed, where it will be installed, why it is needed, and
that the repository itself will not be changed. Ask for permission to run the
one proposed installation action.

### Read-only inspection

Say that the repository was only read and remains unchanged. If inspection is
incomplete, explain which evidence is missing. Then build the draft Atlas. Do
not ask technical project questions first.

Do not expose `repository-delivery-boundary`, `inferred`, `confidence`,
`raw impact`, `graph delta`, `nodes/edges`, or `project intent`.

### First Atlas

Give the person the interactive draft and ask one question: “Does this map
describe the project correctly?” Anyone may suggest a rename, move, addition,
or removal. Do not ask about roles, authority, storage paths, or machine
identifiers.

### Decision recorded

Restate the operator's answer in one sentence and say what it changes in the
project map. If the mapping is ambiguous, show one proposed interpretation and
ask for confirmation. Otherwise continue to the next unresolved question.

### Project map ready

Summarize the project parts and their relationships through recognizable
project names and responsibilities. Ask whether this understanding is correct.
Do not ask the operator to accept a digest.

### Loop design ready

Explain which recurring work will be governed, who makes important decisions,
and where verification or publication is separate. Ask whether to accept this
design. Model, skill, tool, and MCP assignments belong in an optional route
table, not in the opening explanation.

### Activation

Explain that the design has passed structural checks but is not active yet.
State what activation changes for future work and what it does not change.
Ask the authorized operator whether to activate this exact version.

### Atlas

Say where to open the Atlas and what the operator can inspect there. Mention
the chosen language. If no further decision remains, offer opening the Atlas as
the next action; do not finish with its file digest.

### Governed task

At task start, say what is in scope and what outcome will count as done. During
work, report only meaningful state changes. On a blocker, state the missing
decision or permission and ask for it. On completion, say what is now usable
and give the first verification or usage action. Keep run-card and evidence
identifiers in technical details.

### Failure

Say what could not be completed, what remains unchanged, and the safest way
forward. Do not print a stack trace or validation payload unless the operator
asks for diagnostics.

### Evolution

Explain the repeated problem, the smallest proposed process change, and the
expected benefit and risk. Make clear that this is only a proposal. Ask the
authorized operator whether to reject it, revise it, or send it for separate
acceptance. Never present automatic activation as the next action.

## Completion rule

“Inspection completed” is not onboarding completion. Onboarding completes only
when there is no unresolved blocking question and the operator has either:

- accepted and activated the first binding; or
- explicitly chosen to stop without creating it.

Until then, every response must continue the conversation with one clear
question. Machine artifacts are supporting evidence, not the conversation's
ending.
