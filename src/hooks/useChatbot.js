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

const useChatbot = () => {
  const [messages, setMessages] = useState([
    { text: "¡Hola! ¿En qué puedo ayudarte hoy?", sender: "bot" }
  ]);
  const [history, setHistory] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(null);
  const [temperature, setTemperature] = useState(0.7);
  const [topP, setTopP] = useState(1);
  const [maxOutputTokens, setMaxOutputTokens] = useState(256);
  const [autoRead, setAutoRead] = useState(() => JSON.parse(localStorage.getItem("autoRead")) ?? true);
  const [isSaved, setIsSaved] = useState(false);           // Ya está definido correctamente ✅
  const [isHistoryVisible, setIsHistoryVisible] = useState(true); // 🔧 Este faltaba
  
  const [selectedPdf, setSelectedPdf] = useState(null);
  
  const chatRef = useRef(null);
  const [selectedModel, setSelectedModel] = useState("gemini-1.5");

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
          const txtFilename = filename.replace(".pdf", "") + ".txt"; // ✅ CORRECTO
          const res = await fetch(`https://jhutdencubufyjuvtnwx.supabase.co/storage/v1/object/public/pdfs/${txtFilename}`);

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
  }, [messages]);

  const speak = (text) => {
    if (!autoRead || !window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "es-ES";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  };

  // --- Dentro de useChatbot.js ---

const fetchServerHistory = async (preserveIndex = false) => {
  const userId = localStorage.getItem("userId");
  if (!userId) return;

  try {
    const result = await getConversations(userId); // Obtiene las conversaciones (asumimos oldest -> newest)

    // 1. Invierte la lista para que la más nueva esté al principio (índice 0)
    const reversed = result.slice().reverse(); // [newest, ..., oldest]
    setHistory(reversed); // Guarda la lista invertida en el estado

    // 2. Si no se debe preservar el índice (carga inicial o nueva convo)
    //    Y hay conversaciones en la lista invertida...
    if (!preserveIndex && reversed.length > 0) {
      const newIndex = 0; // El índice 0 ahora apunta a la conversación MÁS NUEVA
      setMessages(reversed[newIndex].messages); // Carga los mensajes de la más nueva
      setCurrentIndex(newIndex); // Establece el índice actual a 0
      console.log(`Historial cargado. Seleccionando la conversación más reciente (índice ${newIndex} en la lista invertida).`);
    }
    // 3. Si se debe preservar el índice y ese índice es válido en la lista invertida...
    else if (preserveIndex && currentIndex !== null && reversed[currentIndex]) {
      // Asegúrate de que los mensajes se carguen si el índice se preserva
      // (esto ya debería estar cubierto por la lógica existente, pero es bueno confirmarlo)
      setMessages(reversed[currentIndex].messages);
      console.log(`Historial refrescado. Preservando índice ${currentIndex}.`);
    }
    // 4. Si no hay historial después de obtenerlo...
    else if (reversed.length === 0) {
        startNewConversation(); // Inicia una nueva conversación si no hay historial
        console.log("No se encontró historial, iniciando nueva conversación.");
    }

  } catch (err) {
    console.error("❌ Error al cargar historial:", err);
    // Considera manejar el error de forma más visual para el usuario
     setMessages([{ text: "Error al cargar el historial.", sender: "bot" }]);
     setHistory([]);
     setCurrentIndex(null);
  }
};
  
  
const renameConversation = async (index, newName) => {
  const updated = [...history];
  const chat = updated[index];
  chat.name = newName;
  setHistory(updated);

  // Enviar cambio al backend actualizado
  try {
    const res = await fetch("https://backnode-60g0.onrender.com/rename_chat", {
      method: "PATCH", // PATCH (no POST)
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        chatId: chat.id,  // Correcto
        newName: newName, // Correcto
      }),
    });

    const result = await res.json();

    if (!result.success) {
      alert("❌ No se pudo renombrar en la base de datos");
    }
  } catch (err) {
    console.error("Error al renombrar:", err);
    alert("⚠️ Error de red al renombrar");
  }
};

  

  const sendMessage = async ({ text, sender = "user" }) => {
    const newMessage = { text, sender };
    const updatedMessages = [...messages, newMessage]; // Agregar el nuevo mensaje
    setMessages(updatedMessages);
  
    let prompt = updatedMessages
      .slice(-10)
      .map((m) => `${m.sender === "user" ? "Usuario" : "Asistente"}: ${m.text}`)
      .join("\n");
  
    prompt += `\nUsuario: ${text}\nAsistente:`;
  
    const totalInputTokens = estimateTokens(prompt);
    if (totalInputTokens > 3000) {
      setMessages((prev) => [...prev, {
        text: "⚠️ Demasiado texto. Acorta la conversación o empieza una nueva.",
        sender: "bot"
      }]);
      return;
    }
  
    try {
      let pdfContext = "";
      const normalizedText = text.toLowerCase();
      const keywords = ["pdf", "documento", "resumen", "contenido"];
      console.log("📎 selectedPdf actual:", selectedPdf);
      const mentionsPdf = selectedPdf &&
        (keywords.some((kw) => normalizedText.includes(kw)) ||
          normalizedText.includes(selectedPdf.originalname.toLowerCase().replace(".pdf", "")));
  
      if (selectedPdf && mentionsPdf) {
        pdfContext = await extractTextFromPDF(selectedPdf.filename);
      }
  
      let fullPrompt = "";
      if (pdfContext) {
        const isAskingForSummary = normalizedText.includes("resumen") || normalizedText.includes("resumelo");
        fullPrompt = isAskingForSummary
          ? `Resume claramente el siguiente documento:\n\n${pdfContext}`
          : `El usuario ha hecho una pregunta relacionada con el siguiente documento PDF (${selectedPdf.originalname}). Usa su contenido para responder:\n\n${pdfContext}\n\nPregunta: ${text}`;
      } else {
        fullPrompt = prompt;
      }
  
      let botText;
  
      if (selectedModel === "deepseek") {
        botText = await generateContent({
          messages: [
            { role: "user", content: fullPrompt }
          ],
          maxOutputTokens,
          temperature,
          topP,
        });
      } else {
        botText = await generateContent({
          prompt: fullPrompt,
          maxOutputTokens,
          temperature,
          topP,
        });
      }
  
      const botReply = { text: botText, sender: "bot" };
      const finalMessages = [...updatedMessages, botReply];
      setMessages(finalMessages);  // Actualiza los mensajes correctamente
      speak(botText);
  
      const userId = localStorage.getItem("userId");
      if (!userId) return;
  
      if (currentIndex === null) {
        const name = newMessage.text.slice(0, 30) || "Conversación";
        const saved = await saveConversation(userId, name, finalMessages);
        if (saved.success) {
          const updated = await getConversations(userId);
          setHistory(updated);
          setCurrentIndex(updated.length - 1);  // Actualiza el índice de la última conversación
        }
      } else {
        const existingConv = history[currentIndex];
        if (existingConv?.id) {
          await updateConversation(existingConv.id, finalMessages);
          await fetchServerHistory(); // Asegura que se recargue el historial
        }
      }
    } catch (err) {
      console.error("❌ Error generando respuesta:", err);
    }
  };
  
  
  


  const startNewConversation = () => {
    setMessages([{ text: "¡Hola! ¿En qué puedo ayudarte hoy?", sender: "bot" }]);
    setCurrentIndex(null);
    setIsSaved(false);
    setSelectedPdf(null); // 👈 Añade esto para limpiar el PDF seleccionado
  };
  

  const loadConversation = (index) => {
    if (history[index]) {
      setMessages(history[index].messages);
      setCurrentIndex(index);
    }
  };

  const deleteConversationByIndex = async (index) => {
    const item = history[index];
    if (!item) return;
    try {
      await deleteConversation(item.id);
      await fetchServerHistory();
      startNewConversation();
    } catch (err) {
      console.error("❌ Error al eliminar:", err);
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
    selectedModel,          // ✅ nuevo
    setSelectedModel,
    renameConversation
  };
};

export default useChatbot;
