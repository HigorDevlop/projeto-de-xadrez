"""Validate uploaded avatars without relying on the upload stream cursor."""
from io import BytesIO
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError


def normalize_photo(data: bytes, *, square=False) -> bytes:
    if not data or len(data) > 10 * 1024 * 1024:
        raise ValueError("Escolha uma imagem de até 10 MB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as original:
                if original.width * original.height > 20_000_000:
                    raise ValueError("Escolha uma imagem com até 20 milhões de pixels.")
                original.load()
                photo = ImageOps.exif_transpose(original).convert("RGBA")
                if square:
                    photo = ImageOps.fit(photo, (320, 320), method=Image.Resampling.LANCZOS)
                else:
                    photo.thumbnail((512, 512))
                output = BytesIO()
                photo.save(output, format="PNG")
                return output.getvalue()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as error:
        raise ValueError("Não foi possível abrir a foto. Escolha um PNG, JPEG ou WebP válido.") from error
