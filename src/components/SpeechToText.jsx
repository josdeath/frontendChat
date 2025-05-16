import React, { useState } from "react";
import "./SpeechToText.css";
const SpeechToText = ({ onTranscription }) => {
  const [listening, setListening] = useState(false);
  const recognition = new window.webkitSpeechRecognition(); // O SpeechRecognition según navegador

  recognition.lang = "es-ES";
  recognition.continuous = false;
  recognition.interimResults = false;

  const startListening = () => {
    setListening(true);
    recognition.start();

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setListening(false);
      onTranscription(transcript);
    };

    recognition.onerror = (err) => {
      console.error("Error:", err);
      setListening(false);
    };
  };

  return (
    <button onClick={startListening}  className={`record-btn ${listening ? "recording" : ""}`}>
      {listening ? "🔴" : "⏺️"}
    </button>
  );
};

export default SpeechToText;