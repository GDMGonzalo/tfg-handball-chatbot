////////////////////////////////////////////////////////////////////////////////////////////
// Variables globales
let selectedPlayer = null
let currentCategory = null
let currentEventType = null
let eventsData = []
let isGlobalEventActive = false // Nueva variable para rastrear si hay un evento global activo
const substitutionState = {
  active: false,
  playerOut: null,
  waitingForPlayerIn: false,
}

// Constantes para IDs de tipos de eventos
const EVENTO_EXCLUSION_2MIN_ID = 5
const EVENTO_FIN_SANCION_2MIN_ID = 11
const EVENTO_TIRO_PARADO_ID = 3
const EVENTO_TIRO_7M_PARADO_ID = 15
const EVENTO_TIEMPO_MUERTO_ID = 10
const EVENTO_INICIO_PRORROGA_ID = 19
// Constantes para eventos de tiro
const EVENTO_TIRO_IDS = [37] // IDs de eventos que son tiros
// Actualizar las zonas de tiro para incluir extremo izquierdo y extremo derecho
const ZONAS_TIRO = [
  "6m",
  "6-9m",
  "+9m",
  "Campo trasero",
  "Contraataque",
  "Extremo izquierdo",
  "Extremo derecho",
  "Golpe Franco",
]
const RESULTADOS_TIRO = ["Gol", "Parado", "Fallado", "Palo", "Bloqueado"]

// Variables para el submenú de tiro
let tiroSelectionState = {
  active: false,
  zona: null,
  resultado: null,
  eventTypeId: null,
  eventTypeName: null,
}

// Inicialización cuando el DOM está listo
document.addEventListener("DOMContentLoaded", () => {
  console.log("DOM cargado, inicializando componentes de anotación de eventos")

  // Crear el elemento de notificación si no existe
  if (!document.getElementById("event-notification")) {
    const notification = document.createElement("div")
    notification.className = "event-notification"
    notification.id = "event-notification"
    notification.style.position = "fixed"
    notification.style.bottom = "20px"
    notification.style.right = "20px"
    notification.style.padding = "10px 10px"
    notification.style.borderRadius = "4px"
    notification.style.color = "white"
    notification.style.zIndex = "9999"
    notification.style.opacity = "0"
    notification.style.transition = "opacity 0.3s ease"
    document.body.appendChild(notification)
    console.log("Elemento de notificación creado")
  }

  // Añadir estilos para diferenciar visualmente entre jugador y entrenador
  const style = document.createElement("style")
  style.textContent = `
    .event-instructions.coach-selected {
      color: #d32f2f;
      font-weight: bold;
    }
    .event-instructions.player-selected {
      color: #1976d2;
      font-weight: bold;
    }
    .event-instructions.bench-player {
      color: #ff9800;
      font-weight: bold;
    }
    .event-instructions.global-selected {
      color: #009688;
      font-weight: bold;
    }
    .player-card.selected {
      border: 2px solid #4caf50 !important;
      box-shadow: 0 0 8px rgba(76, 175, 80, 0.6) !important;
    }
    .player-card.entrenador {
      background-color = #ffebee !important;
    }
    .player-card.in-pista {
      background-color = #e8f5e9 !important;
    }
    .player-card.in-banquillo {
      background-color = #fff8e1 !important;
    }
    .category-btn.disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    .category-btn.available {
      border: 2px solid #4caf50;
    }
  `
  document.head.appendChild(style)

  // Cargar categorías de eventos
  loadEventCategories()

  // Inicializar eventos registrados
  loadSavedEvents()

  // Hacer que los jugadores sean seleccionables
  initializePlayerSelection()

  document.addEventListener("click", (e) => {
    const clickedOnPlayerCard = e.target.closest(".player-card")
    const clickedOnEventPanel = e.target.closest(".events-panel")
    const clickedOnCategoryBtn = e.target.closest(".category-btn")
    const clickedOnEventTypeBtn = e.target.closest(".event-type-btn")
    if (!clickedOnPlayerCard && !clickedOnEventPanel && !clickedOnCategoryBtn && !clickedOnEventTypeBtn) {
      if (selectedPlayer) {
        deselectPlayer()
      }
      if (isGlobalEventActive) {
        resetGlobalEventSelection()
      }
      document.querySelectorAll(".category-btn.active").forEach((btn) => {
        btn.classList.remove("active")
      })
      document.querySelectorAll(".event-type-btn.active").forEach((btn) => {
        btn.classList.remove("active")
      })
      const eventTypesContainer = document.getElementById("event-types-container")
      if (eventTypesContainer) {
        eventTypesContainer.innerHTML = ""
      }
    }
  })

  const videoPlayer = document.getElementById("video-player")
  if (videoPlayer) {
    videoPlayer.addEventListener("loadedmetadata", () => {
      videoPlayer.addEventListener("timeupdate", () => {
        if (
          window.controlFasesPartido &&
          typeof window.controlFasesPartido.determinarFasePorTiempoVideo === "function"
        ) {
          window.controlFasesPartido.determinarFasePorTiempoVideo(videoPlayer.currentTime)
        }
      })
    })
  }
})

// Función para cargar eventos disponibles para el video actual
function cargarEventosDisponibles() {
  const videoId = document.getElementById("video-player").dataset.videoId
  const username = document.getElementById("video-player").dataset.username
  console.log("Cargando eventos disponibles para el video:", videoId, "de usuario:", username)
  if (!videoId || !username) {
    console.error("No se pudo obtener el ID del video o el nombre de usuario")
    return
  }

  // Hacer la petición a la API
  fetch(`/${username}/video/${videoId}/eventos-disponibles`)
    .then((response) => {
      if (!response.ok) {
        throw new Error("Error al cargar eventos disponibles")
      }
      return response.json()
    })
    .then((data) => {
      if (data.success) {
        //console.log("Eventos disponibles cargados:", data.eventos)
        // Aquí puedes procesar los eventos disponibles
        // Por ejemplo, filtrar los eventos estándar según los disponibles
      } else {
        console.error("Error:", data.message)
      }
    })
    .catch((error) => {
      console.error("Error al cargar eventos disponibles:", error)
    })
}

// Llamar a la función cuando se carga la página
document.addEventListener("DOMContentLoaded", () => {
  // Verificar si estamos en la página de ver video
  if (document.getElementById("video-player")) {
    cargarEventosDisponibles()
  }
})

// Nueva función para resetear la selección de evento global
function resetGlobalEventSelection() {
  isGlobalEventActive = false
  currentCategory = null
  currentEventType = null
  updateInstructions("Selecciona un jugador para comenzar a registrar eventos o usa la categoría Global")
  highlightAvailableCategories()
}

// Inicializar la selección de jugadores
function initializePlayerSelection() {
  setTimeout(() => {
    const playerCards = document.querySelectorAll(
      "#jugadores-pista-local .player-card, #jugadores-pista-visitante .player-card, #jugadores-local .player-card, #jugadores-visitante .player-card",
    )
    playerCards.forEach((card) => {
      const isOnField = card.closest("#jugadores-pista-local") || card.closest("#jugadores-pista-visitante")
      const isCoach =
        card.classList.contains("entrenador") ||
        card.hasAttribute("data-entrenador") ||
        (card.querySelector(".rol") && card.querySelector(".rol").textContent.toLowerCase().includes("entrenador")) ||
        card.getAttribute("data-rol") === "entrenador" ||
        card.dataset.rol === "entrenador"
      if (isCoach) {
        card.classList.add("entrenador")
      } else if (isOnField) {
        card.classList.add("in-pista")
      } else {
        card.classList.add("in-banquillo")
      }
      if (!card.dataset.playerId) {
        const playerId =
          card.id || card.getAttribute("data-jugador-id") || "player-" + Math.random().toString(36).substr(2, 9)
        card.setAttribute("data-player-id", playerId)
      }
      card.addEventListener("click", function (e) {
        e.preventDefault()
        e.stopPropagation()
        if (isGlobalEventActive) {
          resetGlobalEventSelection()
        }
        const isOnField = this.closest("#jugadores-pista-local") || this.closest("#jugadores-pista-visitante")
        const teamType =
          this.closest("#jugadores-pista-local") || this.closest("#jugadores-local") ? "local" : "visitante"
        const isCoach =
          this.classList.contains("entrenador") ||
          this.hasAttribute("data-entrenador") ||
          (this.querySelector(".rol") && this.querySelector(".rol").textContent.toLowerCase().includes("entrenador")) ||
          this.getAttribute("data-rol") === "entrenador" ||
          this.dataset.rol === "entrenador"
        const playerId = this.dataset.playerId || this.getAttribute("data-jugador-id")
        const playerName = this.querySelector(".nombre")?.textContent || "Jugador"
        const playerNumber = this.querySelector(".dorsal")?.textContent || ""
        const teamName =
          teamType === "local"
            ? document.querySelector('meta[name="equipo-local-nombre"]').content
            : document.querySelector('meta[name="equipo-visitante-nombre"]').content
        const equipoId =
          teamType === "local"
            ? document.querySelector('meta[name="equipo-local-id"]').content
            : document.querySelector('meta[name="equipo-visitante-id"]').content
        if (substitutionState.active) {
          if (substitutionState.waitingForPlayerIn) {
            if (isOnField) {
              showNotification("El jugador que entra debe estar en el banquillo", "warning")
              return
            }
            if (substitutionState.playerOut.team !== teamType) {
              showNotification("Los jugadores deben ser del mismo equipo", "warning")
              return
            }
            const playerIn = {
              id: playerId,
              name: playerName,
              number: playerNumber,
              team: teamType,
              teamName: teamName,
              equipoId: equipoId,
              isOnField: false,
              isCoach: isCoach,
              element: this,
            }
            performSubstitution(substitutionState.playerOut, playerIn)
            resetSubstitutionState()
            return
          }
        }
        if (selectedPlayer) {
          const prevSelected = document.querySelector(".player-card.selected")
          if (prevSelected) {
            prevSelected.classList.remove("selected")
          }
        }
        selectedPlayer = {
          id: playerId,
          name: playerName,
          number: playerNumber,
          team: teamType,
          teamName: teamName,
          equipoId: equipoId,
          isOnField: isOnField ? true : false,
          isCoach: isCoach,
          element: this,
        }
        this.classList.add("selected")
        updateInstructionsAndCategories()
      })
    })
    updateInstructions("Selecciona un jugador para comenzar a registrar eventos o usa la categoría Global")
  }, 500)
}

