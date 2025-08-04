document.getElementById('imageForm').addEventListener('submit', async function (event) {
  event.preventDefault();

  const formData = new FormData(this);
  const loading = document.getElementById('imageLoadingIndicator');
  const submitBtn = this.querySelector('button[type="submit"]');

  if (loading) loading.classList.remove('hidden');
  if (submitBtn) submitBtn.disabled = true;

  try {
    const response = await fetch('https://pdfcompress-1097766937022.europe-west1.run.app/image-to-pdf', {
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

    // Trigger download
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
    if (loading) loading.classList.add('hidden');
    if (submitBtn) submitBtn.disabled = false;
  }
});

// Update file label
document.getElementById('image-upload').addEventListener('change', function () {
  const file = this.files[0];
  const label = document.getElementById('file-label');
  if (label) {
    label.textContent = file ? file.name : 'Click to select an image file';
  }
});
