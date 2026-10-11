"""Własny podkład boom-bap 88 BPM (syntetyzowany, zero Content ID). Użycie: python3 beat.py out.wav sekundy"""
import sys, numpy as np, wave
SR = 44100; BPM = 88; beat = 60 / BPM; bar = 4 * beat
rng = np.random.default_rng(7)

def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / d)

def kick():
    n = int(0.5 * SR); t = np.arange(n) / SR
    f = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.25)

def snare():
    n = int(0.3 * SR); t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    noise = np.convolve(noise, [1, -0.6], "same")
    return (0.7 * noise * env(n, 0.001, 0.09) + 0.4 * np.sin(2 * np.pi * 190 * t) * env(n, 0.001, 0.05))

def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR)
    x = np.diff(rng.normal(0, 1, n + 1))
    return 0.25 * x * env(n, 0.0005, 0.08 if open_ else 0.018)

def pad(freqs, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t + 0.3 * np.sin(2 * np.pi * 0.2 * t)) for f in freqs)
    a = np.minimum(t / 0.4, 1) * np.minimum((dur - t) / 0.4, 1)
    return 0.08 * s * a

def bass(f, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    return 0.35 * np.tanh(2 * np.sin(2 * np.pi * f * t)) * env(n, 0.005, dur * 0.6)

# Am – F – Dm – E (ciemny, "lekcyjny" klimat)
chords = [(110, [220, 261.6, 329.6]), (87.3, [174.6, 220, 261.6]),
          (73.4, [146.8, 174.6, 220]), (82.4, [164.8, 207.7, 246.9])]

def loop(nbars=4):
    L = int(nbars * bar * SR); out = np.zeros(L + SR)
    def put(x, at, g=1.0):
        i = int(at * SR); out[i:i + len(x)] += g * x
    for b in range(nbars):
        t0 = b * bar
        root, triad = chords[b % 4]
        put(pad(triad, bar), t0)
        put(bass(root / 2, beat * 1.5), t0); put(bass(root / 2, beat), t0 + 2.5 * beat)
        for k in (0, 1.75, 2.5): put(kick(), t0 + k * beat, 0.9)
        for s in (1, 3): put(snare(), t0 + s * beat, 0.6)
        for h in range(8):
            swing = 0.03 if h % 2 else 0
            put(hat(h == 7), t0 + (h * 0.5 + swing) * beat, 0.8 if h % 2 == 0 else 0.5)
    return out[:L]

secs = float(sys.argv[2])
one = loop(4)
reps = int(np.ceil(secs * SR / len(one)))
x = np.tile(one, reps)[: int(secs * SR)]
fade = int(2 * SR); x[-fade:] *= np.linspace(1, 0, fade)
x = x / np.max(np.abs(x)) * 0.8
pcm = (np.stack([x, x], 1) * 32767).astype(np.int16)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
