"""Provider interface for production liveness/face verification.

Replace the demo client-side scoring with a certified provider implementation here.
The backend should receive provider result objects, not raw biometric data from partners.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Protocol, Any


@dataclass
class ProviderResult:
    passed: bool
    liveness_score: float
    face_quality_score: float
    duplicate_risk: str
    provider_session_id: str
    reasons: list[str]
    metadata: Dict[str, Any]


class FaceVerificationProvider(Protocol):
    def create_challenge(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Return provider-specific capture/challenge instructions."""

    def verify_capture(self, session_id: str, encrypted_capture_ref: str, device_attestation: str) -> ProviderResult:
        """Verify a capture using liveness, replay detection, and face quality checks."""
