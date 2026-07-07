# service-go

A minimal Go 1.22 HTTP service pre-wired to the **golden path**. Click "Use this
template", change two placeholders, push — and you get lint, SAST, dependency and
image scanning, a signed image with an SBOM attestation, and a GitOps promotion
PR, with no security work of your own.

## Endpoints

| Method | Path       | Response                          |
|--------|------------|-----------------------------------|
| GET    | `/healthz` | `{"status":"ok"}` — liveness probe |
| GET    | `/hello`   | `{"message":"hello, world"}`; `?name=` overrides |

## Adopt it

1. Replace the module path in [`go.mod`](go.mod) with your repo path.
2. In [`.github/workflows/ci.yml`](.github/workflows/ci.yml), pin the reusable
   workflow `uses:` to a commit SHA of `platform-golden-path` and set your org.
3. Ensure your org provides the config the pipeline needs — the ACR/Azure
   repository *variables* and the GitOps App *secrets* (`secrets: inherit`
   forwards them). See the platform docs.

That `ci.yml` is the whole integration — checkout, scanning, signing, and the
GitOps PR all live in the reusable workflow, not here. If it ever grows past a
dozen lines, that is a signal to push the complexity upstream into the golden
path, not into every service.

## Develop locally

```bash
go test -race ./...     # what the pipeline runs
go run .                # serves on :8080 (override with PORT)
docker build -t service-go .
```

## Why the image is tiny and safe

The [`Dockerfile`](Dockerfile) is multi-stage: a full Go toolchain compiles a
static, stripped binary, which is copied into `gcr.io/distroless/static-debian12:nonroot`.
The runtime image has no shell, no package manager, and runs as UID 65532 — so a
compromised process has nothing to exec into and no root. The result is ~13 MB.
