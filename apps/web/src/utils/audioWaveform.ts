import { resolveMediaUrl } from "@/config";

type PeakCacheKey = string;

const peakCache = new Map<PeakCacheKey, Float32Array>();

/** Min/max pairs per bucket — length = pointCount * 2 */
export function extractPeaks(channel: Float32Array, pointCount: number): Float32Array {
  const peaks = new Float32Array(pointCount * 2);
  const blockSize = Math.max(1, Math.floor(channel.length / pointCount));

  for (let i = 0; i < pointCount; i += 1) {
    const start = i * blockSize;
    const end = Math.min(start + blockSize, channel.length);
    let min = 0;
    let max = 0;
    for (let j = start; j < end; j += 1) {
      const v = channel[j];
      if (v < min) min = v;
      if (v > max) max = v;
    }
    peaks[i * 2] = min;
    peaks[i * 2 + 1] = max;
  }
  return peaks;
}

export async function fetchAudioPeaks(src: string, pointCount: number): Promise<Float32Array> {
  const resolved = resolveMediaUrl(src);
  const cacheKey = `${resolved}@${pointCount}`;
  const cached = peakCache.get(cacheKey);
  if (cached) return cached;

  const response = await fetch(resolved, { credentials: "include" });
  if (!response.ok) {
    throw new Error(`无法加载音频 (${response.status})`);
  }

  const arrayBuffer = await response.arrayBuffer();
  const audioContext = new AudioContext();
  try {
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer.slice(0));
    const channel = audioBuffer.getChannelData(0);
    const peaks = extractPeaks(channel, pointCount);
    peakCache.set(cacheKey, peaks);
    return peaks;
  } finally {
    await audioContext.close();
  }
}

export function peaksToScopePoints(
  width: number,
  height: number,
  peaks: Float32Array,
  progress = 1,
): { x: number; y: number }[] {
  const bucketCount = peaks.length / 2;
  if (bucketCount < 2 || width <= 0) return [];

  const mid = height / 2;
  const ampScale = height * 0.42;
  const visibleBuckets = Math.max(2, Math.floor(bucketCount * Math.min(1, Math.max(0, progress))));
  const points: { x: number; y: number }[] = [];

  for (let i = 0; i < visibleBuckets; i += 1) {
    const x = (i / (bucketCount - 1)) * width;
    const min = peaks[i * 2];
    const max = peaks[i * 2 + 1];
    const y = mid + ((min + max) / 2) * ampScale;
    points.push({ x, y });
  }
  return points;
}

export function timeDomainToScopePoints(
  width: number,
  height: number,
  data: Uint8Array,
): { x: number; y: number }[] {
  if (width <= 0 || data.length < 2) return [];

  const mid = height / 2;
  const ampScale = height * 0.42;
  const points: { x: number; y: number }[] = [];
  const steps = Math.max(2, Math.floor(width));

  for (let i = 0; i <= steps; i += 1) {
    const x = (i / steps) * width;
    const idx = Math.min(data.length - 1, Math.floor((i / steps) * (data.length - 1)));
    const v = (data[idx] - 128) / 128;
    points.push({ x, y: mid - v * ampScale });
  }
  return points;
}

export function idleScopePoints(width: number, height: number): { x: number; y: number }[] {
  const mid = height / 2;
  return [
    { x: 0, y: mid },
    { x: width, y: mid },
  ];
}
