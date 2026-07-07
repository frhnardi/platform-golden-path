# GitOps promotion — the one credential the golden path cannot avoid

The final pipeline stage (`open-gitops-pr`) opens a pull request against
`platform-gitops` that bumps the deployed image **digest** (never a tag) for the
service. This is the only stage that writes to another GitHub repository, and it
is the only place the golden path holds a static secret. This document explains
why, what the alternatives were, and how it is scoped so the exception stays
small.

## Why a stored credential is unavoidable here

Everywhere else the golden path is credential-free (ADR-0003):

- **ACR push** uses `azure/login` with GitHub OIDC — a short-lived federated
  token, nothing stored.
- **cosign signing** is keyless — the signing identity *is* the workflow's OIDC
  token exchanged at Fulcio, no key pair anywhere.

Those work because GitHub OIDC authenticates this workflow **to a third party**
(Azure, Sigstore). It cannot authenticate the workflow **back to the GitHub API
of a different repository**. GitHub's built-in `GITHUB_TOKEN` is scoped to the
repo that is running the workflow and cannot be widened to write to
`platform-gitops`. So promoting into another repo needs a credential GitHub will
accept for that repo — and there is no zero-storage form of one.

## The options, least-bad first

| Option | Blast radius if leaked | Lifetime of the stored secret | Identity | Verdict |
|---|---|---|---|---|
| **GitHub App installation token** (chosen) | The App's permissions on the repos it is installed on (here: `contents:write` + `pull_requests:write` on `platform-gitops` only) | The **private key** is long-lived, but the token minted from it at runtime is ~1 hour and repo-scoped | The App (a first-class bot identity, org-owned) | ✅ Smallest durable surface; centralised; rotatable without touching consumers |
| Fine-grained PAT, repo-scoped | Same repo scope, but the token itself is the long-lived thing sitting in secrets | Long-lived (up to 1 year, or no expiry) | A **human user** — PR authorship, offboarding, and bus-factor all attach to one person | ❌ Strictly worse: the stored secret *is* the live credential, and it is tied to a person |
| Classic PAT / broad token | Whole account | Long-lived | A human user | ❌ Never |

**Chosen: GitHub App.** The durable secret is a private key that grants nothing
by itself — it only mints tokens, and those tokens are short-lived and narrowly
scoped. Rotation is one key in one place; consumers never see it. A PAT, by
contrast, makes the stored secret itself the live, long-lived, human-owned
credential — a larger surface for no benefit.

This is the **one sanctioned exception to ADR-0003**. It is acceptable because
the exception is a *token-minting key*, not a *token*: the thing that can
actually act is ephemeral and minimal.

## Setup (one-time, org-level)

1. **Create a GitHub App** in the org (e.g. "golden-path GitOps promoter").
   - Repository permissions: **Contents: Read and write**, **Pull requests: Read
     and write**. Nothing else.
   - No webhook needed.
2. **Install** it on `platform-gitops` **only** (not org-wide).
3. Generate a private key (PEM).
4. Store two **organization secrets**, granted to the repos that consume the
   golden path:
   - `GITOPS_APP_ID` — the App's numeric ID (semi-public; kept as a secret only
     for a single onboarding story — a repo/org *variable* would be equally
     fine).
   - `GITOPS_APP_PRIVATE_KEY` — the PEM private key. **This is the one secret.**
5. Consumers forward them to the reusable workflow with `secrets: inherit`:

   ```yaml
   jobs:
     golden-path:
       uses: <ORG>/platform-golden-path/.github/workflows/golden-path.yml@<SHA>
       with:
         service-name: my-service
       secrets: inherit
   ```

Rotation: regenerate the App private key, update the one org secret. No consumer
change, no PAT re-issuance per person.

## Assumed platform-gitops layout

The `open-gitops-pr` job edits:

```
apps/<service-name>/kustomization.yaml
```

and expects an `images:` entry keyed by the service name:

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
images:
  - name: my-service                              # keyed by service-name
    newName: myacr.azurecr.io/my-service          # set by the pipeline
    digest: sha256:…                              # set by the pipeline (never a tag)
```

The job sets `newName` + `digest` and deletes any `newTag`, then fails loudly if
no matching entry exists (the service must be onboarded in `platform-gitops`
first). If the real layout differs, adjust the "Pin the new image digest" step;
the equivalent `kustomize edit set image` command is given inline there.

## ADR-0003 consequences — proposed update

Copy the diff below into `platform-infra/docs/adr/ADR-0003-zero-static-credentials.md`
(the "Consequences" section). It records the exception so the next reader does
not treat the stored key as a policy violation.

```diff
 ## Consequences

 * CI authenticates to Azure and to Sigstore via short-lived GitHub OIDC tokens;
   no cloud or signing credentials are stored in GitHub.
 * The only GitHub secret in a consumer repo is, by default, none; non-sensitive
   configuration lives in repository/organization *variables*.
+
+### Exception: cross-repo GitOps promotion (added <DATE>)
+
+* Opening the image-digest promotion PR against `platform-gitops` writes to a
+  **different** GitHub repository. GitHub OIDC cannot authenticate a workflow
+  back to another repo's API, and `GITHUB_TOKEN` is scoped to the running repo,
+  so a stored credential is unavoidable for this one step.
+* **Decision:** use a **GitHub App** ("golden-path GitOps promoter") installed
+  only on `platform-gitops` with `contents:write` + `pull_requests:write`. The
+  only stored secret is the App's **private key** (`GITOPS_APP_PRIVATE_KEY`,
+  plus the semi-public `GITOPS_APP_ID`), held as **organization** secrets.
+* **Why this and not a PAT:** the stored key cannot act on its own — at runtime
+  it mints an installation token that is short-lived (~1h) and scoped to just
+  `platform-gitops`. A fine-grained PAT would instead make the stored secret
+  *itself* the long-lived, human-owned live credential — a larger blast radius
+  for no gain. See `platform-golden-path/docs/gitops-promotion.md`.
+* **Scope of the exception:** exactly one secret (a token-minting key), one
+  installation, two permissions, one target repo. Rotation is a single key in a
+  single place. This does not reopen static credentials for any other stage —
+  ACR push and cosign signing remain credential-free.
```

Replace `<DATE>` with the date the ADR update is merged.