function highlightAvailableCategories() {
  const categoryBtns = document.querySelectorAll(".category-btn")

  categoryBtns.forEach((btn) => {
    const categoryName = btn.dataset.categoryName

    // Resetear clases
    btn.classList.remove("disabled", "available")

    if (!selectedPlayer && !isGlobalEventActive) {
      // Si no hay jugador seleccionado ni evento global activo, solo Global está disponible
      if (categoryName === "Global") {
        btn.classList.add("available")
      } else {
        btn.classList.add("disabled")
      }
      return
    }

    // Si hay un evento global activo, solo mostrar disponible la categoría Global
    if (isGlobalEventActive) {
      if (categoryName === "Global") {
        btn.classList.add("available")
      } else {
        btn.classList.add("disabled")
      }
      return
    }

    // Aplicar reglas según el tipo de elemento seleccionado
    if (selectedPlayer.isCoach) {
      // Entrenador: solo Táctica y Sanción
      if (categoryName === "Táctica" || categoryName === "Sanción") {
        btn.classList.add("available")
      } else {
        btn.classList.add("disabled")
      }
    } else if (selectedPlayer.isOnField) {
      // Jugador en pista: todos excepto Global y Táctica
      if (categoryName !== "Global" && categoryName !== "Táctica") {
        btn.classList.add("available")
      } else {
        btn.classList.add("disabled")
      }
    } else {
      // Jugador en banquillo: solo Sanción
      if (categoryName === "Sanción") {
        btn.classList.add("available")
      } else {
        btn.classList.add("disabled")
      }
    }
  })
}

// Simplificar la función updateInstructionsAndCategories
function updateInstructionsAndCategories() {
  if (!selectedPlayer && !isGlobalEventActive) {
    updateInstructions("Selecciona un jugador para comenzar a registrar eventos o usa la categoría Global")
    return
  }

  if (isGlobalEventActive) {
    updateInstructions("Categoría Global seleccionada. Selecciona un tipo de evento global.")
    return
  }

  // Actualizar instrucciones según el tipo de jugador seleccionado
  let instructionText = ""
  if (selectedPlayer.isCoach) {
    instructionText = `Entrenador seleccionado: ${selectedPlayer.name}. Puedes registrar eventos de Táctica o Sanción.`
  } else if (selectedPlayer.isOnField) {
    instructionText = `Jugador en pista seleccionado: ${selectedPlayer.name} ${selectedPlayer.number ? `(${selectedPlayer.number})` : ""}. Puedes registrar cualquier tipo de evento excepto Global y Táctica.`
  } else {
    instructionText = `Jugador en banquillo seleccionado: ${selectedPlayer.name} ${selectedPlayer.number ? `(${selectedPlayer.number})` : ""}. Solo puedes registrar eventos de Sanción.`
  }

  updateInstructions(instructionText)

  // Destacar visualmente las categorías disponibles
  highlightAvailableCategories()
}

// Actualizar instrucciones
function updateInstructions(text) {
  const instructions = document.querySelector(".event-instructions")
  if (instructions) {
    instructions.textContent = text

    // Quitar todas las clases de estado
    instructions.classList.remove("coach-selected", "player-selected", "bench-player", "global-selected")

    // Si hay un jugador seleccionado, añadir una clase visual según el rol
    if (selectedPlayer) {
      if (selectedPlayer.isCoach) {
        instructions.classList.add("coach-selected")
      } else if (selectedPlayer.isOnField) {
        instructions.classList.add("player-selected")
      } else {
        instructions.classList.add("bench-player")
      }
    } else if (isGlobalEventActive) {
      // Si hay un evento global activo, añadir clase visual
      instructions.classList.add("global-selected")
    }
  }
}

function loadEventCategories() {
  const username = document.querySelector('meta[name="username"]').content
  const videoId = document.querySelector('meta[name="video-id"]').content

  // Usar la nueva ruta que obtiene eventos disponibles para este video
  fetch(`/${username}/video/${videoId}/eventos-disponibles`)
    .then((response) => response.json())
    .then((data) => {
      console.log("Datos recibidos de eventos disponibles:", data)
      const defaultCategories = [
        { id: 1, nombre: "Tiro", icono: "fa-basketball-ball" },
        { id: 2, nombre: "Falta", icono: "fa-hand-paper" },
        { id: 3, nombre: "Sanción", icono: "fa-exclamation-triangle" },
        { id: 4, nombre: "Sustitución", icono: "fa-exchange-alt" },
        { id: 5, nombre: "Global", icono: "fa-globe" },
        { id: 6, nombre: "Táctica", icono: "fa-chalkboard-teacher" },
        { id: 7, nombre: "Penaltis", icono: "fa-bullseye" },
        { id: 8, nombre: "Paradas", icono: "fa-hand-paper" },
        { id: 9, nombre: "Perdidas", icono: "fa-times" },
        { id: 10, nombre: "Defensa", icono: "fa-shield-alt" },
        { id: 11, nombre: "Asistencias", icono: "fa-hands-helping" },
      ]
      renderEventCategories(data, defaultCategories)
    })
    .catch((error) => {
      console.error("Error al cargar categorías de eventos:", error)
      // Fallback a eventos por defecto
      const defaultCategories = [
        { id: 1, nombre: "Tiro", icono: "fa-basketball-ball" },
        { id: 2, nombre: "Falta", icono: "fa-hand-paper" },
        { id: 3, nombre: "Sanción", icono: "fa-exclamation-triangle" },
        { id: 4, nombre: "Sustitución", icono: "fa-exchange-alt" },
        { id: 5, nombre: "Global", icono: "fa-globe" },
        { id: 6, nombre: "Táctica", icono: "fa-chalkboard-teacher" },
        { id: 7, nombre: "Penaltis", icono: "fa-bullseye" },
        { id: 8, nombre: "Paradas", icono: "fa-hand-paper" },
        { id: 9, nombre: "Perdidas", icono: "fa-times" },
        { id: 10, nombre: "Recuperacion", icono: "fa-recycle" },
      ]
      renderEventCategories([], defaultCategories)
    })
}

