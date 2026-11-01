---
needs:
  - request.md
  - plan.md
produces: specification.md
verify:
  specification-format-references: python3 -I -B checks/documents.py specification specification.md
---
Turn the admitted plan into a precise, concise specification of the change in
request.md. Read request.md, plan.md, the relevant source under src/, and the
repository's acceptance/ features and step definitions: the steps show exactly
which interfaces, names and values the scenarios call. The request and the
acceptance scenarios win if the plan conflicts with them.
The captured project already supplies source, tests and acceptance; needs
names only explicit inputs and stage handoffs. Before opening project files,
list the src/, tests/ and acceptance/ directories (and their subdirectories)
with the permitted read tool and open only the paths it returns; never guess a
filename. A failed read stops the run. Read the common, Acceptance IDs
and Specification formats in checks/document-formats.md. Start with the
required JSON metadata, resolving each interface against the captured source.

Write specification.md with these nonempty Markdown sections:

## Behavior
Define the new behaviour precisely, including boundaries, and state which
existing behaviour stays unchanged.

## Interface
Record the public functions, classes, values and errors involved, with their
argument and return shapes. Amounts of money are integer cents.

## Acceptance
Explain how each acceptance scenario is satisfied and what new unittest
coverage will add. Do not replace or weaken the repository's scenarios.

Write the artifact with the permitted file tools. Do not modify inputs,
implement code, run commands/checks, install or delegate. Do not claim
observed executions. Keep ASCII Markdown under 16 KiB. Format and reference
checks do not prove prose semantics; candidate checks decide behavior.
