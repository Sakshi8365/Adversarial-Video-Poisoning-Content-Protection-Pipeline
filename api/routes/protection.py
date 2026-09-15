from fastapi import APIRouter, UploadFile, File, HTTPException
from uuid import uuid4
from typing import Optional
from api.utils.storage import save_upload
from cache.redis_queue import enqueue_job, get_job

router = APIRouter()


@router.post("/jobs", status_code=202)
async def create_job(file: UploadFile = File(...), target_model: Optional[str] = "resnet50"):
    job_id = str(uuid4())
    # save file with job_id prefix to avoid races
    saved_filename = f"{job_id}-{file.filename}"
    saved_path = await save_upload(file, filename=saved_filename)
    job = {
        "job_id": job_id,
        "input_path": saved_path,
        "target_model": target_model,
    }
    await enqueue_job(job)
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
async def get_job_info(job_id: str):
    data = await get_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")
    return data


@router.get("/jobs/{job_id}/status")
async def get_status(job_id: str):
    data = await get_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, "state": data.get('status')}


@router.get("/jobs/{job_id}/results")
async def get_results(job_id: str):
    data = await get_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")
    # results will be stored in job meta when complete
    return data.get('meta', {})


@router.get("/jobs/{job_id}/report")
async def get_report(job_id: str):
    data = await get_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="Job not found")
    report = data.get('meta', {}).get('report') if data.get('meta') else None
    if not report:
        raise HTTPException(status_code=404, detail="Report not available yet")
    return report