function renderEventCategories(eventosDisponibles, defaultCategories) {
  const eventsPanel = document.querySelector(".events-panel")
  if (!eventsPanel) return

  // Limpiar panel existente
  if (!eventsPanel.querySelector("h3")) {
    eventsPanel.innerHTML = "<h3>Eventos</h3>"
  }

  // Crear o actualizar contenedor de instrucciones
  let instructions = eventsPanel.querySelector(".event-instructions")
  if (!instructions) {
    instructions = document.createElement("div")
    instructions.className = "event-instructions"
    instructions.textContent = "Selecciona un jugador para comenzar a registrar eventos o usa la categoría Global"
    eventsPanel.appendChild(instructions)
  }

  // Crear o actualizar contenedor de categorías
  let categoriesContainer = eventsPanel.querySelector(".event-categories")
  if (!categoriesContainer) {
    categoriesContainer = document.createElement("div")
    categoriesContainer.className = "event-categories"
    eventsPanel.appendChild(categoriesContainer)
  } else {
    categoriesContainer.innerHTML = ""
  }

  // Añadir iconos personalizados para categorías específicas
  const iconosPersonalizados = {
    Tiro: "fa-basketball-ball",
    Falta: "fa-hand-paper",
    Sanción: "fa-exclamation-triangle",
    Sustitución: "fa-exchange-alt",
    Global: "fa-globe",
    Táctica: "fa-chalkboard-teacher",
    Penaltis: "fa-bullseye",
    Paradas: "fa-hand-paper",
    Perdidas: "fa-times",
    Defensa: "fa-shield-alt",
    Asistencias: "fa-hands-helping",
  }

  // Filtrar categorías: excluir "Paradas" a menos que tenga eventos personalizados disponibles
  const categoriasAMostrar = defaultCategories.filter((category) => {
    if (category.nombre === "Paradas") {
      // Solo mostrar "Paradas" si hay eventos personalizados disponibles para esta categoría
      const tieneEventosPersonalizados = eventosDisponibles.some(
        (cat) => cat.nombre === "Paradas" && cat.tipos_evento && cat.tipos_evento.length > 0,
      )
      return tieneEventosPersonalizados
    }
    return true
  })

  // Añadir botones de categoría
  categoriasAMostrar.forEach((category) => {
    const categoryBtn = document.createElement("button")
    categoryBtn.className = "category-btn"
    categoryBtn.dataset.categoryId = category.id
    categoryBtn.dataset.categoryName = category.nombre
    categoryBtn.innerHTML = `<i class="fas ${iconosPersonalizados[category.nombre] || "fa-question"}"></i> ${category.nombre}`

    // Evento de clic
    categoryBtn.addEventListener("click", () => {
      // Si el botón está deshabilitado, no hacer nada
      if (categoryBtn.classList.contains("disabled")) {
        const mensaje = getDisabledCategoryMessage(category.nombre)
        showNotification(mensaje, "warning")
        return
      }

      // Caso especial para categoría Global
      if (category.nombre === "Global") {
        // Si ya hay un jugador seleccionado, deseleccionarlo
        if (selectedPlayer) {
          const selectedCard = document.querySelector(".player-card.selected")
          if (selectedCard) {
            selectedCard.classList.remove("selected")
          }
          selectedPlayer = null
        }

        // Activar modo evento global
        isGlobalEventActive = true
        selectCategory(category.id, true)
        return
      }

      // Para todas las demás categorías, verificar que hay un jugador seleccionado
      if (!selectedPlayer) {
        showNotification("Primero debes seleccionar un jugador o entrenador", "warning")
        return
      }

      // Caso especial para sustitución
      if (category.nombre === "Sustitución") {
        // Verificar que el jugador seleccionado esté en pista
        if (!selectedPlayer.isOnField) {
          showNotification("Para realizar una sustitución, primero selecciona un jugador que esté en pista", "warning")
          return
        }
        handleSubstitutionCategory()
        return
      }

      // Para el resto de categorías, simplemente seleccionar
      selectCategory(category.id)
    })

    categoriesContainer.appendChild(categoryBtn)
  })

  // Crear o actualizar contenedor para tipos de eventos
  let eventTypesContainer = eventsPanel.querySelector(".event-types")
  if (!eventTypesContainer) {
    eventTypesContainer = document.createElement("div")
    eventTypesContainer.className = "event-types"
    eventTypesContainer.id = "event-types-container"
    eventsPanel.appendChild(eventTypesContainer)
  }

  // Crear o actualizar contenedor para eventos registrados
  let eventsListContainer = eventsPanel.querySelector(".events-list")
  if (!eventsListContainer) {
    eventsListContainer = document.createElement("div")
    eventsListContainer.className = "events-list"
    eventsListContainer.id = "events-list-container"
    eventsPanel.appendChild(eventsListContainer)
  }

  // Crear notificación si no existe
  if (!document.getElementById("event-notification")) {
    const notification = document.createElement("div")
    notification.className = "event-notification"
    notification.id = "event-notification"
    document.body.appendChild(notification)
  }
}

// Simplificar la función getDisabledCategoryMessage
function getDisabledCategoryMessage(categoryName) {
  if (!selectedPlayer && !isGlobalEventActive) {
    return "Primero debes seleccionar un jugador o entrenador, o usar la categoría Global"
  }

  if (isGlobalEventActive && categoryName !== "Global") {
    return "Cuando se selecciona la categoría Global, no se pueden seleccionar otras categorías"
  }

  if (selectedPlayer.isCoach) {
    if (categoryName !== "Táctica" && categoryName !== "Sanción") {
      return `Los entrenadores solo pueden registrar eventos de Táctica o Sanción`
    }
  } else if (selectedPlayer.isOnField) {
    if (categoryName === "Táctica") {
      return "Los eventos de táctica solo pueden ser asignados a entrenadores"
    }
    if (categoryName === "Global") {
      return "Los eventos globales no requieren seleccionar un jugador"
    }
  } else {
    // Jugador en banquillo
    if (categoryName !== "Sanción") {
      return `Los jugadores en banquillo solo pueden recibir eventos de Sanción`
    }
  }

  return "Esta categoría no está disponible para el jugador seleccionado"
}

// Modificar la función handleSubstitutionCategory para limpiar los tipos de eventos anteriores
function handleSubstitutionCategory() {
  // Verificar que el jugador seleccionado esté en pista
  if (!selectedPlayer.isOnField) {
    showNotification("Para realizar una sustitución, primero selecciona un jugador que esté en pista", "warning")
    return
  }

  // Limpiar cualquier tipo de evento mostrado anteriormente
  const eventTypesContainer = document.getElementById("event-types-container")
  if (eventTypesContainer) {
    eventTypesContainer.innerHTML = ""
  }

  // Iniciar el proceso de sustitución
  substitutionState.active = true
  substitutionState.playerOut = selectedPlayer
  substitutionState.waitingForPlayerIn = true

  // Actualizar instrucciones
  updateInstructions(
    `Sustitución: ${selectedPlayer.name} ${selectedPlayer.number ? `(${selectedPlayer.number})` : ""} sale. Ahora selecciona el jugador que entra del banquillo.`,
  )

  // Destacar visualmente la categoría de sustitución
  const categoryBtns = document.querySelectorAll(".category-btn")
  categoryBtns.forEach((btn) => {
    if (btn.dataset.categoryName === "Sustitución") {
      btn.classList.add("active")
    } else {
      btn.classList.remove("active")
    }
  })
}

