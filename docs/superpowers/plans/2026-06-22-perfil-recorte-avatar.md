# Profile Avatar Crop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir enquadrar, arrastar e ampliar a foto antes de salvar um avatar JPEG 512 × 512 seguro.

**Architecture:** Um editor Canvas sem dependências produz o recorte no navegador. Um serviço Python com Pillow valida, corrige orientação, remove metadados e normaliza o arquivo mesmo no fallback sem JavaScript.

**Tech Stack:** JavaScript Canvas/Pointer Events, Pillow 12.2.0, FastAPI, pytest.

## Global Constraints

- JPEG, PNG, WebP e GIF; máximo 10 MiB.
- Resultado sempre JPEG RGB 512 × 512.
- Arquivo inválido nunca substitui avatar atual.
- Inicializador funciona após `sistionm:content-updated`.

---

### Task 1: Processamento seguro no servidor

**Files:**
- Create: `app/features/profile_avatar/__init__.py`
- Create: `app/features/profile_avatar/service.py`
- Create: `tests/features/test_profile_avatar_service.py`
- Modify: `app/main.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `process_avatar(content: bytes) -> bytes`, `AvatarValidationError`.

- [ ] **Step 1: Escrever testes RED**

```python
result = process_avatar(portrait_png)
image = Image.open(BytesIO(result))
assert image.size == (512, 512)
assert image.mode == "RGB"
assert image.format == "JPEG"
```

Testar paisagem, arquivo corrompido e limite.

- [ ] **Step 2: Executar RED**

Run: `python -m pytest tests/features/test_profile_avatar_service.py -q`
Expected: módulo ausente.

- [ ] **Step 3: Implementar serviço e endpoint**

Usar `Image.open`, `ImageOps.exif_transpose`, `ImageOps.fit((512,512))`, RGB e JPEG quality 90; salvar com token aleatório e somente atualizar banco após sucesso.

- [ ] **Step 4: Executar GREEN**

Run: `python -m pytest tests/features/test_profile_avatar_service.py tests/web/test_portal_pages.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -am "feat: normalize profile avatars securely"`

### Task 2: Editor de moldura

**Files:**
- Create: `app/shared/web/static/js/profile-avatar-editor.js`
- Create: `tests/js/profile-avatar-editor.test.js`
- Modify: `app/templates/profile.html`
- Modify: `app/shared/web/static/css/portal.css`
- Modify: `tests/web/test_portal_pages.py`

**Interfaces:**
- Produces: editor com Canvas, zoom, Pointer Events, cancelar e blob JPEG em `avatar`.

- [ ] **Step 1: Escrever RED**

Testar helpers puros `coverScale`, `clampOffset` e contrato do template para canvas/zoom/status.

- [ ] **Step 2: Executar RED**

Run: `node --test tests/js/profile-avatar-editor.test.js && python -m pytest tests/web/test_portal_pages.py -q`
Expected: módulo/elementos ausentes.

- [ ] **Step 3: Implementar editor**

Exportar helpers para Node, inicializar na carga e `sistionm:content-updated`, desenhar preview circular, limitar deslocamento, gerar blob 512 × 512 e substituir o arquivo do input via `DataTransfer` antes do submit.

- [ ] **Step 4: Executar GREEN**

Run: comando do Step 2 mais `node --check app/shared/web/static/js/profile-avatar-editor.js`. Expected: PASS.

- [ ] **Step 5: Commit**

`git commit -am "feat: add profile avatar crop editor"`

### Task 3: Gate integrado e documentação

**Files:**
- Modify: `docs/file-map.md`
- Modify: `docs/development.md`
- Modify: `docs/bug-audit.md`

- [ ] **Step 1: Documentar módulos e limites**

Registrar unread persistido, reações exclusivas, avatares e comandos Node.

- [ ] **Step 2: Executar gate**

Run: `python -m pytest tests/web tests/performance tests/characterization tests/features -q; python -m ruff check app tests; node --test tests/js/*.test.js; git diff --check`
Expected: zero falhas e somente avisos de depreciação conhecidos.

- [ ] **Step 3: Commit**

`git commit -am "docs: hand off collaboration improvements"`
