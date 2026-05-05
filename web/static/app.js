(function () {
  const msgEl = document.getElementById("msg");
  const fechaEl = document.getElementById("fecha");
  const resumenEl = document.getElementById("resumen-hoy");
  const mensajeEl = document.getElementById("mensaje-turno");
  const checksEl = document.getElementById("checks");
  const listaAsig = document.getElementById("lista-asignaciones");
  const noDispEl = document.getElementById("no-disp");
  const conductoresRef = document.getElementById("conductores-ref");
  const acompaniantesRef = document.getElementById("acompaniantes-ref");
  const almanaqueEl = document.getElementById("almanaque-semanal");

  const DIAS_CORTO = ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"];
  const MESES_CORTO = [
    "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
  ];

  /** Serialización del orden de acompañantes; si no cambió, no recreamos los checkboxes (preserva tildes). */
  let lastOrdenSerialized = null;

  function apiFetch(url, options) {
    const fetchOptions = Object.assign({ cache: "no-store" }, options || {});
    
    // Agregar header de autorización si existe token
    if (auth && auth.token) {
      if (!fetchOptions.headers) {
        fetchOptions.headers = {};
      }
      fetchOptions.headers['Authorization'] = `Bearer ${auth.token}`;
    }
    
    return fetch(url, fetchOptions);
  }

  function setMsg(text, kind) {
    msgEl.textContent = text || "";
    msgEl.className = "msg" + (kind ? " " + kind : "");
  }

  async function parseError(r) {
    // Si es 401 o 403, hacer logout
    if (r.status === 401 || r.status === 403) {
      if (auth) {
        auth.logout();
      }
      throw new Error("Sesión expirada o sin permisos. Por favor inicia sesión nuevamente.");
    }
    
    try {
      const j = await r.json();
      if (j.detail) {
        if (typeof j.detail === "string") return j.detail;
        if (Array.isArray(j.detail)) return j.detail.map((d) => d.msg || d).join("; ");
      }
    } catch (_) {}
    return r.statusText || "Error";
  }

  async function moverAcompanianteExtremoPorId(personaId, alInicio) {
    setMsg("Actualizando…", "");
    try {
      const r = await apiFetch("/personas/acompaniantes/mover-extremo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ persona_id: personaId, al_inicio: alInicio }),
      });
      if (!r.ok) throw new Error(await parseError(r));
      lastOrdenSerialized = null;
      await cargar();
      setMsg("Orden de acompañantes actualizado.", "ok");
    } catch (e) {
      setMsg(String(e.message || e), "error");
    }
  }

  function renderChecks(nombres, data) {
    checksEl.innerHTML = "";
    const idPorNombre = {};
    if (
      auth &&
      auth.isAdmin() &&
      data &&
      Array.isArray(data.acompaniantes_items)
    ) {
      data.acompaniantes_items.forEach(function (row) {
        idPorNombre[row.nombre] = row.id;
      });
    }
    nombres.forEach(function (nombre, idx) {
      const idChk = "chk-" + encodeURIComponent(nombre).replace(/%/g, "_");
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = true;
      input.dataset.nombre = nombre;
      input.id = idChk;
      label.appendChild(input);
      label.appendChild(document.createTextNode(nombre));

      const pid = idPorNombre[nombre];
      const puedeReordenar = auth && auth.isAdmin() && pid != null;
      if (puedeReordenar) {
        const row = document.createElement("div");
        row.className = "disp-check-row";
        row.appendChild(label);
        const actions = document.createElement("span");
        actions.className = "conductores-ref-actions disp-check-actions";
        const atFirst = idx === 0;
        const atLast = idx === nombres.length - 1;
        function mkBtn(txt, disabled, alInicio) {
          const b = document.createElement("button");
          b.type = "button";
          b.className = "btn secondary compact";
          b.textContent = txt;
          b.disabled = disabled;
          b.addEventListener("click", function (e) {
            e.preventDefault();
            moverAcompanianteExtremoPorId(pid, alInicio);
          });
          return b;
        }
        actions.appendChild(mkBtn("Al principio", atFirst, true));
        actions.appendChild(mkBtn("Al final", atLast, false));
        row.appendChild(actions);
        checksEl.appendChild(row);
      } else {
        checksEl.appendChild(label);
      }
    });
  }

  function disponiblesSeleccionados() {
    const out = [];
    checksEl.querySelectorAll("input[type=checkbox]").forEach((inp) => {
      if (inp.checked && inp.dataset.nombre) out.push(inp.dataset.nombre);
    });
    return out;
  }

  function fechaClaveLocal(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return y + "-" + m + "-" + day;
  }

  function inicioSemanaLunes(ref) {
    const d = new Date(ref.getFullYear(), ref.getMonth(), ref.getDate());
    const day = d.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    d.setDate(d.getDate() + diff);
    return d;
  }

  function parejaDesdeEstado(data) {
    const cond = data.conductores || [];
    const asig = data.asignaciones || [];
    const orden = data.acompaniantes_orden || [];
    if (asig.length > 0) {
      return {
        conductor: asig[0].conductor,
        vip: asig[0].acompanante,
        etiqueta: "Confirmado",
      };
    }
    if (cond.length && orden.length) {
      return {
        conductor: cond[0],
        vip: orden[0],
        etiqueta: "Propuesto",
      };
    }
    return { conductor: null, vip: null, etiqueta: null };
  }

  function renderAlmanaqueSemanal(data) {
    if (!almanaqueEl) return;
    almanaqueEl.innerHTML = "";
    const hoy = new Date();
    const claveHoy = fechaClaveLocal(hoy);
    const inicio = inicioSemanaLunes(hoy);
    const pareja = parejaDesdeEstado(data);

    for (let i = 0; i < 7; i++) {
      const cellDate = new Date(
        inicio.getFullYear(),
        inicio.getMonth(),
        inicio.getDate() + i
      );
      const clave = fechaClaveLocal(cellDate);
      const esHoy = clave === claveHoy;
      const diaSem = DIAS_CORTO[cellDate.getDay()];
      const num = cellDate.getDate();
      const mes = MESES_CORTO[cellDate.getMonth()];

      const article = document.createElement("article");
      article.className = "almanaque-dia" + (esHoy ? " almanaque-dia--hoy" : "");
      article.setAttribute("role", "listitem");

      const head = document.createElement("div");
      head.className = "almanaque-dia-head";
      const wk = document.createElement("span");
      wk.className = "almanaque-dia-wk";
      wk.textContent = diaSem;
      const timeEl = document.createElement("time");
      timeEl.className = "almanaque-dia-fecha";
      timeEl.setAttribute("datetime", clave);
      timeEl.textContent = String(num) + " " + mes;
      head.appendChild(wk);
      head.appendChild(timeEl);
      article.appendChild(head);

      let cText = "—";
      let vText = "—";
      let vClass = "almanaque-par-nombre almanaque-par-nombre--muted";
      let cClass = "almanaque-par-nombre almanaque-par-nombre--muted";

      if (esHoy) {
        cClass = "almanaque-par-nombre";
        cText = pareja.conductor || "—";
        if (pareja.vip === "SIN ACOMPAÑANTE") {
          vText = "Sin asignar";
          vClass = "almanaque-par-nombre almanaque-par-nombre--muted";
        } else if (pareja.vip) {
          vText = pareja.vip;
          vClass = "almanaque-par-nombre almanaque-par-nombre--vip";
        } else {
          vText = "—";
          vClass = "almanaque-par-nombre almanaque-par-nombre--muted";
        }
      }

      const laneC = document.createElement("div");
      laneC.className = "almanaque-par";
      const bc = document.createElement("span");
      bc.className = "almanaque-par-badge almanaque-par-badge--cond";
      bc.textContent = "Conductor";
      const nc = document.createElement("p");
      nc.className = cClass;
      nc.textContent = cText;
      laneC.appendChild(bc);
      laneC.appendChild(nc);

      const laneV = document.createElement("div");
      laneV.className = "almanaque-par";
      const bv = document.createElement("span");
      bv.className = "almanaque-par-badge almanaque-par-badge--vip";
      bv.textContent = "VIP";
      const nv = document.createElement("p");
      nv.className = vClass;
      nv.textContent = vText;
      laneV.appendChild(bv);
      laneV.appendChild(nv);

      article.appendChild(laneC);
      article.appendChild(laneV);

      if (esHoy && pareja.etiqueta) {
        const tag = document.createElement("p");
        tag.className = "almanaque-estado";
        tag.textContent = pareja.etiqueta;
        article.appendChild(tag);
      }

      almanaqueEl.appendChild(article);
    }
  }

  function renderAsignacionesLista(asig) {
    listaAsig.innerHTML = "";
    listaAsig.className = "asig-list";
    listaAsig.setAttribute("role", "list");
    if (asig.length === 0) {
      const empty = document.createElement("p");
      empty.className = "asig-empty";
      empty.textContent = "Aún no hay asignaciones.";
      listaAsig.appendChild(empty);
      return;
    }
    asig.forEach(function (a, idx) {
      const sinVip = a.acompanante === "SIN ACOMPAÑANTE";
      const card = document.createElement("article");
      card.className = "asig-card" + (idx === 0 ? " asig-card--primera" : "");
      card.setAttribute("role", "listitem");

      const ribbon = document.createElement("div");
      ribbon.className = "asig-ribbon";
      ribbon.textContent = idx === 0 ? "Turno principal" : "Tanda " + String(idx + 1);

      const laneCond = document.createElement("div");
      laneCond.className = "asig-lane asig-lane--conductor";
      const badgeC = document.createElement("span");
      badgeC.className = "asig-badge asig-badge--conductor";
      badgeC.textContent = "Conductor";
      const wrapC = document.createElement("div");
      wrapC.className = "asig-lane-body";
      const nameC = document.createElement("p");
      nameC.className = "asig-nombre";
      nameC.textContent = a.conductor;
      wrapC.appendChild(nameC);
      laneCond.appendChild(badgeC);
      laneCond.appendChild(wrapC);

      const bridge = document.createElement("div");
      bridge.className = "asig-bridge";
      bridge.setAttribute("aria-hidden", "true");
      const bridgeLine = document.createElement("span");
      bridgeLine.className = "asig-bridge-line";
      bridge.appendChild(bridgeLine);

      const laneVip = document.createElement("div");
      laneVip.className =
        "asig-lane asig-lane--vip" + (sinVip ? " asig-lane--sin-vip" : "");
      const badgeV = document.createElement("span");
      badgeV.className = "asig-badge asig-badge--vip";
      badgeV.textContent = "VIP";
      const wrapV = document.createElement("div");
      wrapV.className = "asig-lane-body";
      const nameV = document.createElement("p");
      nameV.className = "asig-nombre asig-nombre--vip";
      nameV.textContent = sinVip ? "Sin asignar" : a.acompanante;
      wrapV.appendChild(nameV);
      laneVip.appendChild(badgeV);
      laneVip.appendChild(wrapV);

      card.appendChild(ribbon);
      card.appendChild(laneCond);
      card.appendChild(bridge);
      card.appendChild(laneVip);
      listaAsig.appendChild(card);
    });
  }

  function renderConductoresRef(data) {
    const cond = data.conductores || [];
    const items =
      auth && auth.isAdmin() && Array.isArray(data.conductores_items)
        ? data.conductores_items
        : null;
    conductoresRef.innerHTML = "";
    if (items && items.length > 0) {
      items.forEach(function (row, idx) {
        const wrap = document.createElement("div");
        wrap.className = "conductores-ref-row";
        const name = document.createElement("span");
        name.className = "conductores-ref-name";
        name.textContent = row.nombre;
        const actions = document.createElement("span");
        actions.className = "conductores-ref-actions";
        const atFirst = idx === 0;
        const atLast = idx === items.length - 1;
        function mkBtn(label, disabled, alInicio) {
          const b = document.createElement("button");
          b.type = "button";
          b.className = "btn secondary compact";
          b.textContent = label;
          b.disabled = disabled;
          b.addEventListener("click", async function () {
            setMsg("Actualizando…", "");
            try {
              const r = await apiFetch("/personas/conductores/mover-extremo", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ persona_id: row.id, al_inicio: alInicio }),
              });
              if (!r.ok) throw new Error(await parseError(r));
              await cargar();
              setMsg("Orden de conductores actualizado.", "ok");
            } catch (e) {
              setMsg(String(e.message || e), "error");
            }
          });
          return b;
        }
        actions.appendChild(mkBtn("Al principio", atFirst, true));
        actions.appendChild(mkBtn("Al final", atLast, false));
        wrap.appendChild(name);
        wrap.appendChild(actions);
        conductoresRef.appendChild(wrap);
      });
    } else {
      conductoresRef.textContent = cond.join(", ") || "—";
    }
  }

  function renderAcompaniantesRef(data) {
    const orden = data.acompaniantes_orden || [];
    const items =
      auth && auth.isAdmin() && Array.isArray(data.acompaniantes_items)
        ? data.acompaniantes_items
        : null;
    acompaniantesRef.innerHTML = "";
    if (items && items.length > 0) {
      items.forEach(function (row, idx) {
        const wrap = document.createElement("div");
        wrap.className = "conductores-ref-row";
        const name = document.createElement("span");
        name.className = "conductores-ref-name";
        name.textContent = row.nombre;
        const actions = document.createElement("span");
        actions.className = "conductores-ref-actions";
        const atFirst = idx === 0;
        const atLast = idx === items.length - 1;
        function mkBtn(txt, disabled, alInicio) {
          const b = document.createElement("button");
          b.type = "button";
          b.className = "btn secondary compact";
          b.textContent = txt;
          b.disabled = disabled;
          b.addEventListener("click", function () {
            moverAcompanianteExtremoPorId(row.id, alInicio);
          });
          return b;
        }
        actions.appendChild(mkBtn("Al principio", atFirst, true));
        actions.appendChild(mkBtn("Al final", atLast, false));
        wrap.appendChild(name);
        wrap.appendChild(actions);
        acompaniantesRef.appendChild(wrap);
      });
    } else {
      acompaniantesRef.textContent = orden.join(", ") || "—";
    }
  }

  function renderEstado(data) {
    fechaEl.textContent = data.fecha || "—";

    const orden = data.acompaniantes_orden || [];
    const ordenKey =
      JSON.stringify(orden) + (auth && auth.isAdmin() ? "|admin" : "|user");
    if (ordenKey !== lastOrdenSerialized) {
      lastOrdenSerialized = ordenKey;
      if (auth && auth.isAdmin()) {
        renderChecks(orden, data);
      } else {
        checksEl.innerHTML = "";
      }
    }
    const cond = data.conductores || [];
    const asig = data.asignaciones || [];

    if (asig.length > 0) {
      const p = asig[0];
      resumenEl.textContent = "Hoy: " + p.conductor + " con " + p.acompanante;
    } else if (cond.length && orden.length) {
      resumenEl.textContent =
        "Propuesto: " +
        cond[0] +
        " con " +
        orden[0] +
        " (generá asignación para confirmar)";
    } else {
      resumenEl.textContent = "Sin datos suficientes para la pareja del día.";
    }

    {
      const mt = data.mensaje_turno;
      mensajeEl.value = mt == null || mt === undefined ? "" : String(mt);
    }

    renderAsignacionesLista(asig);

    const nd = data.no_disponibles_hoy || [];
    noDispEl.textContent = nd.length ? nd.join(", ") : "Ninguno";

    renderAlmanaqueSemanal(data);
    renderConductoresRef(data);
    renderAcompaniantesRef(data);
  }

  async function cargar() {
    setMsg("Cargando…", "");
    try {
      const r = await apiFetch("/estado/hoy");
      if (!r.ok) throw new Error(await parseError(r));
      const data = await r.json();
      renderEstado(data);
      setMsg("", "");
    } catch (e) {
      setMsg(String(e.message || e), "error");
    }
  }

  document.getElementById("btn-refrescar").addEventListener("click", async function () {
    lastOrdenSerialized = null;
    await cargar();
  });

  document.getElementById("btn-generar").addEventListener("click", async () => {
    setMsg("Generando…", "");
    try {
      // Siempre enviar la lista marcada (puede ser []). Si enviamos {}, la API
      // interpreta disponibles=null como "todos disponibles".
      const body = { disponibles: disponiblesSeleccionados() };
      const r = await apiFetch("/asignacion/generar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(await parseError(r));
      const res = await r.json();
      await cargar();
      if (Object.prototype.hasOwnProperty.call(res, "mensaje_turno")) {
        const mt = res.mensaje_turno;
        mensajeEl.value = mt == null || mt === undefined ? "" : String(mt);
      }
      setMsg("Asignación generada.", "ok");
    } catch (e) {
      setMsg(String(e.message || e), "error");
    }
  });

  document.getElementById("btn-cerrar").addEventListener("click", async () => {
    if (!window.confirm("¿Cerrar el día y preparar el orden de mañana?")) return;
    setMsg("Cerrando día…", "");
    try {
      const r = await apiFetch("/dia/cerrar", { method: "POST" });
      if (!r.ok) throw new Error(await parseError(r));
      const data = await r.json();
      await cargar();
      if (Object.prototype.hasOwnProperty.call(data, "mensaje_turno")) {
        const mt = data.mensaje_turno;
        mensajeEl.value = mt == null || mt === undefined ? "" : String(mt);
      }
      setMsg(data.mensaje || "Listo.", "ok");
    } catch (e) {
      setMsg(String(e.message || e), "error");
    }
  });

  document.getElementById("btn-copiar").addEventListener("click", async () => {
    const t = mensajeEl.value.trim();
    if (!t) {
      setMsg("No hay mensaje para copiar.", "error");
      return;
    }
    try {
      await navigator.clipboard.writeText(t);
      setMsg("Mensaje copiado al portapapeles.", "ok");
    } catch (_) {
      setMsg("No se pudo copiar (permiso del navegador).", "error");
    }
  });

  if (auth && auth.token) {
    cargar();
  }

  window.__trenRecargarEstado = cargar;
  window.__trenInvalidateOrdenChecks = function () {
    lastOrdenSerialized = null;
  };
})();
