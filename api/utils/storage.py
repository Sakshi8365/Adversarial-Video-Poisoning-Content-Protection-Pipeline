import os
from pathlib import Path
from fastapi import UploadFile

UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', 'uploads'))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def save_upload(file: UploadFile, filename: str = None) -> str:
    """Save UploadFile to disk. If `filename` provided, use it; otherwise use original filename."""
    fname = filename or file.filename
    dest = UPLOAD_DIR / fname
    part = UPLOAD_DIR / (fname + '.part')
    # stream to a temporary .part file, then atomically rename
    with open(part, 'wb') as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
        f.flush()
        os.fsync(f.fileno())
    # atomic replace
    os.replace(part, dest)
    return str(dest)
