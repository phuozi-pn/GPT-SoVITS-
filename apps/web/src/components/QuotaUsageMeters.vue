<script setup lang="ts">
import { computed } from "vue";
import type { QuotaSummary } from "@/types/api";
import { buildQuotaMeters, formatResetLabel } from "@/utils/quotaDisplay";

const props = withDefaults(
  defineProps<{
    quota: QuotaSummary;
    layout?: "panel" | "inline" | "cell";
    metric?: "chars" | "train" | "all";
    showReset?: boolean;
  }>(),
  {
    layout: "panel",
    metric: "all",
    showReset: true,
  },
);

const meters = computed(() => {
  const all = buildQuotaMeters(props.quota);
  if (props.metric === "all") return all;
  return all.filter((m) => m.key === props.metric);
});

const resetLabel = computed(() => formatResetLabel(props.quota.reset_at));
</script>

<template>
  <div
    class="quota-meters"
    :class="{
      'quota-meters--panel': layout === 'panel',
      'quota-meters--inline': layout === 'inline',
      'quota-meters--cell': layout === 'cell',
    }"
    role="group"
    :aria-label="layout === 'cell' ? '用量' : '本月平台用量'"
  >
    <p v-if="layout === 'panel'" class="quota-meters__head">
      <span class="quota-meters__eyebrow">本月额度</span>
      <span v-if="showReset" class="quota-meters__reset">{{ resetLabel }}</span>
    </p>

    <div class="quota-meters__grid">
      <article
        v-for="meter in meters"
        :key="meter.key"
        class="quota-meter"
        :class="`quota-meter--${meter.tone}`"
      >
        <div class="quota-meter__top">
          <span class="quota-meter__label">{{ meter.label }}</span>
          <span class="quota-meter__pct">{{ meter.percent }}%</span>
        </div>

        <div class="quota-meter__track" :aria-hidden="true">
          <span class="quota-meter__fill" :style="{ width: `${meter.percent}%` }" />
        </div>

        <div v-if="layout === 'cell'" class="quota-meter__cell-meta">
          <strong>{{ meter.usedLabel }}</strong>
          <span class="hint">/ {{ meter.limitLabel }}</span>
        </div>
        <div v-else class="quota-meter__stats">
          <div class="quota-meter__stat">
            <span class="quota-meter__stat-k">已用</span>
            <strong>{{ meter.usedLabel }}</strong>
          </div>
          <div class="quota-meter__stat">
            <span class="quota-meter__stat-k">上限</span>
            <strong>{{ meter.limitLabel }}</strong>
          </div>
          <div class="quota-meter__stat">
            <span class="quota-meter__stat-k">剩余</span>
            <strong>{{ meter.remainingLabel }}</strong>
          </div>
        </div>

        <svg
          v-if="layout !== 'cell'"
          class="quota-meter__ring"
          viewBox="0 0 40 40"
          aria-hidden="true"
        >
          <circle class="quota-meter__ring-bg" cx="20" cy="20" r="16" />
          <circle
            class="quota-meter__ring-fill"
            cx="20"
            cy="20"
            r="16"
            :stroke-dasharray="`${meter.percent} 100`"
            pathLength="100"
          />
        </svg>
      </article>
    </div>
  </div>
</template>

<style scoped>
.quota-meters--panel {
  padding: 14px 16px;
  border: 1px solid var(--border-glow);
  border-radius: var(--radius-module);
  background: var(--bg-surface);
  box-shadow: var(--shadow-soft);
}

.quota-meters--inline {
  width: 100%;
}

.quota-meters--inline .quota-meters__grid {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.quota-meters--inline .quota-meter__stats {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.quota-meters--cell .quota-meters__grid {
  display: block;
}

.quota-meters__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px 16px;
  margin: 0 0 12px;
}

.quota-meters__eyebrow {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-brushed-dark);
}

.quota-meters__reset {
  font-size: 12px;
  color: var(--color-ink-muted);
}

.quota-meters__grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.quota-meter {
  position: relative;
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  padding-right: 52px;
  border-radius: calc(var(--radius-ui) + 2px);
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface-muted);
}

.quota-meters--cell .quota-meter {
  padding: 8px 10px;
  padding-right: 10px;
  background: transparent;
  border: none;
}

.quota-meter__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.quota-meter__label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-ink);
}

.quota-meter__pct {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--color-ink-muted);
}

.quota-meter__track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: rgb(0 0 0 / 0.08);
}

.quota-meters--cell .quota-meter__track {
  height: 6px;
}

.quota-meter__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--theme-warm);
  transition: width 0.35s ease;
}

.quota-meter--warn .quota-meter__fill {
  background: var(--color-vu-amber-deep);
}

.quota-meter--danger .quota-meter__fill {
  background: var(--color-danger, #c45c4a);
}

.quota-meter__stats {
  display: grid;
  grid-template-columns: repeat(3, auto);
  gap: 8px 14px;
}

.quota-meter__stat {
  display: grid;
  gap: 2px;
}

.quota-meter__stat-k {
  font-size: 11px;
  color: var(--color-ink-muted);
}

.quota-meter__stat strong {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-ink);
}

.quota-meter__cell-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px;
  font-size: 12px;
}

.quota-meter__cell-meta strong {
  font-weight: 600;
}

.quota-meter__ring {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 36px;
  height: 36px;
  transform: rotate(-90deg);
}

.quota-meter__ring-bg,
.quota-meter__ring-fill {
  fill: none;
  stroke-width: 4;
}

.quota-meter__ring-bg {
  stroke: rgb(0 0 0 / 0.08);
}

.quota-meter__ring-fill {
  stroke: var(--theme-warm);
  stroke-linecap: round;
}

.quota-meter--warn .quota-meter__ring-fill {
  stroke: var(--color-vu-amber-deep);
}

.quota-meter--danger .quota-meter__ring-fill {
  stroke: var(--color-danger, #c45c4a);
}
</style>
