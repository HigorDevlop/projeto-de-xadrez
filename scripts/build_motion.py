"""Produz vídeos locais H.264. A abertura usa uma imagem com movimento de câmera.

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


def build_opening():
    """60 fps de câmera contínua, sem inventar movimento corporal entre fotografias."""
    command = [imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-loglevel', 'error',
               '-i', str(ROOT / 'fischer-karpov-scene.png'), '-an', '-vf',
               "scale=3840:-2,zoompan=z='1+0.035*(on/449)*(on/449)*(3-2*on/449)':"
               "x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=450:s=1920x1080:fps=60,"
               'fade=t=in:st=0:d=0.35,fade=t=out:st=7:d=0.5',
               '-frames:v', '450', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
               '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
               str(ROOT / 'fischer-karpov-opening.mp4')]
    subprocess.run(command, check=True)
    print('fischer-karpov-opening.mp4: 1920x1080, 60 quadros/s, 7,5 segundos')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opening-only', action='store_true')
    args = parser.parse_args()
    build_opening()
    if not args.opening_only:
        build('forge-photoreal', 3, 3, 6, .3)