// Modificar la función performSubstitution para registrar los eventos en la base de datos
function performSubstitution(playerOut, playerIn) {
  console.log("Realizando sustitución:", playerOut, playerIn)

  // Validar que el jugador que entra no sea un entrenador
  if (playerIn.isCoach) {
    showNotification("No se puede sustituir un jugador en pista por un entrenador", "warning")
    resetSubstitutionState()
    return
  }

  // Obtener tiempo actual del video
  const videoPlayer = document.getElementById("video-player")
  const currentTime = videoPlayer ? Math.floor(videoPlayer.currentTime) : 0
  const formattedTime = formatTime(currentTime)
  const videoId = document.querySelector('meta[name="video-id"]').content
  const username = document.querySelector('meta[name="username"]').content
  const partidoId = document.querySelector('meta[name="partido-id"]').content
  const equipoId = playerOut.equipoId

  // Mostrar notificación de carga
  showNotification("Registrando sustitución...", "info")

  // 1. Evento: Sale de pista
  const eventDataOut = {
    partido_id: partidoId,
    categoria_id: 4, // ID de la categoría "Sustitución"
    tipo_evento_id: 7, // ID para "Sale de pista"
    tiempo: currentTime,
    jugador_id: playerOut.id,
    equipo_tipo: playerOut.team,
    descripcion: `Sale de pista: ${playerOut.name}`,
    video_id: videoId,
  }

  // 2. Evento: Entra en pista
  const eventDataIn = {
    partido_id: partidoId,
    categoria_id: 4, // ID de la categoría "Sustitución"
    tipo_evento_id: 6, // ID para "Entra a pista"
    tiempo: currentTime,
    jugador_id: playerIn.id,
    equipo_tipo: playerIn.team,
    descripcion: `Entra en pista: ${playerIn.name}`,
    video_id: videoId,
  }

  // Variables para almacenar las respuestas
  let savedResponseOut = null
  let savedResponseIn = null

  Promise.all([
    // Evento de salida
    fetch(`/${username}/video/${videoId}/evento/nuevo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(eventDataOut),
    }).then((response) => response.json()),

    // Evento de entrada
    fetch(`/${username}/video/${videoId}/evento/nuevo`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(eventDataIn),
    }).then((response) => response.json()),
  ])
    .then(([responseOut, responseIn]) => {
      savedResponseOut = responseOut
      savedResponseIn = responseIn

      if (!responseOut || !responseIn) {
        throw new Error("No se recibieron respuestas válidas del servidor para los eventos")
      }

      if (responseOut?.success && responseIn?.success) {
        // Realiza la sustitución en el backend
        return fetch(`/${username}/partido/${partidoId}/sustitucion`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            equipo_id: equipoId,
            jugador_entra_id: playerIn.id,
            jugador_sale_id: playerOut.id,
          }),
        }).then((response) => response.json())
      } else {
        throw new Error("Error al registrar eventos de sustitución")
      }
    })
    .then((data) => {
      if (data.success) {
        // Añade los dos eventos como eventos separados (con formato estándar)
        // 1. Sale de pista
        eventsData.push({
          id: savedResponseOut?.evento_id || `ev-out-${Date.now()}`,
          timestamp: currentTime,
          formattedTime: formattedTime,
          categoryId: 4,
          eventTypeId: 7,
          eventTypeName: "Sale de pista",
          jugadorId: playerOut.id,
          jugadorNombre: playerOut.name,
          jugadorNumero: playerOut.number,
          equipoTipo: playerOut.team,
          equipoNombre: playerOut.teamName,
          partidoId: partidoId,
          descripcion: `Sale de pista: ${playerOut.name}`,
        })
        // 2. Entra en pista
        eventsData.push({
          id: savedResponseIn?.evento_id || `ev-in-${Date.now() + 1}`,
          timestamp: currentTime,
          formattedTime: formattedTime,
          categoryId: 4,
          eventTypeId: 6,
          eventTypeName: "Entra en pista",
          jugadorId: playerIn.id,
          jugadorNombre: playerIn.name,
          jugadorNumero: playerIn.number,
          equipoTipo: playerIn.team,
          equipoNombre: playerIn.teamName,
          partidoId: partidoId,
          descripcion: `Entra en pista: ${playerIn.name}`,
        })

        // Actualizar UI
        renderEventsList()
        // Actualizar tarjetas de jugadores
        updatePlayerCardsInRealTime(playerOut, playerIn)
        // Notificación
        showNotification(`Sustitución: ${playerIn.name} entra por ${playerOut.name}`, "success")
      } else {
        showNotification("Error al registrar sustitución: " + (data.error || "Error desconocido"), "error")
      }
    })
    .catch((error) => {
      showNotification("Error al registrar sustitución: " + error.message, "error")
    })
}

// Nueva función para actualizar las tarjetas de jugadores en tiempo real
function updatePlayerCardsInRealTime(playerOut, playerIn) {
  // Obtener los elementos DOM de los jugadores
  const playerOutElement = playerOut.element
  const playerInElement = playerIn.element

  if (!playerOutElement || !playerInElement) {
    console.error("No se encontraron los elementos DOM de los jugadores")
    return
  }

  // Obtener los contenedores
  const teamType = playerOut.team // local o visitante
  const pistaContainer = document.getElementById(`jugadores-pista-${teamType}`)
  const banquilloContainer = document.getElementById(`jugadores-${teamType}`)

  if (!pistaContainer || !banquilloContainer) {
    console.error("No se encontraron los contenedores para mover las tarjetas")
    return
  }

  try {
    // Actualizar clases CSS para el jugador que sale
    playerOutElement.classList.remove("in-pista")
    playerOutElement.classList.add("in-banquillo")

    // Actualizar clases CSS para el jugador que entra
    playerInElement.classList.remove("in-banquillo")
    playerInElement.classList.add("in-pista")

    // Mover el jugador que sale de la pista al banquillo
    banquilloContainer.appendChild(playerOutElement)

    // Mover el jugador que entra del banquillo a la pista
    pistaContainer.appendChild(playerInElement)

    console.log("Tarjetas de jugadores actualizadas en tiempo real con estilos correctos")
  } catch (error) {
    console.error("Error al actualizar tarjetas en tiempo real:", error)
  }
}

// Resetear el estado de sustitución
function resetSubstitutionState() {
  substitutionState.active = false
  substitutionState.playerOut = null
  substitutionState.waitingForPlayerIn = false

  // Resetear UI
  document.querySelectorAll(".category-btn.active").forEach((btn) => {
    btn.classList.remove("active")
  })

  // Deseleccionar jugador
  const selectedCard = document.querySelector(".player-card.selected")
  if (selectedCard) {
    selectedCard.classList.remove("selected")
  }
  selectedPlayer = null

  // Actualizar instrucciones
  updateInstructions("Selecciona un jugador para comenzar a registrar eventos o usa la categoría Global")

  // Resetear destacado de categorías
  highlightAvailableCategories()
}

// También modificar la función selectCategory para asegurarnos de que se limpie correctamente
function selectCategory(categoryId, isGlobal = false) {
  // Si estamos en modo sustitución y cambiamos de categoría, resetear el estado
  if (substitutionState.active) {
    resetSubstitutionState()
  }

  currentCategory = categoryId

  // Guardar si es un evento global
  const isGlobalEvent = isGlobal

  // Actualizar UI para mostrar la categoría seleccionada
  const categoryBtns = document.querySelectorAll(".category-btn")
  categoryBtns.forEach((btn) => {
    if (btn.dataset.categoryId == categoryId) {
      btn.classList.add("active")
    } else {
      btn.classList.remove("active")
    }
  })

  // Cargar tipos de eventos para esta categoría
  loadEventTypes(categoryId)

  // Actualizar instrucciones según si es global o no
  if (isGlobalEvent) {
    updateInstructions(`Categoría Global seleccionada - Ahora selecciona un tipo de evento`)
  } else {
    updateInstructions(
      `${selectedPlayer.isCoach ? "Entrenador" : "Jugador"} seleccionado: ${selectedPlayer.name} ${selectedPlayer.number ? `(${selectedPlayer.number})` : ""}. Ahora selecciona un tipo de evento`,
    )
  }

  if (Number(categoryId) === 1) {
    // 1 es el ID de categoría "Tiro"
    // Simular selección de tipo de evento de tiro directamente
    selectTiroEventType(37, "Tiro", "jugador") // ID, nombre, tipo_asignacion
  }
}

// Cargar tipos de eventos para una categoría
function loadEventTypes(categoryId) {
  const username = document.querySelector('meta[name="username"]').content
  const videoId = document.querySelector('meta[name="video-id"]').content

  // Obtener eventos disponibles para este video
  fetch(`/${username}/video/${videoId}/eventos-disponibles`)
    .then((response) => response.json())
    .then((data) => {
      console.log("Buscando tipos de eventos para categoría:", categoryId)
      console.log("Datos disponibles:", data)

      // Buscar la categoría seleccionada
      const categoria = data.find((cat) => cat.id == categoryId)
      if (categoria && categoria.tipos_evento) {
        console.log("Tipos de eventos encontrados:", categoria.tipos_evento)
        renderEventTypes(categoria.tipos_evento)
      } else {
        console.log("No se encontraron tipos de eventos para la categoría")
        renderEventTypes([])
      }
    })
    .catch((error) => {
      console.error("Error al cargar tipos de eventos:", error)
      renderEventTypes([])
    })
}

// Renderizar tipos de eventos
function renderEventTypes(eventTypes) {
  const container = document.getElementById("event-types-container")
  if (!container) return

  container.innerHTML = ""

  if (eventTypes.length === 0) {
    container.innerHTML = "<p>No hay tipos de eventos disponibles para esta categoría</p>"
    return
  }

  eventTypes.forEach((type) => {
    const typeBtn = document.createElement("button")
    typeBtn.className = "event-type-btn"

    // Manejar tanto eventos base como personalizados
    if (type.tipo_asignacion === "personalizado") {
      typeBtn.dataset.typeId = type.id // Ya viene como "personalizado_123"
    } else {
      typeBtn.dataset.typeId = type.id // ID numérico normal
    }

    typeBtn.dataset.assignmentType = type.tipo_asignacion || "jugador"
    typeBtn.dataset.typeName = type.nombre
    typeBtn.textContent = type.nombre

    // Verificar si es un evento de tiro (solo para eventos base)
    const isTiroEvent = type.tipo_asignacion !== "personalizado" && EVENTO_TIRO_IDS.includes(Number.parseInt(type.id))

    typeBtn.addEventListener("click", () => {
      if (isTiroEvent) {
        selectTiroEventType(type.id, type.nombre, type.tipo_asignacion || "jugador")
      } else {
        selectEventType(type.id, type.nombre, type.tipo_asignacion || "jugador")
      }
    })

    container.appendChild(typeBtn)
  })
}

function selectEventType(typeId, typeName, assignmentType) {
  currentEventType = {
    id: typeId,
    name: typeName,
    assignmentType: assignmentType,
  }
  const typeBtns = document.querySelectorAll(".event-type-btn")
  typeBtns.forEach((btn) => {
    if (btn.dataset.typeId == typeId) {
      btn.classList.add("active")
    } else {
      btn.classList.remove("active")
    }
  })
  const isGlobalEvent = document.querySelector(".category-btn.active")?.dataset.categoryName === "Global"
  registerEvent(isGlobalEvent)
}

// Nueva función para manejar la selección de eventos de tiro
function selectTiroEventType(typeId, typeName, assignmentType) {
  // Limpiar cualquier submenú anterior
  clearTiroSubmenu()

  // Actualizar el estado
  tiroSelectionState = {
    active: true,
    zona: null,
    resultado: null,
    eventTypeId: typeId,
    eventTypeName: typeName,
    assignmentType: assignmentType,
  }

  // Marcar el botón como activo
  const typeBtns = document.querySelectorAll(".event-type-btn")
  typeBtns.forEach((btn) => {
    if (btn.dataset.typeId == typeId) {
      btn.classList.add("active")
    } else {
      btn.classList.remove("active")
    }
  })

  // Mostrar el submenú de tiro
  showTiroSubmenu()
}

// Función para mostrar el submenú de tiro
function showTiroSubmenu() {
  const container = document.getElementById("event-types-container")
  if (!container) return

  // Crear el contenedor del submenú
  const submenuContainer = document.createElement("div")
  submenuContainer.className = "tiro-submenu-container"
  submenuContainer.id = "tiro-submenu"

  // Sección de zona de tiro
  const zonaSection = document.createElement("div")
  zonaSection.className = "tiro-submenu-section"

  const zonaTitle = document.createElement("span")
  zonaTitle.className = "tiro-submenu-title"
  zonaTitle.textContent = "Zona del tiro:"
  zonaSection.appendChild(zonaTitle)

  const zonaOptions = document.createElement("div")
  zonaOptions.className = "tiro-submenu-options"

  ZONAS_TIRO.forEach((zona) => {
    const btn = document.createElement("button")
    btn.className = "tiro-option-btn zona-btn"
    btn.dataset.zona = zona
    btn.textContent = zona
    btn.addEventListener("click", () => selectTiroZona(zona))
    zonaOptions.appendChild(btn)
  })

  zonaSection.appendChild(zonaOptions)
  submenuContainer.appendChild(zonaSection)

  // Sección de resultado del tiro
  const resultadoSection = document.createElement("div")
  resultadoSection.className = "tiro-submenu-section"

  const resultadoTitle = document.createElement("span")
  resultadoTitle.className = "tiro-submenu-title"
  resultadoTitle.textContent = "Resultado del tiro:"
  resultadoSection.appendChild(resultadoTitle)

  const resultadoOptions = document.createElement("div")
  resultadoOptions.className = "tiro-submenu-options"

  RESULTADOS_TIRO.forEach((resultado) => {
    const btn = document.createElement("button")
    btn.className = "tiro-option-btn resultado-btn"
    btn.dataset.resultado = resultado
    btn.textContent = resultado
    btn.addEventListener("click", () => selectTiroResultado(resultado))
    resultadoOptions.appendChild(btn)
  })

  resultadoSection.appendChild(resultadoOptions)
  submenuContainer.appendChild(resultadoSection)

  // Estado de selección
  const statusDiv = document.createElement("div")
  statusDiv.className = "tiro-selection-status"
  statusDiv.id = "tiro-selection-status"
  statusDiv.textContent = "Selecciona la zona y el resultado del tiro"
  submenuContainer.appendChild(statusDiv)

  // Botón para registrar el evento
  const registerBtn = document.createElement("button")
  registerBtn.className = "tiro-register-btn"
  registerBtn.id = "tiro-register-btn"
  registerBtn.textContent = "Registrar Tiro"
  registerBtn.disabled = true
  registerBtn.addEventListener("click", registerTiroEvent)
  submenuContainer.appendChild(registerBtn)

  // Añadir al contenedor y mostrar
  container.appendChild(submenuContainer)

  // Activar la animación
  setTimeout(() => {
    submenuContainer.classList.add("active")
  }, 10)
}

// Función para seleccionar zona de tiro
function selectTiroZona(zona) {
  tiroSelectionState.zona = zona

  // Actualizar UI
  document.querySelectorAll(".zona-btn").forEach((btn) => {
    if (btn.dataset.zona === zona) {
      btn.classList.add("selected")
    } else {
      btn.classList.remove("selected")
    }
  })

  updateTiroSelectionStatus()
}

// Función para seleccionar resultado de tiro
function selectTiroResultado(resultado) {
  tiroSelectionState.resultado = resultado

  // Actualizar UI
  document.querySelectorAll(".resultado-btn").forEach((btn) => {
    if (btn.dataset.resultado === resultado) {
      btn.classList.add("selected")
    } else {
      btn.classList.remove("selected")
    }
  })

  updateTiroSelectionStatus()
}

// Función para actualizar el estado de selección
function updateTiroSelectionStatus() {
  const statusDiv = document.getElementById("tiro-selection-status")
  const registerBtn = document.getElementById("tiro-register-btn")

  if (!statusDiv || !registerBtn) return

  const zonaSelected = tiroSelectionState.zona !== null
  const resultadoSelected = tiroSelectionState.resultado !== null

  if (zonaSelected && resultadoSelected) {
    statusDiv.textContent = `Zona: ${tiroSelectionState.zona} | Resultado: ${tiroSelectionState.resultado}`
    statusDiv.classList.add("complete")
    registerBtn.disabled = false
  } else if (zonaSelected) {
    statusDiv.textContent = `Zona seleccionada: ${tiroSelectionState.zona}. Ahora selecciona el resultado.`
    statusDiv.classList.remove("complete")
    registerBtn.disabled = true
  } else if (resultadoSelected) {
    statusDiv.textContent = `Resultado seleccionado: ${tiroSelectionState.resultado}. Ahora selecciona la zona.`
    statusDiv.classList.remove("complete")
    registerBtn.disabled = true
  } else {
    statusDiv.textContent = "Selecciona la zona y el resultado del tiro"
    statusDiv.classList.remove("complete")
    registerBtn.disabled = true
  }
}

// Función para registrar el evento de tiro
function registerTiroEvent() {
  if (!tiroSelectionState.zona || !tiroSelectionState.resultado) {
    showNotification("Debes seleccionar tanto la zona como el resultado del tiro", "warning")
    return
  }

  // Usar la función de registro existente pero con datos adicionales
  currentEventType = {
    id: tiroSelectionState.eventTypeId,
    name: tiroSelectionState.eventTypeName,
    assignmentType: tiroSelectionState.assignmentType,
    zona_tiro: tiroSelectionState.zona,
    resultado_tiro: tiroSelectionState.resultado,
  }

  const isGlobalEvent = document.querySelector(".category-btn.active")?.dataset.categoryName === "Global"
  registerEvent(isGlobalEvent)
}

// Función para limpiar el submenú de tiro
function clearTiroSubmenu() {
  const submenu = document.getElementById("tiro-submenu")
  if (submenu) {
    submenu.remove()
  }

  tiroSelectionState = {
    active: false,
    zona: null,
    resultado: null,
    eventTypeId: null,
    eventTypeName: null,
  }
}

// Registrar un evento
function registerEvent(isGlobalEvent = false) {
  const videoPlayer = document.getElementById("video-player")
  const currentTime = videoPlayer ? Math.floor(videoPlayer.currentTime) : 0
  const formattedTime = formatTime(currentTime)
  const partidoId = document.querySelector('meta[name="partido-id"]').content
  let event = {
    id: Date.now(),
    timestamp: currentTime,
    formattedTime: formattedTime,
    categoryId: currentCategory,
    eventTypeId: currentEventType.id,
    eventTypeName: currentEventType.name,
    partidoId: partidoId,
    isGlobal: isGlobalEvent,
  }

  // Añadir información de tiro si existe
  if (currentEventType && currentEventType.zona_tiro && currentEventType.resultado_tiro) {
    event.zona_tiro = currentEventType.zona_tiro
    event.resultado_tiro = currentEventType.resultado_tiro
  }

  if (!isGlobalEvent) {
    if (!selectedPlayer || !selectedPlayer.id) {
      showNotification("Error: No hay un jugador seleccionado válido", "error")
      return
    }
    event = {
      ...event,
      jugadorId: selectedPlayer.id,
      jugadorNombre: selectedPlayer.name,
      jugadorNumero: selectedPlayer.number,
      equipoTipo: selectedPlayer.team,
      equipoNombre: selectedPlayer.teamName,
      isCoach: selectedPlayer.isCoach,
    }
    if (Number.parseInt(currentEventType.id) === EVENTO_TIEMPO_MUERTO_ID) {
      if (window.controlFasesPartido) {
        const validacion = window.controlFasesPartido.validarTiempoMuerto(event)
        if (!validacion.valido) {
          showNotification(validacion.mensaje, "warning")
          return
        }
      }
    }
  } else {
    if (Number.parseInt(currentEventType.id) === EVENTO_INICIO_PRORROGA_ID) {
      if (window.controlFasesPartido) {
        const validacion = window.controlFasesPartido.validarProrroga()
        if (!validacion.valido) {
          showNotification(validacion.mensaje, "warning")
          return
        }
      }
    }
  }
  eventsData.push(event)
  saveEventToServer(event, isGlobalEvent)
    .then((data) => {
      if (data && data.evento_estadistico_id) {
        const index = eventsData.findIndex((e) => e.id === event.id)
        if (index !== -1) {
          eventsData[index].eventoEstadisticoId = data.evento_estadistico_id
        }
      }
      renderEventsList()
      if (isGlobalEvent) {
        showNotification(`Evento global registrado: ${event.eventTypeName} - ${formattedTime}`)
      } else {
        showNotification(`Evento registrado: ${event.eventTypeName} - ${selectedPlayer.name} - ${formattedTime}`)
      }
      resetEventSelection(isGlobalEvent)
      if (window.controlFasesPartido && typeof window.controlFasesPartido.analizarEventosExternos === "function") {
        window.controlFasesPartido.analizarEventosExternos(eventsData)
      }
    })
    .catch((error) => {
      console.error("Error en el proceso de registro de evento:", error)
    })
}

function saveEventToServer(event, isGlobalEvent = false) {
  const username = document.querySelector('meta[name="username"]').content
  const videoId = document.querySelector('meta[name="video-id"]').content

  // Preparar datos para enviar
  let eventData = {
    partido_id: event.partidoId,
    categoria_id: event.categoryId,
    tiempo: event.timestamp,
  }

  // Verificar si es un evento personalizado
  const isPersonalizado =
    event.eventTypeId && typeof event.eventTypeId === "string" && event.eventTypeId.startsWith("personalizado_")

  if (isPersonalizado) {
    // Es un evento personalizado
    const eventoPersonalizadoId = event.eventTypeId.replace("personalizado_", "")
    eventData.evento_personalizado_id = Number.parseInt(eventoPersonalizadoId)
    console.log("Registrando evento personalizado con ID:", eventoPersonalizadoId)
  } else {
    // Es un evento base
    eventData.tipo_evento_id = Number.parseInt(event.eventTypeId)
    console.log("Registrando evento base con ID:", event.eventTypeId)

    // Añadir datos específicos de tiro si existen
    if (currentEventType && currentEventType.zona_tiro && currentEventType.resultado_tiro) {
      eventData.zona_tiro = currentEventType.zona_tiro
      eventData.resultado_tiro = currentEventType.resultado_tiro
    }
  }

  // Si no es un evento global, añadir información del jugador y equipo
  if (!isGlobalEvent) {
    if (!event.jugadorId) {
      console.error("Error: Intentando registrar evento con jugador_id undefined", event)
      showNotification("Error: ID de jugador no válido", "error")
      return Promise.reject(new Error("ID de jugador no válido"))
    }

    eventData = {
      ...eventData,
      jugador_id: event.jugadorId,
      equipo_tipo: event.equipoTipo,
    }
  }

  console.log("Enviando datos de evento al servidor:", eventData)

  // Enviar al servidor
  return fetch(`/${username}/video/${videoId}/evento/nuevo`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(eventData),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Error HTTP: ${response.status}`)
      }
      return response.json()
    })
    .then((data) => {
      if (data.success) {
        // Actualizar ID del evento con el ID real del servidor
        const index = eventsData.findIndex((e) => e.id === event.id)
        if (index !== -1) {
          eventsData[index].id = data.evento_id
          console.log("Evento guardado con éxito, ID:", data.evento_id)

          if (data.evento_estadistico_id) {
            eventsData[index].eventoEstadisticoId = data.evento_estadistico_id
            console.log("Evento estadístico asociado con ID:", data.evento_estadistico_id)
          }

          // Disparar evento personalizado para actualizar estadísticas
          document.dispatchEvent(
            new CustomEvent("eventoRegistrado", {
              detail: {
                ...event,
                isPersonalizado: isPersonalizado,
              },
            }),
          )
        }

        if (data.warning) {
          showNotification(data.warning, "warning")
        } else {
          showNotification("Evento guardado correctamente", "success")
        }

        return data
      } else {
        console.error("Error al guardar evento:", data.error)
        showNotification("Error al guardar evento: " + (data.error || "Error desconocido"), "error")
        throw new Error(data.error || "Error desconocido")
      }
    })
    .catch((error) => {
      console.error("Error al guardar evento:", error)
      showNotification("Error al guardar evento: " + error.message, "error")
      throw error
    })
}

