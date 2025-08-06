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

document.getElementById('splitForm').addEventListener('submit', async function (event) {
  event.preventDefault();

  const formData = new FormData(this);
  const loading = document.getElementById('splitLoadingIndicator');

  if (loading) loading.classList.remove('hidden');

  try {
    const response = await fetch('https://your-cloud-url/split', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Split failed: ${response.status} - ${errorText}`);
    }

    const blob = await response.blob();
    if (blob.size === 0) throw new Error('Received an empty file. Split may have failed.');

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'split.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    alert(error.message);
    console.error('Split error:', error);
  } finally {
    if (loading) loading.classList.add('hidden');
  }
});
