# Ngozen

**Face verification without face exposure.**

Ngozen is a privacy-first verification wallet + partner SDK. A user can prove they are a real, live, face-verified person while partner apps receive signed claims — not selfies, videos, face embeddings, ID cards, legal names, or a universal tracking ID.

## What this repo includes

- Runnable web app and API using only Python standard library
- Camera-based browser demo that sends derived metrics, not the face image
- Signed proof token issuance
- Partner token verification endpoint
- Pairwise subject IDs per partner app
- SQLite audit trail and credential tables
- Minimal web SDK
- Dockerfile, Render config, GitHub Actions CI, and GitHub Pages landing page
- Production adapter interface for real liveness/face providers

## Important warning

This is a product MVP scaffold, **not production biometric security**.

In `DEMO_MODE=true`, the server trusts client-side camera/quality/challenge metrics and does not receive face images. This protects privacy for demos but can be spoofed. For production, set `DEMO_MODE=false` and connect a certified provider in `adapters/`.

## Quick start

```bash
cd ngozen
python server.py
```

Open:

```text
http://localhost:8080
```

Health check:

```bash
curl http://localhost:8080/v1/health
```

## Docker run

```bash
docker build -t ngozen .
docker run -p 8080:8080 -e NGOZEN_SECRET_KEY="change-this-secret" ngozen
```

## API flow

### 1. Create verification session

```bash
curl -X POST http://localhost:8080/v1/verification/session \
  -H "Content-Type: application/json" \
  -d '{
    "email":"demo@example.com",
    "requested_level":"L2",
    "claims":["real_human","face_verified","liveness_verified","duplicate_risk"],
    "retention_mode":"delete_raw_after_verification"
  }'
```

### 2. Submit demo proof

Use the UI for this step, or send a demo proof manually:

```bash
curl -X POST http://localhost:8080/v1/verification/submit \
  -H "Content-Type: application/json" \
  -d '{
    "session_id":"vs_REPLACE_THIS",
    "client_proof":{
      "camera_permission":true,
      "face_detected":true,
      "face_count":1,
      "completed_actions":["blink","turn_head_left"],
      "quality":{"brightness":130,"sharpness":12}
    }
  }'
```

### 3. Partner verifies signed proof token

```bash
curl -X POST http://localhost:8080/v1/partner/verify-token \
  -H "Content-Type: application/json" \
  -d '{
    "token":"PASTE_TOKEN_HERE",
    "partner_app_id":"demo_partner_app",
    "api_key":"demo_partner_key_change_me"
  }'
```

## GitHub deployment

This repository is designed to run as a GitHub-hosted project with a static landing page in `/docs` and a deployable Python backend.

### GitHub Pages

GitHub Pages can host only the static landing page in `/docs`, not the Python backend.

After pushing:

1. Open repo settings.
2. Go to **Pages**.
3. Select source: `Deploy from a branch`.
4. Branch: `main`, folder: `/docs`.
5. Save.

### Backend deployment

Use Render, Fly.io, Railway, or any Docker host. This repo includes `render.yaml` and `Dockerfile`.

For Render:

1. Push the repo to GitHub.
2. In Render, create a new Blueprint or Web Service from the repo.
3. Render will read `render.yaml`.
4. Set `DEMO_MODE=false` only after adding a production provider adapter.

## Production checklist

Before handling real users:

- Replace `NGOZEN_SECRET_KEY` with a long random secret from a secret manager.
- Set `DEMO_MODE=false`.
- Add a real provider adapter for liveness/deepfake/replay checks.
- Add rate limiting and abuse detection.
- Add device attestation for mobile apps.
- Add explicit consent receipts and deletion flows.
- Add a proper database such as Postgres.
- Add encryption at rest with KMS/HSM.
- Do demographic fairness testing.
- Do a security review before public launch.

## Product positioning

> Verify your humanity. Protect your face. Share proof, not identity.

For partner apps:

> Reduce fake profiles without forcing users to expose their face.
