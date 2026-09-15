import cv2
import numpy as np
import os

os.makedirs('uploads', exist_ok=True)
path = os.path.join('uploads', 'sample.mp4')
width, height = 320, 240
fps = 10.0
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
writer = cv2.VideoWriter(path, fourcc, fps, (width, height))
for i in range(30):
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    color = (i * 8) % 256
    frame[:] = (color, 255 - color, (color * 2) % 256)
    writer.write(frame)
writer.release()
print('Wrote', path)
