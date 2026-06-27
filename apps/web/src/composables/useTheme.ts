import { ref, watch } from "vue";
import {
  applyThemeState,
  DEFAULT_CUSTOM_BG,
  loadThemeState,
  saveThemeState,
  THEME_PRESETS,
  type ThemeMode,
  type ThemeState,
} from "@/utils/theme";

const state = ref<ThemeState>(loadThemeState());
let initialized = false;

function ensureApplied() {
  if (initialized) return;
  initialized = true;
  applyThemeState(state.value);
  watch(
    state,
    (next) => {
      applyThemeState(next);
      saveThemeState(next);
    },
    { deep: true },
  );
}

export function initTheme() {
  ensureApplied();
}

export function useTheme() {
  ensureApplied();

  function setMode(mode: ThemeMode) {
    state.value = { ...state.value, mode };
  }

  function setCustomBg(color: string) {
    state.value = { mode: "custom", customBg: color || DEFAULT_CUSTOM_BG };
  }

  return {
    state,
    presets: THEME_PRESETS,
    setMode,
    setCustomBg,
  };
}
