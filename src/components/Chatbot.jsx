// --- INICIO Chatbot.js ---
import React, { useState, useEffect, useRef } from "react"; // Añadido useRef
import MessageHistory from "./MessageHistory";
import useChatbot from "../hooks/useChatbot";
import HistoryList from "./HistoryList";
import PDFSelector from "./PDFSelector";
import logo from "../logo.png";
import { logout } from "../services/auth"; // Asegúrate que esta ruta sea correcta

// Importa los iconos que usarás para los botones de toggle
import { FaBars, FaFolderOpen } from 'react-icons/fa'; 

// Asegúrate de importar los subcomponentes si están en archivos separados
// import MessageHistory from './MessageHistory';
// import HistoryList from './HistoryList';
// import PDFSelector from './PDFSelector';

// Asegúrate que el hook useChatbot se importa correctamente
// import useChatbot from '../hooks/useChatbot';

const Chatbot = () => {
  // Estados y lógica del hook useChatbot
  const {
    selectedModel,
    setSelectedModel,
    messages,
    sendMessage,
    history,
    loadConversation,
    deleteConversation,
    chatRef, // Ahora useRef está importado
    startNewConversation,
    maxOutputTokens,
    setMaxOutputTokens,
    temperature,
    setTemperature,
    topP,
    setTopP,
    autoRead,
    setAutoRead,
    selectedPdf,
    setSelectedPdf,
    currentIndex,
    setCurrentIndex, // Asegúrate que este se exporta/importa desde useChatbot
    renameConversation,
  } = useChatbot();

  // Otros estados del componente
  const [input, setInput] = useState("");
  const [showTokenSettings, setShowTokenSettings] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeTab, setActiveTab] = useState("chats");
  const [theme, setTheme] = useState("dark");
  const [availablePdfs, setAvailablePdfs] = useState([]);

  // --- Estados para visibilidad móvil ---
  const [isLeftPanelMobileVisible, setIsLeftPanelMobileVisible] = useState(false);
  const [isCenterPanelMobileVisible, setIsCenterPanelMobileVisible] = useState(false);
  // -------------------------------------

  // --- Efectos ---
  useEffect(() => {
    // Cargar tema guardado
    const savedTheme = localStorage.getItem("theme") || "dark";
    setTheme(savedTheme);
    document.body.className = savedTheme;
  }, []);

  useEffect(() => {
    // Cargar PDFs iniciales
    fetchPdfs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Dependencia vacía para que se ejecute solo al montar

  useEffect(() => {
    // Listener para cerrar paneles si la ventana se agranda
    const handleResize = () => {
      if (window.innerWidth > 768) { // Mismo breakpoint que CSS
        setIsLeftPanelMobileVisible(false);
        setIsCenterPanelMobileVisible(false);
      }
    };
    window.addEventListener('resize', handleResize);
    // Limpieza del listener al desmontar
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  // ------------------------------------------------------------

  // --- Funciones ---
  const toggleTheme = () => {
    const newTheme = theme === "dark" ? "light" : "dark";
    setTheme(newTheme);
    document.body.className = newTheme;
    localStorage.setItem("theme", newTheme);
  };

  const fetchPdfs = async () => {
    const userId = localStorage.getItem("userId");
    if (!userId) {
        console.warn("User ID not found for fetching PDFs.");
        return;
    }

    try {
      // Reemplaza 'http://localhost/chatbot-api/' con la URL real de tu API si es diferente
      const res = await fetch(`https://backnode-60g0.onrender.com/get_pdfs?userId=${userId}`);
      if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
      const data = await res.json();
      // Valida que data sea un array antes de asignarlo
      setAvailablePdfs(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Error fetching PDFs:", error);
      setAvailablePdfs([]); // Pone un array vacío en caso de error
    }
  };


  const handleUploadPdf = async (file) => {
     const userId = localStorage.getItem("userId");
     if (!userId) {
       alert("Usuario no identificado. No se puede subir el archivo.");
       return;
     }
     if (!file) {
        alert("No se ha seleccionado ningún archivo.");
        return;
     }

     const formData = new FormData();
     formData.append("userId", userId);
     formData.append("file", file);

     try {
        
        const res = await fetch("https://backnode-60g0.onrender.com/upload_pdf", {
          method: "POST",
          body: formData,
        });
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const result = await res.json();
        if (result.success) {
          alert('PDF subido correctamente!'); // Feedback al usuario
          await fetchPdfs(); // Recarga la lista de PDFs
        } else {
          alert(result.error || "Error desconocido al subir el PDF.");
        }
     } catch (error) {
        console.error("Error uploading PDF:", error);
        alert(`Error de conexión al subir el PDF: ${error.message}`);
     }
  };

  // Filtrar historial basado en el término de búsqueda
  const filteredHistory = Array.isArray(history)
    ? history.filter((conv) =>
        (conv.name || 'Sin título').toLowerCase().includes(searchTerm.toLowerCase())
      )
    : [];

  // Manejar click en una conversación del historial
  const handleConversationClick = (indexInFiltered) => {
    const selectedConv = filteredHistory[indexInFiltered];
    if (!selectedConv) return; // Añadir chequeo por si acaso

    // Encuentra el índice original en el array 'history' sin filtrar
    const originalIndex = history.findIndex((conv) => conv.id === selectedConv.id);

    if (originalIndex !== -1) {
       loadConversation(originalIndex);
       // --- Cierra paneles móviles al seleccionar convo ---
       closeMobilePanels(); // Llama a la función unificada
       // -----------------------------------------------
    } else {
        console.error("Could not find original index for conversation:", selectedConv.id);
    }
  };

  // Manejar borrado de conversación
  const handleDeleteConversation = async (indexInFiltered) => {
     const selectedConv = filteredHistory[indexInFiltered];
     if (!selectedConv) return;

     // Encuentra el índice original en el array 'history' sin filtrar
     const originalIndex = history.findIndex((conv) => conv.id === selectedConv.id);

     if (originalIndex !== -1) {
       await deleteConversation(originalIndex); // Llama a la función del hook
        // Opcional: Si borras la conversación activa, inicia una nueva
       if (originalIndex === currentIndex) {
         startNewConversation();
       }
     } else {
        console.error("Could not find original index for deletion.");
     }
  };

  // Manejar renombrado de conversación
  const handleRenameConversation = async (indexInFiltered, newName) => {
     const selectedConv = filteredHistory[indexInFiltered];
     if (!selectedConv) return;

     const originalIndex = history.findIndex((conv) => conv.id === selectedConv.id);
      if (originalIndex !== -1) {
        await renameConversation(originalIndex, newName); // Llama a la función del hook
      }
  }

  // Manejar envío de mensaje
  const handleSend = () => {
    if (input.trim()) {
      sendMessage({ text: input }); // Usa la función del hook
      setInput("");
    }
  };

  // --- Funciones para toggles móviles ---
  const toggleLeftPanel = () => {
    setIsLeftPanelMobileVisible(!isLeftPanelMobileVisible);
    setIsCenterPanelMobileVisible(false); // Cierra el otro si se abre este
  };

  const toggleCenterPanel = () => {
    setIsCenterPanelMobileVisible(!isCenterPanelMobileVisible);
    setIsLeftPanelMobileVisible(false); // Cierra el otro si se abre este
  };

  const closeMobilePanels = () => {
    setIsLeftPanelMobileVisible(false);
    setIsCenterPanelMobileVisible(false);
  }
  // ------------------------------------

  // --- Funciones Wrapper para cerrar el panel izquierdo en móvil ---
  const handleStartNewConversation = () => {
    startNewConversation(); // Llama a la función original del hook
    closeMobilePanels(); // Cierra ambos paneles por si acaso
  };

  const handleOpenSettings = () => {
    setShowTokenSettings(true);
    closeMobilePanels(); // Cierra ambos paneles
  };
  // ---------------------------------------------------------------

  // --- Renderizado del componente ---
  return (
    <div className="chatbot-container">

      {/* --- Backdrop para cerrar paneles en móvil --- */}
      {(isLeftPanelMobileVisible || isCenterPanelMobileVisible) && (
        <div className="mobile-backdrop" onClick={closeMobilePanels}></div>
      )}
      {/* ------------------------------------------ */}

      {/* --- Botones de Toggle Móvil (se mostrarán/ocultarán por CSS) --- */}
      <button className="mobile-toggle-button mobile-left-toggle" onClick={toggleLeftPanel}>
        <FaBars /> {/* Icono de menú (hamburguesa) */}
      </button>
      <button className="mobile-toggle-button mobile-center-toggle" onClick={toggleCenterPanel}>
        <FaFolderOpen /> {/* Icono de historial/archivos */}
      </button>
      {/* --------------------------------------------------- */}


      {/* Panel izquierdo - Clase condicional para visibilidad móvil */}
      <div className={`izquierda ${isLeftPanelMobileVisible ? 'mobile-visible' : ''}`}>
        {/* Botones superiores del panel izquierdo */}
        <div className="top-buttons">
          <a href="https://united-its.com/" target="_blank" rel="noopener noreferrer">
            <img src={logo} alt="Logo United ITS" className="logo" />
          </a>
          {/* Usa las funciones wrapper para cerrar el panel en móvil */}
          <button onClick={handleStartNewConversation} className="new-conversation" title="Nueva Conversación">+</button>
          <button onClick={handleOpenSettings} className="token-settings-button" title="Ajustes">⚙️</button>
        </div>
        {/* Controles inferiores del panel izquierdo */}
        <div className="bottom-controls">
          {/* Toggle de Tema */}
          <div className="bottom-toggle">
            <div className={`vertical-toggle ${theme}`} onClick={toggleTheme} title={`Cambiar a tema ${theme === 'dark' ? 'claro' : 'oscuro'}`}>
              <div className="toggle-icon">{theme === "dark" ? "🌙" : "☀️"}</div>
            </div>
          </div>
          {/* Botón de Logout */}
          <div className="logout-container">
            <button onClick={logout} className="logout-button" title="Salir">
              <div className="sign">
                <svg viewBox="0 0 512 512"><path d="M377.9 105.9L500.7 228.7c7.2 7.2 11.3 17.1 11.3 27.3s-4.1 20.1-11.3 27.3L377.9 406.1c-6.4 6.4-15 9.9-24 9.9c-18.7 0-33.9-15.2-33.9-33.9l0-62.1-128 0c-17.7 0-32-14.3-32-32l0-64c0-17.7 14.3-32 32-32l128 0 0-62.1c0-18.7 15.2-33.9 33.9-33.9c9 0 17.6 3.6 24 9.9zM160 96L96 96c-17.7 0-32 14.3-32 32l0 256c0 17.7 14.3 32 32 32l64 0c17.7 0 32 14.3 32 32s-14.3 32-32 32l-64 0c-53 0-96-43-96-96L0 128C0 75 43 32 96 32l64 0c17.7 0 32 14.3 32 32s-14.3 32-32 32z"></path></svg>
              </div>
              <div className="text">Salir</div>
            </button>
          </div>
        </div>
      </div>

      {/* Panel central - Clase condicional para visibilidad móvil */}
      <div className={`centro ${isCenterPanelMobileVisible ? 'mobile-visible' : ''}`}>
        {/* Input de búsqueda */}
        <input
          type="text"
          placeholder="🔎 Buscar conversación..."
          className="search-input"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        {/* Botones de Pestañas (Chats/PDFs) */}
        <div className="tab-buttons">
          <button className={`tab-button ${activeTab === "chats" ? "active" : ""}`} onClick={() => setActiveTab("chats")}>
            🗂 Chats
          </button>
          <button className={`tab-button ${activeTab === "pdfs" ? "active" : ""}`} onClick={() => setActiveTab("pdfs")}>
            📄 PDFs
          </button>
        </div>
        {/* Contenido de las Pestañas */}
        <div className="tab-content">
          {/* Selector de Modelo */}
          <div style={{ /* Estilos inline si son pocos, si no, mover a CSS */ }}>
            <label htmlFor="modelSelect" style={{ color:'white' }}>🧠 Modelo:</label>
            <select
              id="modelSelect"
              value={selectedModel}
              onChange={(e) => {
                setSelectedModel(e.target.value);
                startNewConversation(); // Inicia nueva convo al cambiar modelo
                closeMobilePanels(); // Cierra paneles al cambiar modelo
              }}
            >
              {/* Agrupa opciones por proveedor */}
              <optgroup label="Gemini">
                <option value="gemini-1.5">Gemini 1.5</option>
                <option value="gemini-2.0">Gemini 2.0</option> 
              </optgroup>
              <optgroup label="DeepSeek">
                 <option value="deepseek">DeepSeek</option>
              </optgroup>
              {/* Añade más modelos/grupos si es necesario */}
            </select>
          </div>
          {/* Contenido de la pestaña Chats */}
          {activeTab === "chats" && (
            <HistoryList
              history={filteredHistory} // Pasa el historial filtrado
              currentConversationIndex={currentIndex} // Índice de la convo activa (del hook)
              loadConversation={handleConversationClick} // Función para cargar una convo
              deleteConversation={handleDeleteConversation} // Función para borrar
              renameConversation={handleRenameConversation} // Función para renombrar
            />
          )}
          {/* Contenido de la pestaña PDFs */}
          {activeTab === "pdfs" && (
            <PDFSelector
              availablePdfs={availablePdfs} // Lista de PDFs disponibles
              selectedPdf={selectedPdf} // PDF actualmente seleccionado (del hook)
              onSelect={(pdf) => { // Función al seleccionar un PDF
                setSelectedPdf(pdf); // Actualiza el estado del hook
                closeMobilePanels(); // Cierra el panel
              }}
              onUpload={handleUploadPdf} // Función para manejar la subida
            />
          )}
        </div>
      </div>

      {/* Panel derecho (Chat) - Siempre visible en el flujo normal */}
      <div className="chatbot">
        {/* Historial de Mensajes */}
        <MessageHistory messages={messages} chatRef={chatRef} />
        {/* Contenedor del Input */}
        <div className="input-container">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            // Envía al presionar Enter
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
            placeholder="Escribe un mensaje..."
            className="input"
          />
          {/* Botón de Enviar */}
          <button onClick={handleSend} className="enviar" title="Enviar Mensaje">➤</button>
        </div>

        {/* Modal de Ajustes - Se muestra condicionalmente */}
        {showTokenSettings && (
          <div className="settings-modal-backdrop" onClick={() => setShowTokenSettings(false)}>
            {/* Evita que el click en el modal cierre el backdrop */}
            <div className="settings-modal" onClick={(e) => e.stopPropagation()}>
              <h3>Ajustes del Modelo</h3>
              {/* Ajuste Max Output Tokens */}
              <label htmlFor="maxTokens">Máximo Tokens de Salida:</label>
              <input
                id="maxTokens"
                type="number"
                value={maxOutputTokens}
                onChange={(e) => setMaxOutputTokens(Math.max(1, parseInt(e.target.value) || 1))} // Evita 0 o NaN
                min="1" // Mínimo 1 token
              />
              {/* Grupo de Sliders */}
              <div className="slider-group">
                {/* Slider Temperatura */}
                <label>
                  Temperatura: {temperature.toFixed(2)} {/* Muestra 2 decimales */}
                  <input
                     type="range"
                     min="0" max="1" step="0.01"
                     value={temperature}
                     onChange={(e) => setTemperature(parseFloat(e.target.value))}
                     title="Controla la aleatoriedad: más alto = más creativo, más bajo = más determinista"
                  />
                </label>
                {/* Slider Top-p */}
                <label>
                  Top-p: {topP.toFixed(2)} {/* Muestra 2 decimales */}
                  <input
                     type="range"
                     min="0" max="1" step="0.01"
                     value={topP}
                     onChange={(e) => setTopP(parseFloat(e.target.value))}
                     title="Considera solo los tokens cuya probabilidad acumulada suma este valor"
                  />
                </label>
              </div>
              {/* Botón AutoRead (Voz) */}
              <button onClick={() => setAutoRead(!autoRead)} title={autoRead ? "Desactivar lectura en voz alta" : "Activar lectura en voz alta"}>
                {autoRead ? "🔊 Lectura en Voz Activada" : "🔇 Lectura en Voz Desactivada"}
              </button>
              {/* Botón Cerrar Modal */}
              <button onClick={() => setShowTokenSettings(false)} className="close-settings">
                Cerrar Ajustes
              </button>
            </div>
          </div>
        )}
      </div> {/* Fin del div.chatbot */}
    </div> // Fin del div.chatbot-container
  );
};

export default Chatbot; // Exporta el componente
// --- FIN Chatbot.js ---