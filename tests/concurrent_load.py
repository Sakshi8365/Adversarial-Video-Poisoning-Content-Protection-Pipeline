import requests
import time
import os
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

API_URL = os.getenv('API_URL', 'http://localhost:8000')
SAMPLE = os.path.join('uploads', 'sample.mp4')
TOTAL = int(os.getenv('TOTAL_JOBS', '100'))
CONCURRENCY = int(os.getenv('CONCURRENCY', '10'))
OUT_DIR = os.getenv('OUT_DIR', 'tests/metrics_output')

try:
    import psutil
    import matplotlib.pyplot as plt
except Exception:
    psutil = None
    plt = None

if not os.path.exists(SAMPLE):
    raise SystemExit(f"Sample not found: {SAMPLE}. Run tools/generate_sample_video.py first.")

os.makedirs(OUT_DIR, exist_ok=True)

def submit_and_wait(i):
    start = time.time()
    with open(SAMPLE, 'rb') as f:
        files = {'file': ('sample.mp4', f, 'video/mp4')}
        r = requests.post(f"{API_URL}/api/v1/protection/jobs?target_model=resnet50", files=files)
        r.raise_for_status()
        job = r.json()
        jid = job['job_id']
    # poll
    for _ in range(300):
        time.sleep(0.5)
        try:
            s = requests.get(f"{API_URL}/api/v1/protection/jobs/{jid}/status", timeout=5).json()
        except Exception:
            continue
        if s.get('state') in ('COMPLETED','FAILED'):
            end = time.time()
            return {'idx': i, 'job_id': jid, 'state': s.get('state'), 'duration': end-start}
    return {'idx': i, 'job_id': jid, 'state': 'TIMEOUT', 'duration': 300}

# background sampler
sampler_data = {'t': [], 'cpu': [], 'mem': []}
stop_sampler = False

def sampler(interval=0.5):
    while not stop_sampler:
        sampler_data['t'].append(time.time())
        if psutil:
            sampler_data['cpu'].append(psutil.cpu_percent(interval=None))
            sampler_data['mem'].append(psutil.virtual_memory().percent)
        else:
            sampler_data['cpu'].append(None)
            sampler_data['mem'].append(None)
        time.sleep(interval)

start_all = time.time()

# start sampler
import threading
sampler_thread = threading.Thread(target=sampler, args=(0.5,), daemon=True)
sampler_thread.start()

results = []
with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
    futures = [ex.submit(submit_and_wait, i) for i in range(TOTAL)]
    for fut in as_completed(futures):
        try:
            r = fut.result()
            results.append(r)
            print('done', r['idx'], r['state'], f"{r['duration']:.2f}s")
        except Exception as e:
            print('error', e)

stop_sampler = True
end_all = time.time()

summary = {
    'total_jobs': TOTAL,
    'concurrency': CONCURRENCY,
    'completed': len([r for r in results if r['state']=='COMPLETED']),
    'failed': len([r for r in results if r['state']!='COMPLETED']),
    'wall_time_s': end_all - start_all,
}

print('\nSummary:')
print(json.dumps(summary, indent=2))

with open(os.path.join(OUT_DIR, 'concurrent_results.json'), 'w') as fh:
    json.dump({'summary': summary, 'runs': results, 'sampler': sampler_data}, fh, default=str)

# plots
if plt:
    durations = [r['duration'] for r in results]
    plt.figure()
    plt.hist(durations, bins=40)
    plt.title('Concurrent run latencies')
    plt.savefig(os.path.join(OUT_DIR, 'concurrent_latency_hist.png'))

    if sampler_data['cpu'] and any(v is not None for v in sampler_data['cpu']):
        plt.figure()
        times = [t - sampler_data['t'][0] for t in sampler_data['t']]
        plt.plot(times, sampler_data['cpu'], label='cpu%')
        plt.plot(times, sampler_data['mem'], label='mem%')
        plt.legend()
        plt.title('Host CPU/Mem during load')
        plt.xlabel('seconds')
        plt.savefig(os.path.join(OUT_DIR, 'concurrent_cpu_mem.png'))

print('Saved concurrent outputs to', OUT_DIR)
