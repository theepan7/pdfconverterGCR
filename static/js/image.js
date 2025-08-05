document.getElementById('imageForm').addEventListener('submit', async function (event) {
  event.preventDefault();

  const formData = new FormData(this);
  const loading = document.getElementById('imageLoadingIndicator');
  const submitBtn = this.querySelector('button[type="submit"]');

  if (loading) loading.classList.remove('hidden');
  if (submitBtn) submitBtn.disabled = true;

  try {
    const response = await fetch('/image', {
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

// Update file label for multiple files
document.getElementById('image-upload').addEventListener('change', function () {
  const files = this.files;
  const label = document.getElementById('file-label');
  if (label) {
    if (files.length === 0) {
      label.textContent = 'Click to select image files';
    } else if (files.length === 1) {
      label.textContent = files[0].name;
    } else {
      label.textContent = `${files.length} files selected`;
    }
  }
});
