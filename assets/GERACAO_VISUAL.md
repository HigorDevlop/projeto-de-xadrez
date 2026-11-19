# Arquivos visuais e prompts

A imagem do gato foi criada com a ferramenta integrada `image_gen`, no modo padrão da skill imagegen, e copiada para o projeto. A ilustração `coach-instructor.svg` é um vetor original desenhado no código. A foto de entrada `welcome-king.jpg` é uma fotografia em domínio público (CC0 1.0), obtida em https://www.rawpixel.com/image/5918046/free-chess-image-public-domain-hobby-cc0-photo, recortada em 16:9 e levemente tingida de azul. Nenhuma chave de API, vídeo externo ou download em tempo de execução é necessário.

- `cat-photoreal-atlas.png`: PNG RGBA, 1254 × 1254, 16 quadros em quatro colunas e quatro linhas. Consumido por `cat_mascot.py` e `cat-photoreal.js`.

As dimensões acima são as entregues pela ferramenta, diferentes das solicitadas nos prompts. O código calcula as células a partir das dimensões reais. Os arquivos antigos em SVG/WebGL permanecem no repositório, mas não são usados na abertura nem no mascote atuais. As cenas são representações geradas, não fotografias documentais ou filmagens históricas.

## Prompt do gato

```text
Use case: photorealistic-natural.
Asset type: transparent PNG animation sprite atlas for a chess website mascot.
Create ONE 2048x2048 image organized as an EXACT evenly spaced 4 columns by 4 rows grid, 16 equal square cells with no visible borders. Each cell contains the same ultra-photorealistic adult ginger tabby domestic cat seen DIRECTLY FROM ABOVE, head pointing toward the TOP of the image, entire animal including all paws ears whiskers and tail visible within its own cell. True photographic animal anatomy, fine individual hairs, natural ginger stripes, white toes and small white muzzle, green eyes partly visible from overhead, soft realistic light. Consistent animal identity, scale, overhead camera, center registration, neutral light and fur in ALL cells. The torso center must remain at the exact center of each cell. Cat should occupy about 78% of each cell's height and no more than 60% width. Frame order row major: cells 1-8 are consecutive natural walking gait phases, left/right paws moving alternately; cells 9-10 are standing still and attentively observing with very slight head turn; cell 11 crouches preparing a small hop; cell 12 starts the hop with paws pulling in; cell 13 is gently airborne with tucked paws; cell 14 lands naturally; cell 15 lies down watching with tail curled left; cell 16 same lying pose with tail curled slightly right. This is one aligned animation sheet, not a collage. TRANSPARENT alpha background around EACH animal, no floor, no scenery, no contact shadows baked in, no text, no numbers, no outlines, no separator grid. Absolutely no illustration, toy, polygon mesh, cartoon, icon or plastic 3D render. The result must look like photographs of a real cat in 16 poses and be suitable for a smooth sprite animation. Save the output as PNG with actual transparency.
```
