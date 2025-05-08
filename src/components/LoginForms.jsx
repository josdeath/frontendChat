import { useState } from "react";
import { login } from "../services/auth";

export default function LoginForm({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    const success = await login(username, password);
    if (success) {
      onLogin(); // Esto cambia el estado en App
    } else {
      alert("Credenciales incorrectas");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="login-form">
      <h2 style={{ color: "white" }}>Iniciar Sesión</h2>
      <input value={username} onChange={(e) => setUsername(e.target.value)} type="text" placeholder="Usuario" />
      <input value={password} type="password" onChange={(e) => setPassword(e.target.value)} placeholder="Contraseña" />
      <button type="submit">Entrar</button>
    </form>
  );
}
