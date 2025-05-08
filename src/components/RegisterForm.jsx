import { useState } from "react";
import { register } from "../services/auth";

export default function RegisterForm({ onRegister }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    const data = await register(username, password);
    if (data.success) {
      alert("Registro exitoso, ahora inicia sesión.");
      onRegister(); // o redirige a login
    } else {
      alert(data.error || "Error al registrar");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2 style={{ color: "white" }}>Registrarse</h2>
      <input value={username} onChange={(e) => setUsername(e.target.value)} type="text" placeholder="Usuario" />
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Contraseña" />
      <button type="submit">Crear cuenta</button>
    </form>
  );
}
