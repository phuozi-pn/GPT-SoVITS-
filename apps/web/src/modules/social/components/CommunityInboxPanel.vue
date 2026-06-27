<script setup lang="ts">
import ChatPeerPanel from "@/modules/social/components/ChatPeerPanel.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { QUICK_REPLIES, useCommunityInboxInject } from "@/modules/social/composables/useCommunityInbox";

const {
  DEV_USER_PRESETS,
  peerId,
  peerName,
  draft,
  myUserId,
  loading,
  sending,
  search,
  messagesEl,
  showPeerPanel,
  composerEl,
  devMode,
  filteredConversations,
  totalUnread,
  thread,
  threadRows,
  isSystemRow,
  openThread,
  onSend,
  onComposerKeydown,
  insertQuickReply,
  onMentionVoice,
  goCreator,
  startNewChat,
  showProfileModal,
  goDiscover,
  goCatalog,
  formatTimeAgo,
  formatMessageTime,
} = useCommunityInboxInject();
</script>

<template>
  <div class="inbox">
    <!-- Top bar: stats + actions -->
    <header class="inbox__topbar">
      <div class="inbox__topbar-left">
        <span class="inbox__topbar-title">私信</span>
        <span class="inbox__topbar-meta" v-if="filteredConversations.length">
          共 {{ filteredConversations.length }} 个<template v-if="totalUnread"> · {{ totalUnread }} 未读</template>
        </span>
      </div>
      <div class="inbox__topbar-center">
        <input v-model="search" type="search" placeholder="搜索会话…" class="inbox__search-input" />
      </div>
      <div class="inbox__topbar-right">
        <button type="button" class="text-action" @click="startNewChat">+ 私信</button>
        <button type="button" class="text-action" @click="showProfileModal = true">我的资料</button>
      </div>
    </header>

    <!-- Dev quick chips -->
    <div v-if="devMode" class="inbox__quick">
      <span class="inbox__quick-label">快捷联系（开发）</span>
      <div class="inbox__quick-chips">
        <button
          v-for="u in DEV_USER_PRESETS.filter((p) => p.id !== myUserId)"
          :key="u.id"
          type="button"
          class="sample-btn"
          @click="openThread(u.id, u.label)"
        >
          {{ u.label }}
        </button>
      </div>
    </div>

    <!-- Conversation cards (horizontal scroll) -->
    <nav class="inbox__conv-strip" aria-label="会话列表">
      <button
        v-for="c in filteredConversations"
        :key="c.peer_user_id"
        type="button"
        class="conv-card"
        :class="{ 'conv-card--on': peerId === c.peer_user_id }"
        @click="openThread(c.peer_user_id, c.peer_display_name)"
      >
        <UserAvatar :name="c.peer_display_name" :user-id="c.peer_user_id" size="sm" />
        <span class="conv-card__body">
          <strong>{{ c.peer_display_name }}</strong>
          <span class="conv-card__preview">{{ c.last_message }}</span>
        </span>
        <span class="conv-card__time">{{ formatTimeAgo(c.last_at) }}</span>
        <span v-if="c.unread_count" class="conv-card__badge">{{ c.unread_count }}</span>
      </button>
      <div v-if="!filteredConversations.length" class="inbox__empty-guide">
        <p><strong>还没有会话</strong></p>
        <p class="hint">先去发现页或音色馆找到创作者，点「发私信」后会出现在这里</p>
        <div class="inbox__empty-actions">
          <button type="button" class="btn btn--primary btn--sm" @click="goDiscover">去发现</button>
          <button type="button" class="text-action" style="margin-left: 12px" @click="goCatalog">音色馆</button>
        </div>
      </div>
    </nav>

    <!-- Chat area: only shows when a thread is open -->
    <template v-if="peerId">
      <div class="chat-pane">
        <header class="chat-head">
          <button type="button" class="chat-head__back" @click="openThread('', '')" title="关闭会话">&larr;</button>
          <UserAvatar :name="peerName" :user-id="peerId" size="sm" />
          <div class="chat-head__meta">
            <strong>{{ peerName }}</strong>
          </div>
          <button type="button" class="text-action" @click="goCreator(peerId)">主页</button>
          <button type="button" class="text-action" @click="showPeerPanel = !showPeerPanel">
            {{ showPeerPanel ? "收起" : "资料" }}
          </button>
        </header>

        <div ref="messagesEl" class="chat-messages">
          <div v-if="loading && !thread.length" class="chat-messages__loading">加载中…</div>
          <template v-for="row in threadRows" :key="row.key">
            <div v-if="row.kind === 'divider'" class="chat-divider">
              <span>{{ row.label }}</span>
            </div>
            <div
              v-else-if="!isSystemRow(row.message)"
              class="chat-row"
              :class="{ 'chat-row--mine': row.message.sender_user_id === myUserId }"
            >
              <UserAvatar
                v-if="row.message.sender_user_id !== myUserId"
                :name="peerName"
                size="sm"
                class="chat-row__avatar"
              />
              <div
                class="chat-bubble"
                :class="{ 'chat-bubble--mine': row.message.sender_user_id === myUserId }"
              >
                <p>{{ row.message.body }}</p>
                <span class="chat-bubble__meta">
                  <time>{{ formatMessageTime(row.message.created_at) }}</time>
                  <span
                    v-if="row.message.sender_user_id === myUserId && row.message.read_at"
                    class="chat-bubble__read"
                  >
                    已读
                  </span>
                </span>
              </div>
            </div>
            <div v-else class="chat-system">
              <span>{{ row.message.body.replace(/^【系统】/, "").trim() }}</span>
            </div>
          </template>
        </div>

        <div class="chat-quick">
          <button
            v-for="(q, i) in QUICK_REPLIES"
            :key="i"
            type="button"
            class="chat-quick__chip"
            @click="insertQuickReply(q)"
          >
            {{ q }}
          </button>
        </div>

        <form class="chat-composer" @submit.prevent="onSend">
          <textarea
            ref="composerEl"
            v-model="draft"
            rows="1"
            placeholder="输入消息，Enter 发送，Shift+Enter 换行"
            maxlength="2000"
            @keydown="onComposerKeydown"
          />
          <button type="submit" class="btn btn--primary" :disabled="sending || !draft.trim()">
            {{ sending ? "发送中…" : "发送" }}
          </button>
        </form>
      </div>

      <!-- Peer panel: slide-in overlay on the right -->
      <div v-if="showPeerPanel" class="peer-overlay" @click.self="showPeerPanel = false">
        <ChatPeerPanel
          :peer-user-id="peerId"
          :peer-name="peerName"
          class="inbox__peer"
          @mention-voice="onMentionVoice"
        >
          <template #actions>
            <button type="button" class="text-action" @click="showPeerPanel = false">关闭</button>
          </template>
        </ChatPeerPanel>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* ── Layout ── */
