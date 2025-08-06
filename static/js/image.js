document.getElementById('imageForm').addEventListener('submit', async function (event) {
  event.preventDefault();

  const fileInput = document.getElementById('image-upload'); // Your input[type="file"] ID
  const maxSize = 5 * 1024 * 1024; // 5MB

  // ✅ Check all files are within size limit
  for (const file of fileInput.files) {
    if (file.size > maxSize) {
      alert(`⚠️ File "${file.name}" is too large. Max allowed size is 5MB.`);
      return; // stop submission
    }
  }

  const formData = new FormData(this);
  const loading = document.getElementById('imageLoadingIndicator'); // Optional spinner

  if (loading) loading.classList.remove('hidden'); // Show spinner

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
