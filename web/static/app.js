(function () {
  const msgEl = document.getElementById("msg");
  const fechaEl = document.getElementById("fecha");
  const resumenEl = document.getElementById("resumen-hoy");
  const mensajeEl = document.getElementById("mensaje-turno");
  const checksEl = document.getElementById("checks");
  const listaAsig = document.getElementById("lista-asignaciones");
  const noDispEl = document.getElementById("no-disp");
  const conductoresRef = document.getElementById("conductores-ref");
  const ordenRef = document.getElementById("orden-ref");

  /** Serialización del orden de acompañantes; si no cambió, no recreamos los checkboxes (preserva tildes). */
  let lastOrdenSerialized = null;

  function apiFetch(url, options) {
    return fetch(url, Object.assign({ cache: "no-store" }, options || {}));
  }

  function setMsg(text, kind) {
    msgEl.textContent = text || "";
    msgEl.className = "msg" + (kind ? " " + kind : "");
  }

  async function parseError(r) {
    try {
      const j = await r.json();
      if (j.detail) {
        if (typeof j.detail === "string") return j.detail;
        if (Array.isArray(j.detail)) return j.detail.map((d) => d.msg || d).join("; ");
      }
    } catch (_) {}
    return r.statusText || "Error";
  }

  function renderChecks(nombres) {
    checksEl.innerHTML = "";
    nombres.forEach((nombre) => {
      const id = "chk-" + encodeURIComponent(nombre).replace(/%/g, "_");
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = true;
      input.dataset.nombre = nombre;
      input.id = id;
      label.appendChild(input);
      label.appendChild(document.createTextNode(nombre));
      checksEl.appendChild(label);
    });
  }

  function disponiblesSeleccionados() {
    const out = [];
    checksEl.querySelectorAll("input[type=checkbox]").forEach((inp) => {
      if (inp.checked && inp.dataset.nombre) out.push(inp.dataset.nombre);
    });
    return out;
  }

  function renderEstado(data) {
    fechaEl.textContent = data.fecha || "—";

    const orden = data.acompaniantes_orden || [];
    const ordenKey = JSON.stringify(orden);
    if (ordenKey !== lastOrdenSerialized) {
      lastOrdenSerialized = ordenKey;
      renderChecks(orden);
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

    listaAsig.innerHTML = "";
    if (asig.length === 0) {
      const li = document.createElement("li");
      li.textContent = "Aún no hay asignaciones.";
      listaAsig.appendChild(li);
    } else {
      asig.forEach((a) => {
        const li = document.createElement("li");
        li.textContent = a.conductor + " → " + a.acompanante;
        listaAsig.appendChild(li);
      });
    }

    const nd = data.no_disponibles_hoy || [];
    noDispEl.textContent = nd.length ? nd.join(", ") : "Ninguno";

    conductoresRef.textContent = cond.join(", ") || "—";
    ordenRef.textContent = orden.join(", ") || "—";
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

  cargar();

  window.__trenRecargarEstado = cargar;
  window.__trenInvalidateOrdenChecks = function () {
    lastOrdenSerialized = null;
  };
})();
