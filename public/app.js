const $ = (id) => document.getElementById(id);
const state = {
  session: null,
  stream: null,
  metrics: [],
  completedActions: [],
  currentActionIndex: 0,
  faceDetector: null,
  cameraPermission: false,
  token: ""
};

const actionLabels = {
  blink: "Blink once, then capture metric.",
  turn_head_left: "Turn your head slightly left, then capture metric.",
  turn_head_right: "Turn your head slightly right, then capture metric.",
  smile: "Smile briefly, then capture metric.",
  look_up: "Look slightly up, then capture metric."
};

function pretty(obj) { return JSON.stringify(obj, null, 2); }

function selectedClaims() {
  return Array.from(document.querySelectorAll('.claims input:checked')).map(x => x.value);
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const data = await res.json();
  if (!res.ok) throw Object.assign(new Error(data.error || 'Request failed'), { data });
  return data;
}

async function createSession() {
  try {
    const data = await postJSON('/v1/verification/session', {
      email: $('email').value || undefined,
      requested_level: 'L2',
      claims: selectedClaims(),
      retention_mode: 'delete_raw_after_verification'
    });
    state.session = data;
    state.completedActions = [];
    state.metrics = [];
    state.currentActionIndex = 0;
    $('sessionOut').textContent = pretty(data);
    updateChallenge();
  } catch (err) {
    $('sessionOut').textContent = pretty(err.data || { error: err.message });
  }
}

async function startCamera() {
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
    $('video').srcObject = state.stream;
    state.cameraPermission = true;

    if ('FaceDetector' in window) {
      state.faceDetector = new FaceDetector({ fastMode: true, maxDetectedFaces: 2 });
      $('cameraOut').textContent = 'Camera started. Browser FaceDetector is available.';
    } else {
      $('cameraOut').textContent = 'Camera started. Browser FaceDetector is unavailable here; production should use a certified liveness provider.';
    }
  } catch (err) {
    $('cameraOut').textContent = `Camera error: ${err.message}`;
  }
}

function drawVideoToCanvas() {
  const video = $('video');
  const canvas = $('canvas');
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return ctx;
}

function qualityMetrics(ctx) {
  const { width, height } = ctx.canvas;
  const image = ctx.getImageData(0, 0, width, height);
  const data = image.data;
  let brightness = 0;
  let samples = 0;
  for (let i = 0; i < data.length; i += 16) {
    const r = data[i], g = data[i + 1], b = data[i + 2];
    brightness += (r + g + b) / 3;
    samples += 1;
  }
  brightness = brightness / Math.max(samples, 1);

  let diff = 0;
  let count = 0;
  for (let y = 2; y < height - 2; y += 8) {
    for (let x = 2; x < width - 2; x += 8) {
      const idx = (y * width + x) * 4;
      const idx2 = (y * width + x + 2) * 4;
      const l1 = (data[idx] + data[idx + 1] + data[idx + 2]) / 3;
      const l2 = (data[idx2] + data[idx2 + 1] + data[idx2 + 2]) / 3;
      diff += Math.abs(l1 - l2);
      count += 1;
    }
  }
  return { brightness: Math.round(brightness * 10) / 10, sharpness: Math.round((diff / Math.max(count, 1)) * 10) / 10 };
}

async function detectFaces(canvas) {
  if (!state.faceDetector) return { face_detected: false, face_count: 0, boxes: [] };
  try {
    const faces = await state.faceDetector.detect(canvas);
    const ctx = canvas.getContext('2d');
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#91f2d3';
    faces.forEach(face => {
      const b = face.boundingBox;
      ctx.strokeRect(b.x, b.y, b.width, b.height);
    });
    return {
      face_detected: faces.length > 0,
      face_count: faces.length,
      boxes: faces.map(f => ({
        x: Math.round(f.boundingBox.x),
        y: Math.round(f.boundingBox.y),
        width: Math.round(f.boundingBox.width),
        height: Math.round(f.boundingBox.height)
      }))
    };
  } catch (err) {
    return { face_detected: false, face_count: 0, boxes: [], detection_error: err.message };
  }
}

