"""Validate and normalize profile avatars."""

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_AVATAR_BYTES = 10 * 1024 * 1024
MAX_AVATAR_PIXELS = 40_000_000
ALLOWED_FORMATS = {"GIF", "JPEG", "PNG", "WEBP"}


class AvatarValidationError(ValueError):
    """Raised when an avatar cannot be safely decoded and normalized."""


def process_avatar(content: bytes) -> bytes:
    if len(content) > MAX_AVATAR_BYTES:
        raise AvatarValidationError("A imagem excede o limite de 10 MiB.")
    if not content:
        raise AvatarValidationError("A imagem está vazia ou inválida.")

    try:
        with Image.open(BytesIO(content)) as source:
            if source.format not in ALLOWED_FORMATS:
                raise AvatarValidationError("Formato de imagem não permitido.")
            if source.width * source.height > MAX_AVATAR_PIXELS:
                raise AvatarValidationError("A imagem possui resolução excessiva.")
            source.load()
            oriented = ImageOps.exif_transpose(source)
            normalized = ImageOps.fit(
                oriented.convert("RGB"),
                (512, 512),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            output = BytesIO()
            normalized.save(output, format="JPEG", quality=90, optimize=True)
            return output.getvalue()
    except AvatarValidationError:
        raise
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise AvatarValidationError("A imagem selecionada está inválida.") from exc
