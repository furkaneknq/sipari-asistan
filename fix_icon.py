import sys
from PIL import Image

png_path = r'C:\Users\User\.gemini\antigravity\brain\4e736289-a581-4359-b9d6-489def411bdf\modern_app_icon_1782114289221.png'
ico1 = r'C:\Users\User\Desktop\Proje\installer\windows\app.ico'
ico2 = r'C:\Users\User\Desktop\Proje\order_tracking\assets\app.ico'
sizes = [256, 128, 64, 48, 32, 24, 16]

img = Image.open(png_path).convert('RGBA')
imgs = []
for s in sizes:
    imgs.append(img.resize((s, s), Image.Resampling.LANCZOS))

imgs[0].save(ico1, format='ICO', sizes=[(s,s) for s in sizes], append_images=imgs[1:])
imgs[0].save(ico2, format='ICO', sizes=[(s,s) for s in sizes], append_images=imgs[1:])
print('Icon converted properly.')
