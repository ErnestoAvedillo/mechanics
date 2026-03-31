(function () {
  const zones = document.querySelectorAll('.dropzone');

  function renderPreview(input, zone) {
    const preview = zone.querySelector('.dropzone-preview');
    const hint = zone.querySelector('.dropzone-hint');
    const title = zone.querySelector('.dropzone-title');
    const file = input.files && input.files[0];

    if (!file || !file.type.startsWith('image/')) {
      preview.hidden = true;
      preview.removeAttribute('src');
      if (title) {
        title.hidden = false;
      }
      hint.textContent = 'Arrastra una imagen aqui o haz clic para seleccionar';
      return;
    }

    const reader = new FileReader();
    reader.onload = function (event) {
      preview.src = event.target.result;
      preview.hidden = false;
      if (title) {
        title.hidden = true;
      }
      hint.textContent = file.name;
    };
    reader.readAsDataURL(file);
  }

  zones.forEach((zone) => {
    const input = document.getElementById(zone.dataset.target);
    if (!input) return;

    zone.addEventListener('click', function () {
      input.click();
    });

    input.addEventListener('change', function () {
      renderPreview(input, zone);
    });

    zone.addEventListener('dragover', function (event) {
      event.preventDefault();
      zone.classList.add('is-over');
    });

    zone.addEventListener('dragleave', function () {
      zone.classList.remove('is-over');
    });

    zone.addEventListener('drop', function (event) {
      event.preventDefault();
      zone.classList.remove('is-over');

      const dt = event.dataTransfer;
      if (!dt || !dt.files || dt.files.length === 0) return;

      input.files = dt.files;
      renderPreview(input, zone);
    });
  });
})();