.inbox {
  display: flex;
  flex-direction: column;
  min-height: 520px;
  height: 100%;
  background: var(--bg-surface);
  border-top: 1px solid var(--surface-line, rgb(31 28 25 / 0.06));
}

/* ── Top bar ── */
.inbox__topbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  background: var(--bg-surface);
  border-bottom: 1px solid rgb(212 205 195 / 0.2);
}

.inbox__topbar-left {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-shrink: 0;
}

.inbox__topbar-title {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.inbox__topbar-meta {
  font-size: 11px;
  color: var(--color-ink-muted);
  white-space: nowrap;
}

.inbox__topbar-center {
  flex: 1;
  min-width: 0;
}

.inbox__search-input {
  width: 100%;
  max-width: 280px;
  padding: 5px 10px;
  border: 1px solid rgb(212 205 195 / 0.35);
  border-radius: 6px;
  background: var(--bg-surface-muted);
  font-size: 12px;
  color: var(--color-ink);
  outline: none;
  transition: border-color 0.2s ease;
}

.inbox__search-input::placeholder {
  color: var(--color-ink-muted);
}

.inbox__search-input:focus {
  border-color: var(--color-vu-amber);
  box-shadow: 0 0 0 2px var(--color-vu-amber-glow);
}

.inbox__topbar-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  font-size: 12px;
}

