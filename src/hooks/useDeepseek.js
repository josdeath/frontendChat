import CONFIG from "../config";

const useDeepseek = () => {
  // Asegúrate de que estos valores están configurados correctamente en tu archivo CONFIG
  const apiKey = CONFIG.DEEPSEEK; 
  const referer = CONFIG.OPENROUTER_REFERER  ;
  const siteTitle = CONFIG.OPENROUTER_TITLE || "Mi Chat App";

  const estimateTokens = (text) => Math.ceil(text.length / 4);

  // Función para generar contenido utilizando Deepseek
  const generateContent = async ({ messages = [], maxOutputTokens = 1024, temperature= 0.7, topP=1 }) => {
    try {
      // Verificar si la clave API está definida
      if (!apiKey) {
        console.warn("❗ No hay clave API definida para Deepseek.");
        return "❌ No se encontró la clave API de Deepseek. Verifica tu configuración.";
      }

      // Realizar la solicitud a la API de Deepseek
      const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${apiKey}`,
          "HTTP-Referer": "https://itia.onrender.com/",
          "X-Title": siteTitle,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          model: "deepseek/deepseek-chat-v3-0324:free",  // Nombre del modelo
          messages: messages.map((msg) => ({
            role: msg.role,
            content: msg.content,
          })),
          max_tokens: maxOutputTokens, // Establece el máximo de tokens para la respuesta
          temperature: temperature,
          topP:topP
        }),
      });

      // Procesar la respuesta de la API
      const data = await response.json();

      if (!response.ok) {
        console.error("❌ Error en respuesta Deepseek:", data);
        throw new Error(data.error?.message || `Status: ${response.status}`);
      }

      const content = data?.choices?.[0]?.message?.content;

      // Si no se recibe contenido de la API, mostramos una advertencia
      if (!content || content.trim() === "") {
        console.warn("⚠️ Deepseek respondió sin contenido:", JSON.stringify(data, null, 2));
        return "⚠️ Deepseek respondió, pero no envió ningún texto.";
      }

      return content.trim();  // Devolvemos el texto generado por Deepseek
    } catch (error) {
      // Manejo de errores
      if (error.message?.toLowerCase().includes("insufficient balance")) {
        return "❌ No tienes saldo suficiente en tu cuenta de OpenRouter para usar Deepseek.";
      }
      console.error("❌ Error al usar Deepseek:", error);
      return `⚠️ Error al usar Deepseek: ${error.message}`;
    }
  };

  // Función para procesar el archivo (subir PDF y procesarlo)
  const processFile = async ({ file }) => {
    const formData = new FormData();
    formData.append("file", file); // Agregar el archivo a los datos del formulario

    try {
      // Subir el archivo al servidor
      const response = await fetch("http://localhost:5001/upload", {
        method: "POST",
        body: formData,
      });

      // Procesar la respuesta del servidor
      const result = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: result?.error || "Error desconocido al subir el archivo.",
        };
      }

      return {
        success: true,
        fileId: result.fileId,   // ID del archivo procesado
        fileName: result.fileName, // Nombre del archivo
        summary: result.summary,  // Resumen del archivo (probablemente texto extraído)
      };
    } catch (error) {
      console.error("❌ Error al subir archivo PDF:", error);
      return {
        success: false,
        error: error.message || "Error inesperado al subir el archivo.",
      };
    }
  };

  return { generateContent, estimateTokens, processFile };
};

export default useDeepseek;
