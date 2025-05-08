import { uploadPdf } from "../services/pdfService";

export default function UploadForm({ onUploaded }) {
  const handleChange = async (e) => {
    const file = e.target.files[0];
    if (file) {
      const result = await uploadPdf(file);
      if (result.success) {
        alert("PDF subido correctamente");
        onUploaded(); // refresca la lista
      }
    }
  };

  return (
    <div>
      <h3>Subir PDF</h3>
      <input type="file" accept="application/pdf" onChange={handleChange} />
    </div>
  );
}