/* ── Quick chips (dev) ── */
.inbox__quick {
  padding: 6px 16px 0;
}

.inbox__quick-label {
  font-size: 10px;
  color: var(--color-ink-muted);
}

.inbox__quick-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

/* ── Conversation strip (horizontal) ── */
.inbox__conv-strip {
  flex-shrink: 0;
  display: flex;
  gap: 16px;
  padding: 18px 24px;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  border-bottom: 1px solid rgb(212 205 195 / 0.15);
  background: var(--bg-surface);
  scrollbar-width: none;
}

.inbox__conv-strip::-webkit-scrollbar {
  display: none;
}

.conv-card {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 14px;
  flex: 0 0 auto;
  width: 460px;
  min-width: 460px;
  max-width: 460px;
  padding: 20px 24px;
  border: 1px solid rgb(212 205 195 / 0.25);
  border-radius: 16px;
  background: var(--bg-surface-glass);
  text-align: left;
  cursor: pointer;
  transition: all 0.18s ease;
  overflow: hidden;
}

.conv-card:hover {
  border-color: rgb(212 146 74 / 0.4);
  background: var(--color-vu-amber-soft);
  transform: translateY(-1px);
  box-shadow: 0 2px 10px rgb(212 146 74 / 0.1);
}

.conv-card--on {
  border-color: var(--color-vu-amber);
  background: linear-gradient(135deg, var(--color-vu-amber-soft), rgb(255 245 230 / 0.7));
  box-shadow: 0 0 0 1px var(--color-vu-amber), 0 2px 12px rgb(212 146 74 / 0.14);
}

.conv-card__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.conv-card__body strong {
  font-size: 16px;
  font-weight: 600;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-ink);
  max-width: 100%;
}

.conv-card__preview {
  font-size: 14px;
  line-height: 1.55;
  color: var(--color-ink-muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.conv-card__time {
  flex-shrink: 0;
  font-size: 13px;
  color: var(--color-ink-faint);
  align-self: flex-start;
  margin-top: 3px;
}

.conv-card__badge {
  position: absolute;
  top: 8px;
  right: 8px;
  min-width: 22px;
  height: 22px;
  padding: 0 7px;
  border-radius: 999px;
  background: var(--color-vu-amber);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  text-align: center;
  line-height: 22px;
  box-shadow: 0 1px 3px rgb(212 146 74 / 0.25);
}

/* ── Empty guide ── */
.inbox__empty-guide {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 40px 16px;
  text-align: center;
  color: var(--color-ink-muted);
}

.inbox__empty-guide strong {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-ink);
}

.inbox__empty-guide .hint {
  max-width: 300px;
  font-size: 13px;
  line-height: 1.5;
}

.inbox__empty-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 8px;
}

/* ── Chat pane ── */
.chat-pane {
  flex: 1 1 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  position: relative;
  background: var(--bg-surface-muted);
  overflow: hidden;
}

.chat-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-bottom: 1px solid rgb(212 205 195 / 0.2);
  background: var(--bg-surface);
}

.chat-head__back {
  padding: 2px 6px;
  border: none;
  background: none;
  font-size: 16px;
  cursor: pointer;
  color: var(--color-ink-muted);
  line-height: 1;
}

.chat-head__back:hover {
  color: var(--color-vu-amber);
}

.chat-head__meta {
  flex: 1;
  min-width: 0;
}

.chat-head__meta strong {
  font-size: 12px;
  font-weight: 600;
}

/* ── Messages ── */
.chat-messages {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 14px 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--bg-surface-muted);
  scrollbar-width: thin;
  scrollbar-color: rgb(212 205 195 / 0.3) transparent;
}

