# Ngozen Web SDK

Partner apps use this SDK to verify signed proof tokens. They should never receive selfie images, video, or face embeddings.

```js
import NgozenClient from './ngozen-web.js';

const ngozen = new NgozenClient({ baseUrl: 'https://your-ngozen-api.example.com' });

const verification = await ngozen.verifyPartnerToken({
  token,
  partnerAppId: 'demo_partner_app',
  apiKey: process.env.NGOZEN_PARTNER_KEY
});

if (verification.valid && verification.claims.real_human) {
  // Show a "Verified Human — Face Private" badge.
}
```
