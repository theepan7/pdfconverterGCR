document.getElementById('compressForm').addEventListener('submit', async function(event) {
  event.preventDefault();
  const formData = new FormData(this);

  try {
    const response = await fetch('https://pdfcompress-1097766937022.europe-west1.run.app/compress', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) throw new Error('Compression failed');

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'compressed.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (error) {
    alert(error.message);
  }
});
