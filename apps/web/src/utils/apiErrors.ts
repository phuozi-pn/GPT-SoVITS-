import { ApiError } from "@/api/client";

const CODE_MESSAGES: Record<string, string> = {
  VOICE_NOT_GRANTED: "你没有使用该音色的权限——请确认已导入、已授权，或切换调试用户",
  AI_DISCLOSURE_REQUIRED: "请先勾选「已确认 AI 合成告知义务」",
  INVALID_TEXT: "台本为空或只有标点——请输入有效台词",
  TEXT_TOO_LONG: "台本超过长度限制——请缩短后重试",
  SENSITIVE_WORD: "台本含敏感词——请修改后重试",
  QUOTA_EXCEEDED: "本月字符配额已用完——请下月再试或联系运营",
  UNAUTHORIZED: "登录已过期——请重新登录",
  FORBIDDEN: "无权执行此操作",
  VALIDATION_ERROR: "请求参数有误——请检查音色 ID 与台本格式",
  HTTP_ERROR: "服务暂时不可用——请确认平台 API 是否在运行",
};

export function formatApiError(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.status === 402 || e.code === "QUOTA_EXCEEDED") return CODE_MESSAGES.QUOTA_EXCEEDED;
    const hint = CODE_MESSAGES[e.code];
    if (hint) return hint;
    if (e.status === 401) return CODE_MESSAGES.UNAUTHORIZED;
    if (e.status === 403) return e.message || CODE_MESSAGES.FORBIDDEN;
    if (e.status === 422) return `${CODE_MESSAGES.VALIDATION_ERROR}（${e.message}）`;
    return e.message || `${e.code}（HTTP ${e.status}）`;
  }
  if (e instanceof Error) return e.message;
  return String(e);
}
