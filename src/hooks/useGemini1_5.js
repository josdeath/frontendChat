import CONFIG from "../config";

const useGemini1_5 = () => {
  const apiKey = CONFIG.GEMINI_API_KEY;

  const estimateTokens = (text) => Math.ceil(text.length / 4); // Estimación simple

  const generateContent = async ({
    prompt,
    maxOutputTokens = 256,
    temperature = 0.7,
    topP = 1,
  }) => {
    try {
      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }], // Cambié para el nuevo formato de request
            generationConfig: {
              maxOutputTokens,
              temperature,
              topP,
            },
          }),
        }
      );

      if (!response.ok) throw new Error(`Error: ${response.status}`);
      const data = await response.json();
      return (
        data.candidates[0]?.content?.parts[0]?.text.trim() || "No response"
      );
    } catch (error) {
      console.error("Error en generateContent:", error);
      return "⚠️ Error de conexión con IA.";
    }
  };

  const processFile = async ({
    base64,
    mimeType,
    extraText = "",
    maxOutputTokens = 256,
    temperature = 0.7,
    topP = 1,
  }) => {
    try {
      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents: [
              {
                parts: [
                  { inline_data: { mime_type: mimeType, data: base64 } },
                  { text: extraText },
                ],
              },
            ],
            generationConfig: {
              maxOutputTokens,
              temperature,
              topP,
            },
          }),
        }
      );

      if (!response.ok) throw new Error(`Error: ${response.status}`);
      const data = await response.json();
      return (
        data.candidates[0]?.content?.parts[0]?.text ||
        "No se pudo analizar el archivo."
      );
    } catch (error) {
      console.error("Error en processFile:", error);
      return "⚠️ Error al procesar el archivo.";
    }
  };

  return { generateContent, processFile, estimateTokens };
};

export default useGemini1_5;
