---
needs:
  - request.md
  - specification.md
  - changes.diff
  - implementation.md
produces:
  - documentation.diff
  - documentation.md
budget:
  max_attempts: 2
  max_seconds: 300
verify:
  documentation-links: python3 -I -B checks/documentation.py changes.diff documentation.diff
  combined-candidate: python3 -I -B checks/combined.py changes.diff documentation.diff
  documentation-report-format: python3 -I -B checks/documents.py documentation documentation.md
---
Update the repository's documentation under docs/ for the admitted change.
Read request.md, specification.md, changes.diff, implementation.md and the
captured pages under docs/ (list the directory first). The request and the
repository's acceptance scenarios remain authoritative. Both declared outputs
are new files: documentation.md and documentation.diff are not inputs to read.
The new documentation.md is a report, not a substitute for updating the pages.

Read the common, Documentation report and Project documentation pages formats
in checks/document-formats.md. Use the supplied write_file artifact tool to
edit only Markdown pages under docs/ (prefer the existing page that covers the
changed code) and to write documentation.md. Describe the changed behaviour
for a reader: what now happens, the boundaries, and what stays the same. In the
new text, link to the src/ files that changes.diff changed, with relative
inline links that exist in the combined candidate. Do not link to checks/,
request.md, specification.md, implementation.md or other factory and stage
files; they are not delivered with the project.

Write documentation.md with the required JSON metadata and nonempty Changes,
Validation and Limitations sections. Explain the actual page edits, what the
independent documentation and combined-candidate checks assess, and
limitations. Do not claim observed executions.

After editing, invoke the supplied export_changes tool exactly once with
{"output":"documentation.diff"}. Export actual page edits, not hand-authored
patch hunks. Keep changes.diff, application source, tests, acceptance and check
resources unchanged. Do not apply the code patch, run commands/checks, install
or delegate. If a tool reports an error, stop rather than inventing an output.

The independent checkers apply changes.diff first, then documentation.diff,
to a fresh copy of the original project. They rerun the repository's
acceptance scenarios and tests on the combined candidate. Passing these checks
is not host isolation or semantic certification. Keep pages and report ASCII
and under 16 KiB each; keep the patch under 128 KiB.
