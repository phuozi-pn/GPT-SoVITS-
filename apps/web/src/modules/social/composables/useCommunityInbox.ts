import { computed, inject, nextTick, onMounted, ref, watch, type InjectionKey } from "vue";
import { useRoute, useRouter } from "vue-router";
import { DEV_USER_PRESETS, getDevUserId } from "@/api/catalog";
import { useThreadPoll } from "@/composables/useThreadPoll";
import { useUnreadMessages } from "@/composables/useUnreadMessages";
import {
  fetchConversations,
  fetchThread,
  fetchUserDirectory,
  fetchUserProfile,
  sendMessage,
  updateMyProfile,
  type ConversationPreview,
  type MessageItem,
  type UserDirectoryEntry,
} from "@/api/social";
import { SYSTEM_USER_ID } from "@/config";
import { formatApiError } from "@/utils/apiErrors";
import { formatDateDivider, formatMessageTime, formatTimeAgo } from "@/utils/timeAgo";

export const QUICK_REPLIES = [
  "你好，想了解一下授权范围和使用场景。",
  "方便发一段更长的试听样音吗？",
  "想咨询商用授权价格。",
  "已购买，请问如何在项目里使用？",
];

export type ThreadRow =
  | { kind: "divider"; key: string; label: string }
  | { kind: "message"; key: string; message: MessageItem };

