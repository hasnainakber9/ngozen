#!/usr/bin/env python3
"""Ngozen privacy-first face verification MVP. Demo only, not production biometric security."""
from __future__ import annotations

import base64, hashlib, hmac, json, mimetypes, os, secrets, time, urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

APP_NAME = "Ngozen"
ISSUER = os.getenv("NGOZEN_ISSUER", "ngozen-local-demo")
SECRET_KEY = os.getenv("NGOZEN_SECRET_KEY", "dev-only-change-this-secret-key")
PORT = int(os.getenv("PORT", "8080"))
HOST = os.getenv("HOST", "0.0.0.0")
BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
SDK_DIR = BASE_DIR / "sdk"
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "86400"))
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "600"))
DEMO_PARTNER_ID = os.getenv("DEMO_PARTNER_ID", "demo_partner_app")
DEMO_PARTNER_CODE = os.getenv("DEMO_PARTNER_CODE", "demo_partner_access_code")

SESSIONS: dict[str, dict[str, Any]] = {}
USERS: dict[str, str] = {}
CHALLENGE_ACTIONS = ["blink", "turn_head_left", "turn_head_right", "smile", "look_up"]
DEFAULT_CLAIMS = ["real_human", "face_verified", "liveness_verified", "duplicate_risk"]


def now() -> int:
    return int(time.time())


def utc_iso(ts: int | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts or now()))


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"), sort_keys=True)


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def b64url_decode(data: str) -> bytes:
    return base64.urlsafe_b64decode((data + "=" * (-len(data) % 4)).encode())


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def stable_hmac_hex(purpose: str, value: str) -> str:
    return hmac.new(SECRET_KEY.encode(), f"{purpose}:{value}".encode(), hashlib.sha256).hexdigest()


