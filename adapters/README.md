# Production provider adapters

The default MVP runs in `DEMO_MODE=true`, which avoids receiving or storing raw face data. That is useful for product demos, but not sufficient for fraud-resistant production verification.

For production:

1. Set `DEMO_MODE=false`.
2. Implement `FaceVerificationProvider` in `face_provider.py`.
3. Use a provider that supports liveness checks, replay detection, device/session binding, audit logs, and data retention controls.
4. Store only the minimum result metadata needed for proof issuance.
5. Never send raw face images, videos, or face embeddings to partner apps.
