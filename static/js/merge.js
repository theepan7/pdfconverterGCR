document.getElementById('mergeForm').addEventListener('submit', async function (event) {
  event.preventDefault();

  const formData = new FormData();
  const files = document.querySelector('input[name="files"]').files;

  if (files.length === 0) {
    alert('Please select at least two PDF files to merge.');
    return;
  }

  for (const file of files) {
    formData.append('files', file);
  }

  try {
    const response = await fetch('https://pdfcompress-1097766937022.europe-west1.run.app/merge', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error('Merging failed. Please try again.');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'merged.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (error) {
    alert(error.message);
  }
});
