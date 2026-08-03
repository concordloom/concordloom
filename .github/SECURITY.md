# Security policy

## Supported versions

Security fixes target the latest published release and the current `main` branch. Older releases may not receive patches.

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/concordloom/concordloom/security/advisories/new) when it is available. If that channel is unavailable, contact the maintainers privately through the repository owner's verified GitHub profile instead of opening a public issue.

Include:

- the affected version or commit;
- the vulnerable component and prerequisites;
- reproducible steps or a minimal proof of concept;
- the likely impact;
- any suggested mitigation;
- whether the report or details have been shared elsewhere.

Do not access data that is not yours, degrade shared services, or publish exploit details before maintainers have had a reasonable opportunity to respond.

Maintainers will acknowledge a usable report when possible, investigate it, and coordinate remediation and disclosure. Response times are not guaranteed. Acknowledgement, severity, remediation, and publication are separate decisions; a local fix is not evidence that users are protected until the relevant release or deployment is verified.

Concord Loom validates declarative governance artifacts. It is not an operating-system sandbox, credential manager, cryptographic identity service, or general-purpose security boundary. See the [trust model](../docs/TRUST_MODEL.md) before using it for consequential effects.
