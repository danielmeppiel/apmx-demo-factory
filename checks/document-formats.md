# Feature factory document formats

These formats belong to this factory, not to APMX generally. They check
structure and reference consistency, not whether every sentence is true.
`request.md` and the repository's `acceptance/` scenarios remain authoritative.

## Common report shape

Every produced report starts with exactly one fenced `json` metadata object,
before its Markdown sections. Use schema `software-factory-document/2` and the
appropriate `document` value. Required H2 sections appear once and contain
nonempty content. Reports are ASCII and at most 16 KiB. Do not add metadata
keys, duplicate JSON keys or additional JSON fences.

Read only the stage-specific format below. Prose wording is not prescribed.

## Acceptance IDs

The acceptance IDs are the titles of every `Scenario` and `Scenario Outline`
in the repository's `acceptance/*.feature` files, exactly as written after the
keyword (an outline counts once, whatever its number of example rows). List
each one exactly once, in any order. The checker reads them from the captured
feature files.

## Planning

`targets` names every file the change will add or edit, each once, with
`state` `existing` (present in the captured project) or `new`. Targets stay
under `src/`, `tests/` or `docs/`; they include at least one `src/` file, at
least one new `tests/` file and at least one `docs/` page. Existing tests are
preserved, so they are never targets.

```json
{
  "schema": "software-factory-document/2",
  "document": "planning",
  "acceptance": ["<every scenario title>"],
  "targets": [
    {"path": "src/<package>/<module>.py", "state": "existing"},
    {"path": "tests/test_<feature>.py", "state": "new"},
    {"path": "docs/<page>.md", "state": "existing"}
  ]
}
```

Required H2 sections: Goal, Changes, Validation, Risks.

## Specification

Use the same complete acceptance list as Planning. `interfaces` lists the
existing public functions and classes the change touches, as
`src/<path>.py:<name>`; each must be a top-level, non-underscore `def` or
`class` in the captured source (the checker parses it without importing it).

```json
{
  "schema": "software-factory-document/2",
  "document": "specification",
  "acceptance": ["<every scenario title>"],
  "interfaces": ["src/<package>/<module>.py:<function_or_class>"]
}
```

Required H2 sections: Behavior, Interface, Acceptance.

## Implementation report

```json
{"schema":"software-factory-document/2","document":"implementation"}
```

Required H2 sections: Changes, Validation, Limitations.

## Documentation report

```json
{"schema":"software-factory-document/2","document":"documentation"}
```

Required H2 sections: Changes, Validation, Limitations.

## Advisory review

```json
{"schema":"software-factory-document/2","document":"review","findings":[]}
```

Required H2 sections: Assessment, Findings, Limitations.

Zero findings is valid. For an actual finding, replace the empty list with
objects containing exactly `artifact`, `line` and `detail`. `artifact` names
one of `request.md`, `specification.md`, `changes.diff`, `implementation.md`,
`documentation.diff` or `documentation.md`; `line` is an existing 1-based line
in that artifact, not a line in a reconstructed source file. `detail` is
nonempty and at most 800 characters. At most 20 findings are accepted.
Findings and prose are advice, never an acceptance verdict.

## Project documentation pages

Pages under `docs/` are Markdown, ASCII, at most 16 KiB, with H2 sections.
They are not reports and do not use the JSON metadata above.

Use inline links only, for example `[the module](../src/<package>/<module>.py)` and
`[errors](#input-errors)`. No query strings or reference-style links. Local
targets must exist in the combined candidate (the repository's `src/`,
`tests/`, `docs/`, `acceptance/` and `README.md`, plus the delivered changes);
H2 fragments must exist. Absolute HTTP(S) links are allowed but not fetched.

The documentation checker requires at least one edited page to link to a
`src/` file that the code patch changed: document the change on the page that
documents the changed code. Another check reruns the repository's
acceptance scenarios and unittest suite on the code-plus-docs tree. These
finite checks do not prove that all prose is semantically correct.
