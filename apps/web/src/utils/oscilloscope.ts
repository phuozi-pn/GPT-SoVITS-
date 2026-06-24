import { createSeededRandom, hashSeed } from "@/utils/waveform";

export function drawPaperGrid(ctx: CanvasRenderingContext2D, w: number, h: number): void {
  ctx.fillStyle = "#F2EBE1";
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = "rgba(42, 37, 32, 0.06)";
  ctx.lineWidth = 1;
  const step = 16;
  for (let x = 0; x <= w; x += step) {
    ctx.beginPath();
    ctx.moveTo(x + 0.5, 0);
    ctx.lineTo(x + 0.5, h);
    ctx.stroke();
  }
  for (let y = 0; y <= h; y += step) {
    ctx.beginPath();
    ctx.moveTo(0, y + 0.5);
    ctx.lineTo(w, y + 0.5);
    ctx.stroke();
  }

  ctx.strokeStyle = "rgba(42, 37, 32, 0.12)";
  ctx.beginPath();
  ctx.moveTo(0, h / 2 + 0.5);
  ctx.lineTo(w, h / 2 + 0.5);
  ctx.stroke();
}

/** Dark rack scope — matches Studio / page-surface theme */
export function drawStudioGrid(ctx: CanvasRenderingContext2D, w: number, h: number): void {
  ctx.fillStyle = "rgb(18 21 26 / 0.92)";
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = "rgb(255 255 255 / 0.05)";
  ctx.lineWidth = 1;
  const step = 20;
  for (let x = 0; x <= w; x += step) {
    ctx.beginPath();
    ctx.moveTo(x + 0.5, 0);
    ctx.lineTo(x + 0.5, h);
    ctx.stroke();
  }
  for (let y = 0; y <= h; y += step) {
    ctx.beginPath();
    ctx.moveTo(0, y + 0.5);
    ctx.lineTo(w, y + 0.5);
    ctx.stroke();
  }

  ctx.strokeStyle = "rgb(255 255 255 / 0.08)";
  ctx.beginPath();
  ctx.moveTo(0, h / 2 + 0.5);
  ctx.lineTo(w, h / 2 + 0.5);
  ctx.stroke();
}

export function buildScopePoints(
  width: number,
  height: number,
  seed: number,
  phase: number,
  amplitude: number,
  progress = 1,
): { x: number; y: number }[] {
  const points: { x: number; y: number }[] = [];
  const mid = height / 2;
  const rand = createSeededRandom(seed);
  const steps = Math.max(120, Math.floor(width / 3));
  const visibleWidth = width * progress;

  for (let i = 0; i <= steps; i += 1) {
    const x = (i / steps) * width;
    if (x > visibleWidth) break;
    const t = i / steps;
    const w1 = Math.sin(t * Math.PI * 6 + phase * 0.04) * 0.35;
    const w2 = Math.sin(t * Math.PI * 14 + phase * 0.07 + rand() * 2) * 0.18;
    const w3 = Math.sin(t * Math.PI * 2.5 + phase * 0.02) * 0.25;
    const env = 0.35 + 0.65 * Math.sin(t * Math.PI) ** 0.8;
    const y = mid + (w1 + w2 + w3) * env * amplitude * (height * 0.38);
    points.push({ x, y });
  }
  return points;
}

export function drawScopeCurve(
  ctx: CanvasRenderingContext2D,
  points: { x: number; y: number }[],
  color: string,
  mutedColor: string,
  progress: number,
): void {
  if (points.length < 2) return;
  const split = Math.floor(points.length * progress);

  ctx.lineWidth = 1.75;
  ctx.lineJoin = "round";
  ctx.lineCap = "round";

  ctx.strokeStyle = mutedColor;
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i += 1) ctx.lineTo(points[i].x, points[i].y);
  ctx.stroke();

  if (split > 1) {
    ctx.strokeStyle = color;
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < split; i += 1) ctx.lineTo(points[i].x, points[i].y);
    ctx.stroke();
  }

  if (progress > 0 && progress < 1 && split < points.length) {
    const p = points[split];
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
    ctx.fill();
  }
}

export function seedFromText(text: string): number {
  return hashSeed(text || "scope");
}
