# Adversarial Video Poisoning & Content Protection Pipeline (YouTube)

Quick dev instructions

Requirements: Docker, docker-compose, Python 3.11

Build images:
```bash
docker-compose build --no-cache worker
```

Start services:
```bash
docker-compose up -d
```

Generate a sample video (host):
```bash
python tools/generate_sample_video.py
```

Run integration test (host):
```bash
python -m pip install requests
python tests/integration_test.py
```

Notes:
- Use `curl.exe` on Windows if testing uploads from PowerShell (PowerShell `curl` is an alias that may not post files correctly).
- Uploads are saved to `uploads/` and processed by the `worker` which writes `uploads/protected-<job_id>.mp4` on success.