async function captureMetric() {
  if (!state.stream) {
    $('cameraOut').textContent = 'Start the camera first.';
    return;
  }
  const ctx = drawVideoToCanvas();
  const face = await detectFaces(ctx.canvas);
  const quality = qualityMetrics(ctx);
  const action = state.session?.challenge_actions?.[state.currentActionIndex] || 'center';
  const metric = {
    action,
    captured_at: new Date().toISOString(),
    ...face,
    quality
  };
  state.metrics.push(metric);
  $('cameraOut').textContent = pretty({ last_metric: metric, all_metrics_count: state.metrics.length });
}

function completeCurrentAction() {
  if (!state.session) {
    $('cameraOut').textContent = 'Create a session first.';
    return;
  }
  const action = state.session.challenge_actions[state.currentActionIndex];
  if (action && !state.completedActions.includes(action)) state.completedActions.push(action);
  state.currentActionIndex = Math.min(state.currentActionIndex + 1, state.session.challenge_actions.length);
  updateChallenge();
}

function updateChallenge() {
  const box = $('challengeBox');
  if (!state.session) {
    box.textContent = 'Create a session first.';
    return;
  }
  const action = state.session.challenge_actions[state.currentActionIndex];
  if (!action) {
    box.textContent = 'Challenges completed. Submit proof.';
  } else {
    box.textContent = `${state.currentActionIndex + 1}/${state.session.challenge_actions.length}: ${actionLabels[action] || action}`;
  }
}

function mergedProof() {
  const latest = state.metrics[state.metrics.length - 1] || {};
  const avgBrightness = state.metrics.reduce((s, m) => s + (m.quality?.brightness || 0), 0) / Math.max(state.metrics.length, 1);
  const avgSharpness = state.metrics.reduce((s, m) => s + (m.quality?.sharpness || 0), 0) / Math.max(state.metrics.length, 1);
  const faceDetectedCount = state.metrics.filter(m => m.face_detected).length;
  const bestFaceCount = Math.max(0, ...state.metrics.map(m => m.face_count || 0));
  return {
    camera_permission: state.cameraPermission,
    face_detected: faceDetectedCount > 0 || !state.faceDetector,
    face_count: bestFaceCount || 1,
    completed_actions: state.completedActions,
    quality: {
      brightness: Math.round(avgBrightness * 10) / 10 || latest.quality?.brightness || 0,
      sharpness: Math.round(avgSharpness * 10) / 10 || latest.quality?.sharpness || 0
    },
    browser_face_detector_available: Boolean(state.faceDetector),
    note: 'No raw image, video, or face embedding is sent by this demo client.'
  };
}

async function submitProof() {
  if (!state.session) {
    $('cameraOut').textContent = 'Create a verification session first.';
    return;
  }
  try {
    const proof = mergedProof();
    const data = await postJSON('/v1/verification/submit', {
      session_id: state.session.session_id,
      client_proof: proof
    });
    state.token = data.partner_token || '';
    $('tokenBox').value = state.token;
    $('cameraOut').textContent = pretty(data);
  } catch (err) {
    $('cameraOut').textContent = pretty(err.data || { error: err.message });
  }
}

async function verifyToken() {
  const token = $('tokenBox').value.trim();
  if (!token) {
    $('partnerOut').textContent = 'No token yet. Complete verification first.';
    return;
  }
  try {
    const data = await postJSON('/v1/partner/verify-token', {
      token,
      partner_app_id: $('partnerId').value.trim(),
      access_code: $('partnerKey').value.trim()
    });
    $('partnerOut').textContent = pretty(data);
  } catch (err) {
    $('partnerOut').textContent = pretty(err.data || { error: err.message });
  }
}

$('startSession').addEventListener('click', createSession);
$('startCamera').addEventListener('click', startCamera);
$('captureMetric').addEventListener('click', captureMetric);
$('completeAction').addEventListener('click', completeCurrentAction);
$('submitProof').addEventListener('click', submitProof);
$('verifyToken').addEventListener('click', verifyToken);
