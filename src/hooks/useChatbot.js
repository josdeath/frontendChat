import { useState, useEffect, useRef } from "react";
import useGemini1_5 from "./useGemini1_5";
import useGemini2_0 from "./useGemini2_0";
import useDeepseek from "./useDeepseek";
import {
  getConversations,
  saveConversation,
  deleteConversation,
  updateConversation
} from "../services/chatService";

// --- URL de tu backend ---
const BACKEND_URL = "https://backnode-60g0.onrender.com"; // Asegúrate que esta es tu URL de OnRender

const useChatbot = () => {
  const [messages, setMessages] = useState([
    { text: "¡Hola! ¿En qué puedo ayudarte hoy?", sender: "bot" }
  ]);
  const [history, setHistory] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(null);
  const [temperature, setTemperature] = useState(0.7);
  const [topP, setTopP] = useState(1);
  const [maxOutputTokens, setMaxOutputTokens] = useState(2048); // Aumentado para RAG
  const [autoRead, setAutoRead] = useState(() => JSON.parse(localStorage.getItem("autoRead")) ?? true);
  // const [isSaved, setIsSaved] = useState(false); // No se usa activamente
  const [isHistoryVisible, setIsHistoryVisible] = useState(true);
  
  const [selectedPdf, setSelectedPdf] = useState(null);
  
  const chatRef = useRef(null);
  const [selectedModel, setSelectedModel] = useState("gemini-1.5");

  // --- Nuevo estado para la búsqueda en internet ---
  const [isSearchingInternet, setIsSearchingInternet] = useState(false);
  // --- Fin de nuevo estado ---

  const gemini = useGemini1_5();
  const gemini2 = useGemini2_0();
  const deepseek = useDeepseek();

  const { generateContent, estimateTokens } =
    selectedModel === "gemini-2.0"
      ? gemini2
      : selectedModel === "deepseek"
      ? deepseek
      : gemini;

  const extractTextFromPDF = async (filename) => {
    try {
      const txtFilename = filename.replace(".pdf", "") + ".txt";
      const res = await fetch(`https://jhutdencubufyjuvtnwx.supabase.co/storage/v1/object/public/pdfs/${txtFilename}`);
      if (!res.ok) throw new Error(`Error al cargar texto PDF: ${res.status}`);
      return await res.text();
    } catch (err) {
      console.error("❌ Error leyendo el texto del PDF:", err);
      return "";
    }
  };
      
  useEffect(() => {
    localStorage.setItem("autoRead", JSON.stringify(autoRead));
  }, [autoRead]);

  useEffect(() => {
    fetchServerHistory();
  }, []);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages, isSearchingInternet]); // Añadido isSearchingInternet

  const speak = (text) => {
    if (!autoRead || !window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "es-ES";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  const fetchServerHistory = async (preserveIndex = false) => {
    const userId = localStorage.getItem("userId");
    if (!userId) return;
    try {
      const result = await getConversations(userId);
      const reversed = result.slice().reverse();
      setHistory(reversed);
      const savedIndexStr = localStorage.getItem("lastConversationIndex");
      const savedIndex = savedIndexStr !== null ? parseInt(savedIndexStr, 10) : null;

      if (!preserveIndex && reversed.length > 0) {
        const indexToUse = (savedIndex !== null && reversed[savedIndex]) ? savedIndex : 0;
        if (reversed[indexToUse]) {
            setMessages(reversed[indexToUse].messages);
            setCurrentIndex(indexToUse);
            localStorage.setItem("lastConversationIndex", indexToUse.toString());
        } else if (reversed[0]) {
            setMessages(reversed[0].messages);
            setCurrentIndex(0);
            localStorage.setItem("lastConversationIndex", "0");
        } else {
             startNewConversation();
        }
      } else if (preserveIndex && currentIndex !== null && reversed[currentIndex]) {
        setMessages(reversed[currentIndex].messages);
      } else if (reversed.length === 0) {
        startNewConversation();
      }
    } catch (err) {
      console.error("❌ Error al cargar historial:", err);
      setMessages([{ text: "Error al cargar el historial.", sender: "bot" }]);
      setHistory([]);
      setCurrentIndex(null);
    }
    
  };
  
  const renameConversation = async (index, newName) => {
    if(!history[index]) return;
    const updatedHistoryArray = [...history];
    const chat = updatedHistoryArray[index];
    chat.name = newName;
    setHistory(updatedHistoryArray);
    try {
      const res = await fetch(`${BACKEND_URL}/rename_chat`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chatId: chat.id, newName: newName }),
      });
      const result = await res.json();
      if (!result.success) {
        alert("❌ No se pudo renombrar en la base de datos");
        fetchServerHistory(true);
      }
    } catch (err) {
      console.error("Error al renombrar:", err);
      alert("⚠️ Error de red al renombrar");
      fetchServerHistory(true);
    }
  };

  const sendMessage = async ({ text, sender = "user" }) => {
    const newMessage = { text, sender };
    let currentDisplayMessages = [...messages, newMessage]; // Mensajes para UI y prompt
    setMessages(currentDisplayMessages);
  
    const normalizedText = text.toLowerCase();
    let pdfContext = ""; // Texto del PDF
    let contextFromInternetSearch = ""; // Texto de búsqueda en internet
    let isInternetSearchTriggered = false;
    let searchQuery = "";

    // 1. Detectar si es una búsqueda en internet
    const searchTriggers = [
      "busca en internet sobre ", "investiga sobre ", "googlea sobre ",
      "encuentra información de ", "busca información sobre ", "busca en la web sobre ",
      "necesito información de internet sobre ", "busca en internet "
    ];
    for (const trigger of searchTriggers) {
      if (normalizedText.startsWith(trigger)) {
        isInternetSearchTriggered = true;
        searchQuery = text.substring(trigger.length).trim();
        if (trigger === "busca en internet " && !searchQuery) {
          isInternetSearchTriggered = false;
        }
        break;
      }
    }

    try {
      // 2. Si es búsqueda, obtener contexto de internet
      if (isInternetSearchTriggered && searchQuery) {
        setIsSearchingInternet(true);
        const searchingMessage = { text: `Buscando en internet sobre "${searchQuery}"...`, sender: "bot", type: "system_searching" };
        currentDisplayMessages = [...currentDisplayMessages, searchingMessage];
        setMessages(currentDisplayMessages);

        try {
          const response = await fetch(`${BACKEND_URL}/serpapi-search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: searchQuery, hl: "es", gl: "pe" }),
          });
          currentDisplayMessages = currentDisplayMessages.filter(m => m.type !== "system_searching");

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: "Error desconocido del servidor."}));
            throw new Error(errorData.error || `Error del servidor al buscar: ${response.status}`);
          }
          const searchDataFromBackend = await response.json();
          if (searchDataFromBackend.results && searchDataFromBackend.results.length > 0) {
            contextFromInternetSearch = "Resultados de la búsqueda en internet:\n";
            searchDataFromBackend.results.slice(0, 3).forEach((item, index) => {
              contextFromInternetSearch += `[Resultado ${index + 1}] Título: ${item.title}\nFragmento: ${item.snippet || item.link}\n\n`;
            });
          } else {
            currentDisplayMessages = [...currentDisplayMessages, { text: `No se encontraron resultados para: "${searchQuery}".`, sender: "bot" }];
          }
        } catch (searchError) {
          console.error("❌ Error en búsqueda (llamada a backend):", searchError);
          currentDisplayMessages = currentDisplayMessages.filter(m => m.type !== "system_searching");
          currentDisplayMessages = [...currentDisplayMessages, { text: `Error al buscar: ${searchError.message}`, sender: "bot" }];
          setMessages(currentDisplayMessages); // Mostrar error de búsqueda
          setIsSearchingInternet(false);
          return; // No continuar si la búsqueda falla críticamente
        } finally {
          setIsSearchingInternet(false);
          setMessages(currentDisplayMessages); // Actualizar UI con/sin resultados de búsqueda
        }
      } 
      // 3. Si NO es búsqueda en internet, verificar si es PDF
      else { 
        const keywords = ["pdf", "documento", "resumen", "contenido", "archivo"];
        const mentionsPdf = selectedPdf &&
          (keywords.some((kw) => normalizedText.includes(kw)) ||
           (selectedPdf.originalname && normalizedText.includes(selectedPdf.originalname.toLowerCase().replace(".pdf", ""))));
        if (selectedPdf && mentionsPdf) {
          pdfContext = await extractTextFromPDF(selectedPdf.filename);
           if (!pdfContext) {
              currentDisplayMessages = [...currentDisplayMessages, {text: `⚠️ No pude leer el PDF: ${selectedPdf.originalname}`, sender: "bot"}];
              setMessages(currentDisplayMessages);
           }
        }
      }
  
      // 4. Construir el fullPrompt para el LLM
      let fullPrompt = "";
      const historyForPrompt = currentDisplayMessages
          .filter(m => m.type !== "system_searching" && !(m.sender === "bot" && m.text.startsWith("No se encontraron") && m.text.includes(searchQuery))) // Evitar "No resultados para..." en el prompt de LLM si hay búsqueda
          .slice(0, -1) // Todo menos el último mensaje del usuario
          .slice(-9) // últimos 9 de contexto
          .map(m => `${m.sender === "user" ? "Usuario" : "Asistente"}: ${m.text}`)
          .join("\n");

      if (contextFromInternetSearch) { // Prioridad 1: Contexto de Internet
        fullPrompt = (historyForPrompt ? historyForPrompt + "\n" : "") +
                     `Usuario: ${text}\n\n` +
                     `Contexto obtenido de una búsqueda en internet sobre "${searchQuery}":\n${contextFromInternetSearch}\n` +
                     `Basándote en el historial y el contexto de la búsqueda, responde a la pregunta del usuario.\nAsistente:`;
      } else if (pdfContext) { // Prioridad 2: Contexto de PDF
        const isAskingForSummary = normalizedText.includes("resumen") || normalizedText.includes("resumelo");
        fullPrompt = isAskingForSummary
          ? (historyForPrompt ? historyForPrompt + "\n" : "") + `Resume claramente el siguiente documento:\n\n${pdfContext}\nAsistente:`
          : (historyForPrompt ? historyForPrompt + "\n" : "") + `El usuario ha hecho una pregunta relacionada con el siguiente documento PDF (${selectedPdf.originalname}). Usa su contenido para responder:\n\n${pdfContext}\n\nPregunta del usuario: ${text}\nAsistente:`;
      } else { // Prioridad 3: Prompt de conversación normal
        // El prompt base que tenías, pero construido con `currentDisplayMessages` para incluir el mensaje actual del usuario
        fullPrompt = currentDisplayMessages
            .filter(m => m.type !== "system_searching") // Excluir "buscando"
            .slice(-10) // Últimos 10 mensajes
            .map(m => `${m.sender === "user" ? "Usuario" : "Asistente"}: ${m.text}`)
            .join("\n") + "\nAsistente:"; // El .join() ya incluye el user: text y espera el Asistente:
      }
  
      const totalInputTokens = estimateTokens(fullPrompt);
      // Ajusta este límite según el modelo y tus necesidades
      const INPUT_TOKEN_LIMIT = selectedModel === "deepseek" ? 7000 : 28000; 
      if (totalInputTokens > INPUT_TOKEN_LIMIT) {
        const tokenErrorMsg = { text: `⚠️ Demasiado texto para procesar (> ${INPUT_TOKEN_LIMIT} tokens).`, sender: "bot"};
        setMessages(prev => [...prev.filter(m => m.type !== "system_searching"), tokenErrorMsg]);
        return;
      }
  
      // 5. Llamar al LLM
      let botText;
      if (selectedModel === "deepseek") {
        botText = await generateContent({
          messages: [{ role: "user", content: fullPrompt }],
          maxOutputTokens, temperature, topP,
        });
      } else {
        botText = await generateContent({
          prompt: fullPrompt,
          maxOutputTokens, temperature, topP,
        });
      }
  
      const botReply = { text: botText, sender: "bot" };
      // `currentDisplayMessages` ya tiene el user msg y posibles msgs de "no resultados/error búsqueda"
      // Solo necesitamos quitar el de "buscando" (ya se hizo) y añadir la respuesta del bot.
      const finalMessagesToDisplayAndSave = [...currentDisplayMessages.filter(m => m.type !== "system_searching"), botReply];
      setMessages(finalMessagesToDisplayAndSave);
      speak(botText);
  
      // 6. Guardar conversación (tu lógica existente)
      const userId = localStorage.getItem("userId");
      if (!userId) return;
  
      if (currentIndex === null) {
        const name = text.slice(0, 30).trim() || `Conversación ${new Date().toLocaleTimeString()}`;
        const saved = await saveConversation(userId, name, finalMessagesToDisplayAndSave);
        if (saved.success && saved.id) {
          const newHistory = await getConversations(userId);
          const reversed = newHistory.slice().reverse();
          setHistory(reversed);
          const newIndex = reversed.findIndex(conv => conv.id === saved.id);
          if (newIndex !== -1) {
            setMessages(reversed[newIndex].messages);
            setCurrentIndex(newIndex);
            localStorage.setItem("lastConversationIndex", newIndex.toString());
          }
        }
      } else {
        const existingConv = history[currentIndex];
        if (existingConv?.id) {
          await updateConversation(existingConv.id, finalMessagesToDisplayAndSave);
          const newHistory = [...history];
          newHistory[currentIndex] = { ...newHistory[currentIndex], messages: finalMessagesToDisplayAndSave };
          setHistory(newHistory);
        }
      }
    } catch (err) {
      console.error("❌ Error general en sendMessage:", err);
      setMessages(prev => [...prev.filter(m => m.type !== "system_searching"), {text: "Lo siento, ocurrió un error inesperado.", sender: "bot"}]);
    } finally {
        setIsSearchingInternet(false); // Siempre resetear
    }
  };
  
  const startNewConversation = () => {
    setMessages([{ text: "¡Hola! ¿En qué puedo ayudarte hoy?", sender: "bot" }]);
    setCurrentIndex(null);
    // setIsSaved(false); // No se usa
    setSelectedPdf(null);
    localStorage.removeItem("lastConversationIndex");
  };
  
  const loadConversation = (index) => {
    if (history[index]) {
      setMessages(history[index].messages);
      setCurrentIndex(index);
      localStorage.setItem("lastConversationIndex", index.toString());
      setSelectedPdf(null);
    }
  };

  const deleteConversationByIndex = async (index) => {
    const itemToDelete = history[index];
    if (!itemToDelete) return;
    try {
      await deleteConversation(itemToDelete.id);
      const oldHistory = [...history];
      const newHistory = oldHistory.filter((_, i) => i !== index);
      setHistory(newHistory);

      if (newHistory.length === 0) {
        startNewConversation();
      } else if (currentIndex === index) {
        const newIndexToLoad = Math.max(0, index - 1);
        loadConversation(newHistory[newIndexToLoad] ? newIndexToLoad : 0);
      } else if (currentIndex !== null && currentIndex > index) {
        const newCurrentIndex = currentIndex - 1;
        setCurrentIndex(newCurrentIndex);
        localStorage.setItem("lastConversationIndex", newCurrentIndex.toString());
      }
    } catch (err) {
      console.error("❌ Error al eliminar:", err);
      alert("Error al eliminar la conversación del servidor.");
    }
  };

  return {
    messages,
    sendMessage,
    startNewConversation,
    loadConversation,
    deleteConversation: deleteConversationByIndex,
    chatRef,
    temperature,
    setTemperature,
    topP,
    setTopP,
    isHistoryVisible,
    setIsHistoryVisible,
    autoRead,
    setAutoRead,
    history,
    currentIndex,
    maxOutputTokens,
    setMaxOutputTokens,
    selectedPdf,
    setSelectedPdf,
    setCurrentIndex,
    selectedModel,
    setSelectedModel,
    renameConversation,
    isSearchingInternet, // Exportar para la UI
  };
};

export default useChatbot;