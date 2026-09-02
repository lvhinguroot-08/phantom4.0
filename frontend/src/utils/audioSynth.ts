/**
 * PHANTOM 2.0 Web Audio Synthesizer
 * Zero-dependency procedural tactical audio effects (Cyber beeps, sonar locks, hyperdrive warp chimes).
 * 100% reliable across modern browsers without external audio assets.
 */

let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  if (!audioCtx) {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  if (audioCtx && audioCtx.state === 'suspended') {
    audioCtx.resume().catch(() => {});
  }
  return audioCtx;
}

/**
 * Tactical UI Click/Hover blip
 */
export function playHoverBlip() {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(1200, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1800, ctx.currentTime + 0.04);

    gain.gain.setValueAtTime(0.04, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.04);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start();
    osc.stop(ctx.currentTime + 0.05);
  } catch (_) {}
}

/**
 * Access Granted Multi-Tone Tactical Confirmation
 */
export function playAccessGrantedSound() {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;

    const now = ctx.currentTime;

    // Chord sequence: 587Hz (D5) -> 880Hz (A5) -> 1174Hz (D6) -> 1760Hz (A6)
    const freqs = [587.33, 880.0, 1174.66, 1760.0];

    freqs.forEach((freq, idx) => {
      const startTime = now + idx * 0.06;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = idx === 3 ? 'sine' : 'triangle';
      osc.frequency.setValueAtTime(freq, startTime);

      gain.gain.setValueAtTime(0.08, startTime);
      gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.28);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(startTime);
      osc.stop(startTime + 0.3);
    });
  } catch (_) {}
}

/**
 * Deep Cinematic 3D Camera Warp & Laser Sweep Sound
 */
export function playWarpSound() {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;

    const now = ctx.currentTime;

    // Sub bass sweep
    const subOsc = ctx.createOscillator();
    const subGain = ctx.createGain();
    subOsc.type = 'sine';
    subOsc.frequency.setValueAtTime(110, now);
    subOsc.frequency.exponentialRampToValueAtTime(45, now + 1.2);
    subGain.gain.setValueAtTime(0.15, now);
    subGain.gain.exponentialRampToValueAtTime(0.001, now + 1.2);
    subOsc.connect(subGain);
    subGain.connect(ctx.destination);
    subOsc.start(now);
    subOsc.stop(now + 1.25);

    // Hyperdrive riser
    const riserOsc = ctx.createOscillator();
    const riserGain = ctx.createGain();
    riserOsc.type = 'sawtooth';
    riserOsc.frequency.setValueAtTime(220, now + 0.1);
    riserOsc.frequency.exponentialRampToValueAtTime(2400, now + 1.1);
    riserGain.gain.setValueAtTime(0.01, now + 0.1);
    riserGain.gain.linearRampToValueAtTime(0.07, now + 0.8);
    riserGain.gain.exponentialRampToValueAtTime(0.001, now + 1.15);
    riserOsc.connect(riserGain);
    riserGain.connect(ctx.destination);
    riserOsc.start(now + 0.1);
    riserOsc.stop(now + 1.2);
  } catch (_) {}
}

/**
 * Access Denied Buzz
 */
export function playAccessDeniedSound() {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;

    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(150, now);
    osc.frequency.setValueAtTime(110, now + 0.12);

    gain.gain.setValueAtTime(0.1, now);
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);

    osc.connect(gain);
    gain.connect(ctx.destination);

    osc.start(now);
    osc.stop(now + 0.38);
  } catch (_) {}
}
