// Script para añadir clases específicas a cada página basadas en la URL
document.addEventListener("DOMContentLoaded", () => {
  const path = window.location.pathname
  const body = document.body

  // Eliminar clases de página anteriores
  const pageClasses = Array.from(body.classList).filter((cls) => cls.startsWith("page-"))
  pageClasses.forEach((cls) => body.classList.remove(cls))

  // Añadir clase específica basada en la URL
  if (path.includes("/video/")) {
    body.classList.add("video-page")
  } else if (path.includes("/equipo/")) {
    body.classList.add("equipo-page")
  } else if (path.includes("/liga/")) {
    body.classList.add("liga-page")
  } else if (path.includes("/partido/")) {
    body.classList.add("partido-page")
  } else if (path.includes("/temporada/")) {
    body.classList.add("temporada-page")
  } else if (path.includes("/dashboard/")) {
    body.classList.add("dashboard-page")
  } else if (path === "/" || path === "/index" || path === "/index.html") {
    body.classList.add("home-page")
  } else if (path.includes("/login") || path.includes("/register")) {
    body.classList.add("auth-page")
  }

  // Añadir clase para anotación de eventos
  if (path.includes("/anotar-eventos")) {
    body.classList.add("event-annotation")
  }
})
