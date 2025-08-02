document.getElementById('compressForm').addEventListener('submit', async function(event) {
  event.preventDefault();
  const formData = new FormData(this);

  try {
    console.log('Uploading file for compression...');
    const response = await fetch('https://pdfcompress-1097766937022.europe-west1.run.app/compress', {
      method: 'POST',
      body: formData,
    });

    console.log('Response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Compression failed: ${response.status} ${errorText}`);
    }

    const blob = await response.blob();
    console.log('Received blob:', blob);

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'compressed.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

  } catch (error) {
    alert(error.message);
    console.error('Error:', error);
  }
});