.chat-messages::-webkit-scrollbar {
  width: 5px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: rgb(212 205 195 / 0.35);
  border-radius: 999px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: rgb(212 205 195 / 0.55);
}

.chat-messages__loading {
  text-align: center;
  color: var(--color-ink-muted);
  font-size: 12px;
  padding: 24px;
}

.chat-divider {
  display: flex;
  justify-content: center;
  margin: 4px 0;
}

.chat-divider span {
  padding: 2px 10px;
  border-radius: 999px;
  background: rgb(212 205 195 / 0.2);
  font-size: 10px;
  color: var(--color-ink-muted);
}

.chat-system {
  display: flex;
  justify-content: center;
  margin: 3px 0;
}

.chat-system span {
  max-width: 90%;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgb(212 205 195 / 0.15);
  font-size: 11px;
  color: var(--color-ink-muted);
  text-align: center;
}

.chat-row {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  width: 100%;
}

.chat-row--mine {
  justify-content: flex-end;
}

.chat-row__avatar {
  flex-shrink: 0;
  margin-bottom: 2px;
}

.chat-bubble {
  max-width: min(70%, 440px);
  padding: 8px 12px;
  border-radius: 14px 14px 14px 3px;
  background: var(--bg-surface);
  border: 1px solid rgb(212 205 195 / 0.18);
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.04);
}

.chat-bubble--mine {
  border-radius: 14px 14px 3px 14px;
  background: linear-gradient(135deg, rgb(255 245 230 / 0.95), var(--color-vu-amber-soft));
  border-color: rgb(212 146 74 / 0.18);
}

.chat-bubble p {
  margin: 0 0 2px;
  font-size: 13px;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-bubble__meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  color: var(--color-ink-muted);
}

.chat-bubble__read {
  color: var(--color-vu-amber);
}

/* ── Quick replies ── */
.chat-quick {
  display: flex;
  gap: 6px;
  padding: 8px 14px;
  background: var(--bg-surface);
  overflow-x: auto;
  scrollbar-width: none;
}

.chat-quick::-webkit-scrollbar {
  display: none;
}

.chat-quick__chip {
  flex: 0 0 auto;
  max-width: 200px;
  padding: 4px 12px;
  border: 1px solid rgb(212 205 195 / 0.28);
  border-radius: 6px;
  background: var(--bg-surface-muted);
  font-size: 12px;
  color: var(--color-ink-muted);
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background 0.15s, border-color 0.15s;
}

.chat-quick__chip:hover {
  border-color: var(--color-vu-amber);
  background: var(--color-vu-amber-soft);
  color: var(--color-ink);
}

/* ── Composer ── */
.chat-composer {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 14px;
  border-top: 1px solid rgb(212 205 195 / 0.15);
  background: var(--bg-surface);
}

.chat-composer textarea {
  flex: 1;
  min-height: 36px;
  max-height: 90px;
  resize: none;
  padding: 8px 14px;
  border: 1px solid rgb(212 205 195 / 0.3);
  border-radius: 8px;
  background: var(--bg-surface-muted);
  font-size: 13px;
  line-height: 1.45;
  color: var(--color-ink);
  outline: none;
  transition: border-color 0.2s;
  font-family: inherit;
}

.chat-composer textarea::placeholder {
  color: var(--color-ink-faint);
}

.chat-composer textarea:focus {
  border-color: var(--color-vu-amber);
}

.chat-composer .btn--primary {
  padding: 8px 18px;
  border: none;
  border-radius: 8px;
  background: var(--color-vu-amber);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
  flex-shrink: 0;
}

.chat-composer .btn--primary:hover:not(:disabled) {
  opacity: 0.85;
}

.chat-composer .btn--primary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── Peer overlay ── */
.peer-overlay {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  justify-content: flex-end;
  background: rgb(0 0 0 / 0.15);
}

.peer-overlay .inbox__peer {
  width: 260px;
  height: 100%;
  border-left: 1px solid rgb(212 205 195 / 0.25);
  box-shadow: -2px 0 16px rgb(0 0 0 / 0.06);
}
</style>
