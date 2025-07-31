document.getElementById('compressForm').addEventListener('submit', async function (e) {
  e.preventDefault();

  const fileInput = document.querySelector('input[name="file"]');
  const file = fileInput.files[0];

  if (!file || file.type !== 'application/pdf') {
    alert("Please upload a valid PDF file.");
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch('https://pdfcompress-1097766937022.europe-west1.run.app/compress', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) throw new Error("Compression failed");

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'compressed.pdf';
    a.click();
  } catch (error) {
    alert('Error: ' + error.message);
  }
});
