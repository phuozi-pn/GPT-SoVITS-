<script setup lang="ts">
import { ref } from "vue";
import { formatPriceCents } from "@/api/catalog";
import type { FeedItem } from "@/api/community";
import InkWaveformMini from "@/modules/social/components/InkWaveformMini.vue";
import { formatTimeAgo } from "@/utils/timeAgo";

withDefaults(
  defineProps<{
    items: FeedItem[];
    mode?: "interactive" | "readonly";
    loadingMore?: boolean;
    nextBefore?: string | null;
    gallery?: boolean;
  }>(),
  { mode: "interactive", gallery: false },
);

const emit = defineEmits<{
  like: [postId: string];
  catalogPick: [catalogId: string];
  creator: [userId: string];
  message: [userId: string, voiceTitle?: string];
  loadMore: [];
}>();

const imprinted = ref<Set<string>>(new Set());
const hoverId = ref("");

function sealChar(name: string) {
  return name.trim().charAt(0) || "声";
}

function titleOf(it: FeedItem) {
  if (it.type === "event") return String(it.event.payload.title ?? "未命名音色");
  return it.post.body.slice(0, 24) + (it.post.body.length > 24 ? "…" : "");
}

function itemKey(it: FeedItem) {
  return it.type === "event" ? it.event.target_id : it.post.post_id;
}

function isImprinted(it: FeedItem) {
  const key = itemKey(it);
  if (it.type === "post" && it.post.liked_by_me) return true;
  return imprinted.value.has(key);
}

function onImprint(it: FeedItem) {
  const key = itemKey(it);
  if (imprinted.value.has(key)) return;
  const next = new Set(imprinted.value);
  next.add(key);
  imprinted.value = next;
  if (it.type === "post") emit("like", it.post.post_id);
}

function onOpen(it: FeedItem) {
  if (it.type === "event") emit("catalogPick", it.event.target_id);
  else emit("creator", it.post.author_user_id);
}
</script>

<template>
  <div class="feed-stream" :class="{ 'feed-stream--gallery': gallery }">
    <article
      v-for="it in items"
      :key="it.created_at + '-' + it.type"
      class="feed-card feed-card--stream"
      :class="{ 'feed-card--gallery': gallery, 'feed-card--hover': gallery && hoverId === itemKey(it) }"
      @mouseenter="hoverId = itemKey(it)"
      @mouseleave="hoverId = ''"
    >
      <div v-if="gallery" class="gallery-scroll" @click="onOpen(it)">
        <header class="gallery-scroll__head">
          <span
            class="scroll-seal gallery-scroll__seal"
            :class="{ 'gallery-scroll__seal--marked': isImprinted(it) }"
            aria-hidden="true"
          >
            {{ sealChar(it.type === 'event' ? it.event.actor_display_name : it.post.author_display_name) }}
          </span>
          <div class="gallery-scroll__meta">
            <h3 class="gallery-scroll__title">{{ titleOf(it) }}</h3>
            <time class="gallery-scroll__time">
              {{ formatTimeAgo(it.type === 'event' ? it.event.created_at : it.post.created_at) }}
            </time>
          </div>
          <span class="gallery-scroll__scroll-bar" aria-hidden="true" />
        </header>
        <InkWaveformMini :active="hoverId === itemKey(it)" :width="140" :height="24" />
        <div class="gallery-scroll__foot">
          <button
            v-if="mode === 'interactive'"
            type="button"
            class="gallery-imprint"
            :class="{ 'gallery-imprint--on': isImprinted(it) }"
            :aria-pressed="isImprinted(it)"
            @click.stop="onImprint(it)"
          >
            {{ isImprinted(it) ? "已收藏" : "收藏" }}
          </button>
          <span v-if="it.type === 'event'" class="hint gallery-scroll__price">
            {{ formatPriceCents(Number(it.event.payload.price_cents ?? 0)) }}
          </span>
        </div>
      </div>

      <template v-else>
        <template v-if="it.type === 'event'">
          <header class="feed-card__head">
            <div class="feed-card__meta">
              <strong class="feed-card__title">
                {{ it.event.actor_display_name }}
                <span class="feed-card__type">上新</span>
              </strong>
              <time class="hint">{{ formatTimeAgo(it.event.created_at) }}</time>
            </div>
          </header>
          <div class="feed-card__body">
            <button type="button" class="voice-pill" @click="emit('catalogPick', it.event.target_id)">
              {{ String(it.event.payload.title ?? "未命名音色") }}
              <span class="hint">{{ formatPriceCents(Number(it.event.payload.price_cents ?? 0)) }}</span>
            </button>
          </div>
        </template>
        <template v-else>
          <header class="feed-card__head">
            <div class="feed-card__meta">
              <strong class="feed-card__title">{{ it.post.author_display_name }}</strong>
              <time class="hint">{{ formatTimeAgo(it.post.created_at) }}</time>
            </div>
          </header>
          <div class="feed-card__body">
            <p class="feed-card__text">{{ it.post.body }}</p>
            <div v-if="mode === 'interactive'" class="feed-card__actions row-actions">
              <button type="button" class="like-btn" @click="emit('like', it.post.post_id)">
                <span :class="{ 'like-btn__on': it.post.liked_by_me }">赞</span>
                <span class="hint">{{ it.post.like_count }}</span>
              </button>
            </div>
          </div>
        </template>
      </template>
    </article>

    <div v-if="nextBefore !== undefined" class="feed-stream__more">
      <button
        v-if="nextBefore"
        type="button"
        class="text-action"
        :disabled="loadingMore"
        @click="emit('loadMore')"
      >
        {{ loadingMore ? "展卷中…" : "继续展卷" }}
      </button>
      <p v-else-if="items.length && gallery" class="gallery-void-end">
        <span class="scroll-epigraph">已浏览全部内容</span>
      </p>
      <p v-else-if="items.length" class="hint">没有更多了</p>
    </div>
  </div>
</template>
