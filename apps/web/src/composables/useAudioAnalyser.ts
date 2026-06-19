import { onUnmounted, ref, type Ref } from "vue";

type AudioGraph = {
  ctx: AudioContext;
  analyser: AnalyserNode;
  timeDomain: Uint8Array;
};

const elementGraphs = new WeakMap<HTMLAudioElement, AudioGraph>();

export function getOrCreateAudioGraph(audio: HTMLAudioElement): AudioGraph {
  const existing = elementGraphs.get(audio);
  if (existing) return existing;

  const ctx = new AudioContext();
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 2048;
  analyser.smoothingTimeConstant = 0.35;

  const source = ctx.createMediaElementSource(audio);
  source.connect(analyser);
  analyser.connect(ctx.destination);

  const graph: AudioGraph = {
    ctx,
    analyser,
    timeDomain: new Uint8Array(analyser.fftSize),
  };
  elementGraphs.set(audio, graph);
  return graph;
}

export async function resumeAudioGraph(audio: HTMLAudioElement): Promise<AudioGraph> {
  const graph = getOrCreateAudioGraph(audio);
  if (graph.ctx.state === "suspended") {
    await graph.ctx.resume();
  }
  return graph;
}

export function readTimeDomain(audio: HTMLAudioElement): Uint8Array | null {
  const graph = elementGraphs.get(audio);
  if (!graph) return null;
  graph.analyser.getByteTimeDomainData(graph.timeDomain);
  return graph.timeDomain;
}

export function useAudioAnalyser(audioRef: Ref<HTMLAudioElement | null>) {
  const isPlaying = ref(false);

  function bindPlaybackHandlers() {
    const audio = audioRef.value;
    if (!audio) return;

    audio.onplay = () => {
      isPlaying.value = true;
      void resumeAudioGraph(audio);
    };
    audio.onpause = () => {
      isPlaying.value = false;
    };
    audio.onended = () => {
      isPlaying.value = false;
    };
  }

  function readLive(): Uint8Array | null {
    const audio = audioRef.value;
    if (!audio || !isPlaying.value) return null;
    return readTimeDomain(audio);
  }

  onUnmounted(() => {
    isPlaying.value = false;
  });

  return { isPlaying, bindPlaybackHandlers, readLive, resumeAudioGraph };
}
