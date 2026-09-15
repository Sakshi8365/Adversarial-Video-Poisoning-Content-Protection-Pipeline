import asyncio
import os
import json
import tempfile
from loguru import logger
from cache.redis_queue import pop_job, set_job_status

import cv2
import subprocess
import uuid


async def process_job(job: dict):
    job_id = job['job_id']
    logger.info(f"Starting job {job_id}")
    await set_job_status(job_id, 'PROCESSING')
    try:
        input_path = job.get('input_path') or job.get('file_path')
        if not input_path or not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")

        out_dir = os.environ.get('UPLOADS_DIR', 'uploads')
        os.makedirs(out_dir, exist_ok=True)
        protected_path = os.path.join(out_dir, f"protected-{job_id}.mp4")

        def try_open(path):
            c = cv2.VideoCapture(path)
            ok = c.isOpened()
            if not ok:
                c.release()
                return None
            return c

        cap = try_open(input_path)
        temp_fixed = None
        if cap is None:
            # attempt to remux/transcode with ffmpeg to place moov atom at start
            logger.info("cv2 failed to open video, attempting ffmpeg remux for faststart")
            fd, temp_fixed = tempfile.mkstemp(suffix='.mp4')
            os.close(fd)
            cmd = [
                'ffmpeg',
                '-y',
                '-i',
                input_path,
                '-c',
                'copy',
                '-movflags',
                '+faststart',
                temp_fixed,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                logger.error('ffmpeg remux failed: ' + proc.stderr)
                # try a re-encode fallback
                logger.info('Attempting ffmpeg re-encode fallback')
                proc2 = subprocess.run([
                    'ffmpeg', '-y', '-i', input_path,
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                    '-c:a', 'aac', '-movflags', '+faststart', temp_fixed
                ], capture_output=True, text=True)
                if proc2.returncode != 0:
                    logger.error('ffmpeg re-encode failed: ' + proc2.stderr)
                    raise RuntimeError(f"Failed to remux/re-encode video: {input_path}")
            cap = try_open(temp_fixed)
            if cap is None:
                raise RuntimeError(f"Failed to open video after ffmpeg fix: {input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")

        # read first frame to determine size (handles streams with missing metadata)
        ret, first_frame = cap.read()
        if not ret:
            raise RuntimeError(f"No frames found in video: {input_path}")
        height, width = first_frame.shape[:2]

        # write to a .part.mp4 file then atomically rename
        part_path = protected_path + '.part.mp4'
        writer = cv2.VideoWriter(part_path, fourcc, fps, (width, height))
        if not writer.isOpened():
            logger.warning(f"VideoWriter failed for {part_path}, falling back to ffmpeg copy/re-encode")
            # cleanup any partial
            try:
                if os.path.exists(part_path):
                    os.remove(part_path)
            except Exception:
                pass
            cap.release()
            # try ffmpeg copy first
            cmd = ['ffmpeg', '-y', '-i', input_path, '-c', 'copy', '-movflags', '+faststart', part_path]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                logger.error('ffmpeg copy failed: ' + proc.stderr)
                # try re-encode
                proc2 = subprocess.run([
                    'ffmpeg', '-y', '-i', input_path,
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                    '-c:a', 'aac', '-movflags', '+faststart', part_path
                ], capture_output=True, text=True)
                if proc2.returncode != 0:
                    logger.error('ffmpeg re-encode failed: ' + proc2.stderr)
                    raise RuntimeError(f"Failed to write protected video via ffmpeg: {input_path}")
            # move into final path atomically
            os.replace(part_path, protected_path)
            meta = {
                "report": {"note": "processed video via ffmpeg fallback (no-op)", "job_id": job_id},
                "protected_path": protected_path,
            }
            await set_job_status(job_id, 'COMPLETED', extra=meta)
            logger.info(f"Completed job {job_id} via ffmpeg fallback, out={protected_path}")
            return

        frame_count = 0
        # write the first frame we already read
        writer.write(first_frame)
        frame_count = 1
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # No-op processing: could add watermark or transforms here
            writer.write(frame)
            frame_count += 1

        writer.release()
        cap.release()
        # move into final path atomically
        os.replace(part_path, protected_path)
        # cleanup temp fixed file
        if temp_fixed:
            try:
                os.remove(temp_fixed)
            except Exception:
                pass

        meta = {
            "report": {"note": "processed video (no-op)", "job_id": job_id, "frames": frame_count},
            "protected_path": protected_path,
        }
        await set_job_status(job_id, 'COMPLETED', extra=meta)
        logger.info(f"Completed job {job_id}, frames={frame_count}, out={protected_path}")
    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        await set_job_status(job_id, 'FAILED', extra={"error": str(e)})


async def main_loop():
    logger.info("Worker started, polling Redis queue")
    try:
        while True:
            job = await pop_job(timeout=5)
            if not job:
                await asyncio.sleep(1)
                continue
            await process_job(job)
    except asyncio.CancelledError:
        logger.info("Worker cancelled, exiting")


def main():
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("Worker stopping")


if __name__ == '__main__':
    main()
