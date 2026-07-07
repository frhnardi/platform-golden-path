# CLAUDE.md — platform-golden-path

## What this repo is

The **paved road**: reusable GitHub Actions workflows plus a service template. A developer clicks "Use this template", pushes code, and gets security by default — no security knowledge required, no tickets to a security team.

Two deliverables:
1. `.github/workflows/golden-path.yml` — a **reusable workflow** (`workflow_call`) that consumer repos invoke with ~5 lines of YAML.
2. `templates/service-go/` — a minimal Go HTTP service template pre-wired to call the reusable workflow.

## The pipeline (order is fixed — ADR-0008, ADR-0005)

```
lint + unit test
  → Semgrep (SAST, fail on HIGH)
  → Trivy fs scan (dependencies/SCA, fail on CRITICAL)
  → docker build (multi-stage, distroless runtime)
  → Trivy image scan (fail on CRITICAL)
  → Syft SBOM (SPDX JSON, uploaded as artifact + attached as attestation)
  → push to ACR (OIDC auth, no docker password)
  → cosign sign --keyless (GitHub OIDC → Fulcio/Sigstore)
  → cosign attest SBOM
  → open PR against platform-gitops bumping the image digest (by digest, never by tag)
```

## Non-negotiable constraints

- **Keyless signing only** (ADR-0005). No cosign key pairs, no keys in secrets. Identity = GitHub OIDC token of this workflow. The certificate identity regex that Kyverno verifies against lives in `platform-gitops`; if the workflow path or repo changes, that policy must be updated in the same change set.
- **Zero static credentials** (ADR-0003). ACR login via `azure/login` with OIDC + `az acr login`. The only GitHub secret allowed is none; repo variables may hold non-sensitive config (tenant ID, client ID, ACR name).
- **Images are referenced by digest** in GitOps, never by mutable tag.
- **Severity gates are policy, not suggestion**: Semgrep HIGH and Trivy CRITICAL fail the build. Findings below the gate are reported (SARIF → GitHub code scanning) but do not block. Do not silently raise thresholds to make a build pass — that requires a documented exception.
- Developer experience matters as much as security: every failure message must say *what* failed, *why it matters*, and *the exact next step or doc link*. When editing workflow steps, always include a `name:` that reads as a sentence.

## Conventions

- Reusable workflow inputs kept minimal: `service-name`, `language` (start with `go` only), `dockerfile-path`. Sane defaults for everything else.
- Pin all GitHub Actions by commit SHA, not tag (supply-chain hygiene — we are literally building a supply-chain security story; our own pipeline must be exemplary).
- Template service: Go 1.22+, multi-stage Dockerfile, distroless base, non-root USER, healthcheck endpoint `/healthz`.
- Test the reusable workflow via the `sample-service` repo, not by pushing junk commits here.

## Workflow for Claude Code

1. Plan mode first. Workflows are hard to test locally — prefer small, reviewable increments.
2. Use `act` only for syntax smoke tests; real verification happens in `sample-service` CI runs.
3. Never introduce a new scanner/tool without an ADR in `platform-infra/docs/adr/`.

## Definition of done (Phase 2)

- `sample-service` pushes a commit → pipeline runs end-to-end → signed image with SBOM attestation lands in ACR → PR opened against `platform-gitops` with the new digest.
- README contains the 5-line consumer snippet and an architecture diagram (Mermaid).
