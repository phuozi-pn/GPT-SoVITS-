import { onMounted, onUnmounted, ref } from "vue";
import { fetchConversations } from "@/api/social";

const unreadTotal = ref(0);
let listeners = 0;
let timer: ReturnType<typeof setInterval> | null = null;

async function refreshUnread() {
  try {
    const convs = await fetchConversations();
    unreadTotal.value = convs.reduce((n, c) => n + (c.unread_count || 0), 0);
  } catch {
    unreadTotal.value = 0;
  }
}

export function useUnreadMessages() {
  onMounted(() => {
    listeners += 1;
    if (listeners === 1) {
      void refreshUnread();
      timer = setInterval(refreshUnread, 30_000);
    }
  });

  onUnmounted(() => {
    listeners = Math.max(0, listeners - 1);
    if (listeners === 0 && timer) {
      clearInterval(timer);
      timer = null;
    }
  });

  return {
    unreadTotal,
    refreshUnread,
  };
}
