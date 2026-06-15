import sqlite3
from datetime import date
import tkinter as tk
from tkinter import ttk, messagebox

from core.services import (
    asignaciones_a_json,
    asignaciones_desde_json,
    conductor_rota_al_cerrar,
    estado_despues_cierre,
    fusionar_orden_acompaniantes_con_db,
    generar_asignacion as calcular_asignacion,
    generar_texto_turno,
    normalizar_fijos_semana,
    orden_conductores_para_dia,
    resolver_pareja_cierre,
    sanitizar_segundo_acompaniante_estado,
)
from infra import repositories as repo
from infra.state_sync import persistir_orden_sqlite_acompaniantes_desde_estado


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Train Schedule Management. By Di Toro")
        self.geometry("980x620")
        repo.inicializar_db()
        self.conductores = repo.cargar_conductores()
        self.estado = repo.cargar_estado()
        self.check_vars = {}
        raw_asig = self.estado.get("asignaciones_hoy")
        self.resultados = asignaciones_desde_json(
            raw_asig if isinstance(raw_asig, list) else None
        )
        self.crear_ui()
        self.refrescar_ui()

    def crear_ui(self):
        frame_top = ttk.Frame(self, padding=10)
        frame_top.pack(fill="x")
        self.lbl_fecha = ttk.Label(frame_top, text="")
        self.lbl_fecha.pack(side="left")
        ttk.Button(frame_top, text="Gestionar personas", command=self.abrir_gestion).pack(side="right", padx=5)
        ttk.Button(frame_top, text="Generar asignación de hoy", command=self.generar_asignacion).pack(side="right", padx=5)
        ttk.Button(frame_top, text="Cerrar día (preparar mañana)", command=self.cerrar_dia).pack(side="right", padx=5)

        frame_hoy = ttk.LabelFrame(self, text="Conductor y acompañante del día", padding=10)
        frame_hoy.pack(fill="x", padx=10)
        self.lbl_hoy = ttk.Label(frame_hoy, text="Aún no hay asignación generada para hoy.")
        self.lbl_hoy.pack(anchor="w")
        self.lbl_msg_turno = ttk.Label(frame_hoy, text="", wraplength=920, justify="left")
        self.lbl_msg_turno.pack(anchor="w", pady=(6, 0))
        ttk.Button(frame_hoy, text="Copiar mensaje", command=self.copiar_mensaje_turno).pack(anchor="e", pady=(6, 0))

        frame_mid = ttk.Frame(self, padding=10)
        frame_mid.pack(fill="both", expand=True)

        left = ttk.LabelFrame(frame_mid, text="Disponibilidad de acompañantes (hoy)", padding=10)
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.frame_checks_container = ttk.Frame(left)
        self.frame_checks_container.pack(fill="both", expand=True)
        self.canvas_checks = tk.Canvas(self.frame_checks_container, highlightthickness=0)
        self.scroll_checks = ttk.Scrollbar(
            self.frame_checks_container, orient="vertical", command=self.canvas_checks.yview
        )
        self.frame_checks = ttk.Frame(self.canvas_checks)
        self.canvas_checks.configure(yscrollcommand=self.scroll_checks.set)
        self.canvas_checks.pack(side="left", fill="both", expand=True)
        self.scroll_checks.pack(side="right", fill="y")
        self.canvas_checks_window = self.canvas_checks.create_window(
            (0, 0), window=self.frame_checks, anchor="nw"
        )
        self.frame_checks.bind(
            "<Configure>",
            lambda _e: self.canvas_checks.configure(scrollregion=self.canvas_checks.bbox("all"))
        )
        self.canvas_checks.bind(
            "<Configure>",
            lambda e: self.canvas_checks.itemconfigure(self.canvas_checks_window, width=e.width)
        )
        ttk.Label(left, text="Segundo acompañante (opcional):").pack(anchor="w", pady=(8, 2))
        self.var_segundo_acomp = tk.StringVar(value="")
        self.cmb_segundo_acomp = ttk.Combobox(
            left, textvariable=self.var_segundo_acomp, state="readonly", width=36
        )
        self.cmb_segundo_acomp.pack(anchor="w", fill="x")
        self.cmb_segundo_acomp.bind("<<ComboboxSelected>>", self._on_segundo_acomp_change)

        right = ttk.LabelFrame(frame_mid, text="Asignaciones", padding=10)
        right.pack(side="left", fill="both", expand=True, padx=(5, 0))
        self.txt_resultados = tk.Text(right, height=20)
        self.txt_resultados.pack(fill="both", expand=True)

        frame_bottom = ttk.Frame(self, padding=10)
        frame_bottom.pack(fill="x")
        self.lbl_orden = ttk.Label(frame_bottom, text="")
        self.lbl_orden.pack(anchor="w")

    def refrescar_datos(self):
        self.conductores = repo.cargar_conductores()
        acompaniantes_db = repo.cargar_acompaniantes()
        orden_actual = self.estado.get("acompaniantes_orden", [])
        self.estado["acompaniantes_orden"] = fusionar_orden_acompaniantes_con_db(
            orden_actual, acompaniantes_db
        )
        repo.guardar_estado(self.estado)

    def refrescar_ui(self):
        self.refrescar_datos()
        self.lbl_fecha.config(text=f"Fecha estado: {self.estado['fecha']}")
        for w in self.frame_checks.winfo_children():
            w.destroy()
        self.check_vars.clear()
        for nombre in self.estado["acompaniantes_orden"]:
            var = tk.BooleanVar(value=True)
            self.check_vars[nombre] = var
            ttk.Checkbutton(
                self.frame_checks,
                text=nombre,
                variable=var,
                onvalue=True,
                offvalue=False,
            ).pack(anchor="w")
        self.canvas_checks.update_idletasks()
        self.canvas_checks.configure(scrollregion=self.canvas_checks.bbox("all"))
        self._refrescar_combo_segundo_acomp()
        self.lbl_orden.config(text=f"Orden actual acompañantes: {self.estado['acompaniantes_orden']}")
        self.actualizar_panel_hoy()
        self.mostrar_resultados()

    def _vip_actual(self) -> str | None:
        if self.resultados:
            a = self.resultados[0][1]
            if a and a != "SIN ACOMPAÑANTE":
                return a
        orden = self.estado.get("acompaniantes_orden", [])
        return orden[0] if orden else None

    def _refrescar_combo_segundo_acomp(self, *, persistir: bool = True):
        orden = self.estado.get("acompaniantes_orden", [])
        vip = self._vip_actual()
        sanitizar_segundo_acompaniante_estado(self.estado, vip, orden)
        if persistir:
            repo.guardar_estado(self.estado)
        opciones = [""] + [n for n in orden if n != vip]
        self.cmb_segundo_acomp["values"] = opciones
        actual = str(self.estado.get("segundo_acompanante_hoy") or "").strip()
        if actual and actual in opciones:
            self.var_segundo_acomp.set(actual)
        else:
            self.var_segundo_acomp.set("")

    def _on_segundo_acomp_change(self, _event=None):
        elegido = self.var_segundo_acomp.get().strip()
        vip = self._vip_actual()
        if elegido and vip and elegido == vip:
            messagebox.showwarning("Atención", "No puede ser el mismo VIP del turno.")
            self._refrescar_combo_segundo_acomp()
            return
        if elegido:
            self.estado["segundo_acompanante_hoy"] = elegido
        else:
            self.estado.pop("segundo_acompanante_hoy", None)
        repo.guardar_estado(self.estado)
        self.actualizar_panel_hoy()

    def _weekday_operativo(self) -> int:
        raw = str(self.estado.get("fecha") or date.today()).strip()[:10]
        try:
            return date.fromisoformat(raw).weekday()
        except ValueError:
            return date.today().weekday()

    def _conductores_para_hoy(self) -> list[str]:
        fijos = normalizar_fijos_semana(self.estado.get("conductores_fijos_semana"))
        return orden_conductores_para_dia(self.conductores, fijos, self._weekday_operativo())

    def _disponibles_para_mensaje(self) -> set[str] | None:
        raw = self.estado.get("disponibles_hoy")
        if isinstance(raw, list):
            return {str(x) for x in raw}
        if self.check_vars:
            return {n for n, v in self.check_vars.items() if bool(v.get())}
        return None

    def actualizar_panel_hoy(self):
        orden = self.estado.get("acompaniantes_orden", [])
        disp = self._disponibles_para_mensaje()
        segundo = str(self.estado.get("segundo_acompanante_hoy") or "").strip()
        if self.resultados:
            conductor, acomp = self.resultados[0]
            txt = f"Hoy: {conductor} con {acomp}"
            if segundo:
                txt += f" y {segundo}"
            self.lbl_hoy.config(text=txt)
            self.lbl_msg_turno.config(
                text=generar_texto_turno(conductor, acomp, orden, disponibles=disp)
            )
            return
        cond_hoy = self._conductores_para_hoy()
        if cond_hoy and orden:
            self.lbl_hoy.config(
                text=f"Propuesto: {cond_hoy[0]} con {orden[0]} (genera asignación para confirmar)"
            )
            self.lbl_msg_turno.config(
                text=generar_texto_turno(
                    cond_hoy[0], orden[0], orden, disponibles=disp
                )
            )
            return
        self.lbl_hoy.config(text="Sin datos suficientes para mostrar la pareja del día.")
        self.lbl_msg_turno.config(text="")

    def copiar_mensaje_turno(self):
        texto = self.lbl_msg_turno.cget("text").strip()
        if not texto:
            messagebox.showwarning("Atención", "No hay mensaje para copiar.")
            return
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.update_idletasks()
        messagebox.showinfo("Listo", "Mensaje copiado al portapapeles.")

    def generar_asignacion(self):
        orden = self.estado["acompaniantes_orden"][:]
        disponibles = {n for n, v in self.check_vars.items() if bool(v.get())}
        if not self.conductores:
            messagebox.showerror("Error", "No hay conductores cargados.")
            return
        if not orden:
            messagebox.showerror("Error", "No hay acompañantes cargados.")
            return

        cond_hoy = self._conductores_para_hoy()
        if not cond_hoy:
            messagebox.showerror("Error", "No hay conductores activos para este día.")
            return
        asignaciones, no_disp = calcular_asignacion(
            cond_hoy, orden, disponibles
        )
        self.estado["no_disponibles_hoy"] = no_disp
        self.resultados = asignaciones
        self.estado["asignaciones_hoy"] = asignaciones_a_json(asignaciones)
        self.estado["disponibles_hoy"] = [x for x in orden if x in disponibles]
        vip_nuevo = asignaciones[0][1] if asignaciones else None
        sanitizar_segundo_acompaniante_estado(self.estado, vip_nuevo, orden)
        repo.guardar_estado(self.estado)
        self._refrescar_combo_segundo_acomp(persistir=False)
        self.actualizar_panel_hoy()
        self.mostrar_resultados()
        self.update_idletasks()

    def mostrar_resultados(self):
        self.txt_resultados.delete("1.0", tk.END)
        if not self.resultados:
            self.txt_resultados.insert(tk.END, "Aún no hay asignaciones.\n")
            return
        self.txt_resultados.insert(tk.END, "Asignación de hoy:\n\n")
        segundo = str(self.estado.get("segundo_acompanante_hoy") or "").strip()
        for i, (conductor, acomp) in enumerate(self.resultados):
            linea = f"- {conductor} -> {acomp}"
            if i == 0 and segundo:
                linea += f" (+ 2.º acomp.: {segundo})"
            self.txt_resultados.insert(tk.END, linea + "\n")
        nd = self.estado.get("no_disponibles_hoy", [])
        self.txt_resultados.insert(tk.END, "\nNo disponibles hoy (suben al tope mañana):\n")
        self.txt_resultados.insert(tk.END, f"{nd if nd else 'Ninguno'}\n")

    def cerrar_dia(self):
        fijos = normalizar_fijos_semana(self.estado.get("conductores_fijos_semana"))
        weekday = self._weekday_operativo()
        conductor_hoy, acomp_hoy = resolver_pareja_cierre(
            self.resultados,
            self.conductores,
            self.estado["acompaniantes_orden"],
            weekday=weekday,
            fijos_semana=fijos,
        )
        segundo_hoy = str(self.estado.get("segundo_acompanante_hoy") or "").strip() or None

        if conductor_hoy and conductor_rota_al_cerrar(conductor_hoy, fijos, weekday):
            repo.mover_persona_al_final("conductores", conductor_hoy)

        self.estado = estado_despues_cierre(
            self.estado,
            conductor_hoy,
            acomp_hoy,
            str(date.today()),
            segundo_acompanante_hoy=segundo_hoy,
        )
        self.estado.pop("asignaciones_hoy", None)
        self.estado.pop("disponibles_hoy", None)
        repo.guardar_estado(self.estado)
        persistir_orden_sqlite_acompaniantes_desde_estado(self.estado)
        self.resultados = []
        self.refrescar_ui()
        self.mostrar_resultados()
        self.update_idletasks()
        messagebox.showinfo("Listo", "Día cerrado. Orden de mañana actualizado.")

    def abrir_gestion(self):
        ventana = tk.Toplevel(self)
        ventana.title("Gestión de conductores y acompañantes")
        ventana.geometry("860x520")
        ventana.transient(self)
        ventana.grab_set()

        frame = ttk.Frame(ventana, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Gestiona altas, bajas, edición y orden. Usa Enter para alta rápida."
        ).pack(anchor="w", pady=(0, 8))

        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True)
        self._crear_panel_gestion(
            notebook,
            "Conductores",
            "conductores",
            permitir_drag=True,
            permitir_carga_masiva=False,
            padre_ventana=ventana,
        )
        self._crear_panel_gestion(
            notebook,
            "Acompañantes",
            "acompaniantes",
            permitir_drag=False,
            permitir_carga_masiva=True,
            padre_ventana=ventana,
        )

        def cerrar():
            self.refrescar_ui()
            self.mostrar_resultados()
            ventana.destroy()

        ttk.Button(frame, text="Cerrar", command=cerrar).pack(anchor="e", pady=(10, 0))

    def _crear_panel_gestion(self, notebook, titulo, tabla, permitir_drag, permitir_carga_masiva, padre_ventana):
        panel = ttk.Frame(notebook, padding=10)
        notebook.add(panel, text=titulo)

        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(2, weight=1)

        ttk.Label(panel, text=f"Listado de {titulo.lower()}").grid(row=0, column=0, sticky="w")
        filtro_var = tk.StringVar()
        ttk.Entry(panel, textvariable=filtro_var).grid(row=1, column=0, sticky="ew", pady=(4, 8))

        lista = tk.Listbox(panel, height=14)
        lista.grid(row=2, column=0, sticky="nsew")

        entrada = ttk.Entry(panel)
        entrada.grid(row=3, column=0, sticky="ew", pady=(8, 6))

        estado_label = ttk.Label(panel, text="")
        estado_label.grid(row=5, column=0, sticky="w", pady=(6, 0))

        cache = {"items": [], "items_filtrados": []}
        drag_state = {"from_id": None}

        def seleccionar_id(persona_id):
            for idx, (pid, _nombre) in enumerate(cache["items_filtrados"]):
                if pid == persona_id:
                    lista.selection_clear(0, tk.END)
                    lista.selection_set(idx)
                    lista.activate(idx)
                    break

        def recargar(persona_id=None):
            cache["items"] = repo.listar_personas(tabla)
            aplicar_filtro()
            if persona_id is not None:
                seleccionar_id(persona_id)

        def aplicar_filtro(*_args):
            texto = filtro_var.get().strip().casefold()
            if texto:
                cache["items_filtrados"] = [x for x in cache["items"] if texto in x[1].casefold()]
            else:
                cache["items_filtrados"] = cache["items"][:]
            lista.delete(0, tk.END)
            for _pid, nombre in cache["items_filtrados"]:
                lista.insert(tk.END, nombre)
            estado_label.config(
                text=f"Mostrando {len(cache['items_filtrados'])} de {len(cache['items'])} registros."
            )

        def seleccionado():
            idx = lista.curselection()
            if not idx:
                return None
            return cache["items_filtrados"][idx[0]]

        def alta():
            nombre = entrada.get().strip()
            if not nombre:
                messagebox.showwarning("Atención", "Ingresa un nombre.")
                return
            try:
                repo.insertar_persona(tabla, nombre)
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Ese nombre ya existe.")
                return
            entrada.delete(0, tk.END)
            recargar()

        def editar():
            item = seleccionado()
            nombre = entrada.get().strip()
            if not item:
                messagebox.showwarning("Atención", "Selecciona un registro.")
                return
            if not nombre:
                messagebox.showwarning("Atención", "Ingresa el nuevo nombre.")
                return
            try:
                repo.editar_persona(tabla, item[0], nombre)
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Ese nombre ya existe.")
                return
            entrada.delete(0, tk.END)
            recargar(persona_id=item[0])

        def baja():
            item = seleccionado()
            if not item:
                messagebox.showwarning("Atención", "Selecciona un registro.")
                return
            if not messagebox.askyesno("Confirmar", f"¿Eliminar '{item[1]}'?"):
                return
            repo.borrar_persona(tabla, item[0])
            entrada.delete(0, tk.END)
            recargar()

        def mover(direccion):
            item = seleccionado()
            if not item:
                messagebox.showwarning("Atención", "Selecciona un registro.")
                return
            persona_id = item[0]
            items = cache["items"][:]
            idx = next((i for i, (pid, _nombre) in enumerate(items) if pid == persona_id), None)
            if idx is None:
                return
            nuevo_idx = idx + direccion
            if nuevo_idx < 0 or nuevo_idx >= len(items):
                return
            items[idx], items[nuevo_idx] = items[nuevo_idx], items[idx]
            repo.guardar_orden_personas(tabla, items)
            recargar(persona_id=persona_id)

        def mover_a_extremo(al_inicio):
            item = seleccionado()
            if not item:
                messagebox.showwarning("Atención", "Selecciona un registro.")
                return
            persona_id = item[0]
            items = cache["items"][:]
            idx = next((i for i, (pid, _nombre) in enumerate(items) if pid == persona_id), None)
            if idx is None:
                return
            movido = items.pop(idx)
            if al_inicio:
                items.insert(0, movido)
            else:
                items.append(movido)
            repo.guardar_orden_personas(tabla, items)
            recargar(persona_id=persona_id)

        def on_select(_event):
            item = seleccionado()
            if item:
                entrada.delete(0, tk.END)
                entrada.insert(0, item[1])

        def on_drag_start(event):
            idx = lista.nearest(event.y)
            if 0 <= idx < len(cache["items_filtrados"]):
                drag_state["from_id"] = cache["items_filtrados"][idx][0]
            else:
                drag_state["from_id"] = None

        def on_drag_release(event):
            from_id = drag_state["from_id"]
            drag_state["from_id"] = None
            if from_id is None:
                return
            idx = lista.nearest(event.y)
            if idx < 0 or idx >= len(cache["items_filtrados"]):
                return
            to_id = cache["items_filtrados"][idx][0]
            if from_id == to_id:
                return
            items = cache["items"][:]
            from_idx = next((i for i, (pid, _n) in enumerate(items) if pid == from_id), None)
            to_idx = next((i for i, (pid, _n) in enumerate(items) if pid == to_id), None)
            if from_idx is None or to_idx is None:
                return
            movido = items.pop(from_idx)
            items.insert(to_idx, movido)
            repo.guardar_orden_personas(tabla, items)
            recargar(persona_id=from_id)

        filtro_var.trace_add("write", aplicar_filtro)
        lista.bind("<<ListboxSelect>>", on_select)
        entrada.bind("<Return>", lambda _event: alta())

        acciones = ttk.Frame(panel)
        acciones.grid(row=4, column=0, sticky="ew")
        ttk.Button(acciones, text="Alta", command=alta).pack(side="left", padx=2)
        ttk.Button(acciones, text="Editar", command=editar).pack(side="left", padx=2)
        ttk.Button(acciones, text="Baja", command=baja).pack(side="left", padx=2)
        ttk.Separator(acciones, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(acciones, text="Subir", command=lambda: mover(-1)).pack(side="left", padx=2)
        ttk.Button(acciones, text="Bajar", command=lambda: mover(1)).pack(side="left", padx=2)
        ttk.Button(acciones, text="Inicio", command=lambda: mover_a_extremo(True)).pack(side="left", padx=2)
        ttk.Button(acciones, text="Final", command=lambda: mover_a_extremo(False)).pack(side="left", padx=2)

        if permitir_carga_masiva:
            ttk.Separator(acciones, orient="vertical").pack(side="left", fill="y", padx=6)
            ttk.Button(
                acciones,
                text="Carga masiva",
                command=lambda: self._abrir_carga_masiva(titulo, tabla, recargar, padre_ventana),
            ).pack(side="left", padx=2)

        if permitir_drag:
            lista.config(cursor="hand2")
            lista.bind("<ButtonPress-1>", on_drag_start, add="+")
            lista.bind("<ButtonRelease-1>", on_drag_release, add="+")

        recargar()

    def _abrir_carga_masiva(self, titulo, tabla, callback_recarga, padre_ventana):
        ventana_masiva = tk.Toplevel(padre_ventana)
        ventana_masiva.title(f"Carga masiva - {titulo}")
        ventana_masiva.geometry("520x360")
        ventana_masiva.transient(padre_ventana)
        ventana_masiva.grab_set()

        contenedor = ttk.Frame(ventana_masiva, padding=10)
        contenedor.pack(fill="both", expand=True)
        ttk.Label(
            contenedor,
            text="Pega un nombre por línea. Las líneas vacías se ignoran.",
        ).pack(anchor="w", pady=(0, 6))

        txt = tk.Text(contenedor, height=14)
        txt.pack(fill="both", expand=True)

        def procesar_carga():
            contenido = txt.get("1.0", tk.END)
            candidatos = [x.strip() for x in contenido.splitlines() if x.strip()]
            if not candidatos:
                messagebox.showwarning("Atención", "No hay nombres para cargar.")
                return

            agregados = 0
            duplicados = 0
            errores = 0
            vistos = set()
            for nombre in candidatos:
                clave = nombre.casefold()
                if clave in vistos:
                    duplicados += 1
                    continue
                vistos.add(clave)
                try:
                    repo.insertar_persona(tabla, nombre)
                    agregados += 1
                except sqlite3.IntegrityError:
                    duplicados += 1
                except sqlite3.Error:
                    errores += 1

            callback_recarga()
            msg = f"Agregados: {agregados}\nOmitidos (duplicados): {duplicados}"
            if errores:
                msg += f"\nErrores: {errores}"
            messagebox.showinfo("Carga masiva finalizada", msg)
            ventana_masiva.destroy()

        botones_masiva = ttk.Frame(contenedor)
        botones_masiva.pack(fill="x", pady=(8, 0))
        ttk.Button(botones_masiva, text="Cargar", command=procesar_carga).pack(side="right", padx=4)
        ttk.Button(botones_masiva, text="Cancelar", command=ventana_masiva.destroy).pack(side="right")


if __name__ == "__main__":
    app = App()
    app.mainloop()
