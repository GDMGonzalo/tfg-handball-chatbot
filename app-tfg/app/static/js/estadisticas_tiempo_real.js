/**
 * Estadísticas en Tiempo Real
 *
 * Este script maneja la actualización en tiempo real de las estadísticas
 * del partido durante la reproducción y anotación de eventos de video.
 */

// Constantes para IDs de tipos de eventos
const EVENTO_GOL_ID = 37
const EVENTO_GOL_7M_ID = 13
const EVENTO_FALTA_COMETIDA_ID = 4
const EVENTO_PERDIDA_ID = 30 
const EVENTO_RECUPERACION_ID = 31

// Estado de las estadísticas
const estadisticas = {
  local: {
    goles: 0,
    tiemposMuertos: 0,
    faltas: 0,
    perdidas: 0,
    recuperaciones: 0,
  },
  visitante: {
    goles: 0,
    tiemposMuertos: 0,
    faltas: 0,
    perdidas: 0,
    recuperaciones: 0,
  },
}

// Almacenamiento de eventos para cálculos dinámicos de goles y faltas
let golesEvents = []
let faltasEvents = []
let tiemposMuertosEvents = []
let sanciones2MinEvents = []
let perdidasEvents = []
let recuperacionesEvents = []


// Último tiempo procesado para evitar actualizaciones innecesarias
let lastProcessedTime = -1

// Elementos DOM
let golesLocalElement
let tiemposMuertosLocalElement
let faltasLocalElement
let golesVisitanteElement
let tiemposMuertosVisitanteElement
let faltasVisitanteElement
let scoreLocalElement
let scoreVisitanteElement
let perdidasLocalElement
let perdidasVisitanteElement
let recuperacionesLocalElement
let recuperacionesVisitanteElement

// Referencia al reproductor de video
let videoPlayer = null

// Inicialización cuando el DOM está listo
document.addEventListener("DOMContentLoaded", () => {
  console.log("Inicializando módulo de estadísticas en tiempo real")

  // Obtener referencias a los elementos DOM
  golesLocalElement = document.getElementById("goles-local")
  tiemposMuertosLocalElement = document.getElementById("tiempos-muertos-local")
  faltasLocalElement = document.getElementById("faltas-local")
  golesVisitanteElement = document.getElementById("goles-visitante")
  tiemposMuertosVisitanteElement = document.getElementById("tiempos-muertos-visitante")
  faltasVisitanteElement = document.getElementById("faltas-visitante")
  scoreLocalElement = document.getElementById("score-local")
  scoreVisitanteElement = document.getElementById("score-visitante")
  perdidasLocalElement = document.getElementById("perdidas-local")
  perdidasVisitanteElement = document.getElementById("perdidas-visitante")
  recuperacionesLocalElement = document.getElementById("recuperaciones-local")
  recuperacionesVisitanteElement = document.getElementById("recuperaciones-visitante")


  // Verificar que todos los elementos existan
  if (
    !golesLocalElement ||
    !tiemposMuertosLocalElement ||
    !faltasLocalElement ||
    !golesVisitanteElement ||
    !tiemposMuertosVisitanteElement ||
    !faltasVisitanteElement ||
    !perdidasLocalElement ||
    !perdidasVisitanteElement ||
    !recuperacionesLocalElement ||
    !recuperacionesVisitanteElement
  ) {
    console.error("No se encontraron todos los elementos necesarios para las estadísticas")
    return
  }

  // Inicializar el seguimiento del video para goles y faltas dinámicos
  inicializarSeguimientoVideo()

  // Cargar estadísticas iniciales
  cargarEstadisticas()

  // Configurar eventos para actualización de estadísticas
  configurarEventos()
})

/**
 * Inicializa el seguimiento del video para detectar cambios en el tiempo
 * y actualizar los goles y faltas dinámicamente
 */
function inicializarSeguimientoVideo() {
  // Obtener referencia al reproductor de video
  videoPlayer = document.getElementById("video-player")

  if (!videoPlayer) {
    console.warn("No se encontró el reproductor de video. El seguimiento automático de estadísticas no estará disponible.")
    return
  }

  console.log("Inicializando seguimiento del video para estadísticas en tiempo real")

  // Escuchar cambios en el tiempo del video (reproducción normal)
  videoPlayer.addEventListener("timeupdate", manejarCambioTiempo)

  // Escuchar cuando el usuario salta a una posición específica
  videoPlayer.addEventListener("seeking", manejarCambioTiempo)
  videoPlayer.addEventListener("seeked", manejarCambioTiempo)

  // Escuchar cambios en el input de tiempo manual si existe
  const timeInput = document.getElementById("current-time")
  if (timeInput) {
    timeInput.addEventListener("change", function () {
      // Si el input es editable, actualizar las estadísticas basadas en el nuevo tiempo
      const newTime = Number.parseFloat(this.textContent || this.value)
      if (!isNaN(newTime)) {
        actualizarGolesPorTiempo(newTime)
        actualizarFaltasPorTiempo(newTime)
      }
    })
  }

  // Inicializar con el tiempo actual del video
  if (videoPlayer.readyState > 0) {
    actualizarGolesPorTiempo(videoPlayer.currentTime)
    actualizarFaltasPorTiempo(videoPlayer.currentTime)
    actualizarSanciones2MinPorTiempo(videoPlayer.currentTime)
    actualizarTiemposMuertosPorTiempo(videoPlayer.currentTime)
    actualizarPerdidasPorTiempo(videoPlayer.currentTime)
    actualizarRecuperacionesPorTiempo(videoPlayer.currentTime)
  }
}

/**
 * Maneja los cambios en el tiempo del video para actualizar los goles y faltas
 */
function manejarCambioTiempo() {
  if (!videoPlayer) return

  const currentTime = videoPlayer.currentTime

  // Evitar procesamiento innecesario si el cambio es mínimo
  if (Math.abs(currentTime - lastProcessedTime) < 0.5) return

  lastProcessedTime = currentTime

  // Actualizar goles y faltas basados en el tiempo actual
  actualizarGolesPorTiempo(currentTime)
  actualizarFaltasPorTiempo(currentTime)
  actualizarCirculosTiemposMuertos(currentTime)
  actualizarSanciones2MinPorTiempo(currentTime)
  actualizarPerdidasPorTiempo(currentTime)
  actualizarRecuperacionesPorTiempo(currentTime)
}
function actualizarCirculosTiemposMuertos(currentTime) {
  // Máximo 2 por parte, 3 en total (ajusta si tus reglas son diferentes)
  const maxTMporParte = 2
  const maxTMtotal = 3

  // Filtra los TM hasta el instante actual
  let localTM = tiemposMuertosEvents.filter(e => e.equipoTipo === "local" && e.timestamp <= currentTime)
  let visitanteTM = tiemposMuertosEvents.filter(e => e.equipoTipo === "visitante" && e.timestamp <= currentTime)

  // Lógica: maxTMtotal círculos, los usados en rojo, libres en verde
  renderizarCirculosTM("tm-circulos-local", localTM.length, maxTMtotal)
  renderizarCirculosTM("tm-circulos-visitante", visitanteTM.length, maxTMtotal)
}

function renderizarCirculosTM(containerId, usados, total) {
  const wrapper = document.getElementById(containerId)
  if (!wrapper) return
  wrapper.innerHTML = ""
  for (let i = 0; i < total; i++) {
    const circle = document.createElement("span")
    circle.className = "tm-circle " + (i < usados ? "used" : "free")
    wrapper.appendChild(circle)
  }
}


/**
 * Configura los eventos necesarios para la actualización de estadísticas
 */
function configurarEventos() {
  // Escuchar eventos personalizados de registro de eventos
  document.addEventListener("eventoRegistrado", (e) => {
  console.log("Evento registrado detectado:", e.detail)
  const tipoEventoId = Number.parseInt(e.detail.eventTypeId)
  const resultadoTiro = e.detail.resultado_tiro || null
  console.log("Resultado tiro:", resultadoTiro)
  if (tipoEventoId === EVENTO_GOL_7M_ID) {
    golesEvents.push(e.detail)
    golesEvents.sort((a, b) => a.timestamp - b.timestamp)
    if (videoPlayer) {
      actualizarGolesPorTiempo(videoPlayer.currentTime)

    }
  } else if (tipoEventoId === EVENTO_GOL_ID && resultadoTiro ==="Gol") {
    golesEvents.push(e.detail)
    golesEvents.sort((a, b) => a.timestamp - b.timestamp)
    if (videoPlayer) {
      actualizarGolesPorTiempo(videoPlayer.currentTime)
    }
  } else if (tipoEventoId === EVENTO_FALTA_COMETIDA_ID) {
    faltasEvents.push(e.detail)
    faltasEvents.sort((a, b) => a.timestamp - b.timestamp)
    if (videoPlayer) {
      actualizarFaltasPorTiempo(videoPlayer.currentTime)
    }
  }
  // PÉRDIDAS (igual que goles)
  else if (tipoEventoId === EVENTO_PERDIDA_ID) {
    perdidasEvents.push(e.detail)
    perdidasEvents.sort((a, b) => a.timestamp - b.timestamp)
    if (videoPlayer) {
      actualizarPerdidasPorTiempo(videoPlayer.currentTime)
    }
  }
  // RECUPERACIONES (igual que goles)
  else if (tipoEventoId === EVENTO_RECUPERACION_ID) {
    recuperacionesEvents.push(e.detail)
    recuperacionesEvents.sort((a, b) => a.timestamp - b.timestamp)
    if (videoPlayer) {
      actualizarRecuperacionesPorTiempo(videoPlayer.currentTime)
    }
  }
  // Sanciones 2 minutos
  if (tipoEventoId === EVENTO_EXCLUSION_2MIN_ID || tipoEventoId === EVENTO_FIN_SANCION_2MIN_ID) {
    sanciones2MinEvents.push(e.detail)
    sanciones2MinEvents.sort((a, b) => a.timestamp - b.timestamp)
    if (videoPlayer) {
      actualizarSanciones2MinPorTiempo(videoPlayer.currentTime)
    }
  }
})

document.addEventListener("eventoEliminado", (e) => {
  console.log("Evento eliminado detectado:", e.detail)
  const tipoEventoId = Number.parseInt(e.detail.eventTypeId)
  if (tipoEventoId === EVENTO_GOL_ID || tipoEventoId === EVENTO_GOL_7M_ID) {
    golesEvents = golesEvents.filter((evento) => evento.id !== e.detail.id)
    if (videoPlayer) {
      actualizarGolesPorTiempo(videoPlayer.currentTime)
    }
  } else if (tipoEventoId === EVENTO_FALTA_COMETIDA_ID) {
    faltasEvents = faltasEvents.filter((evento) => evento.id !== e.detail.id)
    if (videoPlayer) {
      actualizarFaltasPorTiempo(videoPlayer.currentTime)
    }
  }
  // PÉRDIDAS (igual que goles)
  else if (tipoEventoId === EVENTO_PERDIDA_ID) {
    perdidasEvents = perdidasEvents.filter((evento) => evento.id !== e.detail.id)
    if (videoPlayer) {
      actualizarPerdidasPorTiempo(videoPlayer.currentTime)
    }
  }
  // RECUPERACIONES (igual que goles)
  else if (tipoEventoId === EVENTO_RECUPERACION_ID) {
    recuperacionesEvents = recuperacionesEvents.filter((evento) => evento.id !== e.detail.id)
    if (videoPlayer) {
      actualizarRecuperacionesPorTiempo(videoPlayer.currentTime)
    }
  }
  // Sanciones 2 minutos
  if (tipoEventoId === EVENTO_EXCLUSION_2MIN_ID || tipoEventoId === EVENTO_FIN_SANCION_2MIN_ID) {
    sanciones2MinEvents = sanciones2MinEvents.filter((evento) => evento.id !== e.detail.id)
    if (videoPlayer) {
      actualizarSanciones2MinPorTiempo(videoPlayer.currentTime)
    }
  }
})


  // Configurar botones de actualización manual
  document.querySelectorAll(".refresh-stats").forEach((btn) => {
    btn.addEventListener("click", () => {
      cargarEstadisticas()
      mostrarNotificacion("Estadísticas actualizadas", "info")
    })
  })

  // Escuchar cambios en la lista de eventos (para cuando se carga inicialmente)
  let observerTimeout = null;
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === "childList" && mutation.target.id === "events-list-container") {
        clearTimeout(observerTimeout);
        observerTimeout = setTimeout(() => {
          console.log("✅ Cambio detectado una sola vez: actualizando estadísticas");
          cargarEstadisticas();
        }, 250);
        break;
      }
    }
  });

  const eventsListContainer = document.getElementById("events-list-container")
  if (eventsListContainer) {
    observer.observe(eventsListContainer, { childList: true })
  }
}


