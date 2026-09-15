import requests
import time
import os

API_URL = os.getenv('API_URL', 'http://localhost:8000')
SAMPLE = os.path.join('uploads', 'sample.mp4')


def upload_and_wait():
    with open(SAMPLE, 'rb') as f:
        files = {'file': ('sample.mp4', f, 'video/mp4')}
        r = requests.post(f"{API_URL}/api/v1/protection/jobs?target_model=resnet50", files=files)
        r.raise_for_status()
        job = r.json()
        jid = job['job_id']
        print('queued', jid)

    for i in range(60):
        time.sleep(1)
        s = requests.get(f"{API_URL}/api/v1/protection/jobs/{jid}/status").json()
        state = s.get('state')
        print(i, state)
        if state in ('COMPLETED', 'FAILED'):
            return s
    raise RuntimeError('timeout')


if __name__ == '__main__':
    print(upload_and_wait())
