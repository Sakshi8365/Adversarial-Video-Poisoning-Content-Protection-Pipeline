import os
import json
import time
import asyncio
from typing import Optional
import redis.asyncio as redis

REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')


def _client():
    return redis.from_url(REDIS_URL, decode_responses=True)


async def enqueue_job(job: dict):
    r = _client()
    job_id = job['job_id']
    key = f'job:{job_id}'
    now = str(int(time.time()))
    await r.hset(key, mapping={'status': 'QUEUED', 'created_at': now, 'job': json.dumps(job)})
    # push to queue (right side)
    await r.lpush('jobs_queue', json.dumps(job))
    await r.close()


async def pop_job(timeout: int = 5) -> Optional[dict]:
    r = _client()
    try:
        res = await r.brpop('jobs_queue', timeout=timeout)
        if not res:
            return None
        _, payload = res
        job = json.loads(payload)
        return job
    finally:
        await r.close()


async def set_job_status(job_id: str, status: str, extra: dict = None):
    r = _client()
    key = f'job:{job_id}'
    mapping = {'status': status, 'updated_at': str(int(time.time()))}
    if extra:
        mapping['meta'] = json.dumps(extra)
    await r.hset(key, mapping=mapping)
    await r.close()


async def get_job(job_id: str) -> dict:
    r = _client()
    key = f'job:{job_id}'
    data = await r.hgetall(key)
    await r.close()
    if not data:
        return {}
    # parse fields
    if 'job' in data:
        try:
            data['job'] = json.loads(data['job'])
        except Exception:
            pass
    if 'meta' in data:
        try:
            data['meta'] = json.loads(data['meta'])
        except Exception:
            pass
    return data
