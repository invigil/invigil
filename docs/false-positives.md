# How often Invigil is wrong

**This page publishes that Invigil was wrong about these repositories — not that
these repositories are bad.** Every project named here is named because our check
made a claim about it that did not hold. None of them asked to be scored, none is
ranked, and no grade any of them received is reproduced here. That distinction is
the whole point of the exercise.

Until a tool can say how often it is wrong, nobody should gate a build on it.
This is Invigil's attempt to say so, in public, while the answer is still
embarrassing.

**Status: work in progress.** The sample is 27 repositories against a target of
30, and 331 of 402 findings are still unaudited. Published early on purpose —
holding it until the numbers flatter us would defeat the point.

## Method

1. **Score.** 27 third-party repositories, shallow-cloned, scored with
   `invigil score --profile audit --format json`. The `audit` profile exists
   precisely for repos we don't own: a check keeps its weight there only if any
   maintainer would concede the finding without first adopting Invigil's
   doctrine.
2. **Verify.** For every "no X" finding, walk the tree for X under every naming
   convention a maintainer might plausibly have used, case-insensitively —
   `Changelog.rst` and `CHANGELOG.md` are the same artifact to a human. A hit
   means the artifact is there and Invigil failed to see it.
3. **Read the file.** Anything the globs can't settle is judged by opening the
   flagged file. These hand judgements override the automated pass.

Matching in step 2 is deliberately generous. Over-calling a false positive costs
us a check we didn't strictly need to loosen; under-calling one means publishing
a rate we would lose an argument about with the maintainer whose repo we named.

Two failure modes are kept apart, because blending them produces a meaningless
number:

- **Detection bug** — the claim is *factually false*. The artifact is right
  there under a different name. This is a bug in us.
- **Doctrine disagreement** — the claim is factually true, but the maintainer
  would never concede it matters. This is a bug in what we chose to measure.

Only detection bugs are counted as false positives below. Doctrine disagreements
are handled by removing the check's weight from the `audit` profile instead.

## The sample

27 repositories, chosen to stress naming conventions rather than to collect
prestigious names: `tqdm` for `LICENCE`, `jq` and `curl` for `COPYING`,
`ripgrep` and `bat` for Rust's dual `LICENSE-APACHE` + `LICENSE-MIT`, `chalk`
for lowercase `readme.md`, the Sphinx projects for `docs/index.rst`.

It spans markup (RST · MyST · AsciiDoc · Markdown), governance (solo · org ·
corporate · foundation) and ecosystem (Python · Rust · Go · JS · Java · Ruby · C).
That spread is not decoration: the RST bug only surfaced because `aws-cli` was in
the first five repositories ever scored.

**Under-represented, and therefore a known weakness of the rate below:**
AsciiDoc (3 repos), Java (2), non-English-primary projects (0).

## Result

The audit ran in two passes: before the fixes, and again after them on the same
27 repositories.

### Before the fixes — 448 findings, 106 audited

| check | FP | TRUE | FP rate |
|---|---:|---:|---:|
| `no-tracked-secrets` | 13 | 0 | **100%** |
| `license-present` | 7 | 0 | **100%** |
| `readme-present` | 4 | 0 | **100%** |
| `changelog` | 15 | 4 | 79% |
| `contributor-door` | 8 | 4 | 67% |
| `docs-index` | 12 | 8 | 60% |
| `code-of-conduct` | 5 | 14 | 26% |
| `security-policy` | 2 | 10 | 17% |
| **total** | **66** | **40** | **62%** |

Three checks were wrong every single time they fired.

### After the fixes — 402 findings, 71 audited

| check | FP | TRUE | FP rate |
|---|---:|---:|---:|
| `no-tracked-secrets` | 8 | 0 | see note |
| `changelog` | 2 | 4 | 33% |
| `contributor-door` | 1 | 4 | 20% |
| `security-policy` | 2 | 10 | 17% |
| `docs-index` | 1 | 7 | 12% |
| `code-of-conduct` | 1 | 14 | 7% |
| `actions-sha-pinned` | 0 | 17 | **0%** |
| **total** | **15** | **56** | **21%** |

Across the whole sample: **448 → 402 findings, 13 repositories scoring no gate
at all → 0, five blocker-severity accusations → none.**

## `no-tracked-secrets` is the one that mattered

A wrong security accusation about someone else's repository, in public, is the
most damaging thing this tool can do. It fired 13 times and was wrong 13 times,
five of them at blocker severity.

- **`jqlang/jq`** — we flagged `sig/jq-release-{new,old}.key`. These are
  `-----BEGIN PGP PUBLIC KEY BLOCK-----`: the keys you verify jq releases
  *with*. We accused a project of leaking a secret by pointing at its published
  public key.
- **`prometheus/prometheus`** — `web/ui/react-app/.env`, whose entire contents
  are two comment lines and `PUBLIC_URL=.`. Flagged on filename alone.
- **`vitejs/vite`** — fixtures; the flagged value is literally
  `VITE_PARENT_ENV=dont_load_me`.
- **`spring-projects/spring-boot`** — a test server key under `integration-test/`.
- **`celery/celery`** — `examples/security/ssl/worker.key`, demo material for
  the SSL documentation.

