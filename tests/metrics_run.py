import requests
import time
import os
import statistics
import math
import json
from datetime import datetime

API_URL = os.getenv('API_URL', 'http://localhost:8000')
SAMPLE = os.path.join('uploads', 'sample.mp4')
RUNS = int(os.getenv('RUNS', '10'))
TIMEOUT = int(os.getenv('TIMEOUT', '180'))
OUT_DIR = os.getenv('OUT_DIR', 'tests/metrics_output')

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None

if not os.path.exists(SAMPLE):
    raise SystemExit(f"Sample not found: {SAMPLE}. Run tools/generate_sample_video.py first.")

os.makedirs(OUT_DIR, exist_ok=True)

def percentile(values, p):
    if not values:
        return None
    vals = sorted(values)
    k = (len(vals)-1) * (p/100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return vals[int(k)]
    d0 = vals[int(f)] * (c-k)
    d1 = vals[int(c)] * (k-f)
    return d0 + d1

results = []
errors = 0
start_batch = time.time()
for i in range(RUNS):
    start = time.time()
    with open(SAMPLE, 'rb') as f:
        files = {'file': ('sample.mp4', f, 'video/mp4')}
        r = requests.post(f"{API_URL}/api/v1/protection/jobs?target_model=resnet50", files=files)
        r.raise_for_status()
        job = r.json()
        jid = job['job_id']
    # poll
    finished = False
    for t in range(TIMEOUT):
        time.sleep(1)
        try:
            s = requests.get(f"{API_URL}/api/v1/protection/jobs/{jid}/status", timeout=5).json()
        except Exception:
            continue
        state = s.get('state')
        if state in ('COMPLETED', 'FAILED'):
            end = time.time()
            duration = end - start
            results.append({'job_id': jid, 'state': state, 'duration': duration, 'timestamp': datetime.utcnow().isoformat()})
            finished = True
            print(f"Run {i+1}/{RUNS}: {state} in {duration:.2f}s")
            break
    if not finished:
        errors += 1
        results.append({'job_id': jid, 'state': 'TIMEOUT', 'duration': TIMEOUT, 'timestamp': datetime.utcnow().isoformat()})
        print(f"Run {i+1}/{RUNS}: TIMEOUT after {TIMEOUT}s")

end_batch = time.time()
# compute metrics
completed = [r['duration'] for r in results if r['state']=='COMPLETED']
failed = [r for r in results if r['state']!='COMPLETED']
count_completed = len(completed)
count_total = len(results)

total_wall = end_batch - start_batch
throughput_per_hour = (count_completed / total_wall) * 3600 if total_wall > 0 else 0
mean_latency = statistics.mean(completed) if completed else None
median_latency = percentile(completed, 50)
p95_latency = percentile(completed, 95)
p99_latency = percentile(completed, 99)

summary = {
    'total_runs': count_total,
    'completed': count_completed,
    'failed': len(failed),
    'success_rate_pct': (count_completed/count_total*100) if count_total>0 else 0,
    'throughput_videos_per_hour': throughput_per_hour,
    'mean_latency_s': mean_latency,
    'median_latency_s': median_latency,
    'p95_latency_s': p95_latency,
    'p99_latency_s': p99_latency,
}

print('\n--- Summary ---')
print(json.dumps(summary, indent=2))

# save results
with open(os.path.join(OUT_DIR, 'results.json'), 'w') as fh:
    json.dump({'summary': summary, 'runs': results}, fh, indent=2)

if plt and completed:
    plt.figure(figsize=(6,4))
    plt.hist(completed, bins=40)
    plt.title('Latency histogram (s)')
    plt.xlabel('seconds')
    plt.ylabel('count')
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'latency_histogram.png'))
    print('Saved plot to', os.path.join(OUT_DIR, 'latency_histogram.png'))

print('\nPer-run durations (s):')
for r in results:
    print(r)

if len(failed) > 0:
    raise SystemExit(2)
