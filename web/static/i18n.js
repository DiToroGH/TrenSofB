/**
 * Español, portugués e inglés. Persistencia en localStorage.
 */
(function () {
  const STORAGE_KEY = "tren_lang";

  const LOCALE_TAG = {
    es: "es",
    en: "en",
    pt: "pt-BR",
  };

  const STRINGS = {
    es: {
      appTitle: "Train Schedule — Web",
      brandTitle: "Train Schedule",
      loginSubtitle: "Sistema de asignaciones",
      loginHeading: "Iniciar sesión",
      labelUsername: "Usuario:",
      labelPassword: "Contraseña:",
      phUsername: "admin o usuario",
      phPassword: "••••••",
      loginSubmit: "Iniciar sesión",
      demoUsersTitle: "Usuarios de demostración:",
      demoUsersHtml:
        "Usuario: <code>user</code> / <code>user123</code>",
      brandByline: "By Di Toro",
      logout: "Salir",
      toolbarAria: "Acciones principales",
      langLabel: "Idioma",
      langEs: "Español",
      langEn: "English",
      langPt: "Português",
      btnManagePeople: "Gestionar personas",
      btnPastDays: "Días pasados",
      btnRefresh: "Refrescar",
      btnGenerateToday: "Generar asignación de hoy",
      btnCloseDay: "Cerrar día (preparar mañana)",
      lineaLabel: "Línea",
      btnManageLines: "Gestionar líneas",
      dlgLineasTitle: "Líneas de transporte",
      dlgLineasHint:
        "Creá líneas separadas para distintos grupos de conductores y acompañantes.",
      lineaNewLabel: "Nueva línea",
      lineaNewPlaceholder: "Nombre de la línea",
      lineaCreateBtn: "Crear línea",
      lineaSofbProtected: "Línea base (no eliminable)",
      lineaVisibleLabel: "Visible para usuarios",
      lineaVisibleSaved: "Visibilidad actualizada.",
      lineaNoneVisible: "Ninguna línea visible",
      lineaRenamePrompt: "Nuevo nombre de la línea:",
      lineaDeleteConfirm: "¿Eliminar la línea «{nombre}»? Solo si está vacía.",
      lineaRenamed: "Línea renombrada.",
      lineaDeleted: "Línea eliminada.",
      lineaCreated: "Línea creada.",
      lineaNameRequired: "Indicá un nombre para la línea.",
      almanaqueAria: "Almanaque de 4 semanas",
      weekTitle: "Almanaque — 4 semanas",
      weekHint:
        "Incluye la semana pasada, la semana en curso y las dos siguientes. Hoy es la tanda 1; mañana la 2, y así sucesivamente según el orden actual. Los días pasados sin confirmación no muestran proyección.",
      almanaqueBeforeToday: "—",
      sectionToday: "Hoy",
      metaDatePrefix: "Fecha estado:",
      summaryLoading: "Cargando…",
      msgTurnLabel: "Mensaje de turno",
      msgTurnEditHint:
        "Podés editar el texto. Guardalo o regenerá la plantilla automática.",
      btnSaveMsg: "Guardar mensaje",
      btnRegenMsg: "Regenerar automático",
      btnCopyMsg: "Copiar mensaje",
      noMsgSave: "Escribí un mensaje antes de guardar.",
      msgSaved: "Mensaje guardado.",
      msgRegenerated: "Mensaje regenerado desde la plantilla.",
      availabilityTitle: "Disponibilidad (hoy)",
      availabilityHint:
        "Marcá quiénes pueden ir. Por defecto todos disponibles.",
      secondCompanionLabel: "Segundo acompañante (opcional)",
      secondCompanionHint:
        "Al cerrar el día también pasa al final de la cola.",
      secondCompanionNone: "Ninguno",
      badgeSecondCompanion: "2.º acompañante",
      secondCompanionSaved: "Segundo acompañante guardado.",
      summaryTodayWithSecond: "Hoy: {c} con {v} y {s}",
      assignmentsTitle: "Asignaciones",
      assignmentsIntro:
        "Cada bloque es un tren: <strong>Conductor</strong> al volante y <strong>VIP</strong> como acompañante.",
      noDispLabel: "No disponibles hoy:",
      assignmentsListAria: "Asignaciones del día",
      referenceTitle: "Referencia",
      referenceConductors: "Conductores",
      referenceCompanionsOrder: "Orden acompañantes",
      registrosTitle: "Registros",
      registrosHint:
        "Parejas confirmadas al cerrar el día. Se conservan los últimos 4 meses.",
      registrosEmpty: "Aún no hay registros guardados.",
      registrosLogAria: "Historial de registros",
      registroLabelFecha: "Fecha:",
      registroLabelConductor: "Conductor:",
      registroLabelVip: "VIP:",
      registroLabelSegundo: "2.º acompañante:",
      dlgTitle: "Gestión de conductores y acompañantes",
      dlgHint:
        "Altas, bajas, edición y orden (misma base que el escritorio).",
      tabConductors: "Conductores",
      tabCompanions: "Acompañantes",
      srFilterCond: "Filtrar conductores",
      srFilterAcomp: "Filtrar acompañantes",
      phFilter: "Filtrar…",
      listCondAria: "Lista de conductores",
      listAcompAria: "Lista de acompañantes",
      srNameCond: "Nombre conductor",
      srNameAcomp: "Nombre acompañante",
      phNameQuickCond: "Nombre (Enter = alta rápida)",
      phNameQuickAcomp: "Nombre (Enter = alta rápida)",
      btnAdd: "Alta",
      btnEdit: "Editar",
      btnDelete: "Baja",
      btnUp: "Subir",
      btnDown: "Bajar",
      btnStart: "Inicio",
      btnEnd: "Final",
      masivaLabel: "Carga masiva (un nombre por línea)",
      masivaPlaceholder: "Pegá nombres, uno por línea",
      masivaLoad: "Cargar",
      btnExportCsv: "Exportar CSV",
      exportCsvColOrden: "orden",
      exportCsvColNombre: "nombre",
      exportCsvDone: "CSV exportado.",
      exportCsvEmpty: "No hay acompañantes para exportar.",
      dlgClose: "Cerrar",
      dlgRegistroTitle: "Registro de días pasados",
      dlgRegistroHint:
        "Corregí conductor y VIP confirmados. Podés editar días anteriores a hoy o el día de hoy si ya está confirmado. El VIP es opcional.",
      registroLabelFecha: "Fecha",
      registroLabelConductor: "Conductor",
      registroLabelVip: "VIP / acompañante",
      registroSave: "Guardar",
      registroSinVip: "Sin acompañante (solo conductor)",
      registroFechaPasada: "Elegí una fecha anterior a hoy.",
      registroFechaInvalida: "Elegí hoy (si ya está confirmado) o una fecha anterior.",
      registroHoySinConfirmar: "Hoy solo se puede editar si el día ya está confirmado.",
      registroConductorReq: "Elegí un conductor.",
      registroSaved: "Registro actualizado.",
      opModeAdmin: "Modo operativo (admin): {fecha}",
      badgeConductor: "Conductor",
      badgeVip: "VIP",
      mainShift: "Turno principal",
      shiftN: "Tanda {n}",
      unassigned: "Sin asignar",
      noAssignments: "Aún no hay asignaciones.",
      statusConfirmed: "Confirmado",
      statusProposed: "Propuesto",
      dash: "—",
      none: "Ninguno",
      moveStart: "Al principio",
      moveEnd: "Al final",
      summaryToday: "Hoy: {c} con {v}",
      summaryProposed:
        "Propuesto: {c} con {v} (generá asignación para confirmar)",
      summaryNoData: "Sin datos suficientes para la pareja del día.",
      loading: "Cargando…",
      sessionExpired:
        "Sesión expirada o sin permisos. Por favor inicia sesión nuevamente.",
      updating: "Actualizando…",
      orderCompanionsOk: "Orden de acompañantes actualizado.",
      orderDriversOk: "Orden de conductores actualizado.",
      fijosSemanaTitle: "Conductor fijo por día",
      fijosSemanaHint:
        "Elegí un conductor para cada día. Ese día siempre lo conduce; los demás días no entra en la rotación.",
      fijosSemanaNone: "(rotación normal)",
      fijosSemanaSaved: "Conductor fijo guardado.",
      weekday0: "Lunes",
      weekday1: "Martes",
      weekday2: "Miércoles",
      weekday3: "Jueves",
      weekday4: "Viernes",
      weekday5: "Sábado",
      weekday6: "Domingo",
      generating: "Generando…",
      assignmentGenerated: "Asignación generada.",
      closingDay: "Cerrando día…",
      done: "Listo.",
      noMsgCopy: "No hay mensaje para copiar.",
      copied: "Mensaje copiado al portapapeles.",
      copyFailed: "No se pudo copiar (permiso del navegador).",
      confirmCloseDay: "¿Cerrar el día y preparar el orden de mañana?",
      invalidCreds: "Credenciales inválidas",
      roleAdmin: "Administrador",
      roleUser: "Usuario",
      userDisplay: "{username} ({role})",
      gestionEnterName: "Ingresá un nombre.",
      gestionSelectRecord: "Seleccioná un registro.",
      gestionEnterNewName: "Ingresá el nuevo nombre.",
      gestionConfirmDelete: "¿Eliminar «{name}»?",
      gestionNoNamesBulk: "No hay nombres para cargar.",
      gestionBulkResult:
        "Agregados: {agregados} · Omitidos (duplicados): {duplicados}{errPart}",
      gestionErrSuffix: " · Errores: {n}",
      gestionReady: "Listo.",
      gestionShowing: "Mostrando {shown} de {total} registros.",
      errorGeneric: "Error",
    },
    en: {
      appTitle: "Train Schedule — Web",
      brandTitle: "Train Schedule",
      loginSubtitle: "Assignment system",
      loginHeading: "Sign in",
      labelUsername: "Username:",
      labelPassword: "Password:",
      phUsername: "admin or user",
      phPassword: "••••••",
      loginSubmit: "Sign in",
      demoUsersTitle: "Demo users:",
      demoUsersHtml: "User: <code>user</code> / <code>user123</code>",
      brandByline: "By Di Toro",
      logout: "Log out",
      toolbarAria: "Main actions",
      langLabel: "Language",
      langEs: "Español",
      langEn: "English",
      langPt: "Português",
      btnManagePeople: "Manage people",
      btnPastDays: "Past days",
      btnRefresh: "Refresh",
      btnGenerateToday: "Generate today’s assignment",
      btnCloseDay: "Close day (prepare tomorrow)",
      lineaLabel: "Line",
      btnManageLines: "Manage lines",
      dlgLineasTitle: "Transport lines",
      dlgLineasHint:
        "Create separate lines for different driver and companion groups.",
      lineaNewLabel: "New line",
      lineaNewPlaceholder: "Line name",
      lineaCreateBtn: "Create line",
      lineaSofbProtected: "Base line (cannot delete)",
      lineaVisibleLabel: "Visible to users",
      lineaVisibleSaved: "Visibility updated.",
      lineaNoneVisible: "No visible lines",
      lineaRenamePrompt: "New line name:",
      lineaDeleteConfirm: "Delete line «{nombre}»? Only if empty.",
      lineaRenamed: "Line renamed.",
      lineaDeleted: "Line deleted.",
      lineaCreated: "Line created.",
      lineaNameRequired: "Enter a name for the line.",
      almanaqueAria: "4-week schedule",
      weekTitle: "Schedule — 4 weeks",
      weekHint:
        "Includes the previous week, the current week, and the next two weeks. Today is shift 1; tomorrow shift 2, and so on from the current order. Past days without confirmation show no projection.",
      almanaqueBeforeToday: "—",
      sectionToday: "Today",
      metaDatePrefix: "State date:",
      summaryLoading: "Loading…",
      msgTurnLabel: "Shift message",
      msgTurnEditHint:
        "You can edit the text. Save it or regenerate from the automatic template.",
      btnSaveMsg: "Save message",
      btnRegenMsg: "Regenerate automatic",
      btnCopyMsg: "Copy message",
      noMsgSave: "Write a message before saving.",
      msgSaved: "Message saved.",
      msgRegenerated: "Message regenerated from template.",
      availabilityTitle: "Availability (today)",
      availabilityHint: "Check who can go. Everyone is available by default.",
      secondCompanionLabel: "Second companion (optional)",
      secondCompanionHint:
        "When closing the day they also move to the end of the queue.",
      secondCompanionNone: "None",
      badgeSecondCompanion: "2nd companion",
      secondCompanionSaved: "Second companion saved.",
      summaryTodayWithSecond: "Today: {c} with {v} and {s}",
      assignmentsTitle: "Assignments",
      assignmentsIntro:
        "Each block is a train: <strong>Driver</strong> at the wheel and <strong>VIP</strong> as companion.",
      noDispLabel: "Not available today:",
      assignmentsListAria: "Today’s assignments",
      referenceTitle: "Reference",
      referenceConductors: "Drivers",
      referenceCompanionsOrder: "Companion order",
      registrosTitle: "Records",
      registrosHint:
        "Pairs confirmed when closing the day. Kept for the last 4 months.",
      registrosEmpty: "No records saved yet.",
      registrosLogAria: "Records history",
      registroLabelFecha: "Date:",
      registroLabelConductor: "Driver:",
      registroLabelVip: "VIP:",
      registroLabelSegundo: "2nd companion:",
      dlgTitle: "Drivers and companions",
      dlgHint: "Add, edit, remove and order (same data as the desktop app).",
      tabConductors: "Drivers",
      tabCompanions: "Companions",
      srFilterCond: "Filter drivers",
      srFilterAcomp: "Filter companions",
      phFilter: "Filter…",
      listCondAria: "Driver list",
      listAcompAria: "Companion list",
      srNameCond: "Driver name",
      srNameAcomp: "Companion name",
      phNameQuickCond: "Name (Enter = quick add)",
      phNameQuickAcomp: "Name (Enter = quick add)",
      btnAdd: "Add",
      btnEdit: "Edit",
      btnDelete: "Remove",
      btnUp: "Up",
      btnDown: "Down",
      btnStart: "Start",
      btnEnd: "End",
      masivaLabel: "Bulk load (one name per line)",
      masivaPlaceholder: "Paste names, one per line",
      masivaLoad: "Load",
      btnExportCsv: "Export CSV",
      exportCsvColOrden: "order",
      exportCsvColNombre: "name",
      exportCsvDone: "CSV exported.",
      exportCsvEmpty: "No companions to export.",
      dlgClose: "Close",
      dlgRegistroTitle: "Past days record",
      dlgRegistroHint:
        "Fix confirmed driver and VIP. You can edit past days or today if already confirmed. VIP is optional.",
      registroLabelFecha: "Date",
      registroLabelConductor: "Driver",
      registroLabelVip: "VIP / companion",
      registroSave: "Save",
      registroSinVip: "No companion (driver only)",
      registroFechaPasada: "Pick a date before today.",
      registroFechaInvalida: "Pick today (if already confirmed) or an earlier date.",
      registroHoySinConfirmar: "Today can only be edited if the day is already confirmed.",
      registroConductorReq: "Pick a driver.",
      registroSaved: "Record updated.",
      opModeAdmin: "Operational mode (admin): {fecha}",
      badgeConductor: "Driver",
      badgeVip: "VIP",
      mainShift: "Main shift",
      shiftN: "Shift {n}",
      unassigned: "Unassigned",
      noAssignments: "No assignments yet.",
      statusConfirmed: "Confirmed",
      statusProposed: "Proposed",
      dash: "—",
      none: "None",
      moveStart: "To start",
      moveEnd: "To end",
      summaryToday: "Today: {c} with {v}",
      summaryProposed:
        "Proposed: {c} with {v} (generate assignment to confirm)",
      summaryNoData: "Not enough data for today’s pair.",
      loading: "Loading…",
      sessionExpired:
        "Session expired or no permission. Please sign in again.",
      updating: "Updating…",
      orderCompanionsOk: "Companion order updated.",
      orderDriversOk: "Driver order updated.",
      fijosSemanaTitle: "Fixed driver per weekday",
      fijosSemanaHint:
        "Pick a driver for each weekday. They always drive that day and are excluded from rotation on other days.",
      fijosSemanaNone: "(normal rotation)",
      fijosSemanaSaved: "Fixed driver saved.",
      weekday0: "Monday",
      weekday1: "Tuesday",
      weekday2: "Wednesday",
      weekday3: "Thursday",
      weekday4: "Friday",
      weekday5: "Saturday",
      weekday6: "Sunday",
      generating: "Generating…",
      assignmentGenerated: "Assignment generated.",
      closingDay: "Closing day…",
      done: "Done.",
      noMsgCopy: "No message to copy.",
      copied: "Message copied to clipboard.",
      copyFailed: "Could not copy (browser permission).",
      confirmCloseDay: "Close the day and prepare tomorrow’s order?",
      invalidCreds: "Invalid credentials",
      roleAdmin: "Administrator",
      roleUser: "User",
      userDisplay: "{username} ({role})",
      gestionEnterName: "Enter a name.",
      gestionSelectRecord: "Select a record.",
      gestionEnterNewName: "Enter the new name.",
      gestionConfirmDelete: "Delete “{name}”?",
      gestionNoNamesBulk: "No names to load.",
      gestionBulkResult:
        "Added: {agregados} · Skipped (duplicates): {duplicados}{errPart}",
      gestionErrSuffix: " · Errors: {n}",
      gestionReady: "Done.",
      gestionShowing: "Showing {shown} of {total} records.",
      errorGeneric: "Error",
    },
    pt: {
      appTitle: "Train Schedule — Web",
      brandTitle: "Train Schedule",
      loginSubtitle: "Sistema de atribuições",
      loginHeading: "Entrar",
      labelUsername: "Usuário:",
      labelPassword: "Senha:",
      phUsername: "admin ou usuário",
      phPassword: "••••••",
      loginSubmit: "Entrar",
      demoUsersTitle: "Usuários de demonstração:",
      demoUsersHtml: "Usuário: <code>user</code> / <code>user123</code>",
      brandByline: "By Di Toro",
      logout: "Sair",
      toolbarAria: "Ações principais",
      langLabel: "Idioma",
      langEs: "Español",
      langEn: "English",
      langPt: "Português",
      btnManagePeople: "Gerir pessoas",
      btnPastDays: "Dias passados",
      btnRefresh: "Atualizar",
      btnGenerateToday: "Gerar atribuição de hoje",
      btnCloseDay: "Fechar dia (preparar amanhã)",
      lineaLabel: "Linha",
      btnManageLines: "Gerir linhas",
      dlgLineasTitle: "Linhas de transporte",
      dlgLineasHint:
        "Crie linhas separadas para grupos distintos de condutores e acompanhantes.",
      lineaNewLabel: "Nova linha",
      lineaNewPlaceholder: "Nome da linha",
      lineaCreateBtn: "Criar linha",
      lineaSofbProtected: "Linha base (não eliminável)",
      lineaVisibleLabel: "Visível para utilizadores",
      lineaVisibleSaved: "Visibilidade atualizada.",
      lineaNoneVisible: "Nenhuma linha visível",
      lineaRenamePrompt: "Novo nome da linha:",
      lineaDeleteConfirm: "Eliminar a linha «{nombre}»? Só se estiver vazia.",
      lineaRenamed: "Linha renomeada.",
      lineaDeleted: "Linha eliminada.",
      lineaCreated: "Linha criada.",
      lineaNameRequired: "Indique um nome para a linha.",
      almanaqueAria: "Calendário de 4 semanas",
      weekTitle: "Calendário — 4 semanas",
      weekHint:
        "Inclui a semana anterior, a semana em curso e as duas próximas. Hoje é a tanda 1; amanhã a 2, e assim por diante conforme a ordem atual. Dias passados sem confirmação não mostram projeção.",
      almanaqueBeforeToday: "—",
      sectionToday: "Hoje",
      metaDatePrefix: "Data do estado:",
      summaryLoading: "A carregar…",
      msgTurnLabel: "Mensagem do turno",
      msgTurnEditHint:
        "Pode editar o texto. Guarde ou regenere a partir do modelo automático.",
      btnSaveMsg: "Guardar mensagem",
      btnRegenMsg: "Regenerar automático",
      btnCopyMsg: "Copiar mensagem",
      noMsgSave: "Escreva uma mensagem antes de guardar.",
      msgSaved: "Mensagem guardada.",
      msgRegenerated: "Mensagem regenerada a partir do modelo.",
      availabilityTitle: "Disponibilidade (hoje)",
      availabilityHint:
        "Marque quem pode ir. Por defeito todos disponíveis.",
      secondCompanionLabel: "Segundo acompanhante (opcional)",
      secondCompanionHint:
        "Ao fechar o dia também vai para o fim da fila.",
      secondCompanionNone: "Nenhum",
      badgeSecondCompanion: "2.º acompanhante",
      secondCompanionSaved: "Segundo acompanhante guardado.",
      summaryTodayWithSecond: "Hoje: {c} com {v} e {s}",
      assignmentsTitle: "Atribuições",
      assignmentsIntro:
        "Cada bloco é um comboio: <strong>Condutor</strong> ao volante e <strong>VIP</strong> como acompanhante.",
      noDispLabel: "Indisponíveis hoje:",
      assignmentsListAria: "Atribuições do dia",
      referenceTitle: "Referência",
      referenceConductors: "Condutores",
      referenceCompanionsOrder: "Ordem dos acompanhantes",
      registrosTitle: "Registos",
      registrosHint:
        "Pares confirmados ao fechar o dia. Conservados durante 4 meses.",
      registrosEmpty: "Ainda não há registos guardados.",
      registrosLogAria: "Histórico de registos",
      registroLabelFecha: "Data:",
      registroLabelConductor: "Condutor:",
      registroLabelVip: "VIP:",
      registroLabelSegundo: "2.º acompanhante:",
      dlgTitle: "Gestão de condutores e acompanhantes",
      dlgHint: "Altas, baixas, edição e ordem (mesma base que o desktop).",
      tabConductors: "Condutores",
      tabCompanions: "Acompanhantes",
      srFilterCond: "Filtrar condutores",
      srFilterAcomp: "Filtrar acompanhantes",
      phFilter: "Filtrar…",
      listCondAria: "Lista de condutores",
      listAcompAria: "Lista de acompanhantes",
      srNameCond: "Nome do condutor",
      srNameAcomp: "Nome do acompanhante",
      phNameQuickCond: "Nome (Enter = adição rápida)",
      phNameQuickAcomp: "Nome (Enter = adição rápida)",
      btnAdd: "Adicionar",
      btnEdit: "Editar",
      btnDelete: "Remover",
      btnUp: "Subir",
      btnDown: "Descer",
      btnStart: "Início",
      btnEnd: "Fim",
      masivaLabel: "Carga em massa (um nome por linha)",
      masivaPlaceholder: "Cole nomes, um por linha",
      masivaLoad: "Carregar",
      btnExportCsv: "Exportar CSV",
      exportCsvColOrden: "ordem",
      exportCsvColNombre: "nome",
      exportCsvDone: "CSV exportado.",
      exportCsvEmpty: "Não há acompanhantes para exportar.",
      dlgClose: "Fechar",
      dlgRegistroTitle: "Registo de dias passados",
      dlgRegistroHint:
        "Corrija condutor e VIP confirmados. Pode editar dias anteriores ou hoje se já estiver confirmado. O VIP é opcional.",
      registroLabelFecha: "Data",
      registroLabelConductor: "Condutor",
      registroLabelVip: "VIP / acompanhante",
      registroSave: "Guardar",
      registroSinVip: "Sem acompanhante (só condutor)",
      registroFechaPasada: "Escolha uma data anterior a hoje.",
      registroFechaInvalida: "Escolha hoje (se já confirmado) ou uma data anterior.",
      registroHoySinConfirmar: "Hoje só pode ser editado se o dia já estiver confirmado.",
      registroConductorReq: "Escolha um condutor.",
      registroSaved: "Registo atualizado.",
      opModeAdmin: "Modo operacional (admin): {fecha}",
      badgeConductor: "Condutor",
      badgeVip: "VIP",
      mainShift: "Turno principal",
      shiftN: "Tanda {n}",
      unassigned: "Sem atribuição",
      noAssignments: "Ainda não há atribuições.",
      statusConfirmed: "Confirmado",
      statusProposed: "Proposto",
      dash: "—",
      none: "Nenhum",
      moveStart: "Ao início",
      moveEnd: "Ao fim",
      summaryToday: "Hoje: {c} com {v}",
      summaryProposed:
        "Proposto: {c} com {v} (gere a atribuição para confirmar)",
      summaryNoData: "Dados insuficientes para o par de hoje.",
      loading: "A carregar…",
      sessionExpired:
        "Sessão expirada ou sem permissão. Inicie sessão novamente.",
      updating: "A atualizar…",
      orderCompanionsOk: "Ordem dos acompanhantes atualizada.",
      orderDriversOk: "Ordem dos condutores atualizada.",
      fijosSemanaTitle: "Condutor fixo por dia da semana",
      fijosSemanaHint:
        "Escolha um condutor para cada dia. Nesse dia ele sempre conduz; nos outros não entra na rotação.",
      fijosSemanaNone: "(rotação normal)",
      fijosSemanaSaved: "Condutor fixo guardado.",
      weekday0: "Segunda",
      weekday1: "Terça",
      weekday2: "Quarta",
      weekday3: "Quinta",
      weekday4: "Sexta",
      weekday5: "Sábado",
      weekday6: "Domingo",
      generating: "A gerar…",
      assignmentGenerated: "Atribuição gerada.",
      closingDay: "A fechar o dia…",
      done: "Pronto.",
      noMsgCopy: "Não há mensagem para copiar.",
      copied: "Mensagem copiada para a área de transferência.",
      copyFailed: "Não foi possível copiar (permissão do navegador).",
      confirmCloseDay: "Fechar o dia e preparar a ordem de amanhã?",
      invalidCreds: "Credenciais inválidas",
      roleAdmin: "Administrador",
      roleUser: "Utilizador",
      userDisplay: "{username} ({role})",
      gestionEnterName: "Introduza um nome.",
      gestionSelectRecord: "Selecione um registo.",
      gestionEnterNewName: "Introduza o novo nome.",
      gestionConfirmDelete: "Eliminar «{name}»?",
      gestionNoNamesBulk: "Não há nomes para carregar.",
      gestionBulkResult:
        "Adicionados: {agregados} · Ignorados (duplicados): {duplicados}{errPart}",
      gestionErrSuffix: " · Erros: {n}",
      gestionReady: "Pronto.",
      gestionShowing: "A mostrar {shown} de {total} registos.",
      errorGeneric: "Erro",
    },
  };

  function normalizeLang(code) {
    if (!code || !STRINGS[code]) return "es";
    return code;
  }

  function getLang() {
    return normalizeLang(localStorage.getItem(STORAGE_KEY));
  }

  function format(str, vars) {
    if (!vars) return str;
    let out = str;
    Object.keys(vars).forEach(function (k) {
      out = out.split("{" + k + "}").join(String(vars[k]));
    });
    return out;
  }

  function hasKey(key) {
    const lang = getLang();
    const table = STRINGS[lang] || {};
    return (
      Object.prototype.hasOwnProperty.call(table, key) ||
      Object.prototype.hasOwnProperty.call(STRINGS.es, key)
    );
  }

  function t(key, vars) {
    const lang = getLang();
    const table = STRINGS[lang] || STRINGS.es;
    const fallback = STRINGS.es[key];
    const raw = Object.prototype.hasOwnProperty.call(table, key)
      ? table[key]
      : fallback !== undefined
        ? fallback
        : key;
    return format(raw, vars);
  }

  function getLocaleTag() {
    return LOCALE_TAG[getLang()] || "es";
  }

  function syncLangOptionLabels() {
    document.querySelectorAll(".lang-select").forEach(function (sel) {
      Array.prototype.forEach.call(sel.options, function (opt) {
        if (opt.value === "es") opt.textContent = t("langEs");
        else if (opt.value === "en") opt.textContent = t("langEn");
        else if (opt.value === "pt") opt.textContent = t("langPt");
      });
    });
  }

  function applyStatic() {
    document.title = hasKey("appTitle") ? t("appTitle") : document.title;
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      const key = el.getAttribute("data-i18n");
      if (key && hasKey(key)) el.textContent = t(key);
    });
    document.querySelectorAll("[data-i18n-html]").forEach(function (el) {
      const key = el.getAttribute("data-i18n-html");
      if (key && hasKey(key)) el.innerHTML = t(key);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(function (el) {
      const key = el.getAttribute("data-i18n-placeholder");
      if (key && hasKey(key)) el.setAttribute("placeholder", t(key));
    });
    document.querySelectorAll("[data-i18n-aria]").forEach(function (el) {
      const key = el.getAttribute("data-i18n-aria");
      if (key && hasKey(key)) el.setAttribute("aria-label", t(key));
    });
    document.querySelectorAll("[data-i18n-title]").forEach(function (el) {
      const key = el.getAttribute("data-i18n-title");
      if (key && hasKey(key)) el.setAttribute("title", t(key));
    });
    syncLangOptionLabels();
  }

  function syncLangSelects() {
    const v = getLang();
    document.querySelectorAll(".lang-select").forEach(function (sel) {
      sel.value = v;
    });
  }

  function setLang(lang) {
    lang = normalizeLang(lang);
    localStorage.setItem(STORAGE_KEY, lang);
    const htmlLang = lang === "pt" ? "pt-BR" : lang;
    document.documentElement.lang = htmlLang;
    applyStatic();
    syncLangSelects();
    window.dispatchEvent(
      new CustomEvent("tren-lang-change", { detail: { lang: lang } })
    );
  }

  function wireLangSelects() {
    document.querySelectorAll(".lang-select").forEach(function (sel) {
      sel.addEventListener("change", function () {
        setLang(sel.value);
      });
    });
  }

  window.trenI18n = {
    t: t,
    hasKey: hasKey,
    getLang: getLang,
    setLang: setLang,
    applyStatic: applyStatic,
    getLocaleTag: getLocaleTag,
    syncLangSelects: syncLangSelects,
  };

  document.documentElement.lang =
    getLang() === "pt" ? "pt-BR" : getLang();
  applyStatic();
  wireLangSelects();
  syncLangSelects();
})();
