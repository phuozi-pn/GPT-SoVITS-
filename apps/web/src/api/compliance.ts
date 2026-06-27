import { apiJson } from "./client";

export interface TextComplianceIssue {
  code: string;
  message: string;
  segment_index?: number | null;
}

export interface TextCompliancePrecheckResponse {
  ok: boolean;
  total_chars: number;
  issues: TextComplianceIssue[];
}

export async function precheckSynthesisText(body: {
  texts: string[];
  segmented?: boolean;
}) {
  return apiJson<TextCompliancePrecheckResponse>("/api/v1/compliance/precheck", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
