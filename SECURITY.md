# Security notes

This MVP demonstrates architecture, token handling, and privacy UX. It is not production biometric security.

## Demo limitations

- Client-side liveness metrics are spoofable.
- No real device attestation.
- No deepfake/replay protection.
- No rate limiting.
- HMAC secret defaults to a development value unless changed.
- SQLite is used for local development.

## Production requirements

- Certified liveness provider or well-reviewed in-house model.
- Replay, deepfake, emulator, root/jailbreak, virtual camera, and injection detection.
- Rate limits and velocity checks.
- Strong mobile device attestation.
- KMS/HSM-backed signing keys.
- Key rotation.
- Separate issuer keys by environment.
- Postgres with encryption at rest.
- Structured audit trails.
- Abuse monitoring dashboard.
- Manual review for suspicious sessions.
- Bias/fairness testing across devices, lighting, skin tones, ages, and presentation.

## Reporting issues

Open a private security issue or contact the maintainer.
