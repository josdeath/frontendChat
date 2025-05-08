import React from "react";

const PDFViewer = ({ fileUrl }) => {
  return (
    <iframe
      src={fileUrl}
      title="Visor PDF"
      width="100%"
      height="400px"
      style={{ border: "1px solid #ccc", marginTop: "10px" }}
    />
  );
};

export default PDFViewer;
