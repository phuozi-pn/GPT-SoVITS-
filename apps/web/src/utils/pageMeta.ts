function setMetaTag(name: string, content: string, attr: "name" | "property" = "name") {
  let el = document.querySelector(`meta[${attr}="${name}"]`);
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, name);
    document.head.appendChild(el);
  }
  el.setAttribute("content", content);
}

/** 页面级覆盖 title / description / OG（创作者主页、验真结果等） */
export function setPageMeta(title: string, description: string) {
  document.title = title;
  setMetaTag("description", description);
  setMetaTag("og:title", title, "property");
  setMetaTag("og:description", description, "property");
  setMetaTag("og:type", "website", "property");
}

export function setRouteMetaFromNavigation(title: string, description: string) {
  setPageMeta(title, description);
}
