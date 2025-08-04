document.getElementById('imageForm').addEventListener('submit', async function (event) {
  event.preventDefault();

  const formData = new FormData(this);
  const loading = document.getElementById('imageLoadingIndicator'); // Optional spinner element

  if (loading) loading.classList.remove('hidden'); // Show spinner

  try {
    const response = await fetch('https://your-deployed-domain/image-to-pdf', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Image-to-PDF failed: ${response.status} - ${errorText}`);
    }

    const blob = await response.blob();
    if (blob.size === 0) {
      throw new Error('Received an empty file. Conversion may have failed.');
    }

    // Trigger file download
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'converted.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    alert(error.message);
    console.error('Error during image-to-PDF:', error);
  } finally {
    if (loading) loading.classList.add('hidden'); // Hide spinner
  }
});