function findPlayerCardById(playerId) {
  const playerCards = document.querySelectorAll(".player-card")
  for (const card of playerCards) {
    const cardPlayerId = card.dataset.playerId || card.getAttribute("data-jugador-id")
    if (cardPlayerId == playerId) {
      return card
    }
  }
  return null
}

function loadSavedEvents() {
  const username = document.querySelector('meta[name="username"]').content
  const videoId = document.querySelector('meta[name="video-id"]').content
  fetch(`/${username}/video/${videoId}/eventos`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Error HTTP: ${response.status}`)
      }
      return response.json()
    })
    .then((data) => {
      if (data.eventos && Array.isArray(data.eventos)) {
        eventsData.splice(0, eventsData.length)
        // En la función loadSavedEvents, actualizar cómo se procesan los eventos cargados
        data.eventos.forEach((evento) => {
          const isGlobalEvent = !evento.jugador_id && !evento.equipo

          // Determinar el ID del tipo de evento (base o personalizado)
          let eventTypeId = evento.tipo_evento_id
          let eventTypeName = "Desconocido"

          if (evento.evento_personalizado_id) {
            eventTypeId = `personalizado_${evento.evento_personalizado_id}`
            eventTypeName = evento.evento_personalizado?.nombre || "Evento Personalizado"
          } else if (evento.tipo_evento) {
            eventTypeName = evento.tipo_evento.nombre
          }

          const eventoObj = {
            id: evento.id,
            timestamp: evento.tiempo_seg,
            formattedTime: formatTime(evento.tiempo_seg),
            categoryId: evento.tipo_evento
              ? evento.tipo_evento.categoria_id
              : evento.evento_personalizado
                ? evento.evento_personalizado.categoria_id
                : null,
            eventTypeId: eventTypeId,
            eventTypeName: eventTypeName,
            jugadorId: evento.jugador_id || (evento.jugador ? evento.jugador.id : undefined),
            jugadorNombre: evento.jugador ? `${evento.jugador.nombre} ${evento.jugador.apellido}` : "Desconocido",
            jugadorNumero: evento.jugador && evento.jugador.dorsal ? evento.jugador.dorsal.toString() : "",
            equipoTipo: evento.equipo
              ? evento.equipo.id === Number.parseInt(document.querySelector('meta[name="equipo-local-id"]').content)
                ? "local"
                : "visitante"
              : null,
            equipoNombre: evento.equipo ? evento.equipo.nombre : "Desconocido",
            partidoId: evento.partido_id,
            descripcion: evento.descripcion,
            isGlobal: isGlobalEvent,
            isCoach: evento.jugador ? evento.jugador.rol === "entrenador" : false,
            eventoEstadisticoId: evento.evento_estadistico_id,
            // Añadir campos de tiro si existen
            zona_tiro: evento.zona_tiro,
            resultado_tiro: evento.resultado_tiro,
            // Añadir información de evento personalizado
            isPersonalizado: !!evento.evento_personalizado_id,
            estadisticaTipo: evento.evento_personalizado?.estadistica_tipo || null,
          }
          eventsData.push(eventoObj)
        })

        renderEventsList()

        // Añadir un pequeño retraso para asegurarse de que el video esté listo
        setTimeout(() => {
          positionVideoAtLastEvent()
        }, 500)

        if (window.controlFasesPartido && typeof window.controlFasesPartido.analizarEventosExternos === "function") {
          window.controlFasesPartido.analizarEventosExternos(eventsData)
          const videoPlayer = document.getElementById("video-player")
          if (
            videoPlayer &&
            videoPlayer.readyState > 0 &&
            typeof window.controlFasesPartido.determinarFasePorTiempoVideo === "function"
          ) {
            window.controlFasesPartido.determinarFasePorTiempoVideo(videoPlayer.currentTime)
          }
        }
      } else {
        eventsData.splice(0, eventsData.length)
        renderEventsList()
        if (window.controlFasesPartido && typeof window.controlFasesPartido.analizarEventosExternos === "function") {
          window.controlFasesPartido.analizarEventosExternos([])
        }
      }
    })
    .catch((error) => {
      showNotification("Error al cargar eventos: " + error.message, "error")
    })
}

// Renderizar lista de eventos - Modificada para incluir el nombre del equipo
function renderEventsList() {
  const container = document.getElementById("events-list-container")
  if (!container) return

  container.innerHTML = ""

  // Añadir botón de deshacer si hay eventos
  if (eventsData.length > 0) {
    const undoButtonContainer = document.createElement("div")
    undoButtonContainer.className = "undo-button-container"
    undoButtonContainer.style.textAlign = "right"
    undoButtonContainer.style.marginBottom = "10px"

    const undoButton = document.createElement("button")
    undoButton.className = "undo-button"
    undoButton.innerHTML = '<i class="fas fa-undo"></i> Deshacer último evento'
    undoButton.style.padding = "5px 10px"
    undoButton.style.backgroundColor = "#f8f9fa"
    undoButton.style.border = "1px solid #dee2e6"
    undoButton.style.borderRadius = "4px"
    undoButton.style.cursor = "pointer"
    undoButton.style.fontSize = "0.85rem"
    undoButton.style.color = "#495057"

    undoButton.addEventListener("click", undoLastEvent)

    // Añadir efecto hover
    undoButton.addEventListener("mouseover", function () {
      this.style.backgroundColor = "#e2e6ea"
    })
    undoButton.addEventListener("mouseout", function () {
      this.style.backgroundColor = "#f8f9fa"
    })

    undoButtonContainer.appendChild(undoButton)
    container.appendChild(undoButtonContainer)
  }

  if (eventsData.length === 0) {
    container.innerHTML = "<p>No hay eventos registrados</p>"
    return
  }

  // Ordenar eventos por tiempo (descendente - más recientes primero)
  const sortedEvents = [...eventsData].sort((a, b) => b.timestamp - a.timestamp)

  sortedEvents.forEach((event) => {
    const eventItem = document.createElement("div")
    eventItem.className = "event-item"
    eventItem.dataset.eventId = event.id

    // Añadir la clase del equipo al elemento del evento
    if (event.equipoTipo) {
      eventItem.classList.add(event.equipoTipo) // Añadir clase 'local' o 'visitante'
    }

    // Tiempo
    const timeSpan = document.createElement("span")
    timeSpan.className = "event-time"
    timeSpan.textContent = event.formattedTime
    eventItem.appendChild(timeSpan)

    // Descripción
    const descSpan = document.createElement("span")
    descSpan.className = "event-description"

    // Si es una sustitución, mostrar formato especial
    if (event.isSubstitution) {
      descSpan.textContent = `Sustitución: ${event.playerIn.name} ${event.playerIn.number ? `(${event.playerIn.number})` : ""} entra por ${event.playerOut.name} ${event.playerOut.number ? `(${event.playerOut.number})` : ""} - ${event.equipoNombre}`
    } else if (event.isGlobal) {
      // Formato para eventos globales
      descSpan.textContent = `${event.eventTypeName} - Evento Global`
    } else if (event.isCoach) {
      // Formato para eventos de entrenador
      descSpan.textContent = `${event.eventTypeName} - Entrenador: ${event.jugadorNombre} - ${event.equipoNombre}`
    } else {
      // Formato para eventos normales, incluyendo el nombre del equipo
      let descripcionCompleta = ""

      // Si es un evento de tiro con detalles, crear descripción especial
      if (event.zona_tiro && event.resultado_tiro) {
        // Crear descripción completa para eventos de tiro
        const resultado = event.resultado_tiro.toLowerCase()
        const zona = event.zona_tiro

        if (resultado === "gol") {
          descripcionCompleta = `Gol desde ${zona} - ${event.jugadorNombre} ${event.jugadorNumero ? `(${event.jugadorNumero})` : ""} - ${event.equipoNombre}`
        } else if (resultado === "parado") {
          descripcionCompleta = `Tiro parado desde ${zona} - ${event.jugadorNombre} ${event.jugadorNumero ? `(${event.jugadorNumero})` : ""} - ${event.equipoNombre}`
        } else if (resultado === "fallado") {
          descripcionCompleta = `Tiro fallado desde ${zona} - ${event.jugadorNombre} ${event.jugadorNumero ? `(${event.jugadorNumero})` : ""} - ${event.equipoNombre}`
        } else if (resultado === "palo") {
          descripcionCompleta = `Tiro al palo desde ${zona} - ${event.jugadorNombre} ${event.jugadorNumero ? `(${event.jugadorNumero})` : ""} - ${event.equipoNombre}`
        } else if (resultado === "bloqueado") {
          descripcionCompleta = `Tiro bloqueado desde ${zona} - ${event.jugadorNombre} ${event.jugadorNumero ? `(${event.jugadorNumero})` : ""} - ${event.equipoNombre}`
        } else {
          // Fallback para otros resultados
          descripcionCompleta = `Tiro ${resultado} desde ${zona} - ${event.jugadorNombre} ${event.jugadorNumero ? `(${event.jugadorNumero})` : ""} - ${event.equipoNombre}`
        }
      } else if (
        event.eventTypeName &&
        event.eventTypeName.toLowerCase().includes("tiro") &&
        event.eventTypeName.toLowerCase().includes("parado")
      ) {
        // Caso especial para tiros parados antiguos (sin zona_tiro)
        descripcionCompleta = `${event.eventTypeName} - ${event.jugadorNombre} ${event.jugadorNumero ? `(${event.jugadorNumero})` : ""} - ${event.equipoNombre}`
      } else if (event.eventTypeName && event.eventTypeName.toLowerCase().includes("gol")) {
        // Caso especial para goles antiguos (sin zona_tiro)
        descripcionCompleta = `${event.eventTypeName} - ${event.jugadorNombre} ${event.jugadorNumero ? `(${event.jugadorNumero})` : ""} - ${event.equipoNombre}`
      } else {
        // Formato normal para eventos que no son de tiro
        descripcionCompleta = `${event.eventTypeName} - ${event.jugadorNombre} ${event.jugadorNumero ? `(${event.jugadorNumero})` : ""} - ${event.equipoNombre}`
      }

      descSpan.textContent = descripcionCompleta
    }

    eventItem.appendChild(descSpan)

    // Acciones
    const actionsDiv = document.createElement("div")
    actionsDiv.className = "event-actions"

    // Botón para ir al tiempo del evento
    const goToTimeBtn = document.createElement("button")
    goToTimeBtn.className = "event-action-btn"
    goToTimeBtn.title = "Ir a este momento"
    goToTimeBtn.innerHTML = '<i class="fas fa-play-circle"></i>'
    goToTimeBtn.addEventListener("click", () => {
      const videoPlayer = document.getElementById("video-player")
      if (videoPlayer) {
        videoPlayer.currentTime = event.timestamp
      }
    })
    actionsDiv.appendChild(goToTimeBtn)

    // Botón para eliminar evento
    const deleteBtn = document.createElement("button")
    deleteBtn.className = "event-action-btn delete"
    deleteBtn.title = "Eliminar evento"
    deleteBtn.innerHTML = '<i class="fas fa-trash-alt"></i>'
    deleteBtn.addEventListener("click", (e) => {
      e.preventDefault()
      e.stopPropagation()
      showConfirmDialog(
        "Eliminar evento",
        `¿Estás seguro de que deseas eliminar este evento: ${event.isSubstitution ? "Sustitución" : event.eventTypeName} en ${event.formattedTime}?`,
        () => deleteEvent(event.id, event.isSubstitution, event),
      )
    })
    actionsDiv.appendChild(deleteBtn)

    eventItem.appendChild(actionsDiv)

    container.appendChild(eventItem)
  })
}

// Nueva función para deshacer el último evento
function undoLastEvent() {
  if (eventsData.length === 0) {
    showNotification("No hay eventos para deshacer", "warning")
    return
  }

  // Ordenar eventos por tiempo para obtener el más reciente
  const sortedEvents = [...eventsData].sort((a, b) => b.timestamp - a.timestamp)
  const lastEvent = sortedEvents[0]

  // Mostrar confirmación
  showConfirmDialog(
    "Deshacer último evento",
    `¿Estás seguro de que deseas deshacer el último evento: ${lastEvent.isSubstitution ? "Sustitución" : lastEvent.eventTypeName} en ${lastEvent.formattedTime}?`,
    () => {
      // Si es una sustitución, necesitamos manejarla de forma especial
      if (lastEvent.isSubstitution) {
        deleteEvent(lastEvent.id, true, lastEvent)
      } else {
        deleteEvent(lastEvent.id, false, lastEvent)
      }
    },
  )
}

// Mostrar diálogo de confirmación
function showConfirmDialog(title, message, confirmCallback) {
  console.log("Mostrando diálogo de confirmación:", title, message)

  // Eliminar diálogo anterior si existe
  const existingDialog = document.getElementById("confirm-dialog")
  if (existingDialog) {
    existingDialog.remove()
  }

  const existingBackdrop = document.getElementById("confirm-dialog-backdrop")
  if (existingBackdrop) {
    existingBackdrop.remove()
  }

  // Crear elementos del diálogo
  const backdrop = document.createElement("div")
  backdrop.className = "confirm-dialog-backdrop"
  backdrop.id = "confirm-dialog-backdrop"
  backdrop.style.position = "fixed"
  backdrop.style.top = "0"
  backdrop.style.left = "0"
  backdrop.style.width = "100%"
  backdrop.style.height = "100%"
  backdrop.style.backgroundColor = "rgba(0, 0, 0, 0.5)"
  backdrop.style.zIndex = "9998"

  const dialog = document.createElement("div")
  dialog.className = "confirm-dialog"
  dialog.id = "confirm-dialog"
  dialog.style.position = "fixed"
  dialog.style.top = "50%"
  dialog.style.left = "50%"
  dialog.style.transform = "translate(-50%, -50%)"
  dialog.style.backgroundColor = "white"
  dialog.style.padding = "20px"
  dialog.style.borderRadius = "5px"
  dialog.style.boxShadow = "0 0 10px rgba(0, 0, 0, 0.3)"
  dialog.style.zIndex = "9999"
  dialog.style.minWidth = "300px"

  const dialogTitle = document.createElement("div")
  dialogTitle.className = "confirm-dialog-title"
  dialogTitle.textContent = title
  dialogTitle.style.fontWeight = "bold"
  dialogTitle.style.fontSize = "18px"
  dialogTitle.style.marginBottom = "10px"

  const dialogMessage = document.createElement("div")
  dialogMessage.className = "confirm-dialog-message"
  dialogMessage.textContent = message
  dialogMessage.style.marginBottom = "20px"

  const buttonsContainer = document.createElement("div")
  buttonsContainer.className = "confirm-dialog-buttons"
  buttonsContainer.style.display = "flex"
  buttonsContainer.style.justifyContent = "flex-end"
  buttonsContainer.style.gap = "10px"

  const cancelButton = document.createElement("button")
  cancelButton.className = "confirm-dialog-button cancel"
  cancelButton.textContent = "Cancelar"
  cancelButton.style.padding = "8px 16px"
  cancelButton.style.border = "none"
  cancelButton.style.borderRadius = "4px"
  cancelButton.style.backgroundColor = "#6c757d"
  cancelButton.style.color = "white"
  cancelButton.style.cursor = "pointer"
  cancelButton.addEventListener("click", closeConfirmDialog)

  const confirmButton = document.createElement("button")
  confirmButton.className = "confirm-dialog-button confirm"
  confirmButton.textContent = title.startsWith("Deshacer") ? "Deshacer" : "Eliminar"
  confirmButton.style.padding = "8px 16px"
  confirmButton.style.border = "none"
  confirmButton.style.borderRadius = "4px"
  confirmButton.style.backgroundColor = "#dc3545"
  confirmButton.style.color = "white"
  confirmButton.style.cursor = "pointer"
  confirmButton.addEventListener("click", () => {
    confirmCallback()
    closeConfirmDialog()
  })

  // Ensamblar el diálogo
  buttonsContainer.appendChild(cancelButton)
  buttonsContainer.appendChild(confirmButton)

  dialog.appendChild(dialogTitle)
  dialog.appendChild(dialogMessage)
  dialog.appendChild(buttonsContainer)

  // Añadir al DOM
  document.body.appendChild(backdrop)
  document.body.appendChild(dialog)

  // Añadir evento para cerrar con Escape
  const escHandler = (e) => {
    if (e.key === "Escape") {
      closeConfirmDialog()
      document.removeEventListener("keydown", escHandler)
    }
  }
  document.addEventListener("keydown", escHandler)
}

// Cerrar diálogo de confirmación
function closeConfirmDialog() {
  const dialog = document.getElementById("confirm-dialog")
  const backdrop = document.getElementById("confirm-dialog-backdrop")

  if (dialog) dialog.remove()
  if (backdrop) backdrop.remove()
}

function deleteEvent(eventId, isSubstitution, eventData = null) {
  const username = document.querySelector('meta[name="username"]').content
  showNotification("Eliminando evento...", "info")
  if (isSubstitution) {
    const substitutionEvent = eventsData.find((event) => event.id === eventId)
    if (!substitutionEvent || !substitutionEvent.eventOutId || !substitutionEvent.eventInId) {
      showNotification("Error al eliminar la sustitución", "error")
      return
    }
    Promise.all([
      fetch(`/${username}/evento/${substitutionEvent.eventOutId}/eliminar`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      }).then((response) => response.json()),
      fetch(`/${username}/evento/${substitutionEvent.eventInId}/eliminar`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      }).then((response) => response.json()),
    ])
      .then(([responseOut, responseIn]) => {
        if (responseOut.success && responseIn.success) {
          eventsData = eventsData.filter((event) => event.id !== eventId)
          renderEventsList()
          showNotification("Sustitución eliminada correctamente", "success")
          if (typeof window.cargarJugadoresConvocados === "function") {
            window.cargarJugadoresConvocados()
          }
        } else {
          showNotification("Error al eliminar la sustitución", "error")
        }
      })
      .catch((error) => {
        showNotification("Error al eliminar la sustitución: " + error.message, "error")
      })
    return
  }

  fetch(`/${username}/evento/${eventId}/eliminar`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Error HTTP: ${response.status}`)
      }
      return response.json()
    })
    .then((data) => {
      if (data.success) {
        eventsData = eventsData.filter((event) => event.id !== eventId)
        renderEventsList()
        showNotification("Evento eliminado correctamente", "success")
        document.dispatchEvent(
          new CustomEvent("eventoEliminado", {
            detail: eventData,
          }),
        )
        // ELIMINADO: procesarSanciones2Min()
        if (window.controlFasesPartido && typeof window.controlFasesPartido.analizarEventosExternos === "function") {
          window.controlFasesPartido.analizarEventosExternos(eventsData)
        }
      } else {
        showNotification("Error al eliminar evento: " + (data.error || "Error desconocido"), "error")
      }
    })
    .catch((error) => {
      showNotification("Error al eliminar evento: " + error.message, "error")
    })
}

