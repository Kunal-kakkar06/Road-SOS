import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os

load_dotenv()

# Check if environment variables are set and are valid
cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
api_key = os.getenv("CLOUDINARY_API_KEY")
api_secret = os.getenv("CLOUDINARY_API_SECRET")

is_configured = (
    cloud_name and "your_" not in cloud_name and
    api_key and "your_" not in api_key and
    api_secret and "your_" not in api_secret
)

if is_configured:
    cloudinary.config(
        cloud_name = cloud_name,
        api_key    = api_key,
        api_secret = api_secret,
        secure     = True,
    )
else:
    print("[Cloudinary] Keys not configured or invalid. Using local storage fallback inside static/uploads/")


async def upload_photo(file_bytes: bytes, filename: str,
                        folder: str = "roadsos/incidents") -> str | None:
    if is_configured:
        try:
            result = cloudinary.uploader.upload(
                file_bytes,
                folder          = folder,
                public_id       = filename.rsplit(".", 1)[0],
                resource_type   = "image",
                use_filename    = True,
                unique_filename = True,
                overwrite       = False,
                tags            = ["roadsos", "incident", "evidence"],
                transformation  = [
                    {"quality": "auto", "fetch_format": "auto"},
                    {"width": 1920, "crop": "limit"},
                ],
            )
            url = result.get("secure_url")
            print(f"[Cloudinary] Uploaded: {url}")
            return url
        except Exception as e:
            print(f"[Cloudinary] Failed to upload, trying local fallback: {e}")
    
    # Local Storage Fallback
    try:
        # Create directory inside static/uploads
        upload_dir = os.path.join("static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        # Clean filename to prevent path traversal
        clean_filename = os.path.basename(filename)
        # Append unique timestamp to prevent collisions
        import time
        ts = int(time.time())
        file_name_final = f"{ts}_{clean_filename}"
        file_path = os.path.join(upload_dir, file_name_final)
        
        with open(file_path, "wb") as f:
            f.write(file_bytes)
            
        local_url = f"/static/uploads/{file_name_final}"
        print(f"[Local Storage] Saved file locally: {local_url}")
        return local_url
    except Exception as local_err:
        print(f"[Local Storage] Failed to save file locally: {local_err}")
        return None
