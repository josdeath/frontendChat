import React, { useEffect } from "react";
import Message from "./Message";

const MessageHistory = ({ messages, chatRef }) => {
  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div ref={chatRef} className="message-history">
      {messages.map((msg, index) => (
        <Message key={index} text={msg.text} sender={msg.sender} image={msg.image} />
      ))}
    </div>
  );
};

export default MessageHistory;