const compressInput = document.getElementById('pdf-upload');
const maxSize = 5 * 1024 * 1024; // 5MB

compressInput.addEventListener('change', function () {
  const files = compressInput.files;

  for (const file of files) {
    if (file.size > maxSize) {
      alert(`⚠️ File "${file.name}" is too large. Max allowed size is 5MB.`);
      compressInput.value = ''; // Clear all files
      break;
    }
  }
});

document.getElementById('compressForm').addEventListener('submit', async function (event) {
  event.preventDefault();

  const file = compressInput.files[0];
  if (!file) {
    alert('Please select a PDF file.');
    return;
  }

  const formData = new FormData(this);
  const loading = document.getElementById('compressLoadingIndicator'); // Optional spinner element

  if (loading) loading.classList.remove('hidden'); // Show spinner

  try {
    const response = await fetch('https://pdfcompress-1097766937022.europe-west1.run.app/compress', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Compression failed: ${response.status} - ${errorText}`);
    }

    const blob = await response.blob();
    if (blob.size === 0) {
      throw new Error('Received an empty file. Compression may have failed.');
    }

    // Trigger file download
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
    console.error('Error during compression:', error);
  } finally {
    if (loading) loading.classList.add('hidden'); // Hide spinner
  }
});
