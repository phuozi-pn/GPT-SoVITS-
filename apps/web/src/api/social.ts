import { apiJson } from "@/api/client";

export type UserDirectoryEntry = {
  user_id: string;
  display_name: string;
  bio: string;
  avatar_url?: string | null;
  published_voice_count: number;
};

export type UserPublicProfile = {
  user_id: string;
  display_name: string;
  bio: string;
  avatar_url?: string | null;
  published_voice_count: number;
  is_self: boolean;
};

export type ConversationPreview = {
  peer_user_id: string;
  peer_display_name: string;
  last_message: string;
  last_at: string;
  unread_count: number;
};

export type MessageItem = {
  message_id: string;
  sender_user_id: string;
  recipient_user_id: string;
  body: string;
  read_at: string | null;
  created_at: string;
};

export function fetchUserDirectory() {
  return apiJson<UserDirectoryEntry[]>("/api/v1/users/directory");
}

export function fetchMyProfile() {
  return apiJson<UserPublicProfile>("/api/v1/users/me/profile");
}

export function fetchUserProfile(userId: string) {
  return apiJson<UserPublicProfile>(`/api/v1/users/${userId}`);
}

export function updateMyProfile(body: {
  display_name?: string;
  bio?: string;
  avatar_url?: string | null;
  is_public?: boolean;
}) {
  return apiJson<UserPublicProfile>("/api/v1/users/me/profile", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export interface AvatarGenerateResult {
  avatar_url: string;
  prompt?: string;
}

export function generateCreatorAvatar() {
  return apiJson<AvatarGenerateResult>("/api/v1/users/me/profile/generate-avatar", {
    method: "POST",
  });
}

export function fetchConversations() {
  return apiJson<ConversationPreview[]>("/api/v1/messages/conversations");
}

export function fetchThread(peerUserId: string) {
  return apiJson<MessageItem[]>(`/api/v1/messages/with/${peerUserId}`);
}

export function sendMessage(recipientUserId: string, body: string) {
  return apiJson<MessageItem>("/api/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ recipient_user_id: recipientUserId, body }),
  });
}

export function catalogDemoDownloadUrl(catalogId: string) {
  return `/api/v1/catalog/voices/${catalogId}/demo-download`;
}

export function catalogVoicePackUrl(catalogId: string) {
  return `/api/v1/catalog/voices/${catalogId}/voice-pack`;
}

const API_BASE = import.meta.env.VITE_API_BASE ?? "";

function downloadAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const token = localStorage.getItem("access_token");
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  } else if (localStorage.getItem("dev_mode") === "1") {
    headers["X-User-Id"] =
      localStorage.getItem("dev_user_id") ?? "00000000-0000-0000-0000-000000000001";
  }
  return headers;
}

export async function downloadCatalogAsset(path: string, fallbackName: string) {
  const res = await fetch(`${API_BASE}${path}`, { headers: downloadAuthHeaders() });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.detail?.message ?? message;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  const blob = await res.blob();
  const dispo = res.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";]+)"?/i.exec(dispo);
  const filename = match?.[1] ?? fallbackName;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