/**
 * Carga las estadísticas iniciales desde los eventos existentes
 */
function cargarEstadisticas() {
  const username = document.querySelector('meta[name="username"]').content
  const videoId = document.querySelector('meta[name="video-id"]').content

  // Reiniciar estadísticas
  resetearEstadisticas()

  // Cargar eventos del servidor
  fetch(`/${username}/video/${videoId}/eventos`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Error HTTP: ${response.status}`)
      }
      return response.json()
    })
    .then((data) => {
      if (data.eventos && Array.isArray(data.eventos)) {
        console.log(`Procesando ${data.eventos.length} eventos para estadísticas`)

        // Limpiar arrays de goles y faltas
        golesEvents = []
        faltasEvents = []
        tiemposMuertosEvents = []
        sanciones2MinEvents = []
        perdidasEvents = []
        recuperacionesEvents = []

        


        // Procesar cada evento
      data.eventos.forEach((evento) => {
        const tipoEventoId = Number.parseInt(evento.tipo_evento_id)
        const estadisticaTipo = evento.evento_personalizado?.estadistica_tipo || null
        const resultadoTiro = evento.resultado_tiro || null

       
        
        //console.log("cargamos evento",evento)
        let equipo = null
        if (evento.equipo) {
          const equipoLocalId = document.querySelector('meta[name="equipo-local-id"]').content
          equipo = evento.equipo.id.toString() === equipoLocalId ? "local" : "visitante"
        }

        if (!equipo) return // ignorar eventos sin equipo

        const eventoBase = {
          id: evento.id,
          eventTypeId: tipoEventoId?.toString() || null,
          timestamp: evento.tiempo_seg,
          equipoTipo: equipo,
        }

        if (
          tipoEventoId === EVENTO_GOL_7M_ID ||
          estadisticaTipo === "gol"
        ) {
          estadisticas[equipo].goles++
          golesEvents.push(eventoBase)
        }
        if (
          tipoEventoId === EVENTO_GOL_ID &&
          (resultadoTiro === "Gol"))
        {
          estadisticas[equipo].goles++
          golesEvents.push(eventoBase)
        }

        if (
          tipoEventoId === EVENTO_FALTA_COMETIDA_ID ||
          estadisticaTipo === "falta"
        ) {
          estadisticas[equipo].faltas++
          faltasEvents.push(eventoBase)
        }

        if (
          tipoEventoId === EVENTO_PERDIDA_ID ||
          estadisticaTipo === "perdida"
        ) {
          estadisticas[equipo].perdidas++
          perdidasEvents.push(eventoBase)
        }

        if (
          tipoEventoId === EVENTO_RECUPERACION_ID ||
          estadisticaTipo === "recuperacion"
        ) {
          estadisticas[equipo].recuperaciones++
          recuperacionesEvents.push(eventoBase)
        }

        if (tipoEventoId === EVENTO_TIEMPO_MUERTO_ID) {
          estadisticas[equipo].tiemposMuertos++
          tiemposMuertosEvents.push({
            ...eventoBase,
            eventTypeId: tipoEventoId.toString()
          })
        }

        if (tipoEventoId === EVENTO_EXCLUSION_2MIN_ID || tipoEventoId === EVENTO_FIN_SANCION_2MIN_ID) {
          sanciones2MinEvents.push({
            ...eventoBase,
            jugadorId: evento.jugador ? evento.jugador.id : evento.jugador_id
          })
        }
      })


        // Ordenar eventos por timestamp
        golesEvents.sort((a, b) => a.timestamp - b.timestamp)
        faltasEvents.sort((a, b) => a.timestamp - b.timestamp)
        tiemposMuertosEvents.sort((a, b) => a.timestamp - b.timestamp)
        perdidasEvents.sort((a, b) => a.timestamp - b.timestamp)
        recuperacionesEvents.sort((a, b) => a.timestamp - b.timestamp)


        // Actualizar la interfaz
        actualizarInterfazEstadisticas()
        console.log("golesEvents:", golesEvents)
        // Si hay video, actualizar goles y faltas según el tiempo actual
        if (videoPlayer && videoPlayer.readyState > 0) {
          actualizarGolesPorTiempo(videoPlayer.currentTime)
          actualizarFaltasPorTiempo(videoPlayer.currentTime)
          actualizarSanciones2MinPorTiempo(videoPlayer.currentTime)
          actualizarPerdidasPorTiempo(videoPlayer.currentTime)
          actualizarRecuperacionesPorTiempo(videoPlayer.currentTime)
        }
      }
    })
    .catch((error) => {
      console.error("Error al cargar estadísticas:", error)
    })
}

/**
 * Resetea las estadísticas y limpia la interfaz
 */
function resetearEstadisticas() {
  estadisticas.local.goles = 0
  estadisticas.local.tiemposMuertos = 0
  estadisticas.local.faltas = 0
  estadisticas.visitante.goles = 0
  estadisticas.visitante.tiemposMuertos = 0
  estadisticas.visitante.faltas = 0
  estadisticas.local.perdidas = 0
  estadisticas.local.recuperaciones = 0
  estadisticas.visitante.perdidas = 0
  estadisticas.visitante.recuperaciones = 0

  if (perdidasLocalElement) perdidasLocalElement.textContent = "0"
  if (perdidasVisitanteElement) perdidasVisitanteElement.textContent = "0"
  if (recuperacionesLocalElement) recuperacionesLocalElement.textContent = "0"
  if (recuperacionesVisitanteElement) recuperacionesVisitanteElement.textContent = "0"
  if (golesLocalElement) golesLocalElement.textContent = "0"
  if (golesVisitanteElement) golesVisitanteElement.textContent = "0"
  if (faltasLocalElement) faltasLocalElement.textContent = "0"
  if (faltasVisitanteElement) faltasVisitanteElement.textContent = "0"
  if (tiemposMuertosLocalElement) tiemposMuertosLocalElement.textContent = "0"
  if (tiemposMuertosVisitanteElement) tiemposMuertosVisitanteElement.textContent = "0"
}

/**
 * Actualiza la interfaz de estadísticas con los valores actuales
 */
function actualizarInterfazEstadisticas() {
  golesLocalElement.textContent = estadisticas.local.goles
  golesVisitanteElement.textContent = estadisticas.visitante.goles
  faltasLocalElement.textContent = estadisticas.local.faltas
  faltasVisitanteElement.textContent = estadisticas.visitante.faltas
  perdidasLocalElement.textContent = estadisticas.local.perdidas
  perdidasVisitanteElement.textContent = estadisticas.visitante.perdidas
  recuperacionesLocalElement.textContent = estadisticas.local.recuperaciones
  recuperacionesVisitanteElement.textContent = estadisticas.visitante.recuperaciones

  
}

/**
 * Actualiza el contador de goles dinámicamente según el minuto del video
 */
function actualizarGolesPorTiempo(currentTime) {
  let golesLocal = 0
  let golesVisitante = 0

  golesEvents.forEach((evento) => {
    if (evento.timestamp <= currentTime) {
      if (evento.equipoTipo === "local") golesLocal++
      else if (evento.equipoTipo === "visitante") golesVisitante++
    }
  })

  golesLocalElement.textContent = golesLocal
  golesVisitanteElement.textContent = golesVisitante
  if (scoreLocalElement) scoreLocalElement.textContent = golesLocal
  if (scoreVisitanteElement) scoreVisitanteElement.textContent = golesVisitante
}

/**
 * Actualiza el contador de faltas dinámicamente según el minuto del video
 */
function actualizarFaltasPorTiempo(currentTime) {
  let faltasLocal = 0
  let faltasVisitante = 0

  faltasEvents.forEach((evento) => {
    if (evento.timestamp <= currentTime) {
      if (evento.equipoTipo === "local") faltasLocal++
      else if (evento.equipoTipo === "visitante") faltasVisitante++
    }
  })

  faltasLocalElement.textContent = faltasLocal
  faltasVisitanteElement.textContent = faltasVisitante
}
function actualizarSanciones2MinPorTiempo(currentTime) {
  // 1. Limpia todas las clases .sancionado-2min de todos los jugadores
  document.querySelectorAll(".player-card.sancionado-2min").forEach(card => {
    card.classList.remove("sancionado-2min")
  })

  // 2. Busca qué jugadores están sancionados en este instante
  // Recoge todos los jugadores afectados por EXCLUSIÓN sin un FIN posterior
  // Creamos un mapa {jugadorId: [timestamps de inicio de sanción]}
  const sancionados = {}

  sanciones2MinEvents
    .filter(ev => Number(ev.eventTypeId) === EVENTO_EXCLUSION_2MIN_ID && ev.timestamp <= currentTime)
    .forEach(ev => {
      // Busca si hay un fin de sanción posterior a este inicio y antes del currentTime
      const tieneFin = sanciones2MinEvents.some(finEv =>
        Number(finEv.eventTypeId) === EVENTO_FIN_SANCION_2MIN_ID &&
        finEv.jugadorId === ev.jugadorId &&
        finEv.timestamp > ev.timestamp &&
        finEv.timestamp <= currentTime
      )
      // Si NO tiene fin, está sancionado
      if (!tieneFin) {
        sancionados[ev.jugadorId] = true
      }
    })

  Object.keys(sancionados).forEach(jugadorId => {
  console.log('Buscando sanción para:', jugadorId)
  const card = document.querySelector(`.player-card[data-player-id='${jugadorId}'], .player-card[data-jugador-id='${jugadorId}']`)
  console.log('Elemento encontrado:', card)
  if (card) {
    card.classList.add("sancionado-2min")
    console.log('Pintando sancionado:', jugadorId)
  } else {
    console.warn('No se encuentra card para jugador sancionado:', jugadorId)
  }
})


}

function actualizarPerdidasPorTiempo(currentTime) {
  let perdidasLocal = 0
  let perdidasVisitante = 0

  perdidasEvents.forEach((evento) => {
    if (evento.timestamp <= currentTime) {
      if (evento.equipoTipo === "local") perdidasLocal++
      else if (evento.equipoTipo === "visitante") perdidasVisitante++
    }
  })

  perdidasLocalElement.textContent = perdidasLocal
  perdidasVisitanteElement.textContent = perdidasVisitante
}

function actualizarRecuperacionesPorTiempo(currentTime) {
  let recuperacionesLocal = 0
  let recuperacionesVisitante = 0

  recuperacionesEvents.forEach((evento) => {
    if (evento.timestamp <= currentTime) {
      if (evento.equipoTipo === "local") recuperacionesLocal++
      else if (evento.equipoTipo === "visitante") recuperacionesVisitante++
    }
  })

  recuperacionesLocalElement.textContent = recuperacionesLocal
  recuperacionesVisitanteElement.textContent = recuperacionesVisitante
}


