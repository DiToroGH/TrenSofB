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

    const conductores = data.conductores || [];
    const orden = data.acompaniantes_orden || [];
    const vistos = {};
    const todasPersonas = [];

    function agregarNombre(nombre) {
      const n = String(nombre || "").trim();
      if (!n) return;
      const clave = n.toLowerCase();
      if (vistos[clave]) return;
      vistos[clave] = true;
      todasPersonas.push(n);
    }

    conductores.forEach(agregarNombre);
    orden.forEach(agregarNombre);

    selCond.innerHTML = "";
    todasPersonas.forEach(function (nombre) {
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
    todasPersonas.forEach(function (nombre) {
      const o = document.createElement("option");
      o.value = nombre;
      o.textContent = nombre;
      selVip.appendChild(o);
    });
  }

  function fechaConfirmadaParaEdicion(fecha) {
    const data = window.__trenLastEstado;
    if (!data) return false;
    if (window.__trenLastRegistroPorFecha) {
      const reg = window.__trenLastRegistroPorFecha[fecha];
      if (reg && String(reg.conductor || "").trim()) return true;
    }
    const fechaEstado = String(data.fecha || "").trim().slice(0, 10);
    if (fechaEstado !== fecha) return false;
    return Array.isArray(data.asignaciones) && data.asignaciones.length > 0;
  }

  function abrirDialogo() {
    if (!dlg || !inpFecha) return;
    rellenarSelects();
    const maxD = hoyISO();
    inpFecha.max = maxD;
    const data = window.__trenLastEstado;
    const fechaEstado = data && data.fecha ? String(data.fecha).trim().slice(0, 10) : "";
    if (fechaEstado && fechaEstado <= maxD && fechaConfirmadaParaEdicion(fechaEstado)) {
      inpFecha.value = fechaEstado;
    } else if (!inpFecha.value || inpFecha.value > maxD) {
      inpFecha.value = maxD <= hoyISO() && fechaConfirmadaParaEdicion(maxD)
        ? maxD
        : ayerISO();
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
      if (!fecha || fecha > hoyISO()) {
        setMsg(t("registroFechaInvalida"), "error");
        return;
      }
      if (fecha === hoyISO() && !fechaConfirmadaParaEdicion(fecha)) {
        setMsg(t("registroHoySinConfirmar"), "error");
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
