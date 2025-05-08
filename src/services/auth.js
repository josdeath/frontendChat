export const login = async (username, password) => {
  const res = await fetch("https://backnode-60g0.onrender.com/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ username, password })
  });

  const data = await res.json();
  if (data.success) {
    localStorage.setItem("userId", data.userId);
    return true;
  }
  return false;
};

export const register = async (username, password) => {
  const res = await fetch("https://backnode-60g0.onrender.com/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ username, password })
  });

  const data = await res.json();
  return data;
};

// 💥 Aquí estaba faltando:
export const logout = () => {
  localStorage.removeItem("userId");
  window.location.reload(); 
};
