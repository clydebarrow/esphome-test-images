// Decodes a JPEG twice in RGB565: once through the draw callback, once into a framebuffer whose
// pitch is the image width. Prints how many pixels differ, and which rows and columns they are in.
// Build: cc -O2 -D__LINUX__ -DNO_SIMD -I<JPEGDEC>/src fb_check.c -o fb_check -lm
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "JPEGDEC.h"
#undef HAS_NEON  // JPEGDEC.h sets it on aarch64 even with NO_SIMD; test the C path
#include "jpeg.inl"
#if defined(HAS_NEON) || defined(HAS_SSE) || defined(HAS_SIMD)
#error "SIMD path compiled in"
#endif

static JPEGIMAGE jpg;
static uint16_t *ref;
static int ref_w;

static int draw(JPEGDRAW *d) {
  for (int y = 0; y < d->iHeight; y++)
    memcpy(&ref[(d->y + y) * ref_w + d->x], &d->pPixels[y * d->iWidth], d->iWidthUsed * 2);
  return 1;
}

int main(int argc, char **argv) {
  if (!JPEG_openFile(&jpg, argv[1], draw))
    return 1;
  const int w = jpg.iWidth, h = jpg.iHeight;
  ref_w = w;
  ref = calloc((size_t) w * h, 2);
  jpg.ucPixelType = RGB565_LITTLE_ENDIAN;
  JPEG_decode(&jpg, 0, 0, 0);
  const int subsample = JPEG_getSubSample(&jpg);
  JPEG_close(&jpg);

  // Same allocation as linux/examples/c_cmdline: width x (height + 15)
  uint16_t *fb = calloc((size_t) w * (h + 15), 2);
  JPEG_openFile(&jpg, argv[1], draw);
  JPEG_setFramebuffer(&jpg, fb);
  jpg.ucPixelType = RGB565_LITTLE_ENDIAN;
  JPEG_decode(&jpg, 0, 0, 0);
  JPEG_close(&jpg);

  int bad = 0, bad_rows = 0, min_x = w, max_x = -1;
  for (int y = 0; y < h; y++) {
    int row_bad = 0;
    for (int x = 0; x < w; x++) {
      if (fb[y * w + x] != ref[y * w + x]) {
        bad++;
        row_bad = 1;
        if (x < min_x) min_x = x;
        if (x > max_x) max_x = x;
      }
    }
    bad_rows += row_bad;
  }
  printf("%s: %dx%d, subsampling 0x%02x: ", argv[1], w, h, subsample);
  if (bad == 0)
    printf("identical\n");
  else
    printf("%d pixels differ, on %d of %d rows, columns %d-%d\n", bad, bad_rows, h, min_x, max_x);
  return bad != 0;
}
