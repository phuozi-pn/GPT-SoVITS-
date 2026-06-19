import { apiJson } from "@/api/client";

export type FeedPost = {
  post_id: string;
  author_user_id: string;
  author_display_name: string;
  body: string;
  tags: string[];
  created_at: string;
  like_count: number;
  liked_by_me: boolean;
};

export type FeedEvent = {
  event_id: string;
  kind: string;
  actor_user_id: string;
  actor_display_name: string;
  target_type: string;
  target_id: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type FeedItem =
  | { type: "post"; created_at: string; post: FeedPost; event: null }
  | { type: "event"; created_at: string; post: null; event: FeedEvent };

export type FeedResponse = { items: FeedItem[]; next_before: string | null };

export function fetchCommunityFeed(opts?: { before?: string; limit?: number }) {
  const params = new URLSearchParams();
  if (opts?.before) params.set("before", opts.before);
  if (opts?.limit) params.set("limit", String(opts.limit));
  const q = params.toString();
  return apiJson<FeedResponse>(`/api/v1/community/feed${q ? `?${q}` : ""}`);
}

export function createCommunityPost(body: { body: string; tags?: string[] }) {
  return apiJson<FeedPost>("/api/v1/community/posts", {
    method: "POST",
    body: JSON.stringify({ body: body.body, tags: body.tags ?? [] }),
  });
}

export function togglePostLike(postId: string) {
  return apiJson<FeedPost>(`/api/v1/community/posts/${postId}/like`, { method: "POST" });
}

