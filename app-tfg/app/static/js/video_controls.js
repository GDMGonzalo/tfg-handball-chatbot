document.addEventListener("DOMContentLoaded", () => {
  // Elementos del video y controles
  const video = document.getElementById("video-player")
  const loadingMessage = document.getElementById("loading-message")
  const playPauseBtn = document.getElementById("play-pause")
  const currentTimeEl = document.getElementById("current-time")
  const durationEl = document.getElementById("duration")
  const progressContainer = document.getElementById("progress-container")
  const progressBar = document.getElementById("progress-bar")
  const fullscreenBtn = document.getElementById("fullscreen-button")
  const minimalControls = document.querySelector(".minimal-controls")
  const playbackSpeedSelect = document.getElementById("playback-speed")
  const stepBackwardBtn = document.getElementById("step-backward")
  const stepForwardBtn = document.getElementById("step-forward")
  const backwardBtn = document.getElementById("backward")
  const forwardBtn = document.getElementById("forward")
  const timePreview = document.createElement("div")

  // Configuración de saltos de tiempo
  let skipTimeSeconds = 10 // Valor predeterminado para saltos de tiempo

  // Crear selector de tiempo de salto
  const skipTimeSelect = document.createElement("select")
  skipTimeSelect.className = "skip-time-select"
  skipTimeSelect.title = "Segundos de salto"

  // Opciones para el selector de tiempo de salto
  const skipTimeOptions = [5, 10, 15, 30, 60]
  skipTimeOptions.forEach((seconds) => {
    const option = document.createElement("option")
    option.value = seconds
    option.textContent = `${seconds}s`
    if (seconds === skipTimeSeconds) {
      option.selected = true
    }
    skipTimeSelect.appendChild(option)
  })

  // Insertar el selector después del selector de velocidad
  if (playbackSpeedSelect && playbackSpeedSelect.parentNode) {
    playbackSpeedSelect.parentNode.insertBefore(skipTimeSelect, playbackSpeedSelect.nextSibling)
  }

  // Evento para cambiar el tiempo de salto
  skipTimeSelect.addEventListener("change", () => {
    skipTimeSeconds = Number.parseInt(skipTimeSelect.value, 10)
    // Actualizar texto de los botones
    backwardBtn.title = `Retroceder ${skipTimeSeconds} segundos (←)`
    forwardBtn.title = `Avanzar ${skipTimeSeconds} segundos (→)`
  })

  // Variables globales
  let selectedPlayerCard = null
  let controlsTimeout
  const frameTime = 1 / 30 // Aproximadamente un fotograma
  const MAX_PLAYERS_IN_PISTA = 7 // Máximo de jugadores en pista
  let isDragging = false
  let isEditingTime = false // Nueva variable para controlar la edición de tiempo

  // Configurar el preview de tiempo
  timePreview.className = "time-preview"
  timePreview.style.display = "none"
  progressContainer.appendChild(timePreview)

  // Ocultar controles nativos del video
  if (video) {
    video.controls = false

    // Eventos para manejar la carga del video
    video.addEventListener("loadstart", () => {
      console.log("Video: loadstart")
      if (loadingMessage) loadingMessage.style.display = "block"
    })

    video.addEventListener("canplay", () => {
      console.log("Video: canplay")
      if (loadingMessage) loadingMessage.style.display = "none"
    })

    video.addEventListener("error", (e) => {
      console.error("Error al cargar el video:", e)
      if (loadingMessage) {
        loadingMessage.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error al cargar el video'
        loadingMessage.style.backgroundColor = "rgba(220, 53, 69, 0.8)"
      }
    })

    // Intentar cargar el video explícitamente
    video.load()
  }

  // Función para formatear el tiempo (segundos a MM:SS)
  function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60)
    seconds = Math.floor(seconds % 60)
    return `${minutes}:${seconds < 10 ? "0" : ""}${seconds}`
  }

  // Función para convertir formato MM:SS a segundos
  function parseTimeToSeconds(timeStr) {
    const parts = timeStr.split(":")
    if (parts.length !== 2) return 0

    const minutes = Number.parseInt(parts[0], 10)
    const seconds = Number.parseInt(parts[1], 10)

    if (isNaN(minutes) || isNaN(seconds)) return 0

    return minutes * 60 + seconds
  }

  // Actualizar la duración del video cuando esté disponible
  video.addEventListener("loadedmetadata", () => {
    durationEl.textContent = formatTime(video.duration)
  })

  // Actualizar el tiempo actual y la barra de progreso
  video.addEventListener("timeupdate", () => {
    if (!isDragging && !isEditingTime) {
      currentTimeEl.textContent = formatTime(video.currentTime)
      const percent = (video.currentTime / video.duration) * 100
      progressBar.style.width = `${percent}%`
    }
  })

  // Función para alternar reproducción/pausa
  function togglePlay() {
    if (video.paused) {
      video.play()
      playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>'
    } else {
      video.pause()
      playPauseBtn.innerHTML = '<i class="fas fa-play"></i>'
    }
  }

  // Reproducir/Pausar el video
  playPauseBtn.addEventListener("click", (e) => {
    e.stopPropagation() // Evitar que el clic se propague al video
    togglePlay()
  })

  // También permitir hacer clic en el video para reproducir/pausar
  video.addEventListener("click", togglePlay)

  // Actualizar el icono de reproducción cuando el video se pausa o reproduce
  video.addEventListener("play", () => {
    playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>'
  })

  video.addEventListener("pause", () => {
    playPauseBtn.innerHTML = '<i class="fas fa-play"></i>'
  })

  // Mejorar la barra de progreso con arrastre y preview
  progressContainer.addEventListener("mousedown", (e) => {
    e.stopPropagation()
    isDragging = true
    updateProgressOnDrag(e)

    // Añadir eventos para arrastrar
    document.addEventListener("mousemove", updateProgressOnDrag)
    document.addEventListener("mouseup", stopDragging)
  })

  // Mostrar preview al pasar el mouse por la barra de progreso
  progressContainer.addEventListener("mousemove", (e) => {
    if (!isDragging) {
      const rect = progressContainer.getBoundingClientRect()
      const pos = (e.clientX - rect.left) / rect.width
      const previewTime = pos * video.duration

      // Mostrar el preview
      timePreview.style.display = "block"
      timePreview.textContent = formatTime(previewTime)
      timePreview.style.left = `${pos * 100}%`
    }
  })

  // Ocultar preview al salir de la barra de progreso
  progressContainer.addEventListener("mouseleave", () => {
    if (!isDragging) {
      timePreview.style.display = "none"
    }
  })

  // Función para actualizar la barra de progreso durante el arrastre
  function updateProgressOnDrag(e) {
    if (isDragging) {
      const rect = progressContainer.getBoundingClientRect()
      const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
      const seekTime = pos * video.duration

      // Actualizar visualmente la barra de progreso
      progressBar.style.width = `${pos * 100}%`

      // Actualizar el tiempo mostrado
      currentTimeEl.textContent = formatTime(seekTime)

      // Mostrar el preview
      timePreview.style.display = "block"
      timePreview.textContent = formatTime(seekTime)
      timePreview.style.left = `${pos * 100}%`
    }
  }

  // Función para detener el arrastre
  function stopDragging(e) {
    if (isDragging) {
      const rect = progressContainer.getBoundingClientRect()
      const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))

      // Establecer el tiempo del video
      video.currentTime = pos * video.duration

      // Limpiar
      isDragging = false
      timePreview.style.display = "none"
      document.removeEventListener("mousemove", updateProgressOnDrag)
      document.removeEventListener("mouseup", stopDragging)
    }
  }

  // Alternar pantalla completa
  fullscreenBtn.addEventListener("click", (e) => {
    e.stopPropagation() // Evitar que el clic se propague al video

    if (!document.fullscreenElement) {
      if (video.requestFullscreen) {
        video.requestFullscreen()
      } else if (video.webkitRequestFullscreen) {
        video.webkitRequestFullscreen()
      } else if (video.msRequestFullscreen) {
        video.msRequestFullscreen()
      }
      fullscreenBtn.innerHTML = '<i class="fas fa-compress"></i>'
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen()
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen()
      } else if (document.msExitFullscreen) {
        document.msExitFullscreen()
      }
      fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>'
    }
  })

  // Actualizar icono de pantalla completa cuando cambia el estado
  document.addEventListener("fullscreenchange", () => {
    if (document.fullscreenElement) {
      fullscreenBtn.innerHTML = '<i class="fas fa-compress"></i>'
    } else {
      fullscreenBtn.innerHTML = '<i class="fas fa-expand"></i>'
    }
  })

  // Controles de velocidad de reproducción
  playbackSpeedSelect.addEventListener("change", () => {
    video.playbackRate = Number.parseFloat(playbackSpeedSelect.value)
  })

  // Controles de navegación por fotogramas
  stepBackwardBtn.addEventListener("click", (e) => {
    e.stopPropagation()
    video.currentTime -= frameTime
  })

  stepForwardBtn.addEventListener("click", (e) => {
    e.stopPropagation()
    video.currentTime += frameTime
  })

  // Controles de salto de tiempo
  backwardBtn.addEventListener("click", (e) => {
    e.stopPropagation()
    video.currentTime = Math.max(0, video.currentTime - skipTimeSeconds) // Retroceder skipTimeSeconds segundos
  })

  forwardBtn.addEventListener("click", (e) => {
    e.stopPropagation()
    video.currentTime = Math.min(video.duration, video.currentTime + skipTimeSeconds) // Avanzar skipTimeSeconds segundos
  })

  // Ocultar controles después de un tiempo de inactividad
  function hideControls() {
    if (!video.paused) {
      minimalControls.style.opacity = "0"
    }
  }

  function resetControlsTimeout() {
    clearTimeout(controlsTimeout)
    minimalControls.style.opacity = "1"
    controlsTimeout = setTimeout(hideControls, 3000)
  }

  video.addEventListener("mousemove", resetControlsTimeout)
  minimalControls.addEventListener("mousemove", resetControlsTimeout)

  // Iniciar el timeout
  resetControlsTimeout()

  // Mantener controles visibles cuando el video está pausado
  video.addEventListener("pause", () => {
    minimalControls.style.opacity = "1"
    clearTimeout(controlsTimeout)
  })

  video.addEventListener("play", resetControlsTimeout)

  // Hacer que el tiempo actual sea editable
  currentTimeEl.classList.add("editable-time")
  currentTimeEl.title = "Haz clic para editar el tiempo"

  // Crear un input para editar el tiempo
  const timeInput = document.createElement("input")
  timeInput.type = "text"
  timeInput.className = "time-input"
  timeInput.style.display = "none"
  timeInput.maxLength = 5 // Formato MM:SS

  // Insertar el input después del tiempo actual
  currentTimeEl.parentNode.insertBefore(timeInput, currentTimeEl.nextSibling)

  // Función para activar la edición de tiempo
  currentTimeEl.addEventListener("click", (e) => {
    e.stopPropagation()

    // Pausar el video mientras se edita el tiempo
    const wasPlaying = !video.paused
    if (wasPlaying) {
      video.pause()
    }

    // Mostrar el input y ocultar el span
    currentTimeEl.style.display = "none"
    timeInput.style.display = "inline"
    timeInput.value = currentTimeEl.textContent
    timeInput.focus()
    timeInput.select()

    isEditingTime = true

    // Función para aplicar el tiempo editado
    const applyTimeEdit = () => {
      const newTimeStr = timeInput.value.trim()
      const timePattern = /^([0-9]+):([0-5][0-9])$/

      if (timePattern.test(newTimeStr)) {
        const newTimeSeconds = parseTimeToSeconds(newTimeStr)

        // Verificar que el tiempo esté dentro de los límites del video
        if (newTimeSeconds >= 0 && newTimeSeconds <= video.duration) {
          video.currentTime = newTimeSeconds
          currentTimeEl.textContent = formatTime(newTimeSeconds)
        } else {
          // Si el tiempo está fuera de los límites, mostrar un mensaje
          alert(`El tiempo debe estar entre 0:00 y ${formatTime(video.duration)}`)
          timeInput.value = currentTimeEl.textContent
        }
      } else {
        // Si el formato no es válido, restaurar el valor anterior
        timeInput.value = currentTimeEl.textContent
      }

      // Ocultar el input y mostrar el span
      timeInput.style.display = "none"
      currentTimeEl.style.display = "inline"

      isEditingTime = false

      // Reanudar la reproducción si estaba reproduciéndose
      if (wasPlaying) {
        video.play()
      }
    }

    // Aplicar el tiempo cuando se presiona Enter
    timeInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault()
        applyTimeEdit()
      } else if (e.key === "Escape") {
        e.preventDefault()
        timeInput.value = currentTimeEl.textContent
        timeInput.style.display = "none"
        currentTimeEl.style.display = "inline"
        isEditingTime = false

        // Reanudar la reproducción si estaba reproduciéndose
        if (wasPlaying) {
          video.play()
        }
      }
    })

    // Aplicar el tiempo cuando el input pierde el foco
    timeInput.addEventListener("blur", applyTimeEdit)
  })

  // FUNCIONALIDAD DE JUGADORES EN PISTA Y EVENTOS

  // Función para crear tarjeta de jugador
  function crearTarjetaJugador(jugador, enPista = false) {
      const card = document.createElement("div")

      // Detectar si es entrenador, capitán o portero
      const esEntrenador = jugador.rol && jugador.rol.toLowerCase() === "entrenador"
      const esPortero = jugador.posicion && jugador.posicion.toLowerCase() === "portero"
      const esCapitan = jugador.es_capitan

      // Formatear nombre
      const nombre = jugador.nombre?.trim() || ""
      const apellido = jugador.apellido?.trim() || ""
      const nombreFormateado = nombre && apellido ? `${nombre[0]}. ${apellido}` : nombre || apellido || "Sin nombre"

      // Clase base
      card.className = "player-card"
      if (esEntrenador) card.classList.add("coach-card")
      else if (esPortero) card.classList.add("goalkeeper-card")
      card.classList.add(enPista ? "in-pista" : "in-banquillo")

      // Dorsal visible
      let numeroDorsal = esEntrenador ? "Entrenador" : `#${jugador.dorsal || "N/A"}`
      if (!esEntrenador && esCapitan) numeroDorsal += " (C)"

      // HTML interno
      card.innerHTML = `
        <div class="dorsal">${numeroDorsal}</div>
        <div class="nombre">${nombreFormateado}</div>
      `

      // Atributos completos del jugador
      card.setAttribute("data-player-id", jugador.id)
      card.setAttribute("data-jugador-id", jugador.id)
      card.setAttribute("data-equipo-id", jugador.equipo_id)
      card.setAttribute("data-nombre", nombre)
      card.setAttribute("data-apellido", apellido)
      card.setAttribute("data-dorsal", jugador.dorsal || "")
      card.setAttribute("data-rol", jugador.rol || "jugador")
      card.setAttribute("data-posicion", jugador.posicion || "")
      card.setAttribute("data-capitan", esCapitan ? "true" : "false")

      // Evento de selección visual
      card.addEventListener("click", function (e) {
        e.preventDefault()
        e.stopPropagation()

        document.querySelectorAll(".player-card").forEach((c) => c.classList.remove("selected"))
        this.classList.add("selected")
        selectedPlayerCard = this

        console.log(`Jugador seleccionado: ${nombre} ${apellido} (ID: ${jugador.id})`)
      })

      return card
}


  // Función para cargar jugadores convocados y distribuirlos entre pista y banquillo
  function cargarJugadoresConvocados() {
    const partidoId = document.querySelector('meta[name="partido-id"]')?.getAttribute("content")
    const username = document.querySelector('meta[name="username"]')?.getAttribute("content")
    const tiempoActual = Math.floor(video?.currentTime || 0)

    if (!partidoId || !username) {
      console.error("No se pudo encontrar el ID del partido o el nombre de usuario")
      return
    }

    // Obtener jugadores convocados y jugadores en pista
    Promise.all([
      fetch(`/${username}/partido/${partidoId}/convocados`).then((res) => res.json()),
      fetch(`/${username}/partido/${partidoId}/jugadores-pista?tiempo=${tiempoActual}`).then((res) => res.json()),
    ])
      .then(([convocadosData, pistaData]) => {
        // Contenedores para jugadores en pista
        const containerPistaLocal = document.getElementById("jugadores-pista-local")
        const containerPistaVisitante = document.getElementById("jugadores-pista-visitante")

        // Contenedores para jugadores en banquillo
        const containerBanquilloLocal = document.getElementById("jugadores-local")
        const containerBanquilloVisitante = document.getElementById("jugadores-visitante")

        if (
          !containerPistaLocal ||
          !containerPistaVisitante ||
          !containerBanquilloLocal ||
          !containerBanquilloVisitante
        ) {
          console.error("No se encontraron los contenedores de jugadores")
          return
        }

        // Limpiar contenedores
        containerPistaLocal.innerHTML = ""
        containerPistaVisitante.innerHTML = ""
        containerBanquilloLocal.innerHTML = ""
        containerBanquilloVisitante.innerHTML = ""

        // Obtener IDs de jugadores en pista
        const jugadoresEnPistaLocalIds = pistaData.local.map((j) => j.id)
        const jugadoresEnPistaVisitanteIds = pistaData.visitante.map((j) => j.id)

        // Primero ordenamos los jugadores (entrenador al final)
        const sortJugadores = (jugadores) => {
          return jugadores.sort((a, b) => {
            // Entrenadores al final
            if (a.rol === "entrenador" && b.rol !== "entrenador") return 1
            if (a.rol !== "entrenador" && b.rol === "entrenador") return -1
            // Ordenar por dorsal
            return (a.dorsal || 999) - (b.dorsal || 999)
          })
        }

        // Procesar jugadores locales
        const jugadoresLocal = sortJugadores(convocadosData.local)
        jugadoresLocal.forEach((jugador) => {
          const estaEnPista = jugadoresEnPistaLocalIds.includes(jugador.id)
          const tarjeta = crearTarjetaJugador(jugador, estaEnPista)

          if (estaEnPista) {
            containerPistaLocal.appendChild(tarjeta)
          } else {
            containerBanquilloLocal.appendChild(tarjeta)
          }
        })

        // Procesar jugadores visitantes
        const jugadoresVisitante = sortJugadores(convocadosData.visitante)
        jugadoresVisitante.forEach((jugador) => {
          const estaEnPista = jugadoresEnPistaVisitanteIds.includes(jugador.id)
          const tarjeta = crearTarjetaJugador(jugador, estaEnPista)

          if (estaEnPista) {
            containerPistaVisitante.appendChild(tarjeta)
          } else {
            containerBanquilloVisitante.appendChild(tarjeta)
          }
        })

        // Mostrar mensaje si no hay jugadores en pista
        if (containerPistaLocal.children.length === 0) {
          containerPistaLocal.innerHTML = '<div class="empty-state"><p>No hay jugadores en pista</p></div>'
        }

        if (containerPistaVisitante.children.length === 0) {
          containerPistaVisitante.innerHTML = '<div class="empty-state"><p>No hay jugadores en pista</p></div>'
        }

        // Mostrar mensaje si no hay jugadores en banquillo
        if (containerBanquilloLocal.children.length === 0) {
          containerBanquilloLocal.innerHTML = '<div class="empty-state"><p>No hay jugadores en banquillo</p></div>'
        }

        if (containerBanquilloVisitante.children.length === 0) {
          containerBanquilloVisitante.innerHTML = '<div class="empty-state"><p>No hay jugadores en banquillo</p></div>'
        }
      })
      
      .catch((error) => console.error("Error al cargar los jugadores:", error))
      .finally(() => {
        // ¡¡¡AQUÍ!!!
        if (typeof actualizarSanciones2MinPorTiempo === "function" && video) {
          actualizarSanciones2MinPorTiempo(video.currentTime);
        }
      });
  }

  // Función para abrir el modal de selección de jugadores en pista
  window.openPlayerSelectionModal = (equipoType) => {
    const modal = document.getElementById("player-selection-modal")
    const partidoId = document.querySelector('meta[name="partido-id"]')?.getAttribute("content")
    const username = document.querySelector('meta[name="username"]')?.getAttribute("content")
    const tiempoActual = Math.floor(video?.currentTime || 0)

    if (!partidoId || !username) {
      console.error("No se pudo encontrar el ID del partido o el nombre de usuario")
      return
    }

    let equipoId

    if (equipoType === "local") {
      equipoId = document.querySelector('meta[name="equipo-local-id"]')?.getAttribute("content")
    } else {
      equipoId = document.querySelector('meta[name="equipo-visitante-id"]')?.getAttribute("content")
    }

    if (!equipoId) {
      console.error("No se pudo encontrar el ID del equipo")
      return
    }

    document.getElementById("equipo-pista-id").value = equipoId

    // Obtener jugadores convocados y jugadores en pista
    Promise.all([
      fetch(`/${username}/partido/${partidoId}/convocados`).then((res) => res.json()),
      fetch(`/${username}/partido/${partidoId}/jugadores-pista?tiempo=${tiempoActual}`).then((res) => res.json()),
    ])
      .then(([convocadosData, pistaData]) => {
        const jugadoresList = document.getElementById("jugadores-pista-list")
        jugadoresList.innerHTML = ""

        // Añadir mensaje informativo
        const infoDiv = document.createElement("div")
        infoDiv.className = "alert alert-info"
        infoDiv.innerHTML = `
        <strong>Tiempo actual:</strong> ${formatTime(tiempoActual)}<br>
        <strong>Nota:</strong> Selecciona hasta ${MAX_PLAYERS_IN_PISTA} jugadores que están en pista en este momento.
      `
        jugadoresList.appendChild(infoDiv)

        // Añadir advertencia de límite de jugadores
        const warningDiv = document.createElement("div")
        warningDiv.className = "player-count-warning"
        warningDiv.id = "player-count-warning"
        warningDiv.textContent = `¡Has seleccionado más de ${MAX_PLAYERS_IN_PISTA} jugadores!`
        warningDiv.style.display = "none"
        jugadoresList.appendChild(warningDiv)

        // Contador de jugadores seleccionados
        const counterDiv = document.createElement("div")
        counterDiv.className = "player-count-info"
        counterDiv.id = "player-count-info"
        counterDiv.textContent = `Jugadores seleccionados: 0/${MAX_PLAYERS_IN_PISTA}`
        jugadoresList.appendChild(counterDiv)

        const jugadores = equipoType === "local" ? convocadosData.local : convocadosData.visitante
        const jugadoresEnPista = equipoType === "local" ? pistaData.local : pistaData.visitante
        const jugadoresEnPistaIds = jugadoresEnPista.map((j) => j.id)

        // Filtrar entrenadores
        const jugadoresFiltrados = jugadores.filter((j) => j.rol !== "entrenador")

        jugadoresFiltrados.forEach((jugador) => {
          const div = document.createElement("div")
          div.className = "player-selection-item"

          const checkbox = document.createElement("input")
          checkbox.type = "checkbox"
          checkbox.name = "jugadores_pista_ids"
          checkbox.value = jugador.id
          checkbox.id = `jugador-pista-${jugador.id}`
          checkbox.className = "jugador-pista-checkbox"

          // Verificar si el jugador está en pista
          const estaEnPista = jugadoresEnPistaIds.includes(jugador.id)
          checkbox.checked = estaEnPista

          // Marcar los jugadores que ya están en pista para poder calcular cambios
          checkbox.dataset.enPista = estaEnPista.toString()

          // Determinar qué texto mostrar
          const label = document.createElement("label")
          label.htmlFor = `jugador-pista-${jugador.id}`
          label.textContent = `${jugador.dorsal ? "#" + jugador.dorsal + " - " : ""}${jugador.nombre} ${jugador.apellido}`
          if (jugador.es_capitan) {
            label.textContent += " (C)"
          }

          div.appendChild(checkbox)
          div.appendChild(label)
          jugadoresList.appendChild(div)
        })

        // Función para actualizar el contador y la advertencia
        function actualizarContador() {
          const seleccionados = document.querySelectorAll(".jugador-pista-checkbox:checked").length
          const warning = document.getElementById("player-count-warning")
          const counter = document.getElementById("player-count-info")

          counter.textContent = `Jugadores seleccionados: ${seleccionados}/${MAX_PLAYERS_IN_PISTA}`

          if (seleccionados > MAX_PLAYERS_IN_PISTA) {
            warning.style.display = "block"
            counter.style.color = "#dc3545"
          } else {
            warning.style.display = "none"
            counter.style.color = ""
          }
        }

        // Añadir evento para controlar el límite de jugadores
        const checkboxes = document.querySelectorAll(".jugador-pista-checkbox")
        checkboxes.forEach((checkbox) => {
          checkbox.addEventListener("change", actualizarContador)
        })

        // Verificar inicialmente
        actualizarContador()

        // Mostrar el modal usando jQuery para mantener la compatibilidad con Bootstrap
        // Asegurarse de que el modal se muestre correctamente
        if (typeof $ !== "undefined" && typeof $.fn.modal === "function") {
          $(modal).modal({
            backdrop: false,
            keyboard: true,
            show: true,
          })
        } else {
          console.error("jQuery o Bootstrap no están disponibles")
          // Fallback en caso de que jQuery no esté disponible
          modal.style.display = "block"
          modal.classList.add("show")
        }
      })
      .catch((err) => {
        console.error("Error al cargar los jugadores:", err)
        alert("Error al cargar los jugadores.")
      })
  }

  window.closePlayerSelectionModal = () => {
    // Cerrar el modal usando jQuery para mantener la compatibilidad con Bootstrap
    if (typeof $ !== "undefined" && typeof $.fn.modal === "function") {
      $("#player-selection-modal").modal("hide")
    } else {
      // Fallback en caso de que jQuery no esté disponible
      const modal = document.getElementById("player-selection-modal")
      if (modal) {
        modal.style.display = "none"
        modal.classList.remove("show")
      }
    }
  }

  // Manejar evento de guardar jugadores en pista
  const savePlayersPistaBtn = document.getElementById("save-players-pista")
  if (savePlayersPistaBtn) {
    savePlayersPistaBtn.addEventListener("click", () => {
      const partidoId = document.querySelector('meta[name="partido-id"]')?.getAttribute("content")
      const username = document.querySelector('meta[name="username"]')?.getAttribute("content")
      const equipoId = document.getElementById("equipo-pista-id").value
      const checkboxes = document.querySelectorAll('#jugadores-pista-list input[type="checkbox"]')

      if (!partidoId || !username || !equipoId) {
        console.error("Faltan datos necesarios para guardar jugadores en pista")
        alert("Error: Faltan datos necesarios para guardar jugadores en pista")
        return
      }

      // Obtener los jugadores actualmente seleccionados
      const jugadoresSeleccionados = Array.from(checkboxes)
        .filter((checkbox) => checkbox.checked)
        .map((checkbox) => checkbox.value)

      // Obtener los jugadores que estaban previamente en pista
      const jugadoresEnPistaActuales = Array.from(checkboxes)
        .filter((checkbox) => checkbox.dataset.enPista === "true")
        .map((checkbox) => checkbox.value)

      // Calcular jugadores que entran (seleccionados ahora pero no estaban antes)
      const jugadoresEntran = jugadoresSeleccionados.filter((id) => !jugadoresEnPistaActuales.includes(id))

      // Calcular jugadores que salen (estaban antes pero no están seleccionados ahora)
      const jugadoresSalen = jugadoresEnPistaActuales.filter((id) => !jugadoresSeleccionados.includes(id))

      // Verificar límite de jugadores
      if (jugadoresSeleccionados.length > MAX_PLAYERS_IN_PISTA) {
        alert(`Solo puedes seleccionar hasta ${MAX_PLAYERS_IN_PISTA} jugadores en pista.`)
        return
      }

      // Mostrar mensaje de carga
      const loadingMessage = document.createElement("div")
      loadingMessage.className = "alert alert-info"
      loadingMessage.textContent = "Guardando cambios..."
      document.getElementById("jugadores-pista-list").appendChild(loadingMessage)

      fetch(`/${username}/partido/${partidoId}/jugadores-pista`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          equipo_id: equipoId,
          jugadores_entran: jugadoresEntran,
          jugadores_salen: jugadoresSalen,
        }),
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Error al guardar los jugadores en pista")
          }
          return response.json()
        })
        .then((data) => {
          console.log("Jugadores en pista guardados correctamente:", data)
          window.closePlayerSelectionModal()
          // Recargar los jugadores en pista sin recargar la página
          setTimeout(() => {
            cargarJugadoresConvocados()
          }, 500)
        })
        .catch((err) => {
          console.error("Error al guardar los jugadores en pista:", err)
          alert("Error al guardar los jugadores en pista")
        })
        .finally(() => {
          // Eliminar mensaje de carga
          if (loadingMessage.parentNode) {
            loadingMessage.parentNode.removeChild(loadingMessage)
          }
        })
    })
  }

  // Llamamos a las funciones al cargar la página
  cargarJugadoresConvocados()

  // Declarar $ para compatibilidad con jQuery
  const $ = window.jQuery || window.$
})

