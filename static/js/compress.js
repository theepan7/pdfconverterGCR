document.getElementById('compressForm').addEventListener('submit', async function (event) {
  event.preventDefault();

  const formData = new FormData(this);
  const loading = document.getElementById('compressLoadingIndicator'); // optional spinner

  if (loading) loading.classList.remove('hidden'); // show loading

  try {
    console.log('Uploading file for compression...');
    
    const response = await fetch('https://pdfcompress-1097766937022.europe-west1.run.app/compress', {
      method: 'POST',
      body: formData,
    });

    console.log('Response status:', response.status);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Compression failed: ${response.status} - ${errorText}`);
    }

    const blob = await response.blob();
    console.log('Received blob:', blob);
    console.log('Blob size:', blob.size);

    if (blob.size === 0) {
      throw new Error('Received an empty file. Compression may have failed.');
    }

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'compressed.pdf';
    document.body.appendChild(a);

    try {
      a.click(); // Try to trigger download
      console.log('Download triggered.');
    } catch (clickError) {
      console.warn('a.click() failed, using fallback window.open');
      window.open(url, '_blank'); // fallback
    }

    a.remove();
    window.URL.revokeObjectURL(url);

  } catch (error) {
    alert(error.message);
    console.error('Error during compression:', error);
  } finally {
    if (loading) loading.classList.add('hidden'); // hide loading
  }
});
