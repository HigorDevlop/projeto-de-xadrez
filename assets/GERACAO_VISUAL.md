# Arquivos visuais e prompts

As duas imagens foram criadas com a ferramenta integrada `image_gen`, no modo padrão da skill imagegen, e copiadas para o projeto. Nenhuma chave de API, vídeo externo ou download em tempo de execução é necessário.

- `cat-photoreal-atlas.png`: PNG RGBA, 1254 × 1254, 16 quadros em quatro colunas e quatro linhas. Consumido por `cat_mascot.py` e `cat-photoreal.js`.
- `bobby-photoreal-atlas.png`: PNG RGB, 1448 × 1086, 12 quadros em três colunas e quatro linhas. Arquivo legado; a abertura atual usa `fischer-karpov-opening.mp4`, derivado de `fischer-karpov-scene.png`.

As dimensões acima são as entregues pela ferramenta, diferentes das solicitadas nos prompts. O código calcula as células a partir das dimensões reais. Os arquivos antigos em SVG/WebGL permanecem no repositório, mas não são usados na abertura nem no mascote atuais. As cenas são representações geradas, não fotografias documentais ou filmagens históricas.

## Prompt do gato

```text
Use case: photorealistic-natural.
Asset type: transparent PNG animation sprite atlas for a chess website mascot.
Create ONE 2048x2048 image organized as an EXACT evenly spaced 4 columns by 4 rows grid, 16 equal square cells with no visible borders. Each cell contains the same ultra-photorealistic adult ginger tabby domestic cat seen DIRECTLY FROM ABOVE, head pointing toward the TOP of the image, entire animal including all paws ears whiskers and tail visible within its own cell. True photographic animal anatomy, fine individual hairs, natural ginger stripes, white toes and small white muzzle, green eyes partly visible from overhead, soft realistic light. Consistent animal identity, scale, overhead camera, center registration, neutral light and fur in ALL cells. The torso center must remain at the exact center of each cell. Cat should occupy about 78% of each cell's height and no more than 60% width. Frame order row major: cells 1-8 are consecutive natural walking gait phases, left/right paws moving alternately; cells 9-10 are standing still and attentively observing with very slight head turn; cell 11 crouches preparing a small hop; cell 12 starts the hop with paws pulling in; cell 13 is gently airborne with tucked paws; cell 14 lands naturally; cell 15 lies down watching with tail curled left; cell 16 same lying pose with tail curled slightly right. This is one aligned animation sheet, not a collage. TRANSPARENT alpha background around EACH animal, no floor, no scenery, no contact shadows baked in, no text, no numbers, no outlines, no separator grid. Absolutely no illustration, toy, polygon mesh, cartoon, icon or plastic 3D render. The result must look like photographs of a real cat in 16 poses and be suitable for a smooth sprite animation. Save the output as PNG with actual transparency.
```

## Prompt do Bobby Fischer

```text
Use case: historical-scene, photorealistic-natural.
Asset type: aligned photographic animation atlas for a chess website opening.
Generate one image, 1920x1440 pixels, containing EXACTLY 3 columns and 4 rows of equally sized 640x360 rectangular frames, edge to edge with NO gutters, NO grid lines, NO text, NO captions. Read frames left to right then top to bottom.
Every frame is the SAME locked-off wide cinematic camera in a realistic elegant 1970s chess study room, warm natural window light, dark green walls, polished wooden floor, wooden table and beautifully realistic green/ivory chessboard with Staunton pieces, wooden leather-backed chair. Full adult Bobby Fischer around age 29, recognizably accurate face, authentic dark suit, white shirt, modest tie, realistic skin and hands. Entire person, chair and chessboard remain within every frame. Real photographs, documentary film quality, NOT drawings, NOT cartoons, NOT painted or CGI style. All architecture, furniture, lighting, composition, chess pieces and clothing must be IDENTICAL and aligned pixel-for-pixel between frames; only the man and pulled chair move.
12 successive frames of one continuous short action: 1 Fischer at the open door left, 2 walking forward first step, 3 walking a second step toward table, 4 approaching chair, 5 reaches for chair back, 6 pulls chair backward, 7 steps in front of chair, 8 begins lowering himself, 9 halfway sitting, 10 seated naturally, 11 leaning slightly toward chessboard, 12 quietly studying the board attentively. Each frame a clean 16:9 photograph filling its cell exactly. Anatomically plausible limbs and hands, physically consistent chair, controlled small changes between consecutive frames. Do not add additional people, speech bubbles, watermarks or any writing. No invented logos. Final output must be the 3x4 atlas, not a single scene.
```

## Revisão Fischer × Karpov

O cenário novo foi gerado com a ferramenta integrada image_gen. O arquivo final, o prompt completo e a distinção entre animação de câmera e filmagem contínua estão em [BOBBY_STUDY_VIDEO.md](BOBBY_STUDY_VIDEO.md). O gato continua usando o atlas original; suas poses são animadas em canvas pela sequência de entrada e descanso em `cat-photoreal.js`.
