/**
 * Ngozen Web SDK - minimal browser SDK for partner apps.
 *
 * This SDK never asks for a selfie and never handles face data. It only requests
 * signed proof tokens from a Ngozen-compatible verification service.
 */
export class NgozenClient {
  constructor({ baseUrl = '' } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  async createVerificationSession({ email, requestedLevel = 'L2', claims = ['real_human', 'face_verified', 'liveness_verified'] } = {}) {
    return this.#post('/v1/verification/session', {
      email,
      requested_level: requestedLevel,
      claims,
      retention_mode: 'delete_raw_after_verification'
    });
  }

  async submitClientProof({ sessionId, clientProof }) {
    return this.#post('/v1/verification/submit', {
      session_id: sessionId,
      client_proof: clientProof
    });
  }

  async verifyPartnerToken({ token, partnerAppId, apiKey }) {
    return this.#post('/v1/partner/verify-token', {
      token,
      partner_app_id: partnerAppId,
      api_key: apiKey
    });
  }

  async #post(path, body) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) {
      const err = new Error(data.error || `Ngozen request failed: ${res.status}`);
      err.response = data;
      throw err;
    }
    return data;
  }
}

export default NgozenClient;