function resetEventSelection(isGlobalEvent = false) {
  currentCategory = null
  currentEventType = null
  document.querySelectorAll(".category-btn.active").forEach((btn) => {
    btn.classList.remove("active")
  })
  document.querySelectorAll(".event-type-btn.active").forEach((btn) => {
    btn.classList.remove("active")
  })
  const eventTypesContainer = document.getElementById("event-types-container")
  if (eventTypesContainer) {
    eventTypesContainer.innerHTML = ""
    // Limpiar submenú de tiro si está activo
    if (tiroSelectionState.active) {
      clearTiroSubmenu()
    }
  }
  if (isGlobalEvent) {
    isGlobalEventActive = false
    updateInstructions("Selecciona un jugador para comenzar a registrar eventos o usa la categoría Global")
  } else if (selectedPlayer) {
    updateInstructionsAndCategories()
  } else {
    updateInstructions("Selecciona un jugador para comenzar a registrar eventos o usa la categoría Global")
  }
}

function showNotification(message, type = "success") {
  const notification = document.getElementById("event-notification")
  if (!notification) {
    return
  }
  if (type === "success") {
    notification.style.backgroundColor = "#28a745"
  } else if (type === "warning") {
    notification.style.backgroundColor = "#ffc107"
    notification.style.color = "#212529"
  } else if (type === "error") {
    notification.style.backgroundColor = "#dc3545"
  } else if (type === "info") {
    notification.style.backgroundColor = "#17a2b8"
  }
  notification.textContent = message
  notification.style.display = "block"
  notification.style.opacity = "1"
  notification.style.visibility = "visible"
  notification.style.zIndex = "9999"
  notification.style.position = "fixed"
  notification.style.bottom = "20px"
  notification.style.right = "20px"
  notification.style.padding = "10px 20px"
  notification.style.borderRadius = "4px"
  notification.style.color = "white"
  notification.style.boxShadow = "0 4px 8px rgba(0,0,0,0.2)"
  notification.style.transition = "opacity 0.3s ease"
  notification.classList.add("show")
  setTimeout(() => {
    notification.classList.remove("show")
    notification.style.opacity = "0"
    setTimeout(() => {
      notification.style.display = "none"
    }, 300)
  }, 3000)
}

