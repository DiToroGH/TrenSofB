(function () {
  function t(key, vars) {
    return window.trenI18n.t(key, vars);
  }

  function fechaClaveLocal(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return y + "-" + m + "-" + day;
  }

  function ayerISO() {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return fechaClaveLocal(d);
  }

  function hoyISO() {
    return fechaClaveLocal(new Date());
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
          return j.detail.map(function (x) {
            return x.msg || x;
          }).join("; ");
      }
    } catch (_) {}
    return r.statusText || t("errorGeneric");
  }

  function apiFetch(url, options) {
    return window.trenLinea.apiFetch(url, options);
  }

  const dlg = document.getElementById("dlg-registro-pasado");
  const inpFecha = document.getElementById("reg-pasado-fecha");
  const selCond = document.getElementById("reg-pasado-cond");
  const selVip = document.getElementById("reg-pasado-vip");
  const msgEl = document.getElementById("msg-registro-pasado");
  const btnOpen = document.getElementById("btn-registro-pasado");
  const btnSave = document.getElementById("reg-pasado-guardar");
  const btnClose = document.getElementById("dlg-registro-cerrar");

  function setMsg(text, kind) {
    if (!msgEl) return;
    msgEl.textContent = text || "";
    msgEl.className = "msg-registro" + (kind ? " " + kind : "");
  }

  function rellenarSelects() {
    const data = window.__trenLastEstado;
    if (!data || !selCond || !selVip) return;

    const cond = data.conductores || [];
    const orden = data.acompaniantes_orden || [];

    selCond.innerHTML = "";
    cond.forEach(function (nombre) {
      const o = document.createElement("option");
      o.value = nombre;
      o.textContent = nombre;
      selCond.appendChild(o);
    });

    selVip.innerHTML = "";
    const oNone = document.createElement("option");
    oNone.value = "";
    oNone.textContent = t("registroSinVip");
    selVip.appendChild(oNone);
    orden.forEach(function (nombre) {
      const o = document.createElement("option");
      o.value = nombre;
      o.textContent = nombre;
      selVip.appendChild(o);
    });
  }

  function abrirDialogo() {
    if (!dlg || !inpFecha) return;
    rellenarSelects();
    const maxD = ayerISO();
    inpFecha.max = maxD;
    if (!inpFecha.value || inpFecha.value >= hoyISO()) {
      inpFecha.value = maxD;
    }
    setMsg("", "");
    if (typeof dlg.showModal === "function") dlg.showModal();
  }

  if (btnOpen) {
    btnOpen.addEventListener("click", function () {
      abrirDialogo();
    });
  }

  if (btnClose && dlg) {
    btnClose.addEventListener("click", function () {
      dlg.close();
    });
  }

  window.addEventListener("tren-lang-change", function () {
    const oNone = selVip && selVip.querySelector('option[value=""]');
    if (oNone) oNone.textContent = t("registroSinVip");
  });

  if (btnSave) {
    btnSave.addEventListener("click", async function () {
      if (!inpFecha || !selCond) return;
      const fecha = inpFecha.value;
      if (!fecha || fecha >= hoyISO()) {
        setMsg(t("registroFechaPasada"), "error");
        return;
      }
      const conductor = selCond.value;
      if (!conductor) {
        setMsg(t("registroConductorReq"), "error");
        return;
      }
      const vipRaw = selVip ? selVip.value : "";
      const body = {
        conductor: conductor,
        acompanante: vipRaw ? vipRaw : null,
      };
      setMsg(t("updating"), "");
      try {
        const r = await apiFetch(
          "/registro/dia/" + encodeURIComponent(fecha),
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }
        );
        if (!r.ok) throw new Error(await parseError(r));
        setMsg(t("registroSaved"), "ok");
        if (typeof window.__trenRecargarEstado === "function") {
          await window.__trenRecargarEstado();
        }
      } catch (e) {
        setMsg(String(e.message || e), "error");
      }
    });
  }
})();
