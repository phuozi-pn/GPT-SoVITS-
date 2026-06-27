<script setup lang="ts">
import AppModal from "@/components/AppModal.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { useCommunityInboxInject } from "@/modules/social/composables/useCommunityInbox";

const {
  showNewChatModal,
  newChatSearch,
  filteredPickUsers,
  openThread,
  goCreator,
  goDiscover,
  showProfileModal,
  editName,
  editBio,
  profileSaving,
  onSaveProfile,
} = useCommunityInboxInject();
</script>

<template>
  <AppModal :open="showNewChatModal" label="私信" title="选择要联系的创作者" wide @close="showNewChatModal = false">
    <p class="hint modal-hint">
      也可以先去
      <button type="button" class="text-action" @click="goDiscover">发现页</button>
      浏览动态，再点「发私信」。
    </p>
    <input v-model="newChatSearch" type="search" placeholder="搜索昵称或简介…" />
    <ul class="creator-suggest-list" style="margin-top: 12px">
      <li v-for="u in filteredPickUsers" :key="u.user_id">
        <button type="button" class="creator-suggest" @click="openThread(u.user_id, u.display_name)">
          <UserAvatar :name="u.display_name" :avatar-url="u.avatar_url" :user-id="u.user_id" size="md" />
          <span class="creator-suggest__meta">
            <strong>{{ u.display_name }}</strong>
            <span class="hint">{{ u.published_voice_count }} 个公开音色 · {{ u.bio || "暂无简介" }}</span>
          </span>
        </button>
        <button type="button" class="text-action" @click.stop="goCreator(u.user_id)">主页</button>
      </li>
    </ul>
    <p v-if="!filteredPickUsers.length" class="hint">没有匹配的创作者</p>
  </AppModal>

  <AppModal :open="showProfileModal" label="资料" title="我的展示资料" @close="showProfileModal = false">
    <div class="form-stack">
      <label class="field">
        <span>展示昵称</span>
        <input v-model="editName" maxlength="64" placeholder="在消息与发现页显示的名称" />
      </label>
      <label class="field">
        <span>简介</span>
        <textarea v-model="editBio" rows="3" maxlength="500" placeholder="一句话介绍自己，方便买家了解你" />
      </label>
    </div>
    <template #footer>
      <button type="button" class="btn btn--ghost btn--sm" @click="showProfileModal = false">取消</button>
      <button type="button" class="btn btn--primary btn--sm" :disabled="profileSaving" @click="onSaveProfile">
        {{ profileSaving ? "保存中…" : "保存" }}
      </button>
    </template>
  </AppModal>
</template>
