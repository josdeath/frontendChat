// src/components/SpeechToText.js
import React, { useState, useEffect, useRef } from "react";
import { Capacitor } from '@capacitor/core';
import { SpeechRecognition } from '@capacitor-community/speech-recognition';
import "./SpeechToText.css";

// console.log("SpeechToText.js - VERSION CORRECTA CARGADA - Fecha: " + new Date().toISOString());
// ^^^ Descomenta esto o usa alert para la verificación inicial si es necesario, pero
// es mejor quitarlo o usar console.log para pruebas repetidas.
// Un alert en cada carga de componente puede ser molesto.

const SpeechToText = ({ onTranscription }) => {
  // Usaremos console.log para la verificación de carga de este componente si es necesario más adelante
  // useEffect(() => {
  //   console.log("SpeechToText Component Montado/Actualizado - Fecha: " + new Date().toISOString());
  // }, []);


  const [listening, setListening] = useState(false);
  const webRecognitionRef = useRef(null);

  useEffect(() => {
    if (!Capacitor.isNativePlatform()) {
      if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const WebSpeechRecognitionAPI = window.webkitSpeechRecognition || window.SpeechRecognition;
        const recognitionInstance = new WebSpeechRecognitionAPI();
        recognitionInstance.lang = "es-ES";
        recognitionInstance.continuous = false;
        recognitionInstance.interimResults = false;

        recognitionInstance.onresult = (event) => {
          const transcript = event.results[0][0].transcript;
          setListening(false);
          if (onTranscription) onTranscription(transcript);
        };
        recognitionInstance.onerror = (event) => {
          console.error("Error de la API Web Speech:", event.error);
          setListening(false);
          if (event.error === 'no-speech') alert("No se detectó voz. Inténtalo de nuevo.");
          else if (event.error === 'audio-capture') alert("Error al capturar audio. Asegúrate de que el micrófono funciona y tiene permisos.");
          else if (event.error === 'not-allowed') alert("Permiso para acceder al micrófono denegado en el navegador.");
          else alert(`Error de reconocimiento de voz web: ${event.error}`);
        };
        recognitionInstance.onend = () => { if (listening) setListening(false); };
        webRecognitionRef.current = recognitionInstance;
      } else {
        console.warn("La API Web Speech no está soportada en este navegador.");
      }
    }
  }, [onTranscription, listening]);

  const handleStartStopListening = async () => {
    if (listening) {
      try {
        if (Capacitor.isNativePlatform()) await SpeechRecognition.stop();
        else if (webRecognitionRef.current) webRecognitionRef.current.stop();
      } catch (error) { console.error("Error al detener la escucha:", error); }
      setListening(false);
      return;
    }

    setListening(true);

    if (Capacitor.isNativePlatform()) {
      try {
        const availability = await SpeechRecognition.available();
        if (!availability.available) {
          alert("El reconocimiento de voz no está disponible en este dispositivo.");
          setListening(false);
          return;
        }

        // --- PUNTO CRÍTICO DE CORRECCIÓN ---
        const permissionResult = await SpeechRecognition.requestPermissions(); // Método plural
        
        // Añade este console.log para ver la estructura del objeto permissionResult
        console.log("Resultado de SpeechRecognition.requestPermissions():", JSON.stringify(permissionResult, null, 2));
        // También podrías poner un alert aquí temporalmente para forzar la revisión de Logcat:
        // alert("Revisa Logcat para ver la estructura de permissionResult");

        // ASÍ ES COMO PROBABLEMENTE DEBAS VERIFICAR EL PERMISO:
        // La clave 'speechRecognition' es común para este plugin.
        // Si el plugin devuelve otra cosa, ajústalo según el console.log.
        if (permissionResult.speechRecognition !== 'granted') { 
          alert(`Permiso de micrófono denegado. Estado: ${permissionResult.speechRecognition}`);
          setListening(false);
          return;
        }
        // --- FIN DEL PUNTO CRÍTICO ---
        
        SpeechRecognition.removeAllListeners();
        SpeechRecognition.addListener('partialResults', (data) => {
          if (data.matches && data.matches.length > 0) {
            const transcript = data.matches[data.matches.length - 1];
            if (transcript) {
              SpeechRecognition.stop().catch(e => console.warn("Advertencia: Error menor al detener STT después del resultado:", e));
              setListening(false);
              if (onTranscription) onTranscription(transcript);
            }
          }
        });
        
        await SpeechRecognition.start({
          language: "es-ES",
          maxResults: 1,
          partialResults: true,
          popup: false,
        });

      } catch (error) {
        console.error("Error de Reconocimiento de Voz Nativo:", error);
        alert(`Error Nativo STT: ${error.message || JSON.stringify(error)}`);
        setListening(false);
        SpeechRecognition.stop().catch(e => console.warn("Advertencia: Error menor al detener STT después de un error de inicio:", e));
      }
    } else { // Web Browser
      if (webRecognitionRef.current) {
        try { webRecognitionRef.current.start(); }
        catch (error) {
          console.error("Error al iniciar la API Web Speech:", error);
          setListening(false);
          if (error.name === 'InvalidStateError') alert("Error al iniciar el reconocimiento de voz web. Inténtalo de nuevo.");
          else alert(`Error de reconocimiento de voz web: ${error.name}`);
        }
      } else {
        alert("El reconocimiento de voz web no está disponible o inicializado en este navegador.");
        setListening(false);
      }
    }
  };

  return (
    <button 
      onClick={handleStartStopListening} 
      className={`record-btn ${listening ? "recording" : ""}`}
      title={listening ? "Detener grabación" : "Grabar voz"}
    >
      {listening ? "🔴 " : "⏺️"}
    </button>
  );
};

export default SpeechToText;