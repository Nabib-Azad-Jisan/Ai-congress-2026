"""Validate uploaded crop photos and locate the private images belonging to a case."""
import io
import warnings
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError


def read_upload(image: UploadFile) -> bytes:
    if Path(image.filename or '').suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
        raise HTTPException(415, 'Use JPG, PNG or WebP')
    data = image.file.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, 'Maximum upload is 8 MB')
    return data


def decode_photo(data: bytes) -> Image.Image:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as decoded:
                if decoded.format not in ('JPEG', 'PNG', 'WEBP') or getattr(decoded, 'n_frames', 1) != 1:
                    raise ValueError('Use a single still photo')
                if decoded.width * decoded.height > 20_000_000:
                    raise ValueError('Image exceeds pixel limit')
                decoded.verify()
            with Image.open(io.BytesIO(data)) as decoded:
                rgba = ImageOps.exif_transpose(decoded).convert('RGBA')
                clean = Image.new('RGB', rgba.size, 'white')
                clean.paste(rgba, mask=rgba.getchannel('A'))
                return clean
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise HTTPException(415, 'Invalid image, animated image or excessive dimensions. Use one JPG, PNG or WebP photo.') from exc


def case_photo_paths(storage: Path, payload: dict) -> list[Path]:
    return [storage / Path(payload[key]).name for key in ('image_file', 'follow_up_image_file') if payload.get(key)]