function handleURLParams() {
    const urlParams = new URLSearchParams(window.location.search)
    const timeParam = urlParams.get("t")

    if (timeParam !== null) {
      const timeInSeconds = Number.parseInt(timeParam, 10)

      // Función para establecer el tiempo cuando el video esté listo
      const setTimeFromURL = () => {
        // Asegurarse de que el tiempo no exceda la duración del video
        const tiempoSeguro = Math.min(timeInSeconds, videoPlayer.duration)
        videoPlayer.currentTime = tiempoSeguro
        console.log(`Video posicionado desde URL en tiempo: ${formatTime(tiempoSeguro)}`)

        // Opcional: reproducir automáticamente
        videoPlayer.play()
        updatePlayPauseIcon()

        // Desplazar el video a la vista
        videoPlayer.scrollIntoView({ behavior: "smooth", block: "center" })
      }

      // Comprobar si el video ya está listo
      if (videoPlayer.readyState >= 3) {
        // HAVE_FUTURE_DATA o superior
        setTimeFromURL()
      } else {
        // Esperar a que el video esté listo
        videoPlayer.addEventListener("canplay", setTimeFromURL, { once: true })
      }

      // Limpiar el parámetro de la URL para evitar problemas al recargar
      window.history.replaceState({}, document.title, window.location.pathname)
    }
  }