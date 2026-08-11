# Contributing to the UK Materials Passport Schema

Thank you for your interest. This repository is the open-source output of an
active Innovate UK feasibility study (project 10188380), so the schema is
under structured change control — but issues, discussion, and pull requests
are genuinely welcome and feed directly into the project's gap analysis and
steering reviews.

## Raising issues

Use GitHub Issues for:

- **Schema gaps** — a field your sector or workflow needs that the core or a
  profile does not carry. Please describe the real-world document or process
  the field comes from.
- **Interoperability problems** — a conformant passport that another standard
  or tool cannot consume, or vice versa.
- **Spec ambiguity** — anywhere two reasonable implementers would read the
  spec differently.
- **Tooling bugs** — `tools/validate.py` misbehaving on a valid (or invalid)
  document. Attach the document if you can.

Please label issues where possible (`schema`, `spec`, `tooling`, `profile:plastics`).

## Pull requests

- **Tooling, examples, documentation:** PRs are reviewed and merged by the
  maintainers on a rolling basis. Run `python tools/validate.py` against every
  file in `examples/` before submitting; CI does the same.
- **Schema and spec changes** (`schema/`, `spec/`): see governance below. PRs
  are welcome as concrete proposals, but they will not be merged directly —
  they are queued for steering review.

## Schema-change governance

The schema is a project deliverable under review by the project steering
group (Helix8 Ltd and validation partners). Process:

1. Proposals are raised as issues or PRs and labelled `schema-change`.
2. Maintainers assess impact: core change vs. profile change vs. editorial.
   Sector-specific needs are met by **profile extension, not core change**
   wherever possible (spec §7).
3. Accepted proposals are batched into the next minor version (see roadmap in
   the README) and recorded in [CHANGELOG.md](CHANGELOG.md).
4. Breaking changes to released versions are not made; a new versioned
   namespace is published instead (`/v0.2/`, `/v1.0/`, …).

During the feasibility study (to January 2027) steering reviews gate each
release. A longer-term neutral governance home for the namespace is an open
issue (spec §10.1) and part of the project's open-ecosystem commitment.

## Code of conduct

This project follows the
[Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
Report unacceptable behaviour to the maintainers at contact@helix8.io.

## Licence of contributions

By contributing you agree that your contributions are licensed under the
repository's [Apache License 2.0](LICENSE).
