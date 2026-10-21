# apmx-demo-factory

A **software factory as an APM package**: five agent contracts plus the
independent checks that judge their work. It turns a checkout feature request
into a plan, a specification, a code patch, a documentation patch, and an
advisory review. Each contract loops until its checks pass, then hands its
files to the next.

```text
planning -> specification -> build -> documentation -> review
            5 contracts, 7 outputs, 9 checks (Gherkin acceptance, regression, formats)
```

## The 30-second story

1. **Review the factory once.** This repository is it: `contracts/` says what
   each agent must deliver, and `checks/` decides whether it did.
   `checks/requirements.txt` pins the checkers' only dependency (Behave 1.3.3)
   with hashes.
2. **Run it anywhere.** [apmx](https://github.com/danielmeppiel/apmx) runs the
   package against an application with Copilot or OpenCode, locally or in CI.
   Every completed run writes a receipt (in-toto, SLSA, CycloneDX) whose
   *definition digest* fingerprints exactly these contracts, checks, pinned
   capabilities and this package commit.
3. **Accept its pull requests by proof.** The receiving repository pins that
   digest in `apm-policy.yml`. Its only gate is `apmx audit`. See
   [apmx-demo-shop](https://github.com/danielmeppiel/apmx-demo-shop).

## Run it

From a plain copy of an application, not a Git checkout with remotes (for
example, the shop app):

```sh
apmx --from danielmeppiel/apmx-demo-factory#v1.0.0 --plan   # preview, no model calls
apmx --from danielmeppiel/apmx-demo-factory#v1.0.0          # Copilot, your default model
apmx audit                                                  # the printed Next command
```

In CI, [`run.yml`](https://github.com/danielmeppiel/apmx/blob/main/.github/workflows/run.yml)
runs the same reference and signs the receipt:

```yaml
uses: danielmeppiel/apmx/.github/workflows/run.yml@<ref>
with:
  factory: "danielmeppiel/apmx-demo-factory#v1.0.0"
  checks-requirements: checks/requirements.txt
```

Checks run with `python3` from your PATH, so Behave 1.3.3 must be installed:
`python3 -m pip install --require-hashes -r checks/requirements.txt`. The
factory imports the pinned
[`python-testing-patterns`](https://github.com/wshobson/agents/tree/46891e7e60da0e52baf1050b7b6391b64e84c6d9/plugins/python-development/skills/python-testing-patterns)
skill through APM.

## Limits

Agents and checks run natively with your identity, files and network: this is
not a sandbox, and model use can cost money. Checks assess their stated scope.
The review stage is advisory, not certification. This factory is the
`examples/contracts/software-factory` example from apmx, published as a
versioned package for the apmx demo.