window.showNotification = showNotification

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, "0")}`
}

function deselectPlayer() {
  if (selectedPlayer) {
    const selectedCard = document.querySelector(".player-card.selected")
    if (selectedCard) {
      selectedCard.classList.remove("selected")
    }
    selectedPlayer = null
    if (substitutionState.active) {
      resetSubstitutionState()
    }
    updateInstructions("Selecciona un jugador para comenzar a registrar eventos o usa la categoría Global")
    highlightAvailableCategories()
  }
}

function cargarJugadoresConvocados() {
  if (typeof window.cargarJugadoresConvocados === "function") {
    window.cargarJugadoresConvocados()
  } else {
    // nada
  }
}
function positionVideoAtLastEvent(specificTime = null) {
  console.log("Intentando posicionar el video en el último evento...")

  // Función auxiliar para formatear el tiempo en formato mm:ss
  function formatTime(timeInSeconds) {
    const minutes = Math.floor(timeInSeconds / 60)
    const seconds = Math.floor(timeInSeconds % 60)
    return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`
  }

  // Verificar si hay un parámetro de tiempo en la URL
  const urlParams = new URLSearchParams(window.location.search)
  const timeParam = urlParams.get("t")

  // Si hay un parámetro de tiempo en la URL, usarlo con prioridad
  if (timeParam !== null) {
    const timeFromUrl = Number.parseInt(timeParam, 10)
    console.log(`Parámetro de tiempo detectado en la URL: ${timeFromUrl}s`)
    specificTime = timeFromUrl
  }

  // Obtener el reproductor de video
  const videoPlayer = document.getElementById("video-player")
  if (!videoPlayer) {
    console.error("No se encontró el reproductor de video")
    return
  }

  // Si se proporcionó un tiempo específico (ya sea por parámetro o URL), usarlo
  if (specificTime !== null) {
    console.log(`Posicionando video en tiempo específico: ${formatTime(specificTime)}`)

    // Función para establecer el tiempo del video
    const setVideoTime = () => {
      // Asegurarse de que el tiempo no exceda la duración del video
      const tiempoSeguro = Math.min(specificTime, videoPlayer.duration || 0)
      videoPlayer.currentTime = tiempoSeguro
      console.log(`Video posicionado en tiempo: ${formatTime(tiempoSeguro)}`)

      // Desplazar el video a la vista
      videoPlayer.scrollIntoView({ behavior: "smooth", block: "center" })

      // Mostrar notificación
      showNotification(`Video posicionado en el tiempo ${formatTime(tiempoSeguro)}`, "info")
    }

    // Comprobar si el video ya está listo
    if (videoPlayer.readyState >= 2) {
      // HAVE_CURRENT_DATA o superior
      setVideoTime()
    } else {
      // Esperar a que el video esté listo
      const canPlayHandler = () => {
        setVideoTime()
        videoPlayer.removeEventListener("canplay", canPlayHandler)
      }
      videoPlayer.addEventListener("canplay", canPlayHandler)
    }

    return
  }

  // Si no hay tiempo específico, continuar con el comportamiento original
  // Verificar si hay eventos
  if (eventsData.length === 0) {
    console.log("No hay eventos registrados, el video comenzará desde el principio")
    return
  }

  // Encontrar el evento con el mayor tiempo_seg
  const ultimoTiempo = Math.max(...eventsData.map((e) => e.timestamp || 0))
  console.log(`Último evento encontrado en tiempo: ${formatTime(ultimoTiempo)}`)

  // Función para establecer el tiempo del video
  const setVideoTime = () => {
    try {
      // Asegurarse de que el tiempo no exceda la duración del video
      const tiempoSeguro = Math.min(ultimoTiempo, videoPlayer.duration || 0)
      videoPlayer.currentTime = tiempoSeguro
      console.log(`Video posicionado en tiempo: ${formatTime(tiempoSeguro)}`)

      // Desplazar el video a la vista
      videoPlayer.scrollIntoView({ behavior: "smooth", block: "center" })

      // Mostrar notificación
      showNotification(`Video posicionado en el último evento (${formatTime(tiempoSeguro)})`, "info")
    } catch (error) {
      console.error("Error al posicionar el video:", error)
    }
  }

  // Comprobar si el video ya está listo
  if (videoPlayer.readyState >= 2) {
    // HAVE_CURRENT_DATA o superior
    setVideoTime()
  } else {
    console.log("Video no está listo, esperando evento canplay...")
    // Esperar a que el video esté listo
    const canPlayHandler = () => {
      setVideoTime()
      videoPlayer.removeEventListener("canplay", canPlayHandler)
    }
    videoPlayer.addEventListener("canplay", canPlayHandler)

    // Como respaldo, intentar después de un tiempo
    setTimeout(() => {
      if (videoPlayer.readyState >= 2) {
        console.log("Intentando posicionar el video después del timeout...")
        setVideoTime()
      }
    }, 2000)
  }
}


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
