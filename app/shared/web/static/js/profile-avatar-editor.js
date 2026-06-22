(function createAvatarEditor(root, factory) {
  const api = factory(root);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root?.document) {
    root.SistIonmAvatarEditor = api;
    api.init();
    root.document.addEventListener('sistionm:content-updated', api.init);
  }
})(typeof window !== 'undefined' ? window : undefined, (root) => {
  const FRAME_SIZE = 320;

  function coverScale(width, height, frameSize, zoom = 1) {
    return Math.max(frameSize / width, frameSize / height) * zoom;
  }

  function clampOffset(offset, scaledSize, frameSize) {
    const limit = Math.max(0, (scaledSize - frameSize) / 2);
    return Math.max(-limit, Math.min(limit, offset));
  }

  function init() {
    const form = root.document.getElementById('profileAvatarForm');
    if (!form || form.dataset.ready) return;
    form.dataset.ready = 'true';
    const input = root.document.getElementById('avatar');
    const editor = root.document.getElementById('profileAvatarEditor');
    const canvas = root.document.getElementById('profileAvatarCanvas');
    const zoomInput = root.document.getElementById('profileAvatarZoom');
    const status = root.document.getElementById('profileAvatarStatus');
    const fallback = form.querySelector('[data-avatar-fallback]');
    const context = canvas?.getContext('2d');
    if (!input || !editor || !canvas || !zoomInput || !context) return;
    if (fallback) fallback.hidden = true;

    const state = { image: null, zoom: 1, offsetX: 0, offsetY: 0, dragging: false, x: 0, y: 0, prepared: false };

    function draw(targetCanvas = canvas, size = FRAME_SIZE) {
      if (!state.image) return;
      const targetContext = targetCanvas.getContext('2d');
      const ratio = size / FRAME_SIZE;
      const scale = coverScale(state.image.width, state.image.height, FRAME_SIZE, state.zoom);
      const width = state.image.width * scale;
      const height = state.image.height * scale;
      targetContext.clearRect(0, 0, size, size);
      targetContext.drawImage(
        state.image,
        ((FRAME_SIZE - width) / 2 + state.offsetX) * ratio,
        ((FRAME_SIZE - height) / 2 + state.offsetY) * ratio,
        width * ratio,
        height * ratio,
      );
    }

    function constrain() {
      const scale = coverScale(state.image.width, state.image.height, FRAME_SIZE, state.zoom);
      state.offsetX = clampOffset(state.offsetX, state.image.width * scale, FRAME_SIZE);
      state.offsetY = clampOffset(state.offsetY, state.image.height * scale, FRAME_SIZE);
    }

    function cancel() {
      input.value = '';
      state.image = null;
      state.prepared = false;
      editor.hidden = true;
      status.textContent = '';
      input.focus();
    }

    input.addEventListener('change', () => {
      const file = input.files?.[0];
      if (!file) return;
      if (!file.type.startsWith('image/')) { status.textContent = 'Selecione um arquivo de imagem.'; return; }
      const image = new Image();
      const objectUrl = URL.createObjectURL(file);
      image.onload = () => {
        URL.revokeObjectURL(objectUrl);
        Object.assign(state, { image, zoom: 1, offsetX: 0, offsetY: 0, prepared: false });
        zoomInput.value = '1';
        editor.hidden = false;
        status.textContent = 'Ajuste a foto dentro da moldura.';
        draw();
      };
      image.onerror = () => { URL.revokeObjectURL(objectUrl); status.textContent = 'Não foi possível abrir esta imagem.'; };
      image.src = objectUrl;
    });

    zoomInput.addEventListener('input', () => {
      state.zoom = Number(zoomInput.value || 1);
      if (state.image) { constrain(); draw(); }
    });
    canvas.addEventListener('pointerdown', (event) => {
      state.dragging = true; state.x = event.clientX; state.y = event.clientY;
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', (event) => {
      if (!state.dragging || !state.image) return;
      state.offsetX += event.clientX - state.x; state.offsetY += event.clientY - state.y;
      state.x = event.clientX; state.y = event.clientY; constrain(); draw();
    });
    canvas.addEventListener('pointerup', () => { state.dragging = false; });
    form.querySelector('[data-avatar-action="cancel"]')?.addEventListener('click', cancel);
    form.addEventListener('submit', (event) => {
      if (!state.image || state.prepared) return;
      event.preventDefault();
      const output = root.document.createElement('canvas'); output.width = 512; output.height = 512; draw(output, 512);
      output.toBlob((blob) => {
        if (!blob) { status.textContent = 'Não foi possível preparar a imagem.'; return; }
        const transfer = new DataTransfer();
        transfer.items.add(new File([blob], 'avatar-cropped.jpg', { type: 'image/jpeg' }));
        input.files = transfer.files; state.prepared = true; status.textContent = 'Salvando foto…'; form.requestSubmit();
      }, 'image/jpeg', 0.9);
    });
  }

  return { clampOffset, coverScale, init };
});
