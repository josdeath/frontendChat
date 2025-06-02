import React, { useState } from "react";
import botAvatar from "../assests/bot-avatar.png";
import userAvatar from "../assests/user-avatar.png";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";

const Message = ({ text, sender, image }) => {
  const avatar = sender === "bot" ? botAvatar : userAvatar;
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className={`message ${sender}`}>
      <div className="message-header">
        <img src={avatar} alt={sender} className="avatar" />
        {sender === "bot" && (
          <button className="copy-button" onClick={handleCopy} title="Copiar mensaje">
            {copied ? "✅" : "📋"}
          </button>
        )}
      </div>
      <div className="message-content">
        {image && <p>Archivo enviado</p>}
        {sender === "bot" ? (
          <ReactMarkdown rehypePlugins={[rehypeRaw]}>{text}</ReactMarkdown>
        ) : (
          <p>{text}</p>
        )}
      </div>
    </div>
  );
};

export default Message;
