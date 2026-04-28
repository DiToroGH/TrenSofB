(function () {
  const dlg = document.getElementById("dlg-gestion");
  const btnGestion = document.getElementById("btn-gestion");
  const btnCerrarDlg = document.getElementById("dlg-gestion-cerrar");
  const msgG = document.getElementById("msg-gestion");

  const tabBtns = document.querySelectorAll(".gestion-tabs .tab");
  const panelCond = document.getElementById("panel-cond");
  const panelAcomp = document.getElementById("panel-acomp");

  const listaCond = document.getElementById("lista-cond");
  const listaAcomp = document.getElementById("lista-acomp");
  const filtroCond = document.getElementById("filtro-cond");
  const filtroAcomp = document.getElementById("filtro-acomp");
  const nombreCond = document.getElementById("nombre-cond");
  const nombreAcomp = document.getElementById("nombre-acomp");
  const metaCond = document.getElementById("meta-cond");
  const metaAcomp = document.getElementById("meta-acomp");
  const masivaTa = document.getElementById("masiva-acomp");

  if (!dlg || !btnGestion) return;

  let conductores = [];
  let acompaniantes = [];
  let selCondId = null;
  let selAcompId = null;

  function setMsgG(text, kind) {
    msgG.textContent = text || "";
    msgG.className = "msg-gestion" + (kind === "error" ? " error" : "");
  }

  async function parseError(r) {
    try {
      const j = await r.json();
      if (j.detail) {
        if (typeof j.detail === "string") return j.detail;
        if (Array.isArray(j.detail)) return j.detail.map(function (d) { return d.msg || d; }).join("; ");
      }
    } catch (_) {}
    return r.statusText || "Error";
  }

  function recargarPrincipal() {
    if (typeof window.__trenRecargarEstado === "function") {
      window.__trenRecargarEstado();
    }
  }

  async function fetchConductores() {
    const r = await fetch("/personas/conductores");
    if (!r.ok) throw new Error(await parseError(r));
    conductores = await r.json();
  }

  async function fetchAcompaniantes() {
    const r = await fetch("/personas/acompaniantes");
    if (!r.ok) throw new Error(await parseError(r));
    acompaniantes = await r.json();
  }

  async function cargarTodo() {
    await fetchConductores();
    await fetchAcompaniantes();
    renderLista("cond");
    renderLista("acomp");
  }

  function filtrar(items, texto) {
    const t = texto.trim().toLowerCase();
    if (!t) return items.slice();
    return items.filter(function (x) { return x.nombre.toLowerCase().indexOf(t) !== -1; });
  }

  function renderLista(tipo) {
    const isCond = tipo === "cond";
    const ul = isCond ? listaCond : listaAcomp;
    const filtro = isCond ? filtroCond : filtroAcomp;
    const meta = isCond ? metaCond : metaAcomp;
    const items = isCond ? conductores : acompaniantes;
    const selId = isCond ? selCondId : selAcompId;
    const filtrados = filtrar(items, filtro.value);

    ul.innerHTML = "";
    filtrados.forEach(function (p) {
      const li = document.createElement("li");
      li.textContent = p.nombre;
      li.dataset.id = String(p.id);
      if (p.id === selId) li.classList.add("selected");
      li.addEventListener("click", function () {
        if (isCond) {
          selCondId = p.id;
          nombreCond.value = p.nombre;
        } else {
          selAcompId = p.id;
          nombreAcomp.value = p.nombre;
        }
        renderLista("cond");
        renderLista("acomp");
      });
      ul.appendChild(li);
    });
    meta.textContent =
      "Mostrando " + filtrados.length + " de " + items.length + " registros.";
  }

  function setTab(which) {
    tabBtns.forEach(function (b) {
      const on = b.getAttribute("data-panel") === (which === "cond" ? "panel-cond" : "panel-acomp");
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    panelCond.hidden = which !== "cond";
    panelAcomp.hidden = which !== "acomp";
  }

  tabBtns.forEach(function (b) {
    b.addEventListener("click", function () {
      const panel = b.getAttribute("data-panel");
      setTab(panel === "panel-cond" ? "cond" : "acomp");
      setMsgG("");
    });
  });

  function seleccionId(tipo) {
    return tipo === "cond" ? selCondId : selAcompId;
  }

  function basePath(tipo) {
    return tipo === "cond" ? "/personas/conductores" : "/personas/acompaniantes";
  }

  async function postAlta(tipo) {
    const inp = tipo === "cond" ? nombreCond : nombreAcomp;
    const nombre = inp.value.trim();
    if (!nombre) {
      setMsgG("Ingresá un nombre.", "error");
      return;
    }
    const r = await fetch(basePath(tipo), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre: nombre }),
    });
    if (!r.ok) throw new Error(await parseError(r));
    const created = await r.json();
    if (tipo === "cond") {
      selCondId = created.id;
      nombreCond.value = created.nombre;
    } else {
      selAcompId = created.id;
      nombreAcomp.value = created.nombre;
    }
  }

  async function patchEditar(tipo) {
    const id = seleccionId(tipo);
    const inp = tipo === "cond" ? nombreCond : nombreAcomp;
    const nombre = inp.value.trim();
    if (!id) {
      setMsgG("Seleccioná un registro.", "error");
      return;
    }
    if (!nombre) {
      setMsgG("Ingresá el nuevo nombre.", "error");
      return;
    }
    const r = await fetch(basePath(tipo) + "/" + id, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre: nombre }),
    });
    if (!r.ok) throw new Error(await parseError(r));
  }

  async function deleteBaja(tipo) {
    const id = seleccionId(tipo);
    if (!id) {
      setMsgG("Seleccioná un registro.", "error");
      return;
    }
    var items = tipo === "cond" ? conductores : acompaniantes;
    var row = items.filter(function (x) { return x.id === id; })[0];
    if (!window.confirm("¿Eliminar '" + (row ? row.nombre : id) + "'?")) return;
    const r = await fetch(basePath(tipo) + "/" + id, { method: "DELETE" });
    if (!r.ok) throw new Error(await parseError(r));
    if (tipo === "cond") {
      selCondId = null;
      nombreCond.value = "";
    } else {
      selAcompId = null;
      nombreAcomp.value = "";
    }
  }

  async function postMover(tipo, direccion) {
    const id = seleccionId(tipo);
    if (!id) {
      setMsgG("Seleccioná un registro.", "error");
      return;
    }
    const r = await fetch(basePath(tipo) + "/mover", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ persona_id: id, direccion: direccion }),
    });
    if (!r.ok) throw new Error(await parseError(r));
  }

  async function postMoverExtremo(tipo, alInicio) {
    const id = seleccionId(tipo);
    if (!id) {
      setMsgG("Seleccioná un registro.", "error");
      return;
    }
    const r = await fetch(basePath(tipo) + "/mover-extremo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ persona_id: id, al_inicio: alInicio }),
    });
    if (!r.ok) throw new Error(await parseError(r));
  }

  async function postMasiva() {
    const texto = masivaTa.value;
    if (!texto.trim()) {
      setMsgG("No hay nombres para cargar.", "error");
      return;
    }
    const r = await fetch("/personas/acompaniantes/carga-masiva", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto: texto }),
    });
    if (!r.ok) throw new Error(await parseError(r));
    const res = await r.json();
    masivaTa.value = "";
    setMsgG(
      "Agregados: " + res.agregados + " · Omitidos (duplicados): " + res.duplicados +
        (res.errores ? " · Errores: " + res.errores : ""),
      ""
    );
  }

  function wireAcciones(tipo) {
    var prefix = tipo === "cond" ? "cond" : "acomp";
    async function run(fn) {
      try {
        setMsgG("…", "");
        await fn();
        await cargarTodo();
        if (tipo === "acomp" && typeof window.__trenInvalidateOrdenChecks === "function") {
          window.__trenInvalidateOrdenChecks();
        }
        recargarPrincipal();
        setMsgG("Listo.", "");
      } catch (e) {
        setMsgG(String(e.message || e), "error");
      }
    }
    document.getElementById(prefix + "-alta").onclick = function () {
      run(function () { return postAlta(tipo); });
    };
    document.getElementById(prefix + "-editar").onclick = function () {
      run(function () { return patchEditar(tipo); });
    };
    document.getElementById(prefix + "-baja").onclick = function () {
      run(function () { return deleteBaja(tipo); });
    };
    document.getElementById(prefix + "-subir").onclick = function () {
      run(function () { return postMover(tipo, -1); });
    };
    document.getElementById(prefix + "-bajar").onclick = function () {
      run(function () { return postMover(tipo, 1); });
    };
    document.getElementById(prefix + "-inicio").onclick = function () {
      run(function () { return postMoverExtremo(tipo, true); });
    };
    document.getElementById(prefix + "-final").onclick = function () {
      run(function () { return postMoverExtremo(tipo, false); });
    };
  }

  wireAcciones("cond");
  wireAcciones("acomp");

  document.getElementById("acomp-masiva").addEventListener("click", async function () {
    try {
      setMsgG("…", "");
      await postMasiva();
      await cargarTodo();
      if (typeof window.__trenInvalidateOrdenChecks === "function") {
        window.__trenInvalidateOrdenChecks();
      }
      recargarPrincipal();
    } catch (e) {
      setMsgG(String(e.message || e), "error");
    }
  });

  filtroCond.addEventListener("input", function () { renderLista("cond"); });
  filtroAcomp.addEventListener("input", function () { renderLista("acomp"); });

  nombreCond.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      document.getElementById("cond-alta").click();
    }
  });
  nombreAcomp.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      document.getElementById("acomp-alta").click();
    }
  });

  btnGestion.addEventListener("click", async function () {
    setMsgG("");
    setTab("cond");
    try {
      await cargarTodo();
      if (typeof dlg.showModal === "function") dlg.showModal();
    } catch (e) {
      if (typeof dlg.showModal === "function") dlg.showModal();
      setMsgG(String(e.message || e), "error");
    }
  });

  btnCerrarDlg.addEventListener("click", function () {
    dlg.close();
    setMsgG("");
  });

  dlg.addEventListener("cancel", function (e) {
    e.preventDefault();
    dlg.close();
  });
})();
