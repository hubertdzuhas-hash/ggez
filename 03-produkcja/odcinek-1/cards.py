"""Plansze 1920x1080 w identyfikacji marki (grafit/złoto/biel/czerwień)."""
import re, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1920, 1080
GOLD, BG, WHITE, RED = (245,183,0), (20,20,20), (255,255,255), (230,57,70)
GREY = (120,120,120)
ANTON = "/tmp/claude-0/-home-user-ggez/0d8ec3d4-9ab0-5df2-b74e-8f847ab040a2/scratchpad/Anton.ttf"
INTER = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
INTER_B = "/usr/share/fonts/opentype/inter/Inter-Black.otf"

def F(path, size): return ImageFont.truetype(path, size)

def background(seed, watermark=""):
    random.seed(seed)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # winieta + delikatne złote smugi
    glow = Image.new("RGB", (W, H), BG); g = ImageDraw.Draw(glow)
    cx, cy = random.randint(300, 1600), random.randint(200, 800)
    for r in range(900, 0, -30):
        c = int(20 + 18 * (1 - r/900))
        g.ellipse([cx-r, cy-r*0.7, cx+r, cy+r*0.7], fill=(c+6, c+3, c-4))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(60)), 1.0)
    d = ImageDraw.Draw(img)
    if watermark:
        f = F(ANTON, 460)
        bb = d.textbbox((0, 0), watermark, font=f)
        d.text((W - (bb[2]-bb[0]) - 60, H - (bb[3]-bb[1]) - 260), watermark, font=f, fill=(34,33,30))
    # ziarno
    noise = Image.effect_noise((W, H), 18).convert("RGB")
    img = Image.blend(img, noise, 0.04)
    return img

def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def progress(d, idx, total=12):
    # pasek 1..12 na dole
    x0, y, step = 560, 1010, 70
    for i in range(1, total+1):
        x = x0 + (i-1)*step
        col = GOLD if i == idx else ((90,90,90) if i > idx else (170,140,40))
        r = 14 if i == idx else 9
        d.ellipse([x-r, y-r, x+r, y+r], fill=col)
        if i < total: d.line([x+r+4, y, x+step-14, y], fill=(60,60,60), width=3)

def title_card(seg, idx, path):
    img = background(seg["id"], seg.get("years","").split(" ")[0])
    d = ImageDraw.Draw(img)
    if seg["badge"]:
        fb = F(ANTON, 150)
        badge = "#" + seg["badge"]
        bw = d.textlength(badge, font=fb)
        d.rounded_rectangle([140, 200, 140+bw+80, 400], 18, fill=GOLD)
        d.text((180, 205), badge, font=fb, fill=BG)
    ft = F(ANTON, 130 if len(seg["title"]) < 24 else 104)
    y = 450 if seg["badge"] else 360
    for line in wrap(d, seg["title"], ft, 1640):
        d.text((140, y), line, font=ft, fill=WHITE); y += ft.size + 20
    fs = F(INTER_B, 52)
    meta = "  ·  ".join(x for x in [seg.get("years",""), seg.get("sub","")] if x)
    d.text((144, y + 20), meta.upper(), font=fs, fill=GOLD)
    if idx: progress(d, idx)
    img.save(path)

def text_card(seg, idx, caption, path, n):
    img = background(seg["id"] + str(n), seg.get("years","").split(" ")[0])
    d = ImageDraw.Draw(img)
    # nagłówek segmentu
    fh = F(ANTON, 54)
    head = (("#" + seg["badge"] + "  ") if seg["badge"] else "") + seg["title"]
    d.rectangle([0, 60, 22, 130], fill=GOLD)
    d.text((70, 62), head, font=fh, fill=GOLD)
    if seg.get("years"):
        d.text((72, 135), seg["years"], font=F(INTER, 34), fill=GREY)
    # duży tekst narracji, wyróżnienie słów w cudzysłowie/kluczowych
    size = 76
    while True:
        fc = F(INTER_B, size)
        lines = wrap(d, caption, fc, 1600)
        if len(lines) * (size * 1.28) <= 640 or size <= 48: break
        size -= 4
    total_h = len(lines) * size * 1.28
    y = 260 + (640 - total_h) / 2
    for line in lines:
        x = 160
        for i, w in enumerate(line.split()):
            col = RED if w.strip(".,!?").lower() in KEY else WHITE
            d.text((x, y), w, font=fc, fill=col)
            x += d.textlength(w + " ", font=fc)
        y += size * 1.28
    d.text((W-330, 40), "BROFESSOR BEATS", font=F(ANTON, 40), fill=(70,70,70))
    if idx: progress(d, idx)
    img.save(path)

KEY = {"beef","diss","war","wars","killed","murdered","shot","ether","won","winner","lost","dead","receipts","knockout","undefeated","catchier","memes","speed","sells"}

def captions(text, target=230):
    sents = re.split(r"(?<=[.?!])\s+", text.strip())
    out, cur = [], ""
    for s in sents:
        if cur and len(cur) + len(s) > target: out.append(cur); cur = s
        else: cur = (cur + " " + s).strip()
    if cur: out.append(cur)
    return out
