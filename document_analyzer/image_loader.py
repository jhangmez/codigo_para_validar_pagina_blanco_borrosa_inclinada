"""
Cargador de imágenes optimizado que soporta URLs web, rutas locales y bytes en memoria.
"""
from __future__ import annotations

import os
import urllib.error
import urllib.request
from typing import Union

import cv2
import numpy as np


class ImageLoadError(Exception):
    """Excepción lanzada cuando ocurre un error al cargar o descargar la imagen."""
    pass


def load_image(
    source: Union[str, bytes, np.ndarray],
    timeout_seconds: float = 12.0
) -> np.ndarray:
    """
    Carga una imagen en formato BGR (NumPy ndarray) desde una URL, ruta local o bytes.

    Args:
        source: URL (http/https), ruta de archivo local, bytes de imagen o ndarray.
        timeout_seconds: Tiempo límite para descargas por red.

    Returns:
        np.ndarray: Imagen decodificada en formato BGR de OpenCV (H, W, C) o escala de grises.

    Raises:
        ImageLoadError: Si la imagen no puede ser descargada, encontrada o decodificada.
    """
    if isinstance(source, np.ndarray):
        if source.size == 0:
            raise ImageLoadError("El array NumPy proporcionado está vacío.")
        return source

    if isinstance(source, bytes):
        return _decode_bytes(source, "memoria (bytes)")

    if isinstance(source, str):
        # 1. Si es una URL web
        if source.startswith("http://") or source.startswith("https://"):
            return _download_from_url(source, timeout_seconds)

        # 2. Si es una ruta de archivo local
        if not os.path.exists(source):
            raise ImageLoadError(f"El archivo local no existe: '{source}'")

        try:
            # np.fromfile previene problemas con caracteres especiales y acentos en rutas
            raw_bytes = np.fromfile(source, dtype=np.uint8)
            img = cv2.imdecode(raw_bytes, cv2.IMREAD_COLOR)
            if img is None:
                raise ImageLoadError(f"No se pudo decodificar el archivo como imagen válida: '{source}'")
            return img
        except Exception as e:
            if isinstance(e, ImageLoadError):
                raise
            raise ImageLoadError(f"Error al leer el archivo '{source}': {e}") from e

    raise ImageLoadError(f"Tipo de fuente no soportado: {type(source).__name__}")


def _download_from_url(url: str, timeout: float) -> np.ndarray:
    """Descarga de forma segura y eficiente una imagen usando bibliotecas nativas de Python."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()

        if not data:
            raise ImageLoadError(f"La URL respondió con cuerpo vacío: {url}")

        return _decode_bytes(data, f"URL: {url}")

    except urllib.error.HTTPError as e:
        raise ImageLoadError(f"Error HTTP {e.code} ({e.reason}) al descargar: {url}") from e
    except urllib.error.URLError as e:
        raise ImageLoadError(f"Error de conexión al conectar a la URL '{url}': {e.reason}") from e
    except Exception as e:
        if isinstance(e, ImageLoadError):
            raise
        raise ImageLoadError(f"Falla inesperada al descargar de '{url}': {e}") from e


def _decode_bytes(data: bytes, origin_desc: str) -> np.ndarray:
    """Decodifica un bloque de bytes a una matriz de OpenCV."""
    nparr = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ImageLoadError(
            f"Los datos binarios recibidos desde {origin_desc} no representan un formato de imagen soportado (PNG, JPG, TIFF, WEBP, etc.)."
        )
    return img
