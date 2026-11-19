"""Produz o vídeo local H.264 do ferreiro dos exercícios táticos.

Dependências de construção: Pillow e imageio-ffmpeg (dispensáveis na execução do site).
Execute: python scripts/build_motion.py
"""
from pathlib import Path
import subprocess
from PIL import Image
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1] / 'assets'


def build(name, columns, rows, rate, hold):
    atlas = Image.open(ROOT / f'{name}-atlas.png').convert('RGB')
    # Arredondar fronteiras evita carregar pixels da célula vizinha.
    width, height = atlas.size
    size = (round(width / columns / 2) * 2, round(height / rows / 2) * 2)
    frames = [atlas.crop((round(x * width / columns), round(y * height / rows),
                          round((x + 1) * width / columns), round((y + 1) * height / rows)))
              .resize(size, Image.Resampling.LANCZOS)
              for y in range(rows) for x in range(columns)]
    frames[0].save(ROOT / f'{name}-poster.jpg', quality=94)
    command = [imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error',
               '-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size', f'{size[0]}x{size[1]}',
               '-framerate', str(rate), '-i', 'pipe:0', '-an', '-vf',
               'minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none,'
               f'tpad=stop_mode=clone:stop_duration={hold}',
               '-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-pix_fmt', 'yuv420p',
               '-movflags', '+faststart', str(ROOT / f'{name}.mp4')]
    subprocess.run(command, input=b''.join(frame.tobytes() for frame in frames + [frames[-1]]), check=True)
    print(f'{name}.mp4: {size[0]}x{size[1]}, 30 quadros/s')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    build('forge-photoreal', 3, 3, 6, .3)
