document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("questionInput")
  const sendBtn = document.getElementById("sendBtn")
  const chatMessages = document.getElementById("chatMessages")
  const root = document.getElementById("chatbotRoot")

  if (!input || !sendBtn || !chatMessages || !root) return

  const queryUrl = root.dataset.queryUrl

  function addMessage(text, isUser) {
    const msg = document.createElement("div")
    msg.className = isUser ? "message user" : "message bot"
    msg.innerText = text
    chatMessages.appendChild(msg)
    chatMessages.scrollTop = chatMessages.scrollHeight
  }

  async function sendQuestion() {
    const question = input.value.trim()
    if (!question) return

    addMessage(question, true)
    input.value = ""

    const loadingId = "loading-message"
    const loading = document.createElement("div")
    loading.className = "message bot"
    loading.id = loadingId
    loading.innerText = "Pensando..."
    chatMessages.appendChild(loading)
    chatMessages.scrollTop = chatMessages.scrollHeight

    try {
      const response = await fetch(queryUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ question })
      })

      const data = await response.json()
      const loadingNode = document.getElementById(loadingId)
      if (loadingNode) loadingNode.remove()

      if (data.answer) {
        addMessage(data.answer, false)
      } else if (data.error) {
        addMessage(`Error: ${data.error}`, false)
      } else {
        addMessage("No he podido procesar la pregunta.", false)
      }
    } catch (error) {
      const loadingNode = document.getElementById(loadingId)
      if (loadingNode) loadingNode.remove()
      addMessage("Error de conexión con el servidor.", false)
    }
  }

  sendBtn.addEventListener("click", sendQuestion)

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault()
      sendQuestion()
    }
  })
})