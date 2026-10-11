"""Składa odcinek: lektor (mp3) + plansze + podkład -> MP4 1080p, -14 LUFS.
Użycie: python3 render.py vo.mp3 out.mp4 seg_id [seg_id ...]"""
import sys, os, json, subprocess, re
import cards
from faster_whisper import WhisperModel

vo, out, ids = sys.argv[1], sys.argv[2], sys.argv[3:]
here = os.path.dirname(os.path.abspath(__file__))
work = os.environ.get("WORK", "/tmp/render"); os.makedirs(work, exist_ok=True)
segs = {s["id"]: s for s in json.load(open(os.path.join(here, "narration.json")))}
segs = [segs[i] for i in ids]
FPS = 30

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p]))

# 1) znaczniki czasu słów z Whispera
model = WhisperModel("small.en", device="cpu", compute_type="int8")
import numpy as np
pcm = subprocess.check_output(["ffmpeg", "-v", "error", "-i", vo, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"])
audio = np.frombuffer(pcm, np.float32)
words = [w for seg in model.transcribe(audio, word_timestamps=True)[0] for w in seg.words]
total = dur(vo)

# 2) podział skryptu na napisy i mapowanie na czas (proporcja słów)
script_words = sum(len(s["text"].split()) for s in segs)
ratio = len(words) / script_words
def t_at(word_idx):
    i = min(int(round(word_idx * ratio)), len(words) - 1)
    return words[i].start

shots, wi = [], 0  # (start, image)
for k, s in enumerate(segs):
    idx = int(s["badge"].split("/")[0]) if s["badge"] else 0
    seg_start = 0.0 if wi == 0 else t_at(wi)
    if s["id"] == "intro" or s["badge"]:
        p = f"{work}/{s['id']}_title.png"; cards.title_card(s, idx, p)
        shots.append((seg_start, p, "title"))
    for n, cap in enumerate(cards.captions(s["text"], target=130)):
        st = t_at(wi)
        if s["badge"] and n == 0: st = max(st, seg_start + 3.5)  # karta tytułowa min. 3,5 s
        p = f"{work}/{s['id']}_{n:02d}.png"
        if s["id"] == "cold": cards.cold_card(cap, p, n)
        else: cards.text_card(s, idx, cap, p, n)
        shots.append((st, p, "text"))
        wi += len(cap.split())

# 3) klipy z lekkim zoomem
end_pad = 2.0
clips = []
for j, (st, img, kind) in enumerate(shots):
    en = shots[j + 1][0] if j + 1 < len(shots) else total + end_pad
    d = max(en - st, 0.5); nfr = int(round(d * FPS))
    c = f"{work}/clip_{j:03d}.mp4"
    z = "1.0+0.05*on/{n}".format(n=nfr) if j % 2 == 0 else "1.05-0.05*on/{n}".format(n=nfr)
    vf = (f"scale=2880:1620,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={nfr}:s=1920x1080:fps={FPS},"
          f"fade=t=in:st=0:d=0.15,format=yuv420p")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", img, "-vf", vf, "-frames:v", str(nfr),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", c], check=True)
    clips.append(c)
lst = f"{work}/list.txt"
open(lst, "w").write("".join(f"file '{c}'\n" for c in clips))
video = f"{work}/video.mp4"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video], check=True)

# 4) podkład + miks + loudness
L = total + end_pad
beat = f"{work}/beat.wav"
subprocess.run([sys.executable, os.path.join(here, "beat.py"), beat, str(L)], check=True)
af = ("[1:a]volume=0.13[m];[0:a]adelay=0|0,apad=pad_dur=%s[v];[v][m]amix=inputs=2:duration=longest:normalize=0,"
      "loudnorm=I=-14:TP=-1:LRA=11[a]" % end_pad)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", vo, "-i", beat, "-i", video, "-filter_complex", af,
                "-map", "2:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-t", str(L), "-movflags", "+faststart", out], check=True)
print("OK", out, round(L, 1), "s,", len(shots), "ujęć")
