import { useEffect, useState } from "react";
import { fetchPdfs } from "../services/pdfService";

export default function PdfList() {
  const [pdfs, setPdfs] = useState([]);

  useEffect(() => {
    loadPdfs();
  }, []);

  const loadPdfs = async () => {
    const data = await fetchPdfs();
    setPdfs(data);
  };

  return (
    <div>
      <h3>Mis PDFs</h3>
      <ul>
        {pdfs.map((pdf) => (
          <li key={pdf.id}>
            {pdf.originalname} (subido el {new Date(pdf.uploaded_at).toLocaleDateString()})
          </li>
        ))}
      </ul>
    </div>
  );
}
