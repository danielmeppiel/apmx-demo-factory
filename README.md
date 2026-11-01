# apmx-demo-factory

A reusable **feature factory as an APM package**: five agent contracts plus the
independent checks that judge their work. Give it a repository with a
`request.md` (the intent) and its own acceptance scenarios; it delivers a plan,
a specification, a code patch, a documentation patch and an advisory review.
Each contract loops until its checks pass, then hands its files to the next.

```text
planning -> specification -> build -> documentation -> review
            5 contracts, 7 outputs, 11 checks
```

The contracts say *"implement the intent in `request.md` so the repository's
acceptance scenarios pass"*. Nothing in this package names a feature: the
intent changes, the contracts stay. Version `v1.0.0` was a one-feature
checkout factory and stays tagged as history.

## Repository conventions

The factory works on any repository laid out like this:

| Path | Owner | Role |
| --- | --- | --- |
| `request.md` | repository | The intent: what to build, in prose. |
| `acceptance/*.feature`, `acceptance/steps/`, `acceptance/environment.py` | repository | Gherkin scenarios and their step definitions ([Behave](https://behave.readthedocs.io/) 1.3.3). The definition of done. |
| `src/` | factory may edit | Python application code; `src/` is the import root. |
| `tests/` | factory may **add** | `unittest` suite; existing tests are never edited. |
| `docs/` | factory may edit (documentation stage) | Markdown pages. |

Everything else (`.github/`, policy, `request.md`, `acceptance/`) is off
limits to the agents.

## What the checks enforce

Every check runs in a fresh copy of the repository's **original** bytes plus
the artifact under check. The agent's work arrives only as a patch, which the
check applies in its own private copy. Acceptance scenarios and existing tests
are read from the original bytes, so the agent cannot weaken what judges it.

| Contract | Check | Rule |
| --- | --- | --- |
| build | `acceptance-scenarios` | Apply `changes.diff`; every scenario in the repository's `acceptance/*.feature` passes. |
| build | `regression-suite` | The repository's whole existing `unittest` suite still runs and passes, plus at least one new test. |
| build | `change-scope` | The patch adds or edits files under `src/` and new files under `tests/` only: never `acceptance/`, `.github/`, policy, `request.md`, `docs/` or existing tests; no deletes, renames or mode changes. |
| build | `money-in-cents` | House standard: money is integer cents, so `src/` has no float literals and no `float()` calls. |
| build | `implementation-report-format` | Report structure. |
| documentation | `documentation-links` | Only Markdown under `docs/`; links and anchors resolve; an edited page links to the changed source it documents. |
| documentation | `combined-candidate` | Acceptance and regression rerun on code plus docs. |
| plan, spec, docs, review | `*-format*` | Document structure and references (every acceptance scenario title is listed). |

Out-of-scope patches are assessed rejections (exit 1), so the build and
documentation repair budgets can retry them.

## Run it

From a plain copy of a conforming repository (for example
[contoso-payments](https://github.com/danielmeppiel/contoso-payments)):

```sh
apmx --from 'danielmeppiel/apmx-demo-factory#v2.0.0' --plan    # preview, no model calls
apmx --from 'danielmeppiel/apmx-demo-factory#v2.0.0'           # Copilot, your default model
apmx --from 'danielmeppiel/apmx-demo-factory#v2.0.0' --on opencode --model github-copilot/gpt-5.6-sol
apmx audit                                                     # the printed Next command
```

Checks run with `python3` from your PATH, so Behave 1.3.3 must be installed:
`python3 -m pip install --require-hashes -r checks/requirements.txt`. The
factory imports the pinned
[`python-testing-patterns`](https://github.com/wshobson/agents/tree/46891e7e60da0e52baf1050b7b6391b64e84c6d9/plugins/python-development/skills/python-testing-patterns)
skill through APM.

In CI, apmx's reusable
[`run.yml`](https://github.com/danielmeppiel/apmx/blob/main/.github/workflows/run.yml)
runs the same reference and signs the receipt:

```yaml
uses: danielmeppiel/apmx/.github/workflows/run.yml@<ref>
with:
  factory: "danielmeppiel/apmx-demo-factory#v2.0.0"
  checks-requirements: checks/requirements.txt
```

Every completed run writes a receipt whose *definition digest* fingerprints
exactly these contracts, checks, pinned capabilities and this package commit.
A receiving repository pins that digest in its `apm-policy.yml`.

## Limits

Agents and checks run natively with your identity, files and network: this is
not a sandbox, and model use can cost money. The acceptance step definitions
are the repository's own Python and run in the check process. Checks assess
their stated scope; the review stage is advisory, not certification. The
factory adds behaviour: a change that contradicts an existing test needs a
human, because existing tests are never edited.
