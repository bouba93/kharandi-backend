import logging
from django.conf import settings
logger = logging.getLogger(__name__)

def upload_document(file, doc_type="raw"):
    if not getattr(settings, "USE_CLOUDINARY", False): return {"url": None}
    try:
        import cloudinary.uploader
        folder   = "kharandi/videos" if doc_type == "video" else "kharandi/documents"
        resource = "video" if doc_type == "video" else "raw" if doc_type == "raw" else "image"
        result   = cloudinary.uploader.upload(file, folder=folder, resource_type=resource, use_filename=True, unique_filename=True)
        return {"url": result.get("secure_url"), "public_id": result.get("public_id")}
    except Exception as exc:
        logger.error("Cloudinary upload error: %s", exc)
        return {"url": None}

def upload_thumbnail(file):
    if not getattr(settings, "USE_CLOUDINARY", False): return {"url": None}
    try:
        import cloudinary.uploader
        result = cloudinary.uploader.upload(file, folder="kharandi/thumbnails", resource_type="image",
                    transformation=[{"width":800,"height":450,"crop":"fill","quality":"auto"}])
        return {"url": result.get("secure_url")}
    except Exception as exc:
        logger.error("Cloudinary thumbnail error: %s", exc)
        return {"url": None}

def upload_avatar(file):
    if not getattr(settings, "USE_CLOUDINARY", False): return {"url": None}
    try:
        import cloudinary.uploader
        result = cloudinary.uploader.upload(file, folder="kharandi/avatars", resource_type="image",
                    transformation=[{"width":200,"height":200,"crop":"fill","gravity":"face","quality":"auto"}])
        return {"url": result.get("secure_url")}
    except Exception as exc:
        logger.error("Cloudinary avatar error: %s", exc)
        return {"url": None}
