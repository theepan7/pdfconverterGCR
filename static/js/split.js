document.getElementById('splitForm').addEventListener('submit', async function(event) {
  event.preventDefault();

  const formData = new FormData(this);
  const startPage = formData.get('start');
  const endPage = formData.get('end');

  if (!startPage || !endPage) {
    alert("Please enter both start and end page numbers.");
    return;
  }

  try {
    const response = await fetch('https://pdfcompress-1097766937022.europe-west1.run.app/split', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) throw new Error('Splitting failed');

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'split.pdf';
    document.body.appendChild(a);
    a.click();
    a.remove();
  } catch (error) {
    alert(error.message);
  }
});
