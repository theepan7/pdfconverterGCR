const mergeInput = document.getElementById('merge-upload');
const maxSize = 5 * 1024 * 1024; // 5MB per file

mergeInput.addEventListener('change', function () {
  const files = mergeInput.files;
  for (const file of files) {
    if (file.size > maxSize) {
      alert(`⚠️ File "${file.name}" exceeds 5MB limit.`);
      mergeInput.value = ''; // Clear all selected files
      break;
    }
  }
});

document.getElementById('mergeForm').addEventListener('submit', async function (event) {
  event.preventDefault();

  const formData = new FormData(this);
  const loading = document.getElementById('mergeLoadingIndicator');

  if (loading) loading.classList.remove('hidden');

  try {
    const response = await fetch('https://your-cloud-url/merge', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Merge failed: ${response.status} - ${errorText}`);
    }

    const blob = await response.blob();
    if (blob.size === 0) throw new Error('Received an empty file. Merge may have failed.');

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'merged.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    alert(error.message);
    console.error('Merge error:', error);
  } finally {
    if (loading) loading.classList.add('hidden');
  }
});