def sign_token(payload: dict[str, Any]) -> str:
    header = {"alg": "HS256", "typ": "JWT", "kid": "local-hmac"}
    head = b64url_encode(json_dumps(header).encode())
    body = b64url_encode(json_dumps(payload).encode())
    sig = hmac.new(SECRET_KEY.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{b64url_encode(sig)}"


def verify_token(token: str) -> tuple[bool, dict[str, Any] | None, str]:
    try:
        head, body, sig = token.split(".")
        expected = hmac.new(SECRET_KEY.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, b64url_decode(sig)):
            return False, None, "Bad signature"
        payload = json.loads(b64url_decode(body).decode())
        if int(payload.get("exp", 0)) < now():
            return False, payload, "Token expired"
        return True, payload, "OK"
    except Exception as exc:
        return False, None, f"Token error: {exc}"


def public_error(message: str, status: int = 400) -> tuple[int, dict[str, Any]]:
    return status, {"ok": False, "error": message}


def get_or_create_user(email: str | None) -> str:
    key = stable_hmac_hex("email", email.strip().lower()) if email else "anon_" + secrets.token_urlsafe(8)
    if key not in USERS:
        USERS[key] = "user_" + secrets.token_urlsafe(16)
    return USERS[key]


def partner_is_valid(partner_app_id: str, access_code: str) -> bool:
    return partner_app_id == DEMO_PARTNER_ID and hmac.compare_digest(access_code, DEMO_PARTNER_CODE)


def pairwise_subject_id(user_id: str, partner_app_id: str) -> str:
    return "pairwise_" + stable_hmac_hex("pairwise", f"{user_id}:{partner_app_id}")[:32]


def create_session(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    requested_level = payload.get("requested_level", "L2")
    if requested_level not in {"L1", "L2", "L3"}:
        return public_error("requested_level must be L1, L2, or L3")
    user_id = get_or_create_user(payload.get("email"))
    session_id = "vs_" + secrets.token_urlsafe(18)
    actions = secrets.SystemRandom().sample(CHALLENGE_ACTIONS, 2)
    expires = now() + SESSION_TTL_SECONDS
    SESSIONS[session_id] = {
        "user_id": user_id,
        "requested_level": requested_level,
        "claims": payload.get("claims") or DEFAULT_CLAIMS,
        "actions": actions,
        "expires": expires,
        "status": "pending",
    }
    return 200, {
        "ok": True,
        "session_id": session_id,
        "requested_level": requested_level,
        "challenge_actions": actions,
        "expires_at": utc_iso(expires),
        "privacy": {"raw_capture_required_by_demo": False, "partner_receives_face_data": False},
    }


def score_client_proof(proof: dict[str, Any], required: list[str]) -> tuple[float, float, list[str]]:
    reasons: list[str] = []
    if not proof.get("camera_permission"):
        reasons.append("camera_permission_missing")
    if not proof.get("face_detected"):
        reasons.append("face_not_detected")
    if int(proof.get("face_count", 0)) != 1:
        reasons.append("expected_one_face")
    completed = set(proof.get("completed_actions") or [])
    missing = [a for a in required if a not in completed]
    if missing:
        reasons.append("missing_actions:" + ",".join(missing))
    q = proof.get("quality") or {}
    brightness = float(q.get("brightness") or 0)
    sharpness = float(q.get("sharpness") or 0)
    liveness = 0.30 + (0.25 if proof.get("camera_permission") else 0) + (0.20 if proof.get("face_detected") else 0)
    liveness += 0.25 * (len(required) - len(missing)) / max(len(required), 1)
    quality = min(1.0, max(0.0, brightness / 180.0) * 0.55 + max(0.0, min(sharpness, 30) / 30.0) * 0.45)
    return liveness, quality, reasons or ["passed_demo_checks"]


def submit_verification(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    session_id = payload.get("session_id")
    session = SESSIONS.get(session_id or "")
    if not session_id:
        return public_error("session_id is required")
    if not session:
        return public_error("Unknown session", 404)
    if session["expires"] < now():
        session["status"] = "expired"
        return public_error("Session expired", 410)
    liveness, quality, reasons = score_client_proof(payload.get("client_proof") or {}, session["actions"])
    if liveness < 0.70 or quality < 0.60:
        session["status"] = "failed"
        return 422, {"ok": False, "verified": False, "liveness_score": round(liveness, 3), "face_quality_score": round(quality, 3), "reasons": reasons}
    credential_id = "cred_" + secrets.token_urlsafe(18)
    expiry = now() + TOKEN_TTL_SECONDS
    claims = {
        "real_human": True,
        "face_verified": "face_verified" in session["claims"],
        "liveness_verified": True,
        "duplicate_risk": "low",
    }
    claims = {k: v for k, v in claims.items() if k in session["claims"] or k == "duplicate_risk"}
    pairwise_id = pairwise_subject_id(session["user_id"], DEMO_PARTNER_ID)
    token_payload = {
        "iss": ISSUER,
        "aud": f"partner:{DEMO_PARTNER_ID}",
        "sub": pairwise_id,
        "jti": credential_id,
        "iat": now(),
        "exp": expiry,
        "assurance_level": session["requested_level"],
        "claims": claims,
        "privacy": {"raw_face_shared_with_partner": False, "face_embedding_shared_with_partner": False, "pairwise_subject_id": True},
    }
    session["status"] = "verified"
    return 200, {"ok": True, "verified": True, "credential_id": credential_id, "assurance_level": session["requested_level"], "claims": claims, "partner_token": sign_token(token_payload), "expires_at": utc_iso(expiry), "demo_partner": {"partner_app_id": DEMO_PARTNER_ID, "access_code": DEMO_PARTNER_CODE}}


def verify_partner_token(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    token = payload.get("token")
    partner_app_id = payload.get("partner_app_id") or DEMO_PARTNER_ID
    access_code = payload.get("access_code") or ""
    if not token:
        return public_error("token is required")
    if not partner_is_valid(partner_app_id, access_code):
        return public_error("Invalid partner credentials", 401)
    valid, token_payload, message = verify_token(token)
    if not valid or not token_payload:
        return 401, {"ok": False, "valid": False, "error": message}
    if token_payload.get("aud") != f"partner:{partner_app_id}":
        return 403, {"ok": False, "valid": False, "error": "Token audience does not match partner"}
    return 200, {"ok": True, "valid": True, "issuer": token_payload.get("iss"), "pairwise_subject_id": token_payload.get("sub"), "assurance_level": token_payload.get("assurance_level"), "claims": token_payload.get("claims"), "privacy": token_payload.get("privacy"), "expires_at": utc_iso(int(token_payload.get("exp")))}


def health() -> tuple[int, dict[str, Any]]:
    return 200, {"ok": True, "app": APP_NAME, "issuer": ISSUER, "demo_mode": DEMO_MODE, "time": utc_iso()}


ROUTES_POST = {"/v1/verification/session": create_session, "/v1/verification/submit": submit_verification, "/v1/partner/verify-token": verify_partner_token}
ROUTES_GET = {"/v1/health": health}


class NgozenHandler(BaseHTTPRequestHandler):
    server_version = "NgozenMVP/0.1"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode()) if length else {}

    def do_OPTIONS(self) -> None:
        self._send_json(200, {"ok": True})

    def do_GET(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path in ROUTES_GET:
            status, payload = ROUTES_GET[path]()
            self._send_json(status, payload)
        elif path in {"/", "/index.html"}:
            self._send_file(PUBLIC_DIR / "index.html")
        elif path == "/app.js":
            self._send_file(PUBLIC_DIR / "app.js")
        elif path == "/style.css":
            self._send_file(PUBLIC_DIR / "style.css")
        elif path == "/sdk/ngozen-web.js":
            self._send_file(SDK_DIR / "ngozen-web.js")
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path not in ROUTES_POST:
            self._send_json(404, {"ok": False, "error": "Route not found"})
            return
        try:
            status, response = ROUTES_POST[path](self._read_json())
            self._send_json(status, response)
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "error": "Invalid JSON"})
        except Exception as exc:
            self._send_json(500, {"ok": False, "error": f"Server error: {exc}"})

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{utc_iso()}] {self.address_string()} - {fmt % args}")


def main() -> None:
    print(f"{APP_NAME} MVP running on http://localhost:{PORT}")
    print(f"DEMO_MODE={DEMO_MODE}. Demo partner: {DEMO_PARTNER_ID} / {DEMO_PARTNER_CODE}")
    ThreadingHTTPServer((HOST, PORT), NgozenHandler).serve_forever()


if __name__ == "__main__":
    main()
