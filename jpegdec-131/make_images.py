# Writes test JPEGs: a smooth gradient with a grid, at a width that is not a multiple of 16, and one that is
import sys
from PIL import Image, ImageDraw
out = sys.argv[1]
for w, h in ((203, 157), (320, 240)):
    im = Image.new("RGB", (w, h))
    im.putdata([(x * 255 // w, y * 255 // h, (x + y) * 255 // (w + h)) for y in range(h) for x in range(w)])
    d = ImageDraw.Draw(im)
    for x in range(0, w, 20):
        d.line((x, 0, x, h), fill=(255, 255, 255))
    for name, sub in (("444", 0), ("422", 1), ("420", 2)):
        im.save(f"{out}/{name}_{w}x{h}.jpg", quality=90, subsampling=sub)
