import subprocess, time, json, os

N = 5
results = []

for i in range(N):
    start = time.time()
    # upload (use same sample file)
    p = subprocess.run([
        'curl', '-s', '-F', 'file=@sample.mp4',
        'http://localhost:8000/api/v1/protection/jobs?target_model=resnet50'
    ], capture_output=True, text=True)
    try:
        jid = json.loads(p.stdout)['job_id']
    except Exception as e:
        print('upload_failed', p.stdout, p.stderr)
        break
    enqueue_ts = time.time()

    state = None
    poll_start = time.time()
    timeout = 60
    while True:
        time.sleep(0.5)
        q = subprocess.run(['curl', '-s', f'http://localhost:8000/api/v1/protection/jobs/{jid}/status'], capture_output=True, text=True)
        try:
            state = json.loads(q.stdout).get('state')
        except Exception:
            state = None
        if state in ('COMPLETED', 'FAILED'):
            break
        if time.time() - poll_start > timeout:
            state = 'TIMEOUT'
            break
    end = time.time()
    results.append({'job_id': jid, 'enqueue_time': enqueue_ts, 'completed_time': end, 'duration_s': round(end - start, 3), 'state': state})
    print(json.dumps(results[-1]))

print('\nSUMMARY')
print(json.dumps(results, indent=2))
