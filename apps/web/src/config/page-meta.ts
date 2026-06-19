/**
 * 页面元数据
 *
 * 页面标题、描述、工作流说明（纯展示数据，与路由结构无关）。
 */

export type PageMeta = {
  group: string;
  label: string;
  desc: string;
  workflow?: string;
};

/** 页面元数据注册表 */
export const PAGE_META: Record<string, PageMeta> = {
  home: {
    group: "Voice Studio",
    label: "首页",
    desc: "AI 配音与音色市场——试听公开音色，登录后进入工作台",
  },
  browse: {
    group: "Voice Studio",
    label: "音色馆",
    desc: "浏览公开音色与样音试听",
  },
  "public-feed": {
    group: "Voice Studio",
    label: "社区动态",
    desc: "公开浏览音色上新与用户帖子",
  },
  login: {
    group: "Voice Studio",
    label: "登录",
    desc: "登录后进入工作台：训练、合成、购买授权",
  },
  library: {
    group: "制作",
    label: "智能配音",
    desc: "单人朗读、多人对话情景配音；粘贴剧本智能分段并指派音色",
    workflow: "① 选模式（单人/情景）→ ② 编辑分段 → ③ 卡司指派 → ④ 合成",
  },
  projects: {
    group: "制作",
    label: "短剧批量配音",
    desc: "短剧/系列剧 CSV 驱动：多角色大批量合成与合规 ZIP 导出",
    workflow: "① 建项目 → ② 绑角色音色 → ③ 上传 CSV → ④ 下载 ZIP",
  },
  studio: {
    group: "音色",
    label: "训练工作台",
    desc: "上传素材、完成授权、训练专属音色",
    workflow: "① 创建音色 → ② 上传素材 → ③ 训练 → ④ 试听",
  },
  voices: {
    group: "音色",
    label: "我的音色",
    desc: "管理自有音色与版本：重命名、编辑标签、删除",
    workflow: "查看资产 → 编辑资料 → 合成 / 发布 / 删除",
  },
  catalog: {
    group: "音色",
    label: "音色馆",
    desc: "浏览公开音色、购买授权与卖家结算",
    workflow: "浏览精选 → 试听 → 购买 / 发私信洽谈",
  },
  "discover-feed": {
    group: "社区",
    label: "动态",
    desc: "社区时间线：上新与用户动态",
    workflow: "浏览 → 点赞 / 发帖 → 发私信洽谈",
  },
  community: {
    group: "社区",
    label: "消息",
    desc: "私信收件箱，洽谈授权与合作",
    workflow: "选人 → 会话 → 详聊授权细节",
  },
  admin: {
    group: "运营",
    label: "运营台",
    desc: "审核、投诉处理、KYC 与提现审批",
  },
  kyc: {
    group: "音色",
    label: "实名认证",
    desc: "训练前需完成身份核验",
    workflow: "训练工作台前置步骤",
  },
  creator: {
    group: "社区",
    label: "创作者主页",
    desc: "查看创作者公开作品与上架音色",
  },
  quality: {
    group: "音色",
    label: "相似度评测",
    desc: "AB 对比与质量报告",
  },
  verify: {
    group: "Voice Studio",
    label: "授权验真",
    desc: "核验音色授权凭证是否仍然有效",
  },
};

/** 根据路径解析页面 Key */
export function resolvePageKey(path: string, routeName?: string | null): string {
  if (routeName && PAGE_META[routeName]) return routeName;
  return path.replace(/^\//, "").split("/").filter(Boolean)[0] || "library";
}

/** 获取页面元数据 */
export function getPageMeta(path: string, routeName?: string | null): PageMeta {
  const key = resolvePageKey(path, routeName);
  return (
    PAGE_META[key] ?? {
      group: "工作台",
      label: "Voice Studio",
      desc: "AI 配音工作台",
    }
  );
}
