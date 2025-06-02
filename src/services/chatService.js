const API = "https://backnode-60g0.onrender.com";



export const saveConversation = async (userId, name, messages) => {
  const res = await fetch("https://backnode-60g0.onrender.com/save_conversation", {
    method: "POST",
    headers: {
      "Content-Type": "application/json", // 
    },
    body: JSON.stringify({
      userId: parseInt(userId),
      name: name || "Conversación",
      messages,
    }),
  });

  return res.json();
};
  
export const updateConversation = async (id, messages) => {
  const res = await fetch(`${API}/update_conversation`, { // <-- ruta correcta
    method: "POST",                                         // <-- método correcto
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ id, messages }),
  });

  return res.json();
};

export const getConversations = async (userId) => {
  const res = await fetch(`https://backnode-60g0.onrender.com/get_conversations?userId=${userId}`);
  return res.json();
};

export async function deleteConversation(id) {
  const response = await fetch(`${API}/delete_conversation`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ id }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Error del servidor: ${errorText}`);
  }

  return await response.json();
}