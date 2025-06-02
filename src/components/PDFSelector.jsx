import React from "react";

const PDFSelector = ({ availablePdfs, selectedPdf, onSelect, onUpload }) => {
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onUpload(file); // sube el PDF
    }
  };

  return (
    <div className="pdf-selector">
      <h3>📄 Tus PDFs</h3>
      <p style={{color:"white"}}>Selecciona un PDF para usarlo en la conversación:</p>
      <ul>
        {availablePdfs.map((pdf, index) => (
          <li
            key={index}
            className={selectedPdf?.filename === pdf.filename ? "selected" : ""}
            onClick={() => onSelect(pdf)} // ✅ AQUÍ ES DONDE SE LLAMA setSelectedPdf()
            style={{
              cursor: "pointer",
              fontWeight: selectedPdf?.filename === pdf.filename ? "bold" : "normal"
            }}
          >
            {pdf.originalname}
          </li>
        ))}
      </ul>

      <input
        type="file"
        accept="application/pdf"
        onChange={handleFileChange}
        style={{ marginTop: "10px" }}
      />
    </div>
  );
};

export default PDFSelector;
