---
needs:
  - request.md
  - specification.md
produces:
  - changes.diff
  - implementation.md
imports:
  - python-testing-patterns
budget:
  max_attempts: 3
  max_seconds: 600
verify:
  acceptance-scenarios: python3 -I -B checks/acceptance.py changes.diff
  regression-suite: python3 -I -B checks/regression.py changes.diff
  change-scope: python3 -I -B checks/scope.py changes.diff
  money-in-cents: python3 -I -B checks/money.py changes.diff
  implementation-report-format: python3 -I -B checks/documents.py implementation implementation.md
---
Implement the intent in request.md so the repository's acceptance scenarios
pass. Read the request, specification, the relevant source, the existing tests
and the repository's acceptance/ features and step definitions. The request
and the acceptance scenarios remain authoritative if generated specification
text conflicts with them. The project files are already captured; needs is not
a source-file inventory. Before opening project files, list the src/, tests/
and acceptance/ directories (and their subdirectories) with the permitted read
tool and open only the paths it returns; never guess a filename. A failed read
stops the run.
Read the common and Implementation report formats in checks/document-formats.md.

Edit the actual private working copies of the files under src/ that the change
needs. Use the supplied write_file artifact tool with the file's path and
complete content, and workspace-relative paths for every tool call. Preserve
existing interfaces and behaviour that the request does not change.

Add at least one new test module under tests/ (tests/test_<topic>.py) using
Python's standard unittest framework; src/ is the import root. Use the selected
python-testing-patterns capability for test design, adapted to this existing
framework. Its examples do not authorize new dependencies or tools.
Cover the boundaries and unchanged paths of the requested behaviour.

House rules, enforced by the checks:
- Change only src/ and new files under tests/. Never edit acceptance/,
  .github/, request.md, policy files, docs/ (the documentation contract owns
  it) or any existing test. Do not delete or rename files.
- Money is integer cents: no float literals and no float() calls under src/.
- Standard library only.

Use write_file to write implementation.md with the required JSON metadata
and these nonempty Markdown sections:

## Changes
Explain the source changes and the added tests.

## Validation
Describe what the new tests cover and what the separate acceptance,
regression, scope and money checks will assess. Do not claim you ran them.

## Limitations
Record relevant limitations or follow-up work without claiming certification.

After all file edits, invoke the supplied export_changes tool exactly once with
{"output":"changes.diff"}. This bounded operation exports your actual edits
against the captured baseline. Do not hand-author patch hunks, invoke Git
through a shell, or substitute a narrative for the patch. Modified source files
are working copies, not additional published artifacts. If any tool reports an
error, stop; do not invent missing outputs or continue issuing write/export calls.

Use permitted file tools and the bounded export operation only. Do not run
commands/checks, install packages or delegate. Keep source, tests and
artifacts ASCII. Keep changes.diff under 128 KiB and implementation.md under
16 KiB. APMX verifies the captured patch and report independently; producing
the files alone does not establish correctness.
