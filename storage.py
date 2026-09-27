import os
import uuid

from supabase_client import supabase


BUCKET = os.getenv(
    "SUPABASE_BUCKET",
    "audio-wolof"
)


def upload_audio(
    content: bytes,
    original_name: str,
    content_type: str
):
    if not content:
        raise RuntimeError(
            "Le fichier audio est vide."
        )

    extension = ".wav"

    if original_name and "." in original_name:
        candidate = "." + original_name.rsplit(
            ".", 1
        )[1].lower()

        if candidate in {
            ".wav",
            ".webm",
            ".ogg",
            ".mp4",
            ".m4a"
        }:
            extension = candidate

    path = (
        f"contributions/"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    try:
        supabase.storage.from_(BUCKET).upload(
            path=path,
            file=content,
            file_options={
                "content-type": content_type or "audio/wav",
                "upsert": "false",
            },
        )

    except Exception as exc:
        raise RuntimeError(
            f"Erreur Supabase Storage : {exc}"
        )

    return path


def audio_exists(audio_path: str) -> bool:
    """
    Vérifie que le fichier audio existe réellement
    dans Supabase Storage.
    """

    if not audio_path:
        return False

    try:
        # Exemple :
        # contributions/abc123.webm

        if "/" not in audio_path:
            return False

        folder, filename = audio_path.rsplit("/", 1)

        response = (
            supabase.storage
            .from_(BUCKET)
            .list(
                folder,
                {
                    "limit": 100,
                    "search": filename
                }
            )
        )

        if not response:
            return False

        for item in response:
            if item.get("name") == filename:
                return True

        return False

    except Exception:
        return False
