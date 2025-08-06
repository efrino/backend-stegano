from fastapi import APIRouter, File, UploadFile, Form, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user import User
from app.models.artwork import Artwork, generate_unique_key # Asumsi generate_unique_key ada di artwork.py
from app.api.deps import get_current_user
from app.steganography import embed_message_lsb, xor_encrypt_decrypt
from app.utils.image_similarity import compute_all_hashes, is_similar_image
import os, uuid, hashlib, io
from PIL import Image
from app.utils.send_email import send_certificate_email
import os

router = APIRouter()

UPLOAD_DIR = "static/uploads"
WATERMARKED_DIR = "static/watermarked"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(WATERMARKED_DIR, exist_ok=True)

@router.post("/uploads", status_code=status.HTTP_201_CREATED)
async def upload_artwork(
    title: str = Form(...),
    description: str = Form(None),
    category: str = Form(None),
    license_type: str = Form("FREE"),
    price: float = Form(0.00),
    image: UploadFile = File(...),
    watermark_creator_message: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    temp_file_path = None
    watermarked_image_path = None

    try:
        merged_user = db.merge(current_user)
        user_id_str = str(merged_user.id)
        unique_key = generate_unique_key(user_id_str, title, image.filename)
        _, file_extension = os.path.splitext(image.filename)
        file_extension = file_extension.lstrip(".").lower()
        temp_file_name = f"{uuid.uuid4().hex}.{file_extension}"
        temp_file_path = os.path.join(UPLOAD_DIR, temp_file_name)

        license_type = license_type.upper()
        if license_type not in ["FREE", "PAID"]:
            raise HTTPException(status_code=400, detail="Tipe lisensi tidak valid.")
        
        if license_type == "FREE":
            price = 0.0
        elif license_type == "PAID":
            if price <= 0.0:
                raise HTTPException(status_code=400, detail="Harga harus diisi jika lisensi berbayar.")

        content = await image.read()
        pil_image = Image.open(io.BytesIO(content)).convert("RGB")
        uploaded_hashes = compute_all_hashes(pil_image)

        existing_artworks = db.query(Artwork).all()
        for artwork_item in existing_artworks: 
            if is_similar_image(uploaded_hashes, pil_image, artwork_item):
                raise HTTPException(status_code=400, detail="Gambar Ditemukan mirip atau sudah pernah diunggap (terdeteksi duplikat).")

        with open(temp_file_path, "wb") as f:
            f.write(content)

        watermark_hak_cipta = hashlib.sha256(unique_key.encode()).hexdigest()
        
        artwork_secret_code_for_watermark = None
        pesan_gabungan = f"COPYRIGHT:{watermark_hak_cipta}"

        if watermark_creator_message:
            artwork_secret_code_for_watermark = uuid.uuid4().hex[:8] 
            encrypted = xor_encrypt_decrypt(watermark_creator_message, artwork_secret_code_for_watermark)
            pesan_gabungan += f"<USER_MESSAGE>{encrypted}"

        watermarked_image_path = embed_message_lsb(temp_file_path, pesan_gabungan)

        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        filename_without_ext, _ = os.path.splitext(unique_key)

        final_image_name = f"{filename_without_ext}.{file_extension}"
        final_image_path = os.path.join(WATERMARKED_DIR, final_image_name)
        os.rename(watermarked_image_path, final_image_path)

        BASE_URL = "http://localhost:8000"
        image_url_db = f"/static/watermarked/{final_image_name}"
        image_url_full = f"{BASE_URL}{image_url_db}"


        artwork = Artwork(
            id=uuid.uuid4(),
            owner_id=merged_user.id,
            title=title,
            description=description,
            category=category,
            license_type=license_type,
            price=price,
            image_url=image_url_db,
            unique_key=unique_key,
            hash=uploaded_hashes["ahash"],
            hash_phash=uploaded_hashes["phash"],
            hash_dhash=uploaded_hashes["dhash"],
            hash_whash=uploaded_hashes["whash"],
            artwork_secret_code=artwork_secret_code_for_watermark
        )
        db.add(artwork)
        db.commit()
        db.refresh(artwork)

        await send_certificate_email(
            to_email=merged_user.email,
            context={
                "title": title,
                "category": category or "-",
                "description": description or "-",
                "unique_key": unique_key,
                "buyer_code": artwork_secret_code_for_watermark if artwork_secret_code_for_watermark else "N/A", # Kirim kode yang benar
                "image_url": image_url_full
            }
        )

        return {
            "message": "Artwork uploaded successfully with steganography",
            "artwork_id": artwork.id,
            "image_url": image_url_db,
            "unique_key": unique_key,
            "copyright_hash": watermark_hak_cipta,
            "buyer_secret_code": artwork_secret_code_for_watermark
        }

    except HTTPException as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if watermarked_image_path and os.path.exists(watermarked_image_path):
            os.remove(watermarked_image_path)
        raise e
    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if watermarked_image_path and os.path.exists(watermarked_image_path):
            os.remove(watermarked_image_path)
        raise HTTPException(status_code=500, detail=f"Upload gagal: {str(e)}")