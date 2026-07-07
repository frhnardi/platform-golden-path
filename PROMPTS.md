# Claude Code Prompts — platform-golden-path (Phase 2)

Prerequisite: Phase 1 done (OIDC federation live, ACR exists). Paste in order, plan mode first.

---

## Prompt 2.1 — Reusable workflow skeleton: test + SAST + SCA

```
Read CLAUDE.md first. Create .github/workflows/golden-path.yml as a reusable workflow (on: workflow_call) with inputs: service-name (required), language (default "go"), dockerfile-path (default "./Dockerfile").

Implement the first three stages only:
1. lint+test: setup-go, golangci-lint, go test ./...
2. Semgrep: community rules, fail on HIGH+, upload SARIF to code scanning
3. Trivy fs scan: fail on CRITICAL, SARIF upload
Every step name must read as a sentence a developer understands. On failure, use a final if: failure() step that prints WHAT failed, WHY it matters, and a docs link placeholder — per the failure-message rule in CLAUDE.md.
Pin all actions by commit SHA. permissions block: minimal, job-level.
Acceptance: actionlint clean; summary lists each pinned SHA and the action version it corresponds to.
```

## Prompt 2.2 — Build, image scan, SBOM, push via OIDC

```
Extend golden-path.yml with a build-and-push job (needs the scan job):
1. docker build (buildx), tag as <acr>/<service-name>:sha-<short-sha>
2. Trivy image scan on the built image, fail on CRITICAL
3. Syft SBOM in SPDX JSON, upload as artifact
4. azure/login via OIDC (client-id/tenant-id from vars, no secrets), az acr login, push
5. Capture the pushed image DIGEST into a job output — everything downstream references digest, never tag (CLAUDE.md).
Acceptance: actionlint clean; job outputs documented in workflow comments.
```

## Prompt 2.3 — Keyless signing + SBOM attestation

```
Add a sign job (needs build-and-push) implementing ADR-0005:
1. cosign sign --yes <image>@<digest> — keyless, using the job's OIDC token (permissions: id-token: write)
2. cosign attest --yes --predicate sbom.spdx.json --type spdx <image>@<digest>
Then print a verification block in the job summary: the exact cosign verify command with --certificate-identity-regexp pinned to this workflow's ref and --certificate-oidc-issuer https://token.actions.githubusercontent.com. That regexp is what platform-gitops will enforce — flag it clearly.
Acceptance: actionlint clean; README gains a "verify it yourself" section with that command.
```

## Prompt 2.4 — GitOps digest-bump PR

```
Add the final job: open a PR against frhnardi/platform-gitops updating the image digest for this service (kustomize edit set image or yq against apps/<service-name>/kustomization.yaml — match whatever structure platform-gitops defines; if unsure, write it against a documented assumption and note it).
Auth: use a GitHub App or fine-grained PAT? Neither — propose the least-bad option given our zero-static-credential rule (ADR-0003), present trade-offs (GitHub App installation token vs. repo-scoped fine-grained PAT), and implement the GitHub App path with the app id/private key stored as org secrets, clearly documenting this as the ONE exception to "no secrets" and why it is scoped/acceptable. Update ADR-0003 consequences section via a proposed diff I can copy to platform-infra.
Acceptance: PR body template includes digest, run link, and SBOM artifact link.
```

## Prompt 2.5 — service-go template

```
Build templates/service-go per CLAUDE.md: Go 1.22 HTTP service with /healthz and /hello, table-driven tests, multi-stage Dockerfile (distroless nonroot, USER nonroot, no shell), .golangci.yml, and a caller workflow ci.yml that is ONLY: checkout + uses golden-path.yml@<SHA> with inputs. If the caller exceeds ~15 lines, you have leaked complexity — refactor upstream instead.
Acceptance: go test passes; docker build succeeds; hadolint clean on the Dockerfile.
```

## Prompt 2.6 — README + diagram

```
Write the repo README: the 5-line consumer quickstart, a Mermaid sequence diagram of the full pipeline (push -> ... -> GitOps PR -> ArgoCD -> Kyverno admission), the severity-gate table (what blocks vs. what only reports, per ADR-0008), and a "design decisions" section linking each pipeline property to its ADR in platform-infra.
Tone: written for a developer consuming the paved road, not for the platform team.
```
