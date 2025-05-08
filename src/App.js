// App.js
import React from 'react';
import LoginForm from './components/LoginForms';
import RegisterForm from './components/RegisterForm';
import Chatbot from './components/Chatbot';
import './App.css';
import logo from "./logo.png"; // Asegúrate de tener un logo en la ruta correcta
//nada

function App() {
  const [isLoggedIn, setIsLoggedIn] = React.useState(!!localStorage.getItem("userId"));
  const [showRegister, setShowRegister] = React.useState(false);

  const handleLoginSuccess = () => {
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    localStorage.removeItem("userId");
    setIsLoggedIn(false);
  };

  return (
    <div className="App">
      {/* Logo que rebota */}
      <img
        src={logo} // Reemplaza con la ruta de tu logo
        alt="Logo"
        className="rebote"
      />

      {isLoggedIn ? (
        <Chatbot onLogout={handleLogout} />
      ) : (
        <div className="auth-container">
          {showRegister ? (
            <RegisterForm onRegister={() => setShowRegister(false)} onSwitchToLogin={() => setShowRegister(false)} />
          ) : (
            <LoginForm onLogin={handleLoginSuccess} onSwitchToRegister={() => setShowRegister(true)} />
          )}

          <button className="toggle-auth-btn" onClick={() => setShowRegister(!showRegister)}>
            {showRegister ? "Ya tengo cuenta" : "Crear cuenta nueva"}
          </button>
        </div>
      )}
    </div>
  );
}

export default App;