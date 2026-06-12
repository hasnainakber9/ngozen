"""Mock provider for local demos only.

Do not use this in production. It exists to keep the MVP runnable without paid
biometric vendors or storing face data.
"""

from __future__ import annotations

from .face_provider import ProviderResult


class MockProvider:
    def create_challenge(self, user_id: str, session_id: str):
        return {
            "type": "browser_metrics_demo",
            "actions": ["blink", "turn_head_left"],
            "warning": "Demo only. Not production liveness."
        }

    def verify_capture(self, session_id: str, encrypted_capture_ref: str, device_attestation: str) -> ProviderResult:
        return ProviderResult(
            passed=True,
            liveness_score=0.91,
            face_quality_score=0.88,
            duplicate_risk="low",
            provider_session_id=f"mock_{session_id}",
            reasons=["mock_passed"],
            metadata={"demo_only": True},
        )
