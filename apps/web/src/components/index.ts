// 通用/基础组件统一导出
// 分层: components -> 壳层 + 通用基础组件 (跨模块复用)
//       modules/[name]/components -> 模块专用组件

// 壳层组件
export { default as AppLayout } from "./AppLayout.vue";
export { default as AppTopBar } from "./AppTopBar.vue";

// 通用 UI 组件
export { default as AppModal } from "./AppModal.vue";
export { default as ConfirmModal } from "./ConfirmModal.vue";
export { default as PageSurface } from "./PageSurface.vue";
export { default as PageHero } from "./PageHero.vue";
export { default as PageActionBar } from "./PageActionBar.vue";
export { default as PageActionLink } from "./PageActionLink.vue";
export { default as TextAction } from "./TextAction.vue";
export { default as RowActions } from "./RowActions.vue";
export { default as DetailStrip } from "./DetailStrip.vue";
export { default as DetailStripItem } from "./DetailStripItem.vue";
export { default as UserAvatar } from "./UserAvatar.vue";
export { default as StepTabs } from "./StepTabs.vue";
export { default as GuidePanel } from "./GuidePanel.vue";
export { default as WorkspaceLayout } from "./WorkspaceLayout.vue";
export { default as VoicePicker } from "./VoicePicker.vue";
export { default as HistoryCard } from "./HistoryCard.vue";

// 反馈组件
export { default as ErrorBanner } from "./ErrorBanner.vue";
export { default as LoadingSpinner } from "./LoadingSpinner.vue";
export { default as ToastContainer } from "./ToastContainer.vue";

// 新手引导与提示组件
export { default as OnboardingWelcome } from "./OnboardingWelcome.vue";
export { default as EmptyGuide } from "./EmptyGuide.vue";
export { default as HelpHint } from "./HelpHint.vue";

// 类型导出
export type { GuideStep } from "./GuidePanel.vue";
export type { VoicePickerItem } from "./VoicePicker.vue";
export type { StepTab } from "./StepTabs.vue";