An earlier fix had tried to solve this class *by path*, exempting `tests/`.
Every repository that files throwaway key material anywhere else walked straight
back into it. **The fix is not more path patterns.** Read the file: a PEM whose
header says `PUBLIC KEY` is not a secret, and a `.env` holding no
credential-shaped value is not a leak. Path is a tiebreaker for severity, not
the test.

## The other detection bugs

- **`readme-heading-hierarchy`** counted only Markdown ATX headings. `numpy`'s
  README opens with `<h1 align="center">`; we reported "0 H1 titles". Same for
  `axios`, `fastapi`, `bat` and `prometheus`. The centred HTML banner is a
  mainstream convention and we were reading all of them as untitled documents.
- **`license-present`** missed `COPYING` (GNU), `LICENCE` (British), lowercase
  `license`, `LICENSE.rst`, and Rust's `LICENSE-APACHE` + `LICENSE-MIT` pair.
  All 7 flagged repositories ship a license.
- **`readme-present`** missed `README.adoc` and lowercase `readme.md`. All 4
  ship one.
- **`changelog`** missed `CHANGES.md/.rst`, `Changelog.rst` (lowercase L),
  `NEWS`, `HISTORY.md`, `ChangeLog`, `CHANGELOG.adoc`, towncrier's
  `changelog.d/`, and per-crate changelogs in a workspace.
- **`contributor-door`** missed `CONTRIBUTING.rst` and lowercase
  `contributing.md`.
- **`docs-index`** missed Sphinx (`docs/index.rst`, `doc/source/`), Antora
  (`docs/antora.yml`), Hugo (`site/content/_index.md`) and i18n mkdocs
  (`docs/en/mkdocs.yml`).

The common root cause: nearly every one of these checks asked *"did you use our
spelling?"* when the question it meant to ask was *"is it there?"* They now share
a single case-insensitive lookup that answers the second question.

## `license-apache2` was a doctrine bug, not a detection bug

It told MIT and BSD projects that their license "is not Apache-2.0" — 15 times.
The claim is true and completely irrelevant. It is house style with no claim to
universality, and it is exactly what the `audit` profile's own contract forbids.
Nobody at `facebook/react` concedes that finding. It now carries weight 0 in
`audit`, alongside `env-example` and `code-of-conduct`.

## Two judgement calls that move the headline number

Any single blended rate is sensitive to choices that deserve to be visible
rather than buried in a denominator.

1. **Which checks are in the denominator.** The 62% above covers the
   presence-style checks. `actions-sha-pinned` was hand-audited separately at
   17 findings, **0 false positives** — it is the check whose trailing-comment
   trust has bitten us three times, and on other people's repositories it turned
   out to be right every time. Fold it in and the before-fixes rate falls from
   62% to 54%. Both numbers are honest; neither should be quoted without its
   denominator.
2. **Whether a downgraded finding is still wrong.** Post-fix,
   `no-tracked-secrets` still surfaces 8 findings — genuine throwaway TLS
   fixtures — but at WARN rather than blocker. The table above inherits the
   original "false positive" verdict for them, which is why it shows no rate.
   Our position is that surfacing without accusing is the correct tier and these
   are no longer errors; a maintainer could reasonably say we should not have
   mentioned their test fixtures at all. Counted their way, the post-fix rate is
   worse than 21%.

## Still unaudited — 331 of 402 findings

Mostly checks that fire near-universally, which is itself the signal:
`signed-releases-sbom` 27/27, `smoke-published` 26/27, `coverage-gate` 26/27,
`good-first-issues` 26/27, `operator-door` 25/27, `scorecard-workflow` 24/27,
`error-path-tests` 23/27, `lockfile-enforced` 21/27, `ai-door` 21/27.

A check that fires on 27 of 27 diverse, well-run projects is not finding 27
defects. Each needs the same call: is the observation true and simply measuring
something almost nobody does, or is it another detection bug?

**13 of the 27 repositories scored no gate at all** under `audit` before the
fixes, including `curl`, `react` and `prometheus`. Read that as evidence about
the ruler, not about those projects. It is now 0 — which is the point.

## A known false negative, deliberately not fixed here

The secret scanner's exact-match list contains `.env` only, so `.env.local` and
`.env.production` — which routinely *do* hold real credentials — are never
scanned. That is a false **negative** and out of scope for a false-positive
pass, but it should not go unlisted just because it is inconvenient to the
narrative.

## What this does not license

A measured error rate is not permission to start scoring the internet. Publishing
that our tool was wrong about a repository is a different act from publishing a
judgement of that repository, and only the first one is unlocked here. Ranking,
grading or leaderboarding repositories we don't own stays off the table.

## Reproducing this

The audit workspace is kept outside this repository, since nothing in it is
publishable until the rate is one we would defend in a reply from a maintainer
whose repo we named. It holds the 27-repo sample and why each was chosen, the
raw per-repo JSON, the 402 findings one row each, the file-by-file hand
judgements, and the aggregation and verification scripts. The pipeline is
clone → score → aggregate → verify, and it regenerates every number above from
the clones.

This page feeds [Beta condition 1](stability.md#what-beta-requires). That
condition is **not met**: 27 repositories against 30, and 331 findings still
unaudited.
