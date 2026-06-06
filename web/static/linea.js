(function () {
  const STORAGE_KEY = "tren_linea_id";

  function getLineaId() {
    const raw = localStorage.getItem(STORAGE_KEY);
    const n = raw ? parseInt(raw, 10) : 1;
    return Number.isFinite(n) && n > 0 ? n : 1;
  }

  function setLineaId(id) {
    localStorage.setItem(STORAGE_KEY, String(id));
  }

  function withLineaQuery(url) {
    if (!url) return url;
    if (url === "/lineas" || url.startsWith("/lineas?")) return url;
    if (/^\/lineas\/\d+/.test(url)) return url;
    if (url.indexOf("linea_id=") >= 0) return url;
    const sep = url.indexOf("?") >= 0 ? "&" : "?";
    return url + sep + "linea_id=" + encodeURIComponent(String(getLineaId()));
  }

  function applyAuthHeaders(fetchOptions) {
    const opts = Object.assign({ cache: "no-store" }, fetchOptions || {});
    if (typeof auth !== "undefined" && auth && auth.token) {
      if (!opts.headers) opts.headers = {};
      opts.headers.Authorization = "Bearer " + auth.token;
    }
    return opts;
  }

  function apiFetch(url, options) {
    return fetch(withLineaQuery(url), applyAuthHeaders(options));
  }

  window.trenLinea = {
    getLineaId: getLineaId,
    setLineaId: setLineaId,
    withLineaQuery: withLineaQuery,
    apiFetch: apiFetch,
    applyAuthHeaders: applyAuthHeaders,
  };
})();
