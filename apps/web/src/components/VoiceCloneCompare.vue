<script setup lang="ts">
import { computed } from "vue";
import VoicePreviewButton from "@/components/VoicePreviewButton.vue";

const props = withDefaults(
  defineProps<{
    sourceAudioUrl?: string | null;
    cloneDemoAudioUrl?: string | null;
    layout?: "row" | "stack";
    compact?: boolean;
    showHeading?: boolean;
  }>(),
  {
    layout: "row",
    compact: false,
    showHeading: true,
  },
);

const hasSource = computed(() => Boolean(props.sourceAudioUrl));
const hasSynth = computed(() => Boolean(props.cloneDemoAudioUrl));
</script>

<template>
  <section
    class="clone-compare"
    :class="{
      'clone-compare--stack': layout === 'stack',
      'clone-compare--compact': compact,
    }"
    aria-label="原素材与克隆合成对比"
  >
    <header v-if="showHeading && !compact" class="clone-compare__panel-head">
      <span class="clone-compare__eyebrow">成果对比</span>
      <p class="clone-compare__lead">左侧为训练前原声，右侧为平台克隆合成样例</p>
    </header>

    <div class="clone-compare__grid">
      <article
        class="clone-compare__card clone-compare__card--source"
        :class="{ 'clone-compare__card--empty': !hasSource }"
      >
        <div class="clone-compare__card-top">
          <span class="clone-compare__badge">A · 原素材</span>
          <strong class="clone-compare__title">训练前干声</strong>
          <p v-if="!compact" class="clone-compare__hint">你上传的参考 / 训练用音频</p>
        </div>
        <div class="clone-compare__play">
          <VoicePreviewButton
            :src="sourceAudioUrl"
            :size="compact ? 'md' : 'lg'"
            disabled-hint="暂无原声"
          />
        </div>
      </article>

      <div class="clone-compare__bridge" aria-hidden="true">
        <span class="clone-compare__bridge-line" />
        <span class="clone-compare__bridge-chip">克隆</span>
        <span class="clone-compare__bridge-line" />
      </div>

      <article
        class="clone-compare__card clone-compare__card--synth"
        :class="{ 'clone-compare__card--empty': !hasSynth }"
      >
        <div class="clone-compare__card-top">
          <span class="clone-compare__badge">B · 合成样例</span>
          <strong class="clone-compare__title">克隆成果</strong>
          <p v-if="!compact" class="clone-compare__hint">平台用该音色生成的 AI 语音</p>
        </div>
        <div class="clone-compare__play">
          <VoicePreviewButton
            :src="cloneDemoAudioUrl"
            :size="compact ? 'md' : 'lg'"
            disabled-hint="完成试听或测评后显示"
          />
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.clone-compare {
  display: grid;
  gap: 12px;
  padding: 14px 16px;
  border-radius: calc(var(--radius-ui) + 4px);
  border: 1px solid var(--border-glow);
  background:
    radial-gradient(120% 80% at 0% 0%, rgb(148 163 184 / 0.08), transparent 55%),
    radial-gradient(120% 80% at 100% 0%, rgb(196 146 58 / 0.07), transparent 55%),
    var(--bg-surface-muted);
}

.clone-compare--compact {
  padding: 12px 14px;
  gap: 10px;
}

.clone-compare__panel-head {
  display: grid;
  gap: 4px;
}

.clone-compare__eyebrow {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--color-brushed-dark);
}

.clone-compare__lead {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--color-ink-muted);
}

.clone-compare__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: 12px;
  align-items: stretch;
}

.clone-compare--stack .clone-compare__grid {
  grid-template-columns: 1fr;
}

.clone-compare__card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 14px;
  min-height: 148px;
  padding: 14px 16px;
  border-radius: calc(var(--radius-ui) + 2px);
  border: 1px solid transparent;
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.05);
}

.clone-compare--compact .clone-compare__card {
  min-height: 120px;
  padding: 12px 14px;
  gap: 10px;
}

.clone-compare__card--source {
  border-color: color-mix(in srgb, #94a3b8 32%, transparent);
  background: linear-gradient(
    165deg,
    color-mix(in srgb, #94a3b8 12%, var(--bg-surface)),
    var(--bg-surface-muted)
  );
}

.clone-compare__card--source .clone-compare__badge {
  background: color-mix(in srgb, #94a3b8 18%, transparent);
  color: #c8d2e0;
}

.clone-compare__card--synth {
  border-color: color-mix(in srgb, var(--theme-warm) 38%, transparent);
  background: linear-gradient(
    165deg,
    color-mix(in srgb, var(--theme-warm) 14%, var(--bg-surface)),
    var(--bg-surface-muted)
  );
}

.clone-compare__card--synth .clone-compare__badge {
  background: color-mix(in srgb, var(--theme-warm) 22%, transparent);
  color: #f0d4a8;
}

.clone-compare__card--empty {
  opacity: 0.88;
}

.clone-compare__card-top {
  display: grid;
  gap: 6px;
}

.clone-compare__badge {
  display: inline-flex;
  width: fit-content;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.clone-compare__title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 600;
  line-height: 1.25;
  color: var(--color-ink);
}

.clone-compare--compact .clone-compare__title {
  font-size: 14px;
}

.clone-compare__hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--color-ink-muted);
}

.clone-compare__play {
  display: flex;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid rgb(255 255 255 / 0.06);
}

.clone-compare__bridge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 52px;
  padding: 0 2px;
}

.clone-compare--stack .clone-compare__bridge {
  flex-direction: row;
  min-width: 0;
  padding: 2px 0;
}

.clone-compare__bridge-line {
  flex: 1;
  width: 1px;
  min-height: 18px;
  background: linear-gradient(
    to bottom,
    transparent,
    color-mix(in srgb, var(--theme-warm) 45%, transparent),
    transparent
  );
}

.clone-compare--stack .clone-compare__bridge-line {
  width: auto;
  height: 1px;
  min-height: 0;
  min-width: 24px;
  background: linear-gradient(
    to right,
    transparent,
    color-mix(in srgb, var(--theme-warm) 45%, transparent),
    transparent
  );
}

.clone-compare__bridge-chip {
  display: grid;
  place-items: center;
  min-width: 40px;
  height: 40px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--theme-warm) 30%, transparent);
  background: color-mix(in srgb, var(--theme-warm) 10%, var(--bg-surface));
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--theme-warm);
  box-shadow: 0 4px 14px rgb(0 0 0 / 0.1);
}

.clone-compare--compact .clone-compare__bridge-chip {
  min-width: 34px;
  height: 34px;
  font-size: 10px;
}

@media (max-width: 720px) {
  .clone-compare:not(.clone-compare--stack) .clone-compare__grid {
    grid-template-columns: 1fr;
  }

  .clone-compare:not(.clone-compare--stack) .clone-compare__bridge {
    flex-direction: row;
    padding: 2px 0;
  }

  .clone-compare:not(.clone-compare--stack) .clone-compare__bridge-line {
    width: auto;
    height: 1px;
    min-height: 0;
    min-width: 28px;
    background: linear-gradient(
      to right,
      transparent,
      color-mix(in srgb, var(--theme-warm) 45%, transparent),
      transparent
    );
  }
}
</style>
