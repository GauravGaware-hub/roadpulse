from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
def health():
    return {"status": "healthy", "service": "roadpulse-api"}
