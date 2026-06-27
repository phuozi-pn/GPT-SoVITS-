/** 登录后跳转音色馆（支持 pick 深链与购买 intent） */
export function loginToCatalogQuery(catalogId?: string, intent?: string): Record<string, string> {
  const query: Record<string, string> = { redirect: "/catalog" };
  if (catalogId) query.pick = catalogId;
  if (intent) query.intent = intent;
  return query;
}

/** 工作台内音色馆路径（已登录） */
export function catalogAppPath(catalogId?: string, intent?: string) {
  const query: Record<string, string> = {};
  if (catalogId) query.pick = catalogId;
  if (intent) query.intent = intent;
  return Object.keys(query).length ? { path: "/catalog", query } : { path: "/catalog" };
}

export function catalogPurchasePath(catalogId: string) {
  return catalogAppPath(catalogId, "purchase");
}

/** 创作者公开主页（可分享） */
export function creatorPublicPath(userId: string) {
  return `/creator/${userId}`;
}

/** 工作台内「我的主页」 */
export function myCreatorPath() {
  return "/me";
}
