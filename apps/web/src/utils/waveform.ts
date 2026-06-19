/** Deterministic pseudo-random from seed (LCG). */
export function createSeededRandom(seed: number): () => number {
  let state = Math.abs(Math.floor(seed)) % 2147483647;
  if (state <= 0) state += 2147483646;
  return () => {
    state = (state * 16807) % 2147483647;
    return (state - 1) / 2147483646;
  };
}

/** Hash string to numeric seed for stable waveform shapes. */
export function hashSeed(input: string): number {
  let h = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function generateBarHeights(bars: number, seed: number, min = 0.1, max = 1): number[] {
  const rand = createSeededRandom(seed);
  const heights: number[] = [];
  for (let i = 0; i < bars; i += 1) {
    const wave = 0.55 + 0.45 * Math.sin(i * 0.35 + seed * 0.001);
    heights.push(min + rand() * (max - min) * wave);
  }
  return heights;
}

export type DrawBarsOptions = {
  width: number;
  height: number;
  barWidth: number;
  gap: number;
  color: string;
  mutedColor?: string;
  progress?: number;
  mirror?: boolean;
  heights: number[];
  backdrop?: boolean;
};

export function drawWaveBackdrop(ctx: CanvasRenderingContext2D, width: number, height: number): void {
  const bg = ctx.createLinearGradient(0, 0, 0, height);
  bg.addColorStop(0, "rgba(10, 10, 15, 0.95)");
  bg.addColorStop(0.5, "rgba(14, 16, 24, 0.88)");
  bg.addColorStop(1, "rgba(10, 10, 15, 0.95)");
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
  ctx.lineWidth = 1;
  const gridStep = Math.max(24, Math.floor(height / 4));
  for (let y = gridStep; y < height; y += gridStep) {
    ctx.beginPath();
    ctx.moveTo(0, y + 0.5);
    ctx.lineTo(width, y + 0.5);
    ctx.stroke();
  }

  ctx.strokeStyle = "rgba(34, 211, 238, 0.12)";
  ctx.beginPath();
  ctx.moveTo(0, height / 2 + 0.5);
  ctx.lineTo(width, height / 2 + 0.5);
  ctx.stroke();

  const vignette = ctx.createRadialGradient(width / 2, height / 2, height * 0.2, width / 2, height / 2, width * 0.65);
  vignette.addColorStop(0, "rgba(0,0,0,0)");
  vignette.addColorStop(1, "rgba(0,0,0,0.45)");
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, width, height);
}

function roundRectPath(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
): void {
  const radius = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + w - radius, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
  ctx.lineTo(x + w, y + h - radius);
  ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
  ctx.lineTo(x + radius, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

export function drawBars(ctx: CanvasRenderingContext2D, options: DrawBarsOptions): void {
  const { width, height, barWidth, gap, color, mutedColor, progress = 1, mirror, heights, backdrop = true } =
    options;
  const count = heights.length;
  const step = barWidth + gap;
  const totalWidth = count * step - gap;
  const offsetX = (width - totalWidth) / 2;

  ctx.clearRect(0, 0, width, height);
  if (backdrop) drawWaveBackdrop(ctx, width, height);

  for (let i = 0; i < count; i += 1) {
    const x = offsetX + i * step;
    const h = heights[i] * height * 0.82;
    const y = (height - h) / 2;
    const barProgress = progress * count;
    const played = i < barProgress;

    if (played) {
      ctx.shadowColor = "rgba(34, 211, 238, 0.55)";
      ctx.shadowBlur = 8;
      const grad = ctx.createLinearGradient(x, y + h, x, y);
      grad.addColorStop(0, "rgba(8, 145, 178, 0.85)");
      grad.addColorStop(0.45, color);
      grad.addColorStop(1, "rgba(165, 243, 252, 0.95)");
      ctx.fillStyle = grad;
    } else {
      ctx.shadowBlur = 0;
      ctx.fillStyle = mutedColor ?? "rgba(255,255,255,0.1)";
    }

    roundRectPath(ctx, x, y, barWidth, h, barWidth / 2);
    ctx.fill();
    ctx.shadowBlur = 0;

    if (mirror) {
      const mh = h * 0.32;
      ctx.globalAlpha = played ? 0.28 : 0.1;
      ctx.fillStyle = played ? color : "rgba(255,255,255,0.08)";
      roundRectPath(ctx, x, height - mh - 3, barWidth, mh, barWidth / 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    }
  }

  if (progress > 0 && progress < 1) {
    const px = offsetX + progress * totalWidth;
    ctx.strokeStyle = "rgba(165, 243, 252, 0.95)";
    ctx.lineWidth = 2;
    ctx.shadowColor = "rgba(34, 211, 238, 0.8)";
    ctx.shadowBlur = 12;
    ctx.beginPath();
    ctx.moveTo(px, 6);
    ctx.lineTo(px, height - 6);
    ctx.stroke();
    ctx.shadowBlur = 0;

    ctx.fillStyle = "rgba(34, 211, 238, 0.95)";
    ctx.beginPath();
    ctx.arc(px, height / 2, 4, 0, Math.PI * 2);
    ctx.fill();
  }
}

export function drawScrollingBars(
  ctx: CanvasRenderingContext2D,
  options: Omit<DrawBarsOptions, "progress"> & { phase: number },
): void {
  const { phase, heights, ...rest } = options;
  const shifted = heights.map((h, i) => {
    const wobble = 0.18 * Math.sin(phase * 0.08 + i * 0.4);
    return Math.min(1, Math.max(0.06, h + wobble));
  });
  drawBars(ctx, { ...rest, heights: shifted, progress: 1 });
}
