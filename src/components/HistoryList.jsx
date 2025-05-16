import React, { useState, useEffect, useRef } from "react";
import { Filesystem, Directory, Encoding } from '@capacitor/filesystem';
const HistoryList = ({
  history = [],
  loadConversation,
  deleteConversation,
  currentConversationIndex,
  renameConversation,
}) => {
  const [openMenuIndex, setOpenMenuIndex] = useState(null);
  const menuRefs = useRef([]);

  const [editIndex, setEditIndex] = useState(null);
  const [editValue, setEditValue] = useState("");

  const toggleMenu = (index) => {
    setOpenMenuIndex(openMenuIndex === index ? null : index);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        openMenuIndex !== null &&
        menuRefs.current[openMenuIndex] &&
        !menuRefs.current[openMenuIndex].contains(event.target)
      ) {
        setOpenMenuIndex(null);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [openMenuIndex]);

  const handleDownload = (conversation) => {
    const content = conversation.messages
      .map((msg) => `${msg.sender === "user" ? "👤" : "🤖"}: ${msg.text}`)
      .join("\n");

    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${conversation.name || "conversacion"}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="history-list">
      <ul>
      {history.map((conv, index) => {
  const isActive = index === currentConversationIndex;

  return (
    <li
      key={index}
      className={`history-item ${isActive ? "active" : ""}`}
      onClick={() => loadConversation(index)}
    >
          
          {editIndex === index ? (
          <input
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={() => {
              renameConversation(index, editValue);
              setEditIndex(null);
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                renameConversation(index, editValue);
                setEditIndex(null);
              }
            }}
            autoFocus
            className="rename-input"
          />
        ) : (
          <span className="history-name">
            {(conv.name?.length || 0) > 15
              ? conv.name.substring(0, 12) + "..."
              : conv.name || "Sin título"}
          </span>
        )}


      <div
        className="menu-wrapper"
        onClick={(e) => e.stopPropagation()}
        ref={(el) => (menuRefs.current[index] = el)}
      >
        <button
          className="menu-button"
          onClick={() => toggleMenu(index)}
        >
          ⋮
        </button>

        {openMenuIndex === index && (
          <div className="menu-popup">
            <button
              className="download-option"
              onClick={() => {
                handleDownload(conv);
                setOpenMenuIndex(null);
              }}
            >
              Descargar
            </button>

            <button
              className="delete-option"
              onClick={() => {
                deleteConversation(index);
                setOpenMenuIndex(null);
              }}
            >
              Eliminar
            </button>

            <button
              className="edit-option"
              onClick={() => {
                setEditIndex(index);
                setEditValue(conv.name || "");
                setOpenMenuIndex(null);
              }}
            >
              Renombrar
            </button>

          </div>
        )}
      </div>
    </li>
  );
})}

      </ul>
    </div>
  );
};

export default HistoryList;