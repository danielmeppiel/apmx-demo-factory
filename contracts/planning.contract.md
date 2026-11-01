---
needs: request.md
produces: plan.md
verify:
  plan-sections: python3 -I -B checks/documents.py planning plan.md
---
Plan the change described in request.md for this repository. The request
governs the feature, and the repository's acceptance/*.feature scenarios define
when it is done; your plan proposes the work, not a new business rule.
Before opening project files, list the src/, tests/, docs/ and acceptance/
directories (and their subdirectories) with the permitted read tool and open
only the paths it returns; never guess a filename. A failed read stops the run.
Read the common, Acceptance IDs and Planning formats in
checks/document-formats.md. Start plan.md with the required JSON metadata,
listing every acceptance scenario title and distinguishing existing file
targets from new ones.

Write a concise plan.md with these nonempty Markdown sections:

## Goal
Describe the requested behaviour and what must remain compatible.

## Changes
Explain the source, new test and documentation changes. Leave implementation
to the next contracts.

## Validation
Map each acceptance scenario to the behaviour it exercises, and name the
boundary values, unchanged paths and invalid inputs that matter.

## Risks
Describe relevant correctness risks for this change.

Use the permitted file tools supplied by APMX to write the artifact. Do not
modify inputs, run commands or checks, install, or delegate. Do not claim
completed implementation or observed test results. Keep ASCII Markdown under
16 KiB. Format and reference checks do not establish plan quality.
