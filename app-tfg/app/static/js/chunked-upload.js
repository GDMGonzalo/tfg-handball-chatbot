/**
 * Sistema único de subida de videos por fragmentos
 * Todos los videos se suben exclusivamente usando este método
 * No hay límite de tamaño total para los archivos
 */
class ChunkedUploader {
  constructor(options) {
    // Configuración del sistema de fragmentos (único método de subida)
    this.options = {
      chunkSize: 5 * 1024 * 1024, // 5MB por fragmento
      simultaneousUploads: 1, // Número de subidas simultáneas
      endpoint: null, // URL para subir los fragmentos
      file: null, // Archivo a subir
      onProgress: null, // Callback de progreso
      onComplete: null, // Callback de finalización
      onError: null, // Callback de error
      metadata: {}, // Metadatos adicionales
      ...options,
    }

    this.chunks = [] // Lista de fragmentos
    this.uploadedChunks = 0 // Contador de fragmentos subidos
    this.activeUploads = 0 // Contador de subidas activas
    this.totalChunks = 0 // Total de fragmentos
    this.uploadId = null // ID único para esta subida
    this.aborted = false // Indicador de cancelación
  }

  // Iniciar la subida
  start() {
    if (!this.options.file || !this.options.endpoint) {
      this._handleError("Se requiere un archivo y un endpoint")
      return
    }

    // Generar ID único para esta subida
    this.uploadId = this._generateUploadId()

    // Dividir el archivo en fragmentos
    this._prepareChunks()

    // Mostrar información de la subida
    console.log(`Iniciando subida de ${this.options.file.name} (${this._formatFileSize(this.options.file.size)})`)
    console.log(
      `Total de fragmentos: ${this.totalChunks}, Tamaño de fragmento: ${this._formatFileSize(this.options.chunkSize)}`,
    )

    // Iniciar la subida de fragmentos
    this._uploadNextChunks()
  }

  // Cancelar la subida
  abort() {
    this.aborted = true
    console.log("Subida cancelada por el usuario")
  }

  // Dividir el archivo en fragmentos
  _prepareChunks() {
    const file = this.options.file
    const chunkSize = this.options.chunkSize
    const totalChunks = Math.ceil(file.size / chunkSize)

    this.totalChunks = totalChunks
    this.chunks = []

    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize
      const end = Math.min(file.size, start + chunkSize)

      this.chunks.push({
        index: i,
        start: start,
        end: end,
        blob: file.slice(start, end),
        status: "pending", // pending, uploading, done, error
      })
    }
  }

  // Subir los siguientes fragmentos disponibles
  _uploadNextChunks() {
    if (this.aborted) return

    // Buscar fragmentos pendientes
    const pendingChunks = this.chunks.filter((chunk) => chunk.status === "pending")

    if (pendingChunks.length === 0 && this.activeUploads === 0) {
      // Todos los fragmentos han sido subidos
      this._finalizeUpload()
      return
    }

    // Subir fragmentos hasta alcanzar el límite de subidas simultáneas
    while (this.activeUploads < this.options.simultaneousUploads && pendingChunks.length > 0) {
      const chunk = pendingChunks.shift()
      chunk.status = "uploading"
      this.activeUploads++

      this._uploadChunk(chunk)
    }
  }

  // Subir un fragmento específico
  _uploadChunk(chunk) {
    if (this.aborted) {
      this.activeUploads--
      return
    }

    const formData = new FormData()
    formData.append("file", chunk.blob, this.options.file.name)
    formData.append("upload_id", this.uploadId)
    formData.append("chunk_index", chunk.index)
    formData.append("total_chunks", this.totalChunks)
    formData.append("filename", this.options.file.name)

    // Añadir metadatos adicionales
    Object.keys(this.options.metadata).forEach((key) => {
      formData.append(key, this.options.metadata[key])
    })

    fetch(this.options.endpoint, {
      method: "POST",
      body: formData,
      credentials: "same-origin",
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Error HTTP: ${response.status}`)
        }
        return response.json()
      })
      .then((data) => {
        if (this.aborted) return

        chunk.status = "done"
        this.uploadedChunks++
        this.activeUploads--

        // Calcular progreso
        const progress = (this.uploadedChunks / this.totalChunks) * 100

        // Llamar al callback de progreso
        if (this.options.onProgress) {
          this.options.onProgress({
            totalChunks: this.totalChunks,
            uploadedChunks: this.uploadedChunks,
            progress: progress,
            uploadId: this.uploadId,
          })
        }

        // Continuar con los siguientes fragmentos
        this._uploadNextChunks()
      })
      .catch((error) => {
        if (this.aborted) return

        console.error(`Error al subir fragmento ${chunk.index}:`, error)
        chunk.status = "error"
        this.activeUploads--

        // Reintentar el fragmento después de un breve retraso
        setTimeout(() => {
          if (!this.aborted) {
            chunk.status = "pending"
            this._uploadNextChunks()
          }
        }, 3000)
      })
  }

  // Finalizar la subida cuando todos los fragmentos han sido subidos
  _finalizeUpload() {
    if (this.aborted) return

    console.log("Todos los fragmentos han sido subidos. Finalizando...")

    // Enviar solicitud para combinar los fragmentos
    fetch(`${this.options.endpoint}/finalize`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        upload_id: this.uploadId,
        filename: this.options.file.name,
        total_chunks: this.totalChunks,
        ...this.options.metadata,
      }),
      credentials: "same-origin",
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Error HTTP: ${response.status}`)
        }
        return response.json()
      })
      .then((data) => {
        if (this.aborted) return

        console.log("Subida completada con éxito:", data)

        // Llamar al callback de finalización
        if (this.options.onComplete) {
          this.options.onComplete(data)
        }
      })
      .catch((error) => {
        if (this.aborted) return

        console.error("Error al finalizar la subida:", error)
        this._handleError("Error al finalizar la subida: " + error.message)
      })
  }

  // Generar un ID único para la subida
  _generateUploadId() {
    return "upload_" + Date.now() + "_" + Math.random().toString(36).substring(2, 15)
  }

  // Manejar errores
  _handleError(message) {
    console.error(message)

    if (this.options.onError) {
      this.options.onError(message)
    }
  }

  // Formatear tamaño de archivo para mostrar
  _formatFileSize(bytes) {
    if (bytes === 0) return "0 Bytes"

    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))

    return Number.parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i]
  }
}

// Exportar la clase para uso global
window.ChunkedUploader = ChunkedUploader
