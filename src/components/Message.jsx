import React from "react";
import botAvatar from "../assests/bot-avatar.png";
import userAvatar from "../assests/user-avatar.png";
import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";

const Message = ({ text, sender, image }) => {
  const avatar = sender === "bot" ? botAvatar : userAvatar;

  return (
    <div className={`message ${sender}`}>
      <img src={avatar} alt={sender} className="avatar" /> &emsp;
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
