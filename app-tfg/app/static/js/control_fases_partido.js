/**
 * Control de Fases del Partido (Optimizado)
 *
 * Este módulo gestiona:
 * 1. Identificación de la fase actual del partido
 * 2. Restricción de tiempos muertos por equipo y fase
 * 3. Limitación de prórrogas (máximo 2)
 */

window.controlFasesPartido = (() => {
  // Constantes para IDs de eventos
  const EVENTO_INICIO_PRIMER_TIEMPO = 8
  const EVENTO_FIN_PRIMER_TIEMPO = 9
  const EVENTO_INICIO_SEGUNDO_TIEMPO = 17
  const EVENTO_FIN_SEGUNDO_TIEMPO = 18
  const EVENTO_INICIO_PRORROGA = 19
  const EVENTO_FIN_PRORROGA = 20
  const EVENTO_FIN_PARTIDO = 23
  const EVENTO_TIEMPO_MUERTO = 10

  let videoPlayer = null
  let lastProcessedTime = -1
  let parteActual = "prePartido"

  const tiemposMuertosSolicitados = {
    local: { parte1: 0, parte2: 0, prorroga1: 0, prorroga2: 0 },
    visitante: { parte1: 0, parte2: 0, prorroga1: 0, prorroga2: 0 },
  }

  let prorrogasRegistradas = 0
  let eventosFase = []
  let indicadorFaseElement = null
  const contadoresTiemposMuertos = {
    local: null,
    visitante: null,
  }

  function inicializar() {
    console.log("Inicializando control de fases del partido...")
    crearIndicadorFase()
    crearContadoresTiemposMuertos()
    document.addEventListener("eventoRegistrado", manejarNuevoEvento)
    document.addEventListener("eventoEliminado", manejarEventoEliminado)
    inicializarSeguimientoVideo()
    console.log("Esperando eventos desde event_annotation.js...")
  }

  function inicializarSeguimientoVideo() {
    videoPlayer = document.getElementById("video-player")
    if (!videoPlayer) {
      console.warn("No se encontró el reproductor de video. El seguimiento automático de fases no estará disponible.")
      return
    }
    console.log("Inicializando seguimiento del video para detección automática de fases")
    videoPlayer.addEventListener("timeupdate", manejarCambioTiempo)
    videoPlayer.addEventListener("seeking", manejarCambioTiempo)
    videoPlayer.addEventListener("seeked", manejarCambioTiempo)

    const timeInput = document.getElementById("current-time")
    if (timeInput) {
      timeInput.addEventListener("change", function () {
        const newTime = Number.parseFloat(this.textContent || this.value)
        if (!isNaN(newTime)) {
          determinarFasePorTiempoVideo(newTime)
        }
      })
    }

    if (videoPlayer.readyState > 0) {
      determinarFasePorTiempoVideo(videoPlayer.currentTime)
    }
  }

  function manejarCambioTiempo() {
    if (!videoPlayer) return
    const currentTime = videoPlayer.currentTime
    if (Math.abs(currentTime - lastProcessedTime) < 0.5) return
    lastProcessedTime = currentTime
    determinarFasePorTiempoVideo(currentTime)
    actualizarContadoresTiemposMuertos()
  }

  function determinarFasePorTiempoVideo(currentTime) {
    const nuevaFase = detectarFaseSegunTiempo(currentTime)
    if (nuevaFase !== parteActual) {
      console.log(`Fase actualizada automáticamente: ${nuevaFase} (tiempo: ${formatTime(currentTime)})`)
      actualizarFaseActual(nuevaFase)
    }
  }

  function actualizarFaseActual(nuevaFase) {
    parteActual = nuevaFase
    if (nuevaFase.includes("prorroga")) {
      const iniciosProrroga = eventosFase.filter((e) => Number.parseInt(e.eventTypeId) === EVENTO_INICIO_PRORROGA)
      prorrogasRegistradas = iniciosProrroga.length
    }
    actualizarUI()
  }

  function crearIndicadorFase() {
    if (document.getElementById("fase-actual-indicador")) {
      indicadorFaseElement = document.getElementById("fase-actual-indicador")
      return
    }
    const container = document.createElement("div")
    container.id = "fase-partido-container"
    container.className = "fase-partido-container"

    const indicador = document.createElement("div")
    indicador.id = "fase-actual-indicador"
    indicador.className = "fase-actual-indicador"
    indicador.innerHTML = '<i class="fas fa-clock"></i> <span>Fase: Pre-partido</span>'
    indicadorFaseElement = indicador
    container.appendChild(indicador)

    const eventsPanel = document.querySelector(".events-panel")
    if (eventsPanel) {
      eventsPanel.parentNode.insertBefore(container, eventsPanel)
    } else {
      const videoColumn = document.querySelector(".video-column")
      if (videoColumn) {
        videoColumn.appendChild(container)
      }
    }
  }

  function crearContadoresTiemposMuertos() {
    // Local
    const localStatsPanel = document.querySelector("#stats-local")
    if (localStatsPanel) {
      const tiemposMuertosItem = localStatsPanel.querySelector(".stat-item:nth-child(2)")
      if (tiemposMuertosItem) {
        const statLabel = tiemposMuertosItem.querySelector(".stat-label")
        if (statLabel) statLabel.textContent = "TM:"
        const circlesContainer = document.createElement("div")
        circlesContainer.className = "tm-circles-container"
        circlesContainer.id = "tm-circles-local"
        for (let i = 0; i < 3; i++) {
          const circle = document.createElement("div")
          circle.className = "tm-circle available"
          circle.dataset.index = i
          circlesContainer.appendChild(circle)
        }
        const statValue = tiemposMuertosItem.querySelector(".stat-value")
        if (statValue) {
          statValue.after(circlesContainer)
          statValue.style.display = "none"
        } else {
          tiemposMuertosItem.appendChild(circlesContainer)
        }
        contadoresTiemposMuertos.local = circlesContainer
      }
    }
    // Visitante
    const visitanteStatsPanel = document.querySelector("#stats-visitante")
    if (visitanteStatsPanel) {
      const tiemposMuertosItem = visitanteStatsPanel.querySelector(".stat-item:nth-child(2)")
      if (tiemposMuertosItem) {
        const statLabel = tiemposMuertosItem.querySelector(".stat-label")
        if (statLabel) statLabel.textContent = "TM:"
        const circlesContainer = document.createElement("div")
        circlesContainer.className = "tm-circles-container"
        circlesContainer.id = "tm-circles-visitante"
        for (let i = 0; i < 3; i++) {
          const circle = document.createElement("div")
          circle.className = "tm-circle available"
          circle.dataset.index = i
          circlesContainer.appendChild(circle)
        }
        const statValue = tiemposMuertosItem.querySelector(".stat-value")
        if (statValue) {
          statValue.after(circlesContainer)
          statValue.style.display = "none"
        } else {
          tiemposMuertosItem.appendChild(circlesContainer)
        }
        contadoresTiemposMuertos.visitante = circlesContainer
      }
    }
  }

  function analizarEventosExternos(eventos) {
    window.controlFasesPartido.eventosRegistrados = eventos;
    console.log("Analizando eventos externos para determinar fase del partido...")
    if (!eventos || eventos.length === 0) {
      console.log("No hay eventos externos para analizar")
      actualizarUI()
      return
    }
    eventosFase = eventos.filter((evento) => {
      const tipoId = Number.parseInt(evento.eventTypeId)
      return [
        EVENTO_INICIO_PRIMER_TIEMPO,
        EVENTO_FIN_PRIMER_TIEMPO,
        EVENTO_INICIO_SEGUNDO_TIEMPO,
        EVENTO_FIN_SEGUNDO_TIEMPO,
        EVENTO_INICIO_PRORROGA,
        EVENTO_FIN_PRORROGA,
        EVENTO_FIN_PARTIDO,
      ].includes(tipoId)
    })
    eventosFase.sort((a, b) => a.timestamp - b.timestamp)
    sincronizarTiemposMuertos(eventos)
    if (videoPlayer && videoPlayer.readyState > 0) {
      determinarFasePorTiempoVideo(videoPlayer.currentTime)
    } else {
      determinarFaseActual()
    }
    actualizarUI()
  }

  // Unificamos el conteo de tiempos muertos y su sincronización en una sola función
  function sincronizarTiemposMuertos(eventos) {
    tiemposMuertosSolicitados.local = { parte1: 0, parte2: 0, prorroga1: 0, prorroga2: 0 }
    tiemposMuertosSolicitados.visitante = { parte1: 0, parte2: 0, prorroga1: 0, prorroga2: 0 }
    const tiemposMuertos = eventos.filter(
      (evento) => Number.parseInt(evento.eventTypeId) === EVENTO_TIEMPO_MUERTO && evento.equipoTipo,
    )
    tiemposMuertos.forEach((evento) => {
      const equipo = evento.equipoTipo
      const fase = detectarFaseSegunTiempo(evento.timestamp)
      if (tiemposMuertosSolicitados[equipo] && tiemposMuertosSolicitados[equipo][fase] !== undefined) {
        tiemposMuertosSolicitados[equipo][fase]++
      }
    })
    actualizarContadoresTiemposMuertos()
  }

  function determinarFaseActual() {
    parteActual = "prePartido"
    prorrogasRegistradas = 0
    if (eventosFase.length === 0) return
    const iniciosProrroga = eventosFase.filter((e) => Number.parseInt(e.eventTypeId) === EVENTO_INICIO_PRORROGA)
    prorrogasRegistradas = iniciosProrroga.length
    const ultimoEvento = eventosFase[eventosFase.length - 1]
    const tipoId = Number.parseInt(ultimoEvento.eventTypeId)
    switch (tipoId) {
      case EVENTO_INICIO_PRIMER_TIEMPO: parteActual = "parte1"; break
      case EVENTO_FIN_PRIMER_TIEMPO: parteActual = "entrePartes"; break
      case EVENTO_INICIO_SEGUNDO_TIEMPO: parteActual = "parte2"; break
      case EVENTO_FIN_SEGUNDO_TIEMPO: parteActual = "postTiempoReglamentario"; break
      case EVENTO_INICIO_PRORROGA:
        const iniciosProrrogaCount = eventosFase.filter((e) => Number.parseInt(e.eventTypeId) === EVENTO_INICIO_PRORROGA).length
        parteActual = iniciosProrrogaCount === 1 ? "prorroga1" : "prorroga2"
        break
      case EVENTO_FIN_PRORROGA:
        const finesProrroga = eventosFase.filter((e) => Number.parseInt(e.eventTypeId) === EVENTO_FIN_PRORROGA)
        if (finesProrroga.length === 1) {
          const haySegundaProrroga = eventosFase.some(
            (e) => Number.parseInt(e.eventTypeId) === EVENTO_INICIO_PRORROGA && e.timestamp > ultimoEvento.timestamp,
          )
          parteActual = haySegundaProrroga ? "prorroga2" : "entreProrroga"
        } else {
          parteActual = "postProrroga"
        }
        break
      case EVENTO_FIN_PARTIDO: parteActual = "postPartido"; break
    }
    console.log(`Fase actual determinada: ${parteActual}, prórrogas registradas: ${prorrogasRegistradas}`)
  }

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  function detectarFaseSegunTiempo(tiempo) {
    if (eventosFase.length === 0) return "prePartido"
    const eventosOrdenados = [...eventosFase].sort((a, b) => a.timestamp - b.timestamp)
    let fase = "prePartido"
    let iniciosProrroga = 0
    let finesProrroga = 0
    for (const evento of eventosOrdenados) {
      if (evento.timestamp > tiempo) break
      const tipoId = Number.parseInt(evento.eventTypeId)
      switch (tipoId) {
        case EVENTO_INICIO_PRIMER_TIEMPO: fase = "parte1"; break
        case EVENTO_FIN_PRIMER_TIEMPO: fase = "entrePartes"; break
        case EVENTO_INICIO_SEGUNDO_TIEMPO: fase = "parte2"; break
        case EVENTO_FIN_SEGUNDO_TIEMPO: fase = "postTiempoReglamentario"; break
        case EVENTO_INICIO_PRORROGA: iniciosProrroga++; fase = iniciosProrroga === 1 ? "prorroga1" : "prorroga2"; break
        case EVENTO_FIN_PRORROGA:
          finesProrroga++
          if (finesProrroga === 1 && iniciosProrroga > 1) fase = "entreProrroga"
          else if (finesProrroga >= 2 || iniciosProrroga === finesProrroga) fase = "postProrroga"
          break
        case EVENTO_FIN_PARTIDO: fase = "postPartido"; break
      }
    }
    return fase
  }
  // Devuelve el conteo de TM de un equipo por fase HASTA el tiempo actual
function contarTiemposMuertosHasta(equipo, currentTime) {
  // Accede a todos los eventos registrados hasta currentTime
  const eventos = (window.controlFasesPartido && window.controlFasesPartido.eventosRegistrados)
    ? window.controlFasesPartido.eventosRegistrados
    : (window.eventosRegistrados || []);
  const tiemposMuertos = eventos.filter(
    (evento) =>
      Number.parseInt(evento.eventTypeId) === EVENTO_TIEMPO_MUERTO &&
      evento.equipoTipo === equipo &&
      evento.timestamp <= currentTime
  );
  // Inicializa el conteo por fase
  const conteo = { parte1: 0, parte2: 0, prorroga1: 0, prorroga2: 0 };
  tiemposMuertos.forEach(ev => {
    const fase = detectarFaseSegunTiempo(ev.timestamp);
    if (conteo[fase] !== undefined) conteo[fase]++;
  });
  return conteo;
}


  function actualizarUI() {
    if (indicadorFaseElement) {
      let textoFase = "Pre-partido"
      let claseCSS = "pre-partido"
      switch (parteActual) {
        case "parte1": textoFase = "1ª Parte"; claseCSS = "parte1"; break
        case "entrePartes": textoFase = "Descanso"; claseCSS = "descanso"; break
        case "parte2": textoFase = "2ª Parte"; claseCSS = "parte2"; break
        case "postTiempoReglamentario": textoFase = "Fin Tiempo Reglamentario"; claseCSS = "fin-tiempo"; break
        case "prorroga1": textoFase = "1ª Prórroga"; claseCSS = "prorroga1"; break
        case "entreProrroga": textoFase = "Descanso Prórroga"; claseCSS = "descanso-prorroga"; break
        case "prorroga2": textoFase = "2ª Prórroga"; claseCSS = "prorroga2"; break
        case "postProrroga": textoFase = "Fin Prórroga"; claseCSS = "fin-prorroga"; break
        case "postPartido": textoFase = "Fin del Partido"; claseCSS = "fin-partido"; break
      }
      indicadorFaseElement.innerHTML = `<i class="fas fa-clock"></i> <span>Fase: ${textoFase}</span>`
      indicadorFaseElement.className = "fase-actual-indicador"
      indicadorFaseElement.classList.add(claseCSS)
    }
    actualizarContadoresTiemposMuertos()
  }

function actualizarContadoresTiemposMuertos() {
  const currentTime = videoPlayer ? videoPlayer.currentTime : 0;
  actualizarCirculosTiemposMuertos("local", parteActual, currentTime);
  actualizarCirculosTiemposMuertos("visitante", parteActual, currentTime);
}


  function actualizarCirculosTiemposMuertos(equipo, fase,currentTime) {
  const circlesContainer = contadoresTiemposMuertos[equipo]
  if (!circlesContainer) return
  const tiemposMuertos = contarTiemposMuertosHasta(equipo, currentTime);
  let totalCirculos = 3
  if (fase.includes("prorroga") || fase === "entreProrroga" || fase === "postProrroga") {
    const iniciosProrroga = eventosFase.filter(
      (e) => Number.parseInt(e.eventTypeId) === EVENTO_INICIO_PRORROGA,
    ).length
    totalCirculos += iniciosProrroga
    while (circlesContainer.children.length < totalCirculos) {
      const circle = document.createElement("div")
      circle.className = "tm-circle disabled"
      circle.dataset.index = circlesContainer.children.length
      circlesContainer.appendChild(circle)
    }
  }
  const circles = Array.from(circlesContainer.children)
  circles.forEach((circle) => { circle.className = "tm-circle" })

  // === Lógica visual para cada círculo ===
  if (fase === "prePartido") {
    circles[0].classList.add("available")
    circles[1].classList.add("available")
    circles[2].classList.add("disabled")
  } else if (fase === "parte1") {
    if (tiemposMuertos.parte1 >= 1) { circles[0].classList.add("used") } else { circles[0].classList.add("available") }
    if (tiemposMuertos.parte1 >= 2) { circles[1].classList.add("used") } else { circles[1].classList.add("available") }
    circles[2].classList.add("disabled")
  } else if (fase === "entrePartes" || fase === "parte2") {
    if (tiemposMuertos.parte1 >= 1) { circles[0].classList.add("used") } else { circles[0].classList.add("used") }
    if (tiemposMuertos.parte1 >= 2) {
      circles[1].classList.add("used")
    } else if (fase === "parte2" && tiemposMuertos.parte2 >= 1) {
      circles[1].classList.add("used")
    } else {
      circles[1].classList.add(fase === "entrePartes" ? "disabled" : "available")
    }
    if (fase === "parte2" && tiemposMuertos.parte2 >= 2) {
      circles[2].classList.add("used")
    } else if (fase === "parte2" && tiemposMuertos.parte1 >= 2 && tiemposMuertos.parte2 >= 1) {
      circles[2].classList.add("used")
    } else {
      circles[2].classList.add(fase === "entrePartes" ? "disabled" : "available")
    }
  } else if (fase === "postTiempoReglamentario" || fase === "postPartido") {
    if (tiemposMuertos.parte1 >= 1) { circles[0].classList.add("used") } else { circles[0].classList.add("used") }
    if (tiemposMuertos.parte1 >= 2 || tiemposMuertos.parte2 >= 1) { circles[1].classList.add("used") } else { circles[1].classList.add("disabled") }
    if (tiemposMuertos.parte2 >= 2 || (tiemposMuertos.parte1 >= 2 && tiemposMuertos.parte2 >= 1)) { circles[2].classList.add("used") } else { circles[2].classList.add("disabled") }
  } else if (fase.includes("prorroga") || fase === "entreProrroga" || fase === "postProrroga") {
    // Los 3 primeros círculos (tiempo reglamentario)
    if (tiemposMuertos.parte1 >= 1) { circles[0].classList.add("used") } else { circles[0].classList.add("used") }
    if (tiemposMuertos.parte1 >= 2 || tiemposMuertos.parte2 >= 1) { circles[1].classList.add("used") } else { circles[1].classList.add("disabled") }
    if (tiemposMuertos.parte2 >= 2 || (tiemposMuertos.parte1 >= 2 && tiemposMuertos.parte2 >= 1)) { circles[2].classList.add("used") } else { circles[2].classList.add("disabled") }
    // Círculos adicionales para prórrogas
    if (circles.length > 3) {
      if (fase === "prorroga1") {
        if (tiemposMuertos.prorroga1 >= 1) { circles[3].classList.add("used") } else { circles[3].classList.add("available") }
        if (circles.length > 4) circles[4].classList.add("disabled")
      } else if (fase === "prorroga2" || fase === "entreProrroga") {
        if (tiemposMuertos.prorroga1 >= 1) { circles[3].classList.add("used") } else { circles[3].classList.add("disabled") }
        if (circles.length > 4) {
          if (fase === "prorroga2") {
            if (tiemposMuertos.prorroga2 >= 1) { circles[4].classList.add("used") } else { circles[4].classList.add("available") }
          } else {
            circles[4].classList.add("disabled")
          }
        }
      } else if (fase === "postProrroga") {
        if (tiemposMuertos.prorroga1 >= 1) { circles[3].classList.add("used") } else { circles[3].classList.add("disabled") }
        if (circles.length > 4) {
          if (tiemposMuertos.prorroga2 >= 1) { circles[4].classList.add("used") } else { circles[4].classList.add("disabled") }
        }
      }
      for (let i = 3; i < circles.length; i++) {
        circles[i].classList.add("extra")
      }
    }
  }
  const statValue = document.getElementById(`tiempos-muertos-${equipo}`)
  if (statValue) statValue.style.display = "none"
}


  function manejarNuevoEvento(e) {
    const evento = e.detail
    const tipoId = Number.parseInt(evento.eventTypeId)
    const esFase = [
      EVENTO_INICIO_PRIMER_TIEMPO,
      EVENTO_FIN_PRIMER_TIEMPO,
      EVENTO_INICIO_SEGUNDO_TIEMPO,
      EVENTO_FIN_SEGUNDO_TIEMPO,
      EVENTO_INICIO_PRORROGA,
      EVENTO_FIN_PRORROGA,
      EVENTO_FIN_PARTIDO,
    ].includes(tipoId)
    if (esFase) {
      console.log("Nuevo evento de fase registrado:", evento)
      eventosFase.push(evento)
      eventosFase.sort((a, b) => a.timestamp - b.timestamp)
      determinarFaseActual()
      actualizarUI()
    }
    if (tipoId === EVENTO_TIEMPO_MUERTO && evento.equipoTipo) {
      console.log("Nuevo tiempo muerto registrado:", evento)
      const fase = detectarFaseSegunTiempo(evento.timestamp)
      if (tiemposMuertosSolicitados[evento.equipoTipo] && tiemposMuertosSolicitados[evento.equipoTipo][fase] !== undefined) {
        tiemposMuertosSolicitados[evento.equipoTipo][fase]++
        let indexCirculo = 0
        if (fase === "parte1") indexCirculo = tiemposMuertosSolicitados[evento.equipoTipo].parte1 - 1
        else if (fase === "parte2") {
          if (tiemposMuertosSolicitados[evento.equipoTipo].parte1 < 2) indexCirculo = 1
          else indexCirculo = 2
        } else if (fase === "prorroga1") indexCirculo = 3
        else if (fase === "prorroga2") indexCirculo = 4
        //animarCirculoTiempoMuerto(evento.equipoTipo, indexCirculo)
      }
      actualizarUI()
    }
  }

  function manejarEventoEliminado(e) {
    const evento = e.detail
    const tipoId = Number.parseInt(evento.eventTypeId)
    const esFase = [
      EVENTO_INICIO_PRIMER_TIEMPO,
      EVENTO_FIN_PRIMER_TIEMPO,
      EVENTO_INICIO_SEGUNDO_TIEMPO,
      EVENTO_FIN_SEGUNDO_TIEMPO,
      EVENTO_INICIO_PRORROGA,
      EVENTO_FIN_PRORROGA,
      EVENTO_FIN_PARTIDO,
    ].includes(tipoId)
    if (esFase) {
      console.log("Evento de fase eliminado:", evento)
      eventosFase = eventosFase.filter((e) => e.id !== evento.id)
      determinarFaseActual()
      actualizarUI()
    }
    if (tipoId === EVENTO_TIEMPO_MUERTO && evento.equipoTipo) {
      console.log("Tiempo muerto eliminado:", evento)
      const fase = detectarFaseSegunTiempo(evento.timestamp)
      if (
        tiemposMuertosSolicitados[evento.equipoTipo] &&
        tiemposMuertosSolicitados[evento.equipoTipo][fase] !== undefined &&
        tiemposMuertosSolicitados[evento.equipoTipo][fase] > 0
      ) {
        tiemposMuertosSolicitados[evento.equipoTipo][fase]--
      }
      actualizarUI()
    }
  }

  // --------- VALIDACIONES ------------

 function validarTiempoMuerto(evento) {
  console.log("[TM] --- Validando tiempo muerto:", evento);

  if (Number.parseInt(evento.eventTypeId) !== EVENTO_TIEMPO_MUERTO || !evento.equipoTipo) {
    console.log("[TM] No es evento de TM o falta equipo -> válido.");
    return { valido: true }
  }

  const equipo = evento.equipoTipo;
  const tiempo = evento.timestamp;
  const fase = detectarFaseSegunTiempo(tiempo);

  console.log(`[TM] Equipo: ${equipo}, Tiempo: ${tiempo}, Fase detectada: ${fase}`);

  if (
    ["prePartido", "entrePartes", "postTiempoReglamentario", "entreProrroga", "postProrroga", "postPartido"].includes(fase)
  ) {
    console.warn(`[TM] Fase prohibida: ${fase}.`);
    return {
      valido: false,
      mensaje: `No se pueden solicitar tiempos muertos durante ${fase === "prePartido" ? "el pre-partido" : "esta fase"}`
    }
  }

  // Obtener todos los eventos ya registrados
  const eventos = (window.controlFasesPartido && window.controlFasesPartido.eventosRegistrados)
    ? window.controlFasesPartido.eventosRegistrados
    : (window.eventosRegistrados || []);

  // --- NUEVO: Filtrar SOLO los TM de ese equipo
  const tiemposMuertosEquipo = eventos.filter(
    (ev) =>
      Number.parseInt(ev.eventTypeId) === EVENTO_TIEMPO_MUERTO &&
      ev.equipoTipo === equipo
  );
  console.log(`[TM] Lista de TM del equipo (${equipo}):`, tiemposMuertosEquipo);

  // Crear lista por fase
  const tmParte1 = tiemposMuertosEquipo.filter(ev => detectarFaseSegunTiempo(ev.timestamp) === "parte1");
  const tmParte2 = tiemposMuertosEquipo.filter(ev => detectarFaseSegunTiempo(ev.timestamp) === "parte2");
  const tmProrroga1 = tiemposMuertosEquipo.filter(ev => detectarFaseSegunTiempo(ev.timestamp) === "prorroga1");
  const tmProrroga2 = tiemposMuertosEquipo.filter(ev => detectarFaseSegunTiempo(ev.timestamp) === "prorroga2");

  console.log(`[TM] TM parte1:`, tmParte1.length, tmParte1);
  console.log(`[TM] TM parte2:`, tmParte2.length, tmParte2);
  console.log(`[TM] TM prorroga1:`, tmProrroga1.length, tmProrroga1);
  console.log(`[TM] TM prorroga2:`, tmProrroga2.length, tmProrroga2);

  if (fase === "parte1") {
    if (tmParte1.length + 1 > 2) {
      console.warn("[TM] Restricción: más de 2 TM en parte1.");
      return {
        valido: false,
        mensaje: `El equipo ${equipo === "local" ? "local" : "visitante"} ya ha solicitado los 2 tiempos muertos permitidos en la primera parte`
      }
    }
    if (tmParte1.length + tmParte2.length + 1 > 3) {
      console.warn("[TM] Restricción: más de 3 TM en total en tiempo reglamentario.");
      return {
        valido: false,
        mensaje: `El equipo ${equipo === "local" ? "local" : "visitante"} ya ha solicitado los 3 tiempos muertos permitidos en el tiempo reglamentario`
      }
    }
  } else if (fase === "parte2") {
    if (tmParte2.length + 1 > 2) {
      console.warn("[TM] Restricción: más de 2 TM en parte2.");
      return {
        valido: false,
        mensaje: `El equipo ${equipo === "local" ? "local" : "visitante"} ya ha solicitado los 2 tiempos muertos permitidos en la segunda parte`
      }
    }
    if (tmParte1.length + tmParte2.length + 1 > 3) {
      console.warn("[TM] Restricción: más de 3 TM en total en tiempo reglamentario.");
      return {
        valido: false,
        mensaje: `El equipo ${equipo === "local" ? "local" : "visitante"} ya ha solicitado los 3 tiempos muertos permitidos en el tiempo reglamentario`
      }
    }
  } else if (fase === "prorroga1") {
    if (tmProrroga1.length >= 1) {
      return {
        valido: false,
        mensaje: `El equipo ${equipo === "local" ? "local" : "visitante"} ya ha solicitado el tiempo muerto permitido en la primera prórroga`
      }
    }
  } else if (fase === "prorroga2") {
    if (tmProrroga2.length >= 1) {
      return {
        valido: false,
        mensaje: `El equipo ${equipo === "local" ? "local" : "visitante"} ya ha solicitado el tiempo muerto permitido en la segunda prórroga`
      }
    }
  }
  console.log("[TM] Validación pasada, es válido.");
  return { valido: true }
}




  function validarProrroga() {
    if (prorrogasRegistradas >= 2) {
      return {
        valido: false,
        mensaje: "Ya se han registrado las 2 prórrogas permitidas por partido",
      }
    }
    if (!["postTiempoReglamentario", "entreProrroga"].includes(parteActual)) {
      if (eventosFase.length === 0) {
        return { valido: true }
      }
      return {
        valido: false,
        mensaje: `No se puede iniciar una prórroga en la fase actual (${parteActual})`,
      }
    }
    return { valido: true }
  }

  document.addEventListener("DOMContentLoaded", inicializar)

  return {
    inicializar,
    validarTiempoMuerto,
    validarProrroga,
    analizarEventosExternos,
    determinarFasePorTiempoVideo,
    detectarFaseSegunTiempo,
    sincronizarTiemposMuertos,
    // Si necesitas exponer los getters, puedes añadirlos aquí.
  }
})()
