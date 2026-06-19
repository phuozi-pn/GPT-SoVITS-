<script setup lang="ts">
defineProps<{
  asideTitle?: string;
  asideSubtitle?: string;
  asideLabel?: string;
  asideCount?: number;
  fill?: boolean;
}>();
</script>

<template>
  <div class="workspace" :class="{ 'workspace--fill': fill }">
    <div class="workspace__main">
      <slot />
    </div>
    <aside v-if="$slots.aside" class="workspace__aside rack-panel">
      <span v-for="n in 4" :key="n" class="rack-screw" :class="`rack-screw--${['tl', 'tr', 'bl', 'br'][n - 1]}`" aria-hidden="true" />
      <header class="workspace__aside-head">
        <div>
          <p v-if="asideLabel" class="rack-label">{{ asideLabel }}</p>
          <h3 class="workspace__aside-title">{{ asideTitle ?? "侧栏" }}</h3>
          <p v-if="asideSubtitle" class="workspace__aside-sub">{{ asideSubtitle }}</p>
        </div>
        <div class="workspace__aside-actions">
          <span v-if="asideCount != null" class="workspace__count rack-label">{{ asideCount }}</span>
          <slot name="aside-actions" />
        </div>
      </header>
      <div class="workspace__aside-body">
        <slot name="aside" />
      </div>
    </aside>
  </div>
</template>

<style scoped>
.workspace {
  display: grid;
  gap: 24px;
}

@media (min-width: 1024px) {
  .workspace {
    grid-template-columns: minmax(0, 1fr) 288px;
    align-items: start;
  }

  .workspace--fill {
    align-items: stretch;
    min-height: 0;
    flex: 1;
  }
}

.workspace__main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 24px;
}

.workspace--fill .workspace__main {
  min-height: 0;
}

.workspace__aside {
  position: relative;
  display: flex;
  max-height: calc(100vh - 160px);
  flex-direction: column;
  overflow: hidden;
}

.workspace--fill .workspace__aside {
  max-height: none;
}

@media (min-width: 1024px) {
  .workspace__aside {
    position: sticky;
    top: 24px;
  }
}

.workspace__aside-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--color-brushed);
}

.workspace__aside-title {
  margin: 4px 0 0;
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 600;
}

.workspace__aside-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-brushed-dark);
}

.workspace__aside-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
}

.workspace__count {
  padding: 2px 8px;
  border: 1px solid var(--color-brushed);
  border-radius: var(--radius-ui);
  background: var(--bg-tertiary);
}

.workspace__aside-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
</style>
