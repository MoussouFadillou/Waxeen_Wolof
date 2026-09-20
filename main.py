import csv
import io
import os

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from database import create_contribution, list_all_contributions
from storage import upload_audio


app = FastAPI(
    title="Waxeen Wolof API",
    version="6.0.0"
)


FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "https://wakhine-wolof-frontend-qfq4.vercel.app"
)

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Waxeen Wolof API",
        "version": "6.0.0"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "waxeen-wolof-api",
        "database": "Supabase",
        "storage": "Supabase Storage"
    }


@app.post("/api/contribuer")
async def contribuer(
    age: int = Form(...),
    sexe: str = Form(...),
    region: str = Form(...),
    departement: str = Form(...),
    accent: str = Form(...),
    alphabetisation: str = Form(...),
    type_parole: str = Form(...),
    transcription: str = Form(""),
    audioFile: UploadFile = File(...)
):

    if age < 1 or age > 120:
        raise HTTPException(
            status_code=400,
            detail="L'age doit etre compris entre 1 et 120."
        )

    fields = {
        "sexe": sexe,
        "region": region,
        "departement": departement,
        "accent": accent,
        "alphabetisation": alphabetisation,
        "type_parole": type_parole
    }

    for field, value in fields.items():
        if not value or not value.strip():
            raise HTTPException(
                status_code=400,
                detail=f"Le champ {field} est obligatoire."
            )

    content = await audioFile.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Le fichier audio est vide."
        )

    filename = audioFile.filename or "audio.wav"
    content_type = audioFile.content_type or "audio/wav"

    try:
        audio_path = upload_audio(
            content,
            filename,
            content_type
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur Supabase Storage : {str(e)}"
        )

    try:
        row = create_contribution(
            age=age,
            sexe=sexe,
            region=region,
            departement=departement,
            accent=accent,
            alphabetisation=alphabetisation,
            type_parole=type_parole,
            transcription=transcription,
            audio_path=audio_path,
            audio_filename=filename,
            audio_content_type=content_type
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur Supabase Database : {str(e)}"
        )

    return {
        "success": True,
        "message": "Contribution enregistree avec succes.",
        "contribution": row,
        "audio_path": audio_path
    }


@app.get("/api/contributions/csv")
def contributions_csv(
    x_admin_token: str = Header(default="")
):

    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_TOKEN n'est pas configure sur Render."
        )

    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Code administrateur incorrect."
        )

    try:
        rows = list_all_contributions()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur recuperation donnees : {str(e)}"
        )

    fields = [
        "id",
        "age",
        "sexe",
        "region",
        "departement",
        "accent",
        "alphabetisation",
        "type_parole",
        "transcription",
        "audio_path",
        "audio_filename",
        "audio_content_type",
        "created_at"
    ]

    output = io.StringIO()

    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        delimiter=";"
    )

    writer.writeheader()

    for row in rows:
        writer.writerow({
            field: row.get(field, "")
            for field in fields
        })

    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=corpus_wakhin_wolof.csv"
        }
    )
