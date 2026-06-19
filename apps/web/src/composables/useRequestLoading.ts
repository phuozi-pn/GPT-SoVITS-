/**
 * 全局请求 loading 状态管理。
 *
 * 在 apiJson 调用时自动递增/递减计数器，
 * 组件通过 useRequestLoading() 获取当前是否处于加载中。
 */

import { ref } from "vue";

let _pending = 0;
const _loading = ref(false);

/** 内部调用：请求开始时 +1 */
export function _requestStart() {
  _pending++;
  _loading.value = true;
}

/** 内部调用：请求完成时 -1 */
export function _requestEnd() {
  if (_pending > 0) {
    _pending--;
  }
  if (_pending === 0) {
    _loading.value = false;
  }
}

/** 在组件中使用，获取全局请求加载状态 */
export function useRequestLoading() {
  return { loading: _loading };
}
