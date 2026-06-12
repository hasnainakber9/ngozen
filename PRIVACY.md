# Privacy design

Ngozen is designed around data minimization.

## Default MVP behavior

- Browser captures camera locally.
- Browser sends derived metrics, not images.
- Partner apps receive signed claims only.
- Partner apps do not receive face image/video/embedding.
- Users are represented to each partner by a pairwise ID, not one universal ID.
- Raw capture retention mode is set to `delete_raw_after_verification`.

## Claims model

Partner apps should request only what they need:

- `real_human`
- `face_verified`
- `liveness_verified`
- `duplicate_risk`
- `age_over_18` if available in a future age/ID flow

## Do not build

- Search anyone by face
- Central searchable face database
- Face embedding sharing with partner apps
- Universal cross-app person ID
- Silent identity sharing
- Selling verification/biometric data

## Production retention

For real deployments, define retention by assurance level:

- L1/L2: delete raw capture after verification result unless fraud review requires temporary retention.
- L3/L4: retention depends on KYC law and user consent.
- Logs: store minimum audit metadata, not face data.
