import struct, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

out = sys.argv[1]

def qoi_encode(im):
    im = im.convert("RGBA")
    w, h = im.size
    px = im.tobytes()
    out = bytearray(b"qoif" + struct.pack(">IIBB", w, h, 4 if im.mode == "RGBA" else 3, 0))
    index = [(0, 0, 0, 0)] * 64
    prev = (0, 0, 0, 255)
    run = 0
    n = w * h
    for i in range(n):
        p = tuple(px[i * 4:i * 4 + 4])
        if p == prev:
            run += 1
            if run == 62 or i == n - 1:
                out.append(0xC0 | (run - 1)); run = 0
            continue
        if run:
            out.append(0xC0 | (run - 1)); run = 0
        h_ = (p[0] * 3 + p[1] * 5 + p[2] * 7 + p[3] * 11) % 64
        if index[h_] == p:
            out.append(h_)
        else:
            index[h_] = p
            if p[3] == prev[3]:
                dr = (p[0] - prev[0] + 128) % 256 - 128
                dg = (p[1] - prev[1] + 128) % 256 - 128
                db = (p[2] - prev[2] + 128) % 256 - 128
                if -2 <= dr <= 1 and -2 <= dg <= 1 and -2 <= db <= 1:
                    out.append(0x40 | (dr + 2) << 4 | (dg + 2) << 2 | (db + 2))
                elif -32 <= dg <= 31 and -8 <= dr - dg <= 7 and -8 <= db - dg <= 7:
                    out += bytes([0x80 | (dg + 32), (dr - dg + 8) << 4 | (db - dg + 8)])
                else:
                    out += bytes([0xFE, p[0], p[1], p[2]])
            else:
                out += bytes([0xFF, *p])
        prev = p
    out += bytes([0] * 7 + [1])
    return bytes(out)

def qoi_decode(data):
    w, h = struct.unpack(">II", data[4:12])
    pos, px, index, p = 14, [], [(0, 0, 0, 0)] * 64, (0, 0, 0, 255)
    while len(px) < w * h:
        b = data[pos]; pos += 1
        if b == 0xFE: p = (*data[pos:pos + 3], p[3]); pos += 3
        elif b == 0xFF: p = tuple(data[pos:pos + 4]); pos += 4
        elif b >> 6 == 0: p = index[b]
        elif b >> 6 == 1: p = ((p[0] + (b >> 4 & 3) - 2) % 256, (p[1] + (b >> 2 & 3) - 2) % 256, (p[2] + (b & 3) - 2) % 256, p[3])
        elif b >> 6 == 2:
            dg = (b & 0x3F) - 32; b2 = data[pos]; pos += 1
            p = ((p[0] + dg + (b2 >> 4) - 8) % 256, (p[1] + dg) % 256, (p[2] + dg + (b2 & 15) - 8) % 256, p[3])
        else:
            px.extend([p] * ((b & 0x3F) + 1)); index[(p[0]*3+p[1]*5+p[2]*7+p[3]*11) % 64] = p; continue
        index[(p[0]*3+p[1]*5+p[2]*7+p[3]*11) % 64] = p
        px.append(p)
    return w, h, bytes(b for q in px[:w * h] for b in q)

# A generated picture with smooth gradients and fine noise, so it compresses about as badly as a photo
size = (945, 707)
red = Image.radial_gradient("L").resize(size)
green = Image.linear_gradient("L").rotate(90).resize(size)
blue = Image.blend(Image.effect_noise(size, 60).filter(ImageFilter.GaussianBlur(2)), Image.linear_gradient("L").resize(size), 0.5)
photo = Image.merge("RGB", (red, green, blue))
photo = Image.blend(photo, Image.merge("RGB", [Image.effect_noise(size, 24)] * 3), 0.15)
ImageDraw.Draw(photo).ellipse((300, 150, 650, 500), fill=(250, 220, 60))
photo.save(f"{out}/photo24.bmp")
photo.quantize(256).convert("P").save(f"{out}/photo8.bmp")
photo.convert("1").save(f"{out}/mono.bmp")

# A flat image with large areas of one color, like a dashboard
dash = Image.new("RGB", (800, 480), (24, 28, 36))
d = ImageDraw.Draw(dash)
font = ImageFont.load_default(size=40)
for i, col in enumerate([(220, 80, 60), (60, 160, 220), (90, 200, 120), (240, 190, 60)]):
    x, y = 30 + (i % 2) * 380, 30 + (i // 2) * 220
    d.rounded_rectangle((x, y, x + 360, y + 200), 20, fill=(40, 46, 58))
    d.rectangle((x + 20, y + 140, x + 20 + 80 * (i + 1), y + 170), fill=col)
    d.text((x + 20, y + 30), f"Sensor {i + 1}: {17 + i * 3}.{i}", fill=(230, 230, 230), font=font)

for name, im in (("photo", photo), ("dashboard", dash)):
    q = qoi_encode(im)
    w, h, raw = qoi_decode(q)
    assert raw == im.convert("RGBA").tobytes(), name
    open(f"{out}/{name}.qoi", "wb").write(q)
dash.save(f"{out}/dashboard.bmp")
