"""Render real David composited into the virtual office: source [T0,T1] -> social/heygen/work/david_comp.mp4"""
import sys, os, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import gs_comp as G
SRC, OUT, T0, T1, GRADE, PLATE = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), sys.argv[5], sys.argv[6]
gain, bias = np.load(GRADE); pl = G.plate(PLATE); dm = G.desk_mask(pl)
dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', str(T0), '-to', str(T1), '-i', SRC, '-vf', 'fps=30,' + G.ffmpeg_filter(),
                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1080x1920', '-r', '30', '-i', '-',
                        '-c:v', 'libx264', '-preset', 'fast', '-crf', '14', '-pix_fmt', 'yuv420p', OUT], stdin=subprocess.PIPE)
n = W3 = 1080 * 1920 * 3; k = 0; t = time.time()
while True:
    b = dec.stdout.read(W3)
    if len(b) < W3: break
    f = np.frombuffer(b, np.uint8).reshape(1920, 1080, 3).astype(np.float32)
    o, _ = G.composite(f, pl, gain, bias, dm)
    enc.stdin.write(o.tobytes()); k += 1
    if k % 30 == 0: print(k, round(time.time() - t), flush=True)
enc.stdin.close(); enc.wait(); print('done', k)
