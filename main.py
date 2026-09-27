import csv
import io
import os

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from database import create_contribution, list_all_contributions
from storage import upload_audio, audio_exists


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
        "database": "Render PostgreSQL",
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

    # =====================================================
    # Vérification de l'âge
    # =====================================================

    if age < 1 or age > 120:
        raise HTTPException(
            status_code=400,
            detail="L'age doit etre compris entre 1 et 120."
        )

    # =====================================================
    # Vérification de la transcription
    # =====================================================

    transcription = transcription.strip()

    if not transcription:
        raise HTTPException(
            status_code=400,
            detail="La transcription est obligatoire."
        )

    # =====================================================
    # Vérification des autres champs
    # =====================================================

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

    # =====================================================
    # Lecture du fichier audio
    # =====================================================

    content = await audioFile.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Le fichier audio est vide."
        )

    filename = audioFile.filename or "audio.wav"

    content_type = (
        audioFile.content_type
        or "audio/wav"
    )

    # =====================================================
    # Upload audio vers Supabase Storage
    # =====================================================

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

    # =====================================================
    # Enregistrement dans Render PostgreSQL
    # =====================================================

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
            detail=f"Erreur PostgreSQL : {str(e)}"
        )

    # =====================================================
    # Réponse
    # =====================================================

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

    # =====================================================
    # Vérification du token administrateur
    # =====================================================

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

    # =====================================================
    # Récupération des contributions PostgreSQL
    # =====================================================

    try:

        rows = list_all_contributions()

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Erreur recuperation donnees : {str(e)}"
        )

    # =====================================================
    # Colonnes du CSV
    # =====================================================

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

    # =====================================================
    # Création du CSV
    # =====================================================

    output = io.StringIO()

    writer = csv.DictWriter(
        output,
        fieldnames=fields,
        delimiter=";"
    )

    writer.writeheader()

    # Compteurs
    audio_count = 0
    missing_audio_count = 0

    # =====================================================
    # Vérification de chaque audio dans Supabase Storage
    # =====================================================

    for row in rows:

        audio_path = row.get("audio_path")

        # Aucun chemin audio enregistré
        if not audio_path:

            missing_audio_count += 1

            continue

        # Vérification réelle dans Supabase Storage
        try:

            exists = audio_exists(audio_path)

        except Exception:

            exists = False

        # Audio absent de Supabase
        if not exists:

            missing_audio_count += 1

            continue

        # =================================================
        # Audio réellement présent dans Supabase
        # =================================================

        writer.writerow({
            field: row.get(field, "")
            for field in fields
        })

        audio_count += 1

    # =====================================================
    # UTF-8 avec BOM
    # =====================================================

    csv_content = "\ufeff" + output.getvalue()

    # =====================================================
    # Téléchargement du CSV
    # =====================================================

    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                "attachment; "
                "filename=corpus_waxeen_wolof_audio.csv"
            ),
            "X-Audio-Count": str(audio_count),
            "X-Missing-Audio": str(missing_audio_count)
        }
    )
