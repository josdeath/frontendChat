export const uploadPdf = async (file) => {
    const userId = localStorage.getItem("userId");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("userId", userId);
  
    const res = await fetch("https://backnode-60g0.onrender.com/upload_pdf", {
      method: "POST",
      body: formData
    });
  
    return await res.json();
  };
  
  export const fetchPdfs = async () => {
    const userId = localStorage.getItem("userId");
    const res = await fetch(`https://backnode-60g0.onrender.com/get_pdfs?userId=${userId}`);
    return await res.json();
  };
  