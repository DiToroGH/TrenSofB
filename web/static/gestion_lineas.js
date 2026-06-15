(function () {
  function t(key, vars) {
    return window.trenI18n.t(key, vars);
  }

  const dlg = document.getElementById("dlg-lineas");
  const btnOpen = document.getElementById("btn-gestion-lineas");
  const btnClose = document.getElementById("dlg-lineas-cerrar");
  const selLinea = document.getElementById("sel-linea");
  const listaLineas = document.getElementById("lista-lineas");
  const inpNueva = document.getElementById("linea-nueva-nombre");
  const btnCrear = document.getElementById("linea-crear");
  const msgEl = document.getElementById("msg-lineas");

  if (!selLinea) return;

  let lineasCache = [];

  function setMsg(text, kind) {
    if (!msgEl) return;
    msgEl.textContent = text || "";
    msgEl.className = "msg-gestion" + (kind === "error" ? " error" : "");
  }

  function apiFetch(url, options) {
    return window.trenLinea.apiFetch(url, options);
  }

  async function parseError(r) {
    if (r.status === 401 || r.status === 403) {
      if (typeof auth !== "undefined" && auth) auth.logout();
      throw new Error(t("sessionExpired"));
    }
    try {
      const j = await r.json();
      if (j.detail) {
        if (typeof j.detail === "string") return j.detail;
        if (Array.isArray(j.detail))
          return j.detail.map(function (d) {
            return d.msg || d;
          }).join("; ");
      }
    } catch (_) {}
    return r.statusText || t("errorGeneric");
  }

  function esAdmin() {
    return typeof auth !== "undefined" && auth && auth.userType === "admin";
  }

  function lineasParaSelector(lineas) {
    if (esAdmin()) return lineas;
    return lineas.filter(function (row) {
      return row.visible !== false;
    });
  }

  async function fetchLineas() {
    const r = await apiFetch("/lineas");
    if (!r.ok) throw new Error(await parseError(r));
    lineasCache = await r.json();
    return lineasCache;
  }

  function poblarSelector(lineas) {
    const visibles = lineasParaSelector(lineas);
    const actual = window.trenLinea.getLineaId();
    selLinea.innerHTML = "";
    visibles.forEach(function (row) {
      const opt = document.createElement("option");
      opt.value = String(row.id);
      opt.textContent = row.nombre;
      selLinea.appendChild(opt);
    });
    const ids = visibles.map(function (x) {
      return x.id;
    });
    const elegido = ids.indexOf(actual) >= 0 ? actual : visibles[0] ? visibles[0].id : 1;
    selLinea.value = String(elegido);
    window.trenLinea.setLineaId(elegido);
  }

  async function toggleVisible(row, visible) {
    setMsg(t("updating"), "");
    try {
      const r = await apiFetch("/lineas/" + row.id + "/visible", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ visible: visible }),
      });
      if (!r.ok) throw new Error(await parseError(r));
      await refreshLineas(true);
      setMsg(t("lineaVisibleSaved"), "ok");
    } catch (e) {
      setMsg(String(e.message || e), "error");
    }
  }

  function renderListaAdmin(lineas) {
    if (!listaLineas) return;
    listaLineas.innerHTML = "";
    lineas.forEach(function (row) {
      const li = document.createElement("li");
      li.className = "linea-admin-row";
      const nameSpan = document.createElement("span");
      nameSpan.textContent = row.nombre + " (#" + row.id + ")";
      li.appendChild(nameSpan);

      const visibleWrap = document.createElement("label");
      visibleWrap.className = "linea-visible-wrap";
      const chk = document.createElement("input");
      chk.type = "checkbox";
      chk.checked = row.visible !== false;
      chk.disabled = row.id === 1;
      chk.setAttribute("data-i18n-aria", "lineaVisibleLabel");
      chk.title = t("lineaVisibleLabel");
      chk.addEventListener("change", function () {
        void toggleVisible(row, chk.checked);
      });
      const visibleTxt = document.createElement("span");
      visibleTxt.setAttribute("data-i18n", "lineaVisibleLabel");
      visibleTxt.textContent = t("lineaVisibleLabel");
      visibleWrap.appendChild(chk);
      visibleWrap.appendChild(visibleTxt);
      li.appendChild(visibleWrap);

      const actions = document.createElement("span");
      actions.className = "linea-admin-actions";
      if (row.id !== 1) {
        const btnRen = document.createElement("button");
        btnRen.type = "button";
        btnRen.className = "btn secondary small";
        btnRen.textContent = t("btnEdit");
        btnRen.addEventListener("click", function () {
          void renombrarLinea(row);
        });
        const btnDel = document.createElement("button");
        btnDel.type = "button";
        btnDel.className = "btn danger small";
        btnDel.textContent = t("btnDelete");
        btnDel.addEventListener("click", function () {
          void borrarLinea(row);
        });
        actions.appendChild(btnRen);
        actions.appendChild(btnDel);
      } else {
        const badge = document.createElement("span");
        badge.className = "hint";
        badge.textContent = t("lineaSofbProtected");
        actions.appendChild(badge);
      }
      li.appendChild(actions);
      listaLineas.appendChild(li);
    });
  }

  async function renombrarLinea(row) {
    const nuevo = window.prompt(t("lineaRenamePrompt"), row.nombre);
    if (!nuevo || !nuevo.trim() || nuevo.trim() === row.nombre) return;
    setMsg(t("updating"), "");
    try {
      const r = await apiFetch("/lineas/" + row.id, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre: nuevo.trim() }),
      });
      if (!r.ok) throw new Error(await parseError(r));
      await refreshLineas(true);
      setMsg(t("lineaRenamed"), "ok");
    } catch (e) {
      setMsg(String(e.message || e), "error");
    }
  }

  async function borrarLinea(row) {
    if (!window.confirm(t("lineaDeleteConfirm", { nombre: row.nombre }))) return;
    setMsg(t("updating"), "");
    try {
      const r = await apiFetch("/lineas/" + row.id, { method: "DELETE" });
      if (!r.ok) throw new Error(await parseError(r));
      if (window.trenLinea.getLineaId() === row.id) {
        window.trenLinea.setLineaId(1);
      }
      await refreshLineas(true);
      setMsg(t("lineaDeleted"), "ok");
    } catch (e) {
      setMsg(String(e.message || e), "error");
    }
  }

  async function refreshLineas(reloadMain) {
    const lineas = await fetchLineas();
    poblarSelector(lineas);
    renderListaAdmin(lineas);
    if (reloadMain && typeof window.__trenRecargarEstado === "function") {
      await window.__trenRecargarEstado();
    }
  }

  window.__trenRefreshLineas = refreshLineas;

  selLinea.addEventListener("change", async function () {
    const id = parseInt(selLinea.value, 10);
    if (!Number.isFinite(id)) return;
    window.trenLinea.setLineaId(id);
    if (typeof window.__trenRecargarEstado === "function") {
      await window.__trenRecargarEstado();
    }
  });

  if (btnOpen && dlg) {
    btnOpen.addEventListener("click", async function () {
      setMsg("", "");
      try {
        await refreshLineas(false);
        dlg.showModal();
      } catch (e) {
        setMsg(String(e.message || e), "error");
      }
    });
  }

  if (btnClose && dlg) {
    btnClose.addEventListener("click", function () {
      dlg.close();
    });
  }

  if (btnCrear) {
    btnCrear.addEventListener("click", async function () {
      const nombre = inpNueva ? inpNueva.value.trim() : "";
      if (!nombre) {
        setMsg(t("lineaNameRequired"), "error");
        return;
      }
      setMsg(t("updating"), "");
      try {
        const r = await apiFetch("/lineas", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ nombre: nombre }),
        });
        if (!r.ok) throw new Error(await parseError(r));
        if (inpNueva) inpNueva.value = "";
        await refreshLineas(true);
        setMsg(t("lineaCreated"), "ok");
      } catch (e) {
        setMsg(String(e.message || e), "error");
      }
    });
  }

  if (typeof auth !== "undefined" && auth && auth.token) {
    fetchLineas()
      .then(poblarSelector)
      .catch(function () {});
  }
})();
