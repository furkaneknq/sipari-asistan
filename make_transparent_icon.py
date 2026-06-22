import sys
from PIL import Image, ImageDraw

png_path = r'C:\Users\User\.gemini\antigravity\brain\4e736289-a581-4359-b9d6-489def411bdf\green_icon_transparent_1782119023718.png'
out_path = r'C:\Users\User\Desktop\yeni_icon.ico'

img = Image.open(png_path).convert("RGBA")

# Use flood fill to replace white background connected to borders with transparent
ImageDraw.floodfill(img, xy=(0, 0), value=(255, 255, 255, 0), thresh=20)
ImageDraw.floodfill(img, xy=(img.width-1, 0), value=(255, 255, 255, 0), thresh=20)
ImageDraw.floodfill(img, xy=(0, img.height-1), value=(255, 255, 255, 0), thresh=20)
ImageDraw.floodfill(img, xy=(img.width-1, img.height-1), value=(255, 255, 255, 0), thresh=20)

sizes = [256, 128, 64, 48, 32, 24, 16]
imgs = []
for s in sizes:
    imgs.append(img.resize((s, s), Image.Resampling.LANCZOS))

imgs[0].save(out_path, format='ICO', sizes=[(s,s) for s in sizes], append_images=imgs[1:])
print('Icon with transparent background created on desktop.')
