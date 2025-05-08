import CONFIG from "../config";

const useGemini2_0 = () => {
  const apiKey = CONFIG.GEMINI_API_2FLASH;

  const estimateTokens = (text) => Math.ceil(text.length / 4);

  const generateContent = async ({ prompt, messages = [], maxOutputTokens = 256, temperature= 0.7, topP=1 }) => {
    try {
      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${apiKey}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents: messages.length > 0
              ? [{ parts: messages.map(msg => ({ text: msg.content })) }]
              : [{ parts: [{ text: prompt }] }],
            generationConfig: { 
              maxOutputTokens,
              temperature,
              topP
            },
            
          }),
        }
      );

      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message || `Status: ${response.status}`);

      return data.candidates[0]?.content?.parts[0]?.text.trim() || "⚠️ Sin respuesta del modelo.";
    } catch (error) {
      console.error("⚠️ Error en generateContent Gemini 2.0:", error);
      return `❌ Error con Gemini 2.0: ${error.message}`;
    }
  };

  const processFile = async ({ file }) => {
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("https://backnode-60g0.onrender.com/upload", {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: result?.error || "Error desconocido al subir el archivo.",
        };
      }

      return {
        success: true,
        fileId: result.fileId,
        fileName: result.fileName,
        summary: result.summary,
      };
    } catch (error) {
      console.error("❌ Error al subir archivo PDF:", error);
      return {
        success: false,
        error: error.message || "Error inesperado al subir el archivo.",
      };
    }
  };

  return { generateContent, processFile, estimateTokens };
};

export default useGemini2_0;