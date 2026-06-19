<script setup lang="ts">
import { useCopyText } from "@/composables/useCopyText";

const props = withDefaults(
  defineProps<{
    url?: string;
    label?: string;
    copiedLabel?: string;
  }>(),
  {
    label: "复制链接",
    copiedLabel: "已复制链接",
  },
);

const { copied, copy } = useCopyText();

function onCopy() {
  void copy(props.url ?? window.location.href);
}
</script>

<template>
  <button type="button" class="text-action" @click="onCopy">
    {{ copied ? copiedLabel : label }}
  </button>
</template>