export function useCommunityInbox() {
  const route = useRoute();
  const router = useRouter();
  const { refreshUnread } = useUnreadMessages();

  const directory = ref<UserDirectoryEntry[]>([]);
  const conversations = ref<ConversationPreview[]>([]);
  const thread = ref<MessageItem[]>([]);
  const peerId = ref("");
  const peerName = ref("");
  const draft = ref("");
  const myUserId = ref(getDevUserId());
  const loading = ref(false);
  const sending = ref(false);
  const error = ref("");
  const search = ref("");
  const newChatSearch = ref("");
  const messagesEl = ref<HTMLElement | null>(null);
  const showPeerPanel = ref(true);
  const showProfileModal = ref(false);
  const showNewChatModal = ref(false);
  const composerEl = ref<HTMLTextAreaElement | null>(null);

  const editName = ref("");
  const editBio = ref("");
  const profileSaving = ref(false);

  const queryPeer = computed(() => String(route.query.peer ?? ""));
  const queryDraft = computed(() => String(route.query.draft ?? ""));
  const devMode = computed(() => localStorage.getItem("dev_mode") === "1");

  const totalUnread = computed(() =>
    conversations.value.reduce((sum, c) => sum + (c.unread_count ?? 0), 0),
  );

  const filteredConversations = computed(() => {
    const list = [...conversations.value].sort(
      (a, b) => new Date(b.last_at).getTime() - new Date(a.last_at).getTime(),
    );
    const q = search.value.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (c) =>
        c.peer_display_name.toLowerCase().includes(q) ||
        c.last_message.toLowerCase().includes(q),
    );
  });

  const pickableUsers = computed(() =>
    [...directory.value]
      .filter((u) => u.user_id !== myUserId.value)
      .sort((a, b) => b.published_voice_count - a.published_voice_count),
  );

  const filteredPickUsers = computed(() => {
    const q = newChatSearch.value.trim().toLowerCase();
    if (!q) return pickableUsers.value;
    return pickableUsers.value.filter(
      (u) =>
        u.display_name.toLowerCase().includes(q) ||
        u.bio.toLowerCase().includes(q) ||
        u.user_id.toLowerCase().includes(q),
    );
  });

  const threadRows = computed((): ThreadRow[] => {
    const rows: ThreadRow[] = [];
    let lastDay = "";
    for (const m of thread.value) {
      const day = formatDateDivider(m.created_at);
      if (day !== lastDay) {
        rows.push({ kind: "divider", key: `d-${m.created_at}`, label: day });
        lastDay = day;
      }
      rows.push({ kind: "message", key: m.message_id, message: m });
    }
    return rows;
  });

  const isSystemRow = (m: MessageItem) => m.sender_user_id === SYSTEM_USER_ID;

  async function loadDirectory() {
    directory.value = await fetchUserDirectory();
  }

  async function loadConversations() {
    conversations.value = await fetchConversations();
    await refreshUnread();
  }

  async function scrollToBottom() {
    await nextTick();
    const el = messagesEl.value;
    if (el) el.scrollTop = el.scrollHeight;
  }

  function applyRouteDraft() {
    const text = queryDraft.value.trim();
    if (!text) return;
    draft.value = text;
    const { draft: _d, ...rest } = route.query;
    router.replace({ query: rest });
    void nextTick(() => composerEl.value?.focus());
  }

  async function refreshThreadQuiet() {
    if (!peerId.value || loading.value) return;
    try {
      const prevLen = thread.value.length;
      const prevLast = thread.value.at(-1)?.message_id;
      const fresh = await fetchThread(peerId.value);
      if (fresh.length !== prevLen || fresh.at(-1)?.message_id !== prevLast) {
        thread.value = fresh;
        await loadConversations();
        await scrollToBottom();
      }
    } catch {
      /* 轮询失败静默 */
    }
  }

  useThreadPoll(peerId, refreshThreadQuiet);

  async function openThread(id: string, name?: string) {
    if (!id || id === myUserId.value) return;
    peerId.value = id;
    showNewChatModal.value = false;
    loading.value = true;
    error.value = "";
    try {
      if (!name) {
        const profile = await fetchUserProfile(id);
        peerName.value = profile.display_name;
      } else {
        peerName.value = name;
      }
      thread.value = await fetchThread(id);
      await loadConversations();
      const q: Record<string, string | string[]> = { peer: id };
      if (queryDraft.value) q.draft = queryDraft.value;
      router.replace({ query: q });
      applyRouteDraft();
      await scrollToBottom();
    } catch (e) {
      error.value = formatApiError(e);
    } finally {
      loading.value = false;
    }
  }

  async function onSend() {
    const text = draft.value.trim();
    if (!peerId.value || !text || sending.value) return;
    error.value = "";
    sending.value = true;
    try {
      const msg = await sendMessage(peerId.value, text);
      draft.value = "";
      thread.value = [...thread.value, msg];
      await loadConversations();
      await scrollToBottom();
    } catch (e) {
      error.value = formatApiError(e);
    } finally {
      sending.value = false;
    }
  }

  function onComposerKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void onSend();
    }
  }

  function insertQuickReply(text: string) {
    draft.value = text;
    void nextTick(() => composerEl.value?.focus());
  }

  function onMentionVoice(text: string) {
    insertQuickReply(text);
  }

  function goCreator(userId: string) {
    router.push(`/creator/${userId}`);
  }

  function startNewChat() {
    newChatSearch.value = "";
    showNewChatModal.value = true;
  }

  function goDiscover() {
    router.push("/discover/feed");
  }

  function goCatalog() {
    router.push("/catalog");
  }

  async function loadMyProfile() {
    try {
      const p = await fetchUserProfile(myUserId.value);
      editName.value = p.display_name;
      editBio.value = p.bio;
    } catch {
      /* ignore */
    }
  }

  async function onSaveProfile() {
    profileSaving.value = true;
    error.value = "";
    try {
      await updateMyProfile({
        display_name: editName.value.trim(),
        bio: editBio.value.trim(),
      });
      await loadDirectory();
      await loadMyProfile();
      showProfileModal.value = false;
    } catch (e) {
      error.value = formatApiError(e);
    } finally {
      profileSaving.value = false;
    }
  }

  onMounted(async () => {
    loading.value = true;
    try {
      await Promise.all([loadDirectory(), loadConversations(), loadMyProfile()]);
      if (queryPeer.value) {
        await openThread(queryPeer.value);
      }
    } catch (e) {
      error.value = formatApiError(e);
    } finally {
      loading.value = false;
    }
  });

  watch(queryPeer, (id) => {
    if (id && id !== peerId.value) {
      void openThread(id);
    }
  });

  watch(queryDraft, () => {
    if (peerId.value) applyRouteDraft();
  });

  return {
    DEV_USER_PRESETS,
    directory,
    conversations,
    thread,
    peerId,
    peerName,
    draft,
    myUserId,
    loading,
    sending,
    error,
    search,
    newChatSearch,
    messagesEl,
    showPeerPanel,
    showProfileModal,
    showNewChatModal,
    composerEl,
    editName,
    editBio,
    profileSaving,
    devMode,
    totalUnread,
    filteredConversations,
    filteredPickUsers,
    threadRows,
    isSystemRow,
    openThread,
    onSend,
    onComposerKeydown,
    insertQuickReply,
    onMentionVoice,
    goCreator,
    startNewChat,
    goDiscover,
    goCatalog,
    onSaveProfile,
    formatTimeAgo,
    formatMessageTime,
  };
}

export type CommunityInbox = ReturnType<typeof useCommunityInbox>;

export const CommunityInboxKey: InjectionKey<CommunityInbox> = Symbol("CommunityInbox");

export function useCommunityInboxInject() {
  const inbox = inject(CommunityInboxKey);
  if (!inbox) throw new Error("CommunityInbox not provided");
  return inbox;
}
