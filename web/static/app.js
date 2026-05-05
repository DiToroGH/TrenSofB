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

  function t(key, vars) {
    return window.trenI18n.t(key, vars);
  }

  /** Serialización del orden de acompañantes; si no cambió, no recreamos los checkboxes (preserva tildes). */
  let lastOrdenSerialized = null;
  let lastEstadoData = null;

  function apiFetch(url, options) {
    const fetchOptions = Object.assign({ cache: "no-store" }, options || {});

    if (auth && auth.token) {
      if (!fetchOptions.headers) {
        fetchOptions.headers = {};
      }
      fetchOptions.headers["Authorization"] = "Bearer " + auth.token;
    }

    return fetch(url, fetchOptions);
  }

  function setMsg(text, kind) {
    msgEl.textContent = text || "";
    msgEl.className = "msg" + (kind ? " " + kind : "");
  }

  async function parseError(r) {
    if (r.status === 401 || r.status === 403) {
      if (auth) {
        auth.logout();
      }
      throw new Error(t("sessionExpired"));
    }

    try {
      const j = await r.json();
      if (j.detail) {
        if (typeof j.detail === "string") return j.detail;
        if (Array.isArray(j.detail))
          return j.detail.map((d) => d.msg || d).join("; ");
      }
    } catch (_) {}
    return r.statusText || t("errorGeneric");
  }

  function unaRonda(conductores, orden, disponiblesSet, idxIn) {
    if (!conductores.length || !orden.length) return { pairs: [], idx: idxIn };
    let idx = idxIn;
    const pairs = [];
    for (let ci = 0; ci < conductores.length; ci++) {
      const conductor = conductores[ci];
      let intentos = 0;
      let asignado = false;
      while (intentos < orden.length) {
        const acomp = orden[idx];
        if (disponiblesSet.has(acomp)) {
          pairs.push({ conductor: conductor, vip: acomp });
          idx = (idx + 1) % orden.length;
          asignado = true;
          break;
        }
        idx = (idx + 1) % orden.length;
        intentos++;
      }
      if (!asignado) {
        pairs.push({ conductor: conductor, vip: "SIN ACOMPAÑANTE" });
      }
    }
    return { pairs: pairs, idx: idx };
  }

  /** Igual que `generar_asignacion` en core/services.py: varias rondas hasta cubrir n parejas. */
  function parejasParaNDias(conductores, orden, disponiblesSet, n) {
    if (!conductores.length || !orden.length) return [];
    let idx = 0;
    const out = [];
    while (out.length < n) {
      const r = unaRonda(conductores, orden, disponiblesSet, idx);
      idx = r.idx;
      for (let i = 0; i < r.pairs.length; i++) {
        out.push(r.pairs[i]);
        if (out.length >= n) break;
      }
    }
    return out;
  }

  function disponiblesSetDesdeEstado(data) {
    const orden = data.acompaniantes_orden || [];
    const noDisp = data.no_disponibles_hoy || [];
    const set = new Set();
    orden.forEach(function (n) {
      if (noDisp.indexOf(n) === -1) set.add(n);
    });
    return set;
  }

  function formatoDiaAlmanaque(cellDate) {
    const tag = window.trenI18n.getLocaleTag();
    let wk = new Intl.DateTimeFormat(tag, { weekday: "short" }).format(
      cellDate
    );
    wk = wk.replace(/\.$/, "");
    if (wk.length) wk = wk.charAt(0).toUpperCase() + wk.slice(1);
    const mon = new Intl.DateTimeFormat(tag, { month: "short" }).format(
      cellDate
    );
    const monClean = mon.replace(/\.$/, "");
    const num = cellDate.getDate();
    return { diaSem: wk, fechaTxt: String(num) + " " + monClean };
  }

  async function moverAcompanianteExtremoPorId(personaId, alInicio) {
    setMsg(t("updating"), "");
    try {
      const r = await apiFetch("/personas/acompaniantes/mover-extremo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ persona_id: personaId, al_inicio: alInicio }),
      });
      if (!r.ok) throw new Error(await parseError(r));
      lastOrdenSerialized = null;
      await cargar();
      setMsg(t("orderCompanionsOk"), "ok");
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
        actions.appendChild(mkBtn(t("moveStart"), atFirst, true));
        actions.appendChild(mkBtn(t("moveEnd"), atLast, false));
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
        etiqueta: t("statusConfirmed"),
      };
    }
    if (cond.length && orden.length) {
      return {
        conductor: cond[0],
        vip: orden[0],
        etiqueta: t("statusProposed"),
      };
    }
    return { conductor: null, vip: null, etiqueta: null };
  }

  function resumenVipNombre(v) {
    if (v === "SIN ACOMPAÑANTE" || v == null) return t("unassigned");
    return v;
  }

  function renderAlmanaqueSemanal(data) {
    if (!almanaqueEl) return;
    almanaqueEl.innerHTML = "";
    const hoy = new Date();
    const claveHoy = fechaClaveLocal(hoy);
    const inicio = inicioSemanaLunes(hoy);
    const parejaHoy = parejaDesdeEstado(data);

    const cond = data.conductores || [];
    const orden = data.acompaniantes_orden || [];
    const disp = disponiblesSetDesdeEstado(data);
    const pairs = parejasParaNDias(cond, orden, disp, 7);

    for (let i = 0; i < 7; i++) {
      const cellDate = new Date(
        inicio.getFullYear(),
        inicio.getMonth(),
        inicio.getDate() + i
      );
      const clave = fechaClaveLocal(cellDate);
      const esHoy = clave === claveHoy;
      const { diaSem, fechaTxt } = formatoDiaAlmanaque(cellDate);

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
      timeEl.textContent = fechaTxt;
      head.appendChild(wk);
      head.appendChild(timeEl);
      article.appendChild(head);

      const tandaEl = document.createElement("div");
      tandaEl.className = "almanaque-tanda";
      tandaEl.textContent =
        i === 0 ? t("mainShift") : t("shiftN", { n: String(i + 1) });
      article.appendChild(tandaEl);

      const slot = pairs[i];
      let cText = t("dash");
      let vText = t("dash");
      let vClass = "almanaque-par-nombre almanaque-par-nombre--muted";
      let cClass = "almanaque-par-nombre almanaque-par-nombre--muted";

      if (slot && slot.conductor) {
        cClass = "almanaque-par-nombre";
        cText = slot.conductor;
      }
      if (slot && slot.vip) {
        if (slot.vip === "SIN ACOMPAÑANTE") {
          vText = t("unassigned");
          vClass = "almanaque-par-nombre almanaque-par-nombre--muted";
        } else {
          vText = slot.vip;
          vClass = "almanaque-par-nombre almanaque-par-nombre--vip";
        }
      }

      const laneC = document.createElement("div");
      laneC.className = "almanaque-par";
      const bc = document.createElement("span");
      bc.className = "almanaque-par-badge almanaque-par-badge--cond";
      bc.textContent = t("badgeConductor");
      const nc = document.createElement("p");
      nc.className = cClass;
      nc.textContent = cText;
      laneC.appendChild(bc);
      laneC.appendChild(nc);

      const laneV = document.createElement("div");
      laneV.className = "almanaque-par";
      const bv = document.createElement("span");
      bv.className = "almanaque-par-badge almanaque-par-badge--vip";
      bv.textContent = t("badgeVip");
      const nv = document.createElement("p");
      nv.className = vClass;
      nv.textContent = vText;
      laneV.appendChild(bv);
      laneV.appendChild(nv);

      article.appendChild(laneC);
      article.appendChild(laneV);

      if (esHoy && parejaHoy.etiqueta) {
        const tag = document.createElement("p");
        tag.className = "almanaque-estado";
        tag.textContent = parejaHoy.etiqueta;
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
      empty.textContent = t("noAssignments");
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
      ribbon.textContent =
        idx === 0 ? t("mainShift") : t("shiftN", { n: String(idx + 1) });

      const laneCond = document.createElement("div");
      laneCond.className = "asig-lane asig-lane--conductor";
      const badgeC = document.createElement("span");
      badgeC.className = "asig-badge asig-badge--conductor";
      badgeC.textContent = t("badgeConductor");
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
      badgeV.textContent = t("badgeVip");
      const wrapV = document.createElement("div");
      wrapV.className = "asig-lane-body";
      const nameV = document.createElement("p");
      nameV.className = "asig-nombre asig-nombre--vip";
      nameV.textContent = sinVip ? t("unassigned") : a.acompanante;
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
            setMsg(t("updating"), "");
            try {
              const r = await apiFetch("/personas/conductores/mover-extremo", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ persona_id: row.id, al_inicio: alInicio }),
              });
              if (!r.ok) throw new Error(await parseError(r));
              await cargar();
              setMsg(t("orderDriversOk"), "ok");
            } catch (e) {
              setMsg(String(e.message || e), "error");
            }
          });
          return b;
        }
        actions.appendChild(mkBtn(t("moveStart"), atFirst, true));
        actions.appendChild(mkBtn(t("moveEnd"), atLast, false));
        wrap.appendChild(name);
        wrap.appendChild(actions);
        conductoresRef.appendChild(wrap);
      });
    } else {
      conductoresRef.textContent = cond.join(", ") || t("dash");
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
        actions.appendChild(mkBtn(t("moveStart"), atFirst, true));
        actions.appendChild(mkBtn(t("moveEnd"), atLast, false));
        wrap.appendChild(name);
        wrap.appendChild(actions);
        acompaniantesRef.appendChild(wrap);
      });
    } else {
      acompaniantesRef.textContent = orden.join(", ") || t("dash");
    }
  }

  function renderEstado(data) {
    lastEstadoData = data;
    fechaEl.textContent = data.fecha || t("dash");

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
      resumenEl.textContent = t("summaryToday", {
        c: p.conductor,
        v: resumenVipNombre(p.acompanante),
      });
    } else if (cond.length && orden.length) {
      resumenEl.textContent = t("summaryProposed", {
        c: cond[0],
        v: resumenVipNombre(orden[0]),
      });
    } else {
      resumenEl.textContent = t("summaryNoData");
    }

    {
      const mt = data.mensaje_turno;
      mensajeEl.value = mt == null || mt === undefined ? "" : String(mt);
    }

    renderAsignacionesLista(asig);

    const nd = data.no_disponibles_hoy || [];
    noDispEl.textContent = nd.length ? nd.join(", ") : t("none");

    renderAlmanaqueSemanal(data);
    renderConductoresRef(data);
    renderAcompaniantesRef(data);
  }

  async function cargar() {
    setMsg(t("loading"), "");
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

  document
    .getElementById("btn-refrescar")
    .addEventListener("click", async function () {
      lastOrdenSerialized = null;
      await cargar();
    });

  document.getElementById("btn-generar").addEventListener("click", async () => {
    setMsg(t("generating"), "");
    try {
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
      setMsg(t("assignmentGenerated"), "ok");
    } catch (e) {
      setMsg(String(e.message || e), "error");
    }
  });

  document.getElementById("btn-cerrar").addEventListener("click", async () => {
    if (!window.confirm(t("confirmCloseDay"))) return;
    setMsg(t("closingDay"), "");
    try {
      const r = await apiFetch("/dia/cerrar", { method: "POST" });
      if (!r.ok) throw new Error(await parseError(r));
      const data = await r.json();
      await cargar();
      if (Object.prototype.hasOwnProperty.call(data, "mensaje_turno")) {
        const mt = data.mensaje_turno;
        mensajeEl.value = mt == null || mt === undefined ? "" : String(mt);
      }
      setMsg(data.mensaje || t("done"), "ok");
    } catch (e) {
      setMsg(String(e.message || e), "error");
    }
  });

  document.getElementById("btn-copiar").addEventListener("click", async () => {
    const txt = mensajeEl.value.trim();
    if (!txt) {
      setMsg(t("noMsgCopy"), "error");
      return;
    }
    try {
      await navigator.clipboard.writeText(txt);
      setMsg(t("copied"), "ok");
    } catch (_) {
      setMsg(t("copyFailed"), "error");
    }
  });

  window.addEventListener("tren-lang-change", function () {
    window.trenI18n.syncLangSelects();
    if (lastEstadoData) renderEstado(lastEstadoData);
  });

  if (auth && auth.token) {
    cargar();
  }

  window.__trenRecargarEstado = cargar;
  window.__trenInvalidateOrdenChecks = function () {
    lastOrdenSerialized = null;
  };
})();
