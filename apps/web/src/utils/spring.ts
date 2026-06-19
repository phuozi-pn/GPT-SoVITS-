/**
 * 物理弹簧力学算法 — 白皮书标准
 * stiffness: 120 — 劲度系数，确保无大幅度死板回弹
 * damping: 14 — 阻尼比，呈现有韧性的空气阻力感
 */
export type SpringState = { value: number; velocity: number };

export function springStep(
  state: SpringState,
  target: number,
  dt: number,
  stiffness = 120,
  damping = 14,
): SpringState {
  const force = stiffness * (target - state.value);
  const velocity = (state.velocity + force * dt) * Math.exp(-damping * dt);
  const value = state.value + velocity * dt;
  return { value, velocity };
}

/** 带磁吸效应的弹簧步进 — 接近目标 5% 范围内自动吸附 */
export function springStepWithSnap(
  state: SpringState,
  target: number,
  dt: number,
  stiffness = 120,
  damping = 14,
  snapThreshold = 0.05,
): SpringState {
  const result = springStep(state, target, dt, stiffness, damping);
  if (Math.abs(result.value - target) < snapThreshold * Math.abs(target)) {
    result.value = target;
    result.velocity = 0;
  }
  return result;
}

/** Map normalized level 0..1 to VU angle in radians (-50deg .. +50deg from vertical). */
export function levelToVuAngle(level: number): number {
  const clamped = Math.max(0, Math.min(1, level));
  const db = -20 + clamped * 23; // -20 .. +3
  const t = (db + 20) / 23;
  const deg = -50 + t * 100;
  return (deg * Math.PI) / 180;
}

export function levelToDb(level: number): number {
  return -20 + Math.max(0, Math.min(1, level)) * 23;
}
