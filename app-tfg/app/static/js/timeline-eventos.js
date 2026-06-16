document.addEventListener("DOMContentLoaded", () => {
  // Obtener elementos del DOM
  const eventosTbody = document.getElementById("eventos-tbody")
  const filtroTipoEvento = document.getElementById("filtro-tipo-evento")
  const btnMostrarTodos = document.getElementById("btn-mostrar-todos")
  const btnMostrarLocal = document.getElementById("btn-mostrar-local")
  const btnMostrarVisitante = document.getElementById("btn-mostrar-visitante")

  // Obtener datos del partido
  const partidoId = document.querySelector('meta[name="partido-id"]')?.getAttribute("content")
  const username = document.querySelector('meta[name="username"]')?.getAttribute("content")
  const equipoLocalId = document.querySelector('meta[name="equipo-local-id"]')?.getAttribute("content")
  const equipoVisitanteId = document.querySelector('meta[name="equipo-visitante-id"]')?.getAttribute("content")

  // Verificar que tenemos los datos necesarios
  if (!partidoId || !username) {
    console.error("No se pudo encontrar el ID del partido o el nombre de usuario")
    mostrarError("No se pudieron cargar los datos del partido")
    return
  }

  // Mapeo de tipos de evento a iconos y clases CSS (eventos base)
  const tiposEventoIconos = {
    1: { icon: "fa-futbol", class: "evento-gol" }, // Gol
    2: { icon: "fa-times-circle", class: "evento-tiro-fallido" }, // Tiro fallido
    3: { icon: "fa-times-circle", class: "evento-tiro-parado" }, // Tiro parado
    4: { icon: "fa-hand-paper", class: "evento-falta" }, // Falta cometida
    5: { icon: "fa-user-slash", class: "evento-exclusion" }, // Exclusión 2 minutos
    6: { icon: "fa-sign-in-alt", class: "evento-entrada" }, // Entra en pista
    7: { icon: "fa-sign-out-alt", class: "evento-salida" }, // Sale de pista
    8: { icon: "fa-play-circle", class: "evento-inicio-periodo" }, // Inicio primer tiempo
    9: { icon: "fa-pause-circle", class: "evento-fin-periodo" }, // Fin primer tiempo
    10: { icon: "fa-stopwatch", class: "evento-tiempo-muerto" }, // Tiempo muerto
    11: { icon: "fa-user-check", class: "evento-fin-exclusion" }, // Fin sanción 2 minutos
    12: { icon: "fa-hand-paper", class: "evento-falta" }, // Falta Recibida
    13: { icon: "fa-futbol", class: "evento-gol" }, // Gol 7 metros
    14: { icon: "fa-times-circle", class: "evento-tiro-fallido" }, // Tiro fallido 7 metros
    15: { icon: "fa-times-circle", class: "evento-tiro-parado" }, // Tiro parado 7 metros
    16: { icon: "fa-exclamation-triangle", class: "evento-7metros" }, // Comete 7 metros
    17: { icon: "fa-play-circle", class: "evento-inicio-periodo" }, // Inicio segunda parte
    18: { icon: "fa-pause-circle", class: "evento-fin-periodo" }, // Fin segunda parte
    19: { icon: "fa-play-circle", class: "evento-inicio-periodo" }, // Inicio prórroga
    20: { icon: "fa-pause-circle", class: "evento-fin-periodo" }, // Fin prórroga
    23: { icon: "fa-flag-checkered", class: "evento-fin-periodo" }, // Final del partido
    28: { icon: "fa-hand-paper", class: "evento-parada" }, // Parada
    29: { icon: "fa-hand-paper", class: "evento-parada" }, // Parada 7 metros
    30: { icon: "fa-times", class: "evento-perdida" }, // Pérdida
    31: { icon: "fa-shield-alt", class: "evento-defensa" }, // Recuperación (ahora en categoría Defensa)
    32: { icon: "fa-hands-helping", class: "evento-asistencia" }, // Asistencia de gol
    33: { icon: "fa-square", class: "evento-tarjeta-roja" }, // Tarjeta Roja
    34: { icon: "fa-square", class: "evento-tarjeta-amarilla" }, // Tarjeta Amarilla
    35: { icon: "fa-user-plus", class: "evento-portero-jugador" }, // Portería Vacía (7J.) - Portero-jugador
    36: { icon: "fa-user-plus", class: "evento-portero-jugador" }, // Portería Vacía (6J.) - Portero-jugador
    37: { icon: "fa-futbol", class: "evento-tiro" }, // Tiro (nuevo evento personalizable)
    38: { icon: "fa-shield-alt", class: "evento-defensa" }, // Tiro bloqueado (categoría Defensa)
    39: { icon: "fa-exclamation-triangle", class: "evento-sancion" }, // Sustitución ilegal
    40: { icon: "fa-hands-helping", class: "evento-asistencia" }, // Asistencia para Fly
  }

  // Mapeo de tipos de evento a descripciones (eventos base)
  const tiposEventoDescripciones = {
    1: "GOL",
    2: "TIRO FALLIDO",
    3: "TIRO PARADO",
    4: "FALTA COMETIDA",
    5: "EXCLUSIÓN 2 MINUTOS",
    6: "ENTRA EN PISTA",
    7: "SALE DE PISTA",
    8: "INICIO PRIMER TIEMPO",
    9: "FIN PRIMER TIEMPO",
    10: "TIEMPO MUERTO",
    11: "FIN SANCIÓN 2 MINUTOS",
    12: "FALTA RECIBIDA",
    13: "GOL 7 METROS",
    14: "TIRO FALLIDO 7 METROS",
    15: "TIRO PARADO 7 METROS",
    16: "COMETE 7 METROS",
    17: "INICIO SEGUNDA PARTE",
    18: "FIN SEGUNDA PARTE",
    19: "INICIO PRÓRROGA",
    20: "FIN PRÓRROGA",
    23: "FINAL DEL PARTIDO",
    28: "PARADA",
    29: "PARADA 7 METROS",
    30: "PÉRDIDA",
    31: "RECUPERACIÓN",
    32: "ASISTENCIA DE GOL",
    33: "TARJETA ROJA",
    34: "TARJETA AMARILLA",
    35: "PORTERO-JUGADOR (7J.)",
    36: "PORTERO-JUGADOR (6J.)",
    37: "TIRO",
    38: "TIRO BLOQUEADO",
    39: "SUSTITUCIÓN ILEGAL",
    40: "ASISTENCIA PARA FLY",
  }

  // Mapeos dinámicos para eventos personalizados (se llenarán al cargar eventos)
  const eventosPersonalizadosIconos = {}
  const eventosPersonalizadosDescripciones = {}

  // Eventos globales (que no pertenecen a ningún equipo)
  const eventosGlobales = [8, 9, 17, 18, 19, 20, 23]

  // Categorías de eventos para filtrado
  const categoriaEventos = {
    goles: [1, 13],
    paradas: [3, 15, 28, 29],
    exclusiones: [5, 11],
    tiempos: [10],
    periodos: [8, 9, 17, 18, 19, 20, 23],
    perdidas: [30], // Solo pérdidas
    recuperaciones: [31, 38], // Recuperaciones y Tiro bloqueado
    asistencias: [32, 40], // Asistencias de gol y Asistencia para Fly
    tarjetas: [33, 34], // Tarjetas
    portero_jugador: [35, 36], // Portero-jugador
  }

  // Variables para almacenar los datos
  let eventos = []
  let filtroActual = "todos"
  let equipoFiltro = "todos"

  // Función para formatear el tiempo (segundos a MM:SS)
  function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60)
    seconds = Math.floor(seconds % 60)
    return `${minutes}:${seconds < 10 ? "0" : ""}${seconds}`
  }

  // Función para mostrar un mensaje de error
  function mostrarError(mensaje) {
    if (eventosTbody) {
      eventosTbody.innerHTML = `
                <tr>
                    <td colspan="3" class="empty-state">
                        <i class="fas fa-exclamation-circle"></i>
                        <h3>Error</h3>
                        <p>${mensaje}</p>
                    </td>
                </tr>
            `
    }
  }

  // Función para mostrar un mensaje de "sin eventos"
  function mostrarSinEventos() {
    if (eventosTbody) {
      eventosTbody.innerHTML = `
                <tr>
                    <td colspan="3" class="empty-state">
                        <i class="fas fa-info-circle"></i>
                        <h3>No hay eventos</h3>
                        <p>No se encontraron eventos para este partido.</p>
                    </td>
                </tr>
            `
    }
  }

  // Función para obtener información de un evento (base o personalizado)
  function obtenerInfoEvento(evento) {
    let tipoEvento, descripcionEvento

    if (evento.tipo_evento_id) {
      // Para eventos de tiro (ID 37), asignar icono según el resultado
      if (evento.tipo_evento_id == 37) {
        descripcionEvento = "TIRO"

        if (evento.resultado_tiro) {
          const resultado = evento.resultado_tiro.toLowerCase()
          switch (resultado) {
            case "gol":
              tipoEvento = { icon: "fa-futbol", class: "evento-gol" }
              descripcionEvento = "GOL"
              break
            case "parado":
              tipoEvento = { icon: "fa-hand-paper", class: "evento-tiro-parado" }
              descripcionEvento = "TIRO PARADO"
              break
            case "fallado":
              tipoEvento = { icon: "fa-times-circle", class: "evento-tiro-fallido" }
              descripcionEvento = "TIRO FALLADO"
              break
            case "palo":
              tipoEvento = { icon: "fa-exclamation-triangle", class: "evento-tiro-palo" }
              descripcionEvento = "TIRO AL PALO"
              break
            case "bloqueado":
              tipoEvento = { icon: "fa-shield-alt", class: "evento-defensa" }
              descripcionEvento = "TIRO BLOQUEADO"
              break
            default:
              tipoEvento = { icon: "fa-futbol-ball", class: "evento-tiro" }
          }
        } else {
          // Si no tiene resultado_tiro, usar icono por defecto
          tipoEvento = { icon: "fa-futbol-ball", class: "evento-tiro" }
        }
      } else {
        // Para otros eventos base, usar el mapeo normal
        tipoEvento = tiposEventoIconos[evento.tipo_evento_id] || { icon: "fa-circle", class: "" }
        descripcionEvento = tiposEventoDescripciones[evento.tipo_evento_id] || "EVENTO"
      }
    } else if (evento.evento_personalizado_id) {
      // Evento personalizado
      const eventoPersonalizadoKey = `personalizado_${evento.evento_personalizado_id}`

      // Usar el nombre del evento personalizado si está disponible
      if (evento.tipo_evento && evento.tipo_evento.nombre) {
        descripcionEvento = evento.tipo_evento.nombre.toUpperCase()
      } else if (evento.descripcion) {
        descripcionEvento = evento.descripcion.toUpperCase()
      } else {
        descripcionEvento = eventosPersonalizadosDescripciones[eventoPersonalizadoKey] || "EVENTO PERSONALIZADO"
      }

      // Obtener icono del mapeo dinámico o asignar uno por categoría
      tipoEvento = eventosPersonalizadosIconos[eventoPersonalizadoKey]

      if (!tipoEvento && evento.tipo_evento && evento.tipo_evento.categoria_id) {
        // Asignar icono según la categoría si no existe en el mapeo
        tipoEvento = obtenerIconoPorCategoria(evento.tipo_evento.categoria_id)
      }

      if (!tipoEvento) {
        tipoEvento = { icon: "fa-star", class: "evento-personalizado" }
      }
    } else {
      // Fallback - usar descripción del evento si está disponible
      tipoEvento = { icon: "fa-circle", class: "" }
      if (evento.descripcion) {
        descripcionEvento = evento.descripcion.toUpperCase()
      } else {
        descripcionEvento = "EVENTO"
      }
    }

    return { tipoEvento, descripcionEvento }
  }

  // Función para obtener la descripción completa de un evento de tiro
  function obtenerDescripcionTiro(evento) {
    if (evento.zona_tiro && evento.resultado_tiro) {
      const resultado = evento.resultado_tiro.toLowerCase()
      const zona = evento.zona_tiro

      if (resultado === "gol") {
        return `Gol desde ${zona}`
      } else if (resultado === "parado") {
        return `Tiro parado desde ${zona}`
      } else if (resultado === "fallado") {
        return `Tiro fallado desde ${zona}`
      } else if (resultado === "palo") {
        return `Tiro al palo desde ${zona}`
      } else if (resultado === "bloqueado") {
        return `Tiro bloqueado desde ${zona}`
      } else {
        return `Tiro ${resultado} desde ${zona}`
      }
    }
    return null
  }

  // Función para obtener icono por categoría
  function obtenerIconoPorCategoria(categoriaId) {
    const iconosPorCategoria = {
      1: { icon: "fa-futbol", class: "evento-tiro-personalizado" }, // Tiro
      2: { icon: "fa-hand-paper", class: "evento-falta-personalizado" }, // Falta
      3: { icon: "fa-exclamation-triangle", class: "evento-sancion-personalizado" }, // Sanción
      4: { icon: "fa-exchange-alt", class: "evento-sustitucion-personalizado" }, // Sustitución
      5: { icon: "fa-globe", class: "evento-global-personalizado" }, // Global
      6: { icon: "fa-chalkboard-teacher", class: "evento-tactica-personalizado" }, // Táctica
      7: { icon: "fa-bullseye", class: "evento-penaltis-personalizado" }, // Penaltis
      8: { icon: "fa-hand-paper", class: "evento-parada-personalizado" }, // Paradas
      9: { icon: "fa-times", class: "evento-perdida-personalizado" }, // Perdidas
      10: { icon: "fa-shield-alt", class: "evento-defensa-personalizado" }, // Defensa (antes Recuperacion)
      11: { icon: "fa-hands-helping", class: "evento-asistencia-personalizado" }, // Asistencias
    }

    return iconosPorCategoria[categoriaId] || { icon: "fa-star", class: "evento-personalizado" }
  }

  // Función para cargar los eventos del partido
  function cargarEventos() {
    // Mostrar estado de carga
    if (eventosTbody) {
      eventosTbody.innerHTML = `
                <tr>
                    <td colspan="3" class="empty-state">
                        <i class="fas fa-spinner fa-spin"></i>
                        <h3>Cargando eventos...</h3>
                        <p>Por favor, espere mientras se cargan los eventos del partido.</p>
                    </td>
                </tr>
            `
    }

    // Realizar la petición para obtener los eventos
    fetch(`/${username}/partido/${partidoId}/eventos`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Error al cargar los eventos")
        }
        return response.json()
      })
      .then((data) => {
        eventos = data.eventos || []

        // Procesar eventos personalizados para crear mapeos dinámicos
        eventos.forEach((evento) => {
          if (evento.evento_personalizado_id && evento.tipo_evento) {
            const eventoPersonalizadoKey = `personalizado_${evento.evento_personalizado_id}`

            // Obtener icono según la categoría
            let iconClass = "fa-star" // Icono por defecto para eventos personalizados
            let cssClass = "evento-personalizado"

            // Asignar iconos según la categoría
            if (evento.tipo_evento.categoria_id) {
              const iconoCategoria = obtenerIconoPorCategoria(evento.tipo_evento.categoria_id)
              iconClass = iconoCategoria.icon
              cssClass = iconoCategoria.class
            }

            eventosPersonalizadosIconos[eventoPersonalizadoKey] = {
              icon: iconClass,
              class: cssClass,
            }

            // Usar el nombre del evento personalizado
            eventosPersonalizadosDescripciones[eventoPersonalizadoKey] = evento.tipo_evento.nombre
              ? evento.tipo_evento.nombre.toUpperCase()
              : "EVENTO PERSONALIZADO"
          }
        })

        // Ordenar eventos por tiempo
        eventos.sort((a, b) => a.tiempo_seg - b.tiempo_seg)

        // Mostrar los eventos
        mostrarEventos()
      })
      .catch((error) => {
        console.error("Error al cargar los eventos:", error)
        mostrarError("No se pudieron cargar los eventos del partido")
      })
  }

  // Función para verificar si dos eventos son un par de tiro parado y parada
  function sonParTiroParadaYParada(evento1, evento2) {
    // Verificar que los eventos sean de equipos contrarios
    if (evento1.equipo_id === evento2.equipo_id) return false

    // Verificar que ocurran en el mismo segundo o con 1 segundo de diferencia
    if (Math.abs(evento1.tiempo_seg - evento2.tiempo_seg) > 1) return false

    // Verificar que uno sea tiro parado y el otro parada
    const esTiroParado1 =
      (evento1.tipo_evento_id && [3, 15].includes(evento1.tipo_evento_id)) ||
      (evento1.tipo_evento_id === 37 && evento1.resultado_tiro && evento1.resultado_tiro.toLowerCase() === "parado")
    const esParada1 = evento1.tipo_evento_id && [28, 29].includes(evento1.tipo_evento_id)

    const esTiroParado2 =
      (evento2.tipo_evento_id && [3, 15].includes(evento2.tipo_evento_id)) ||
      (evento2.tipo_evento_id === 37 && evento2.resultado_tiro && evento2.resultado_tiro.toLowerCase() === "parado")
    const esParada2 = evento2.tipo_evento_id && [28, 29].includes(evento2.tipo_evento_id)

    return (esTiroParado1 && esParada2) || (esParada1 && esTiroParado2)
  }

  // Función para mostrar los eventos filtrados
  function mostrarEventos() {
    if (!eventosTbody) return

    // Filtrar eventos según los criterios actuales
    let eventosFiltrados = eventos

    // Filtrar por tipo de evento
    if (filtroActual !== "todos") {
      const tiposPermitidos = categoriaEventos[filtroActual] || []
      eventosFiltrados = eventosFiltrados.filter((evento) => {
        // Para eventos base, usar tipo_evento_id
        if (evento.tipo_evento_id) {
          return tiposPermitidos.includes(evento.tipo_evento_id)
        }
        // Para eventos personalizados, no filtrar por ahora (se podrían añadir categorías específicas)
        return false
      })
    }

    // Filtrar por equipo
    if (equipoFiltro !== "todos") {
      eventosFiltrados = eventosFiltrados.filter((evento) => {
        if (equipoFiltro === "local") {
          return evento.equipo_id == equipoLocalId
        } else if (equipoFiltro === "visitante") {
          return evento.equipo_id == equipoVisitanteId
        }
        return true
      })
    }

    // Si no hay eventos después del filtrado, mostrar mensaje
    if (eventosFiltrados.length === 0) {
      mostrarSinEventos()
      return
    }

    // Limpiar contenido actual
    eventosTbody.innerHTML = ""

    // Variables para seguimiento de fases del partido
    let faseActual = ""
    const resultadoActual = { local: 0, visitante: 0 }

    // Marcar eventos que ya han sido procesados (para pares de tiro parado/parada)
    const eventosYaProcesados = new Set()

    // Procesar y mostrar cada evento
    for (let i = 0; i < eventosFiltrados.length; i++) {
      const evento = eventosFiltrados[i]

      // Si este evento ya fue procesado como parte de un par, continuar
      if (eventosYaProcesados.has(evento.id)) continue

      // Determinar la fase del partido basada en eventos especiales (solo eventos base)
      if (evento.tipo_evento_id && [8, 17, 19].includes(evento.tipo_evento_id)) {
        // Eventos de inicio de periodo
        switch (evento.tipo_evento_id) {
          case 8:
            faseActual = "1ª PARTE"
            break
          case 17:
            faseActual = "2ª PARTE"
            break
          case 19:
            faseActual = "PRÓRROGA"
            break
        }

        // Añadir fila de fase
        const filaPeriodo = document.createElement("tr")
        filaPeriodo.className = "evento-fase"
        filaPeriodo.innerHTML = `<td colspan="3">${faseActual}</td>`
        eventosTbody.appendChild(filaPeriodo)
      }

      // Actualizar resultado para eventos de gol (solo eventos base)
      if (
        (evento.tipo_evento_id && [1, 13].includes(evento.tipo_evento_id)) ||
        (evento.tipo_evento_id === 37 && evento.resultado_tiro && evento.resultado_tiro.toLowerCase() === "gol")
      ) {
        if (evento.equipo_id == equipoLocalId) {
          resultadoActual.local++
        } else if (evento.equipo_id == equipoVisitanteId) {
          resultadoActual.visitante++
        }
      }

      // Buscar si este evento forma parte de un par tiro parado/parada
      let eventoPareja = null

      // Solo buscar pareja si es un tiro parado o una parada
      if (
        (evento.tipo_evento_id && [3, 15, 28, 29].includes(evento.tipo_evento_id)) ||
        (evento.tipo_evento_id === 37 && evento.resultado_tiro && evento.resultado_tiro.toLowerCase() === "parado")
      ) {
        // Buscar en los eventos cercanos (siguiente o anterior)
        for (let j = Math.max(0, i - 1); j <= Math.min(eventosFiltrados.length - 1, i + 1); j++) {
          if (i !== j && sonParTiroParadaYParada(evento, eventosFiltrados[j])) {
            eventoPareja = eventosFiltrados[j]
            break
          }
        }
      }

      // Crear fila para el evento
      const fila = document.createElement("tr")
      fila.setAttribute("data-tiempo", evento.tiempo_seg)
      fila.setAttribute("data-evento-id", evento.id)

      // Añadir clase para eventos de periodo (solo eventos base)
      if (evento.tipo_evento_id && eventosGlobales.includes(evento.tipo_evento_id)) {
        fila.classList.add("evento-global")
      }

      // Determinar si el evento es del equipo local o visitante
      const esLocal = evento.equipo_id == equipoLocalId
      const esVisitante = evento.equipo_id == equipoVisitanteId
      const esGlobal =
        (!esLocal && !esVisitante) || (evento.tipo_evento_id && eventosGlobales.includes(evento.tipo_evento_id))

      // Obtener información del tipo de evento
      const { tipoEvento, descripcionEvento } = obtenerInfoEvento(evento)

      // Crear contenido de la celda según el equipo
      let celdaLocal = ""
      let celdaVisitante = ""
      let celdaTiempo = ""

      // Formatear el tiempo
      celdaTiempo = `
                <div class="evento-tiempo">${formatTime(evento.tiempo_seg)}</div>
                <div class="resultado">${resultadoActual.local}-${resultadoActual.visitante}</div>
            `

      // Obtener descripción final (con zona si es un tiro)
      const descripcionTiro = obtenerDescripcionTiro(evento)
      const descripcionFinal = descripcionTiro || descripcionEvento

      // Si tenemos un par de tiro parado/parada, mostrarlos en la misma línea
      if (eventoPareja) {
        // Marcar el evento pareja como procesado
        eventosYaProcesados.add(eventoPareja.id)

        const { tipoEvento: tipoEventoPareja, descripcionEvento: descripcionEventoPareja } =
          obtenerInfoEvento(eventoPareja)

        // Determinar qué evento va en qué lado (local o visitante)
        const eventoLocal = evento.equipo_id == equipoLocalId ? evento : eventoPareja
        const eventoVisitante = evento.equipo_id == equipoVisitanteId ? evento : eventoPareja

        // Información del tipo de evento para cada lado
        const { tipoEvento: tipoEventoLocal, descripcionEvento: descripcionEventoLocal } =
          obtenerInfoEvento(eventoLocal)
        const { tipoEvento: tipoEventoVisitante, descripcionEvento: descripcionEventoVisitante } =
          obtenerInfoEvento(eventoVisitante)

        // Obtener descripciones finales para cada evento
        const descripcionTiroLocal = obtenerDescripcionTiro(eventoLocal)
        const descripcionTiroVisitante = obtenerDescripcionTiro(eventoVisitante)
        const descripcionFinalLocal = descripcionTiroLocal || descripcionEventoLocal
        const descripcionFinalVisitante = descripcionTiroVisitante || descripcionEventoVisitante

        // Crear contenido para el lado local
        celdaLocal = `
          <div>
            <span class="evento-icon ${tipoEventoLocal.class}"><i class="fas ${tipoEventoLocal.icon}"></i></span>
            ${
              eventoLocal.jugador
                ? `
                <span class="evento-jugador">${eventoLocal.jugador.dorsal ? "#" + eventoLocal.jugador.dorsal + " - " : ""}${eventoLocal.jugador.nombre} ${eventoLocal.jugador.apellido}</span>
              `
                : ""
            }
            <span class="evento-detalle">${descripcionFinalLocal}</span>
          </div>
        `

        // Crear contenido para el lado visitante
        celdaVisitante = `
          <div>
            ${
              eventoVisitante.jugador
                ? `
                <span class="evento-jugador">${eventoVisitante.jugador.nombre} ${eventoVisitante.jugador.apellido}${eventoVisitante.jugador.dorsal ? " - #" + eventoVisitante.jugador.dorsal : ""}</span>
              `
                : ""
            }
            <span class="evento-detalle">${descripcionFinalVisitante}</span>
            <span class="evento-icon evento-icon-right ${tipoEventoVisitante.class}"><i class="fas ${tipoEventoVisitante.icon}"></i></span>
          </div>
        `
      } else {
        // Contenido para eventos globales (inicio/fin de periodos, etc.)
        if (esGlobal) {
          // Para eventos globales, mostrar el tiempo debajo del resultado y centrado
          celdaTiempo = `
            <div class="evento-tiempo">${formatTime(evento.tiempo_seg)}</div>
            <div class="resultado">${resultadoActual.local}-${resultadoActual.visitante}</div>
            <div class="evento-global-info">
              <span class="evento-icon ${tipoEvento.class}"><i class="fas ${tipoEvento.icon}"></i></span>
              <span class="evento-detalle-global">${descripcionFinal}</span>
            </div>
          `
          celdaLocal = `<div class="text-center">-</div>`
          celdaVisitante = `<div class="text-center">-</div>`
        }
        // Contenido para eventos del equipo local
        else if (esLocal) {
          celdaLocal = `
                      <div>
                          <span class="evento-icon ${tipoEvento.class}"><i class="fas ${tipoEvento.icon}"></i></span>
                          ${
                            evento.jugador
                              ? `
                              <span class="evento-jugador">${evento.jugador.dorsal ? "#" + evento.jugador.dorsal + " - " : ""}${evento.jugador.nombre} ${evento.jugador.apellido}</span>
                          `
                              : ""
                          }
                          <span class="evento-detalle">${descripcionFinal}</span>
                      </div>
                  `
          celdaVisitante = `<div class="text-center">-</div>`
        }
        // Contenido para eventos del equipo visitante
        else if (esVisitante) {
          celdaLocal = `<div class="text-center">-</div>`
          celdaVisitante = `
                      <div>
                          ${
                            evento.jugador
                              ? `
                              <span class="evento-jugador">${evento.jugador.nombre} ${evento.jugador.apellido}${evento.jugador.dorsal ? " - #" + evento.jugador.dorsal : ""}</span>
                          `
                              : ""
                          }
                          <span class="evento-detalle">${descripcionFinal}</span>
                          <span class="evento-icon evento-icon-right ${tipoEvento.class}"><i class="fas ${tipoEvento.icon}"></i></span>
                      </div>
                  `
        }
      }

      // Asignar contenido a la fila
      fila.innerHTML = `
                <td class="equipo-local">${celdaLocal}</td>
                <td class="tiempo">${celdaTiempo}</td>
                <td class="equipo-visitante">${celdaVisitante}</td>
            `

      // Añadir evento de clic para saltar al tiempo del video
      fila.addEventListener("click", function () {
        const tiempo = Number.parseInt(this.getAttribute("data-tiempo"), 10)
        saltarAlTiempoDelVideo(tiempo)
      })

      // Añadir la fila a la tabla
      eventosTbody.appendChild(fila)
    }
  }

  // Función para saltar al tiempo específico del video
  function saltarAlTiempoDelVideo(tiempoSeg) {
    // Buscar el reproductor de video en la página actual
    const videoPlayer = document.getElementById("video-player")

    if (videoPlayer) {
      // Si estamos en la página del video, saltar al tiempo y reproducir
      videoPlayer.currentTime = tiempoSeg
      videoPlayer.play()

      // Hacer scroll al reproductor de video
      videoPlayer.scrollIntoView({ behavior: "smooth", block: "center" })
    } else {
      // Si estamos en la vista sin video, redirigir a la página del video con el parámetro de tiempo
      const videos = document.querySelectorAll(".video-card a")
      if (videos.length > 0) {
        const videoUrl = videos[0].getAttribute("href")
        if (videoUrl) {
          // Añadir el parámetro de tiempo a la URL
          window.location.href = `${videoUrl}${videoUrl.includes("?") ? "&" : "?"}t=${tiempoSeg}`
        }
      } else {
        // Si no encontramos enlaces de video, intentar obtener el ID del video de otra manera
        const videoId = obtenerPrimerVideoId()
        if (videoId) {
          const username = document.querySelector('meta[name="username"]').content
          window.location.href = `/${username}/video/${videoId}/ver?t=${tiempoSeg}`
        } else {
          // Mostrar notificación si no se puede encontrar un video
         
            alert("No se encontró ningún video para este partido")
          
        }
      }
    }
  }

  // Función auxiliar para obtener el ID del primer video disponible
  function obtenerPrimerVideoId() {
    // Buscar en los enlaces de video en la página
    const videoLinks = document.querySelectorAll('a[href*="/video/"]')
    if (videoLinks.length > 0) {
      // Extraer el ID del video del primer enlace
      const href = videoLinks[0].getAttribute("href")
      const match = href.match(/\/video\/(\d+)\/ver/)
      if (match && match[1]) {
        return match[1]
      }
    }
    return null
  }

  // Eventos para los filtros
  if (filtroTipoEvento) {
    filtroTipoEvento.addEventListener("change", function () {
      filtroActual = this.value
      mostrarEventos()
    })
  }

  if (btnMostrarTodos) {
    btnMostrarTodos.addEventListener("click", () => {
      equipoFiltro = "todos"
      actualizarBotonesEquipo()
      mostrarEventos()
    })
  }

  if (btnMostrarLocal) {
    btnMostrarLocal.addEventListener("click", () => {
      equipoFiltro = "local"
      actualizarBotonesEquipo()
      mostrarEventos()
    })
  }

  if (btnMostrarVisitante) {
    btnMostrarVisitante.addEventListener("click", () => {
      equipoFiltro = "visitante"
      actualizarBotonesEquipo()
      mostrarEventos()
    })
  }

  // Función para actualizar la apariencia de los botones de filtro por equipo
  function actualizarBotonesEquipo() {
    if (btnMostrarTodos) btnMostrarTodos.classList.toggle("active", equipoFiltro === "todos")
    if (btnMostrarLocal) btnMostrarLocal.classList.toggle("active", equipoFiltro === "local")
    if (btnMostrarVisitante) btnMostrarVisitante.classList.toggle("active", equipoFiltro === "visitante")
  }

  // Inicializar la vista
  cargarEventos()
  actualizarBotonesEquipo()

 
})
