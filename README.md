# Acervo de xadrez

Execute `python iniciar.py` nesta pasta e abra http://127.0.0.1:8501. O inicializador cria o ambiente virtual e instala as dependências. No Windows, também há `iniciar.bat` e `iniciar.ps1`.

## Stockfish e livros

O único motor de IA é o **Stockfish**. A cópia Windows restaurada é a versão 17.1, em `engines/stockfish.exe`. Para outra instalação ou sistema operacional, configure `STOCKFISH_PATH` ou coloque o binário nativo em `engines/stockfish`. Não há Ollama, modelo de linguagem, API de análise ou chave necessária. Veja [engines/README.md](engines/README.md).

O aplicativo primeiro extrai o texto dos livros e indexa comentários PGN por posição, além de temas em português/inglês (centro, desenvolvimento, roque, estrutura de peões, finais etc.). Os arquivos da barra lateral e da aba **Estudo com livros** são combinados. Esse índice é preparado antes de iniciar o motor e reutilizado enquanto os livros não mudarem.

Depois, o Stockfish avalia a melhor jogada, a segunda alternativa e o lance realizado. O aplicativo aplica as faixas de pontos esperados abaixo e compõe explicações determinísticas com trechos literais, arquivo/página e fatos verificáveis do tabuleiro. Comentários PGN de uma posição exata têm prioridade; correspondências temáticas são identificadas como tal. Se nenhum trecho corresponder, isso aparece explicitamente. Livros Polyglot contêm jogadas, não prosa.

**O Stockfish não lê nem é treinado pelos livros.** A consulta bibliográfica é feita pelo aplicativo; o cálculo enxadrístico é feito pelo motor. Não há compreensão semântica por um modelo de linguagem. O material orienta as explicações, mas não substitui nem altera arbitrariamente os cálculos. Os trechos usados também ficam disponíveis no painel do lance e no PGN exportado.

Todas as explicações são preparadas em um único lote em segundo plano. Navegar pelos lances usa os resultados da sessão, sem novas análises. Trocar partida, variante, livros, rating ou qualidade invalida o lote. O trabalho anterior é cancelado entre buscas; respostas antigas não substituem a partida atual. Há apenas um processo Stockfish ativo por aplicativo, com **1 thread e 64 MB de hash** (o consumo total inclui também o executável e suas redes NNUE). O processo encerra ao concluir, falhar ou cancelar.

As qualidades Rápida, Equilibrada e Profunda limitam cada busca a 0,08 s, 0,25 s e 0,7 s, respectivamente, além de limites de profundidade. Isso implica uma aproximação dependente do tempo disponível. Não é preciso conexão para avaliar uma partida com os livros já carregados; histórico Chess.com e táticos Lichess continuam usando suas APIs públicas.

## Perfil e tabuleiro

- O quadrado no canto superior esquerdo abre o seletor de imagens do navegador, incluindo a galeria em dispositivos móveis. Arraste a imagem e ajuste o zoom para recortá-la; **Usar foto** envia somente o corte quadrado. PNG, JPEG e WebP são aceitos, até 10 MB e 20 milhões de pixels. A foto permanece na sessão.
- O nick e o rating público da modalidade jogada mais recentemente no Chess.com aparecem abaixo da foto. Não é necessária senha. O último nick é salvo localmente; a consulta de rating ocorre em segundo plano.
- Arraste peças, escolha promoções e use as setas ←/→ ou Home/End para navegar. Alternativas preservam a linha anterior como variante no PGN exportado.
- O ícone de folha ao lado da engrenagem abre a lista de lances PGN. Clique em qualquer lance ou em **Posição inicial** para atualizar o tabuleiro e a explicação. A aba **Anotações** também contém a lista e o tabuleiro.
- O histórico consulta até 100 partidas públicas recentes, em até 12 meses com partidas. Selecione uma partida para abri-la automaticamente.
- Livros PDF com texto selecionável, TXT, Markdown, PGN comentado e Polyglot podem ser carregados. Os trechos são indexados localmente e as fontes usadas são exibidas com a explicação. PDFs digitalizados precisam de OCR.

## Táticos

Escolha um dos 12 cards ilustrados e selecione os ratings inicial e final. A busca começa automaticamente quando ambos estão definidos. Não há slider nem botão adicional de busca.

A [API pública do Lichess](https://lichess-org.github.io/api/#tag/Puzzles/operation/apiPuzzleNext) oferece dificuldade relativa, com referência 1500 para visitantes anônimos, e não um filtro numérico exato. O cliente faz no máximo três tentativas sequenciais, valida tema e rating e **não apresenta exercícios fora da faixa como resultados compatíveis**. Se não encontrar, informa o motivo e permite ampliar a faixa ou tentar novamente. Não baixa o banco de táticos. Faixas extremas ou estreitas podem não retornar resultados.

**Recomeçar tático** restaura a posição inicial sem acesso à rede. Cada tentativa tem uma revisão de estado: eventos antigos são ignorados, e seleção, promoção e animação são limpas. **Próximo tático** faz uma nova busca. A partida principal permanece preservada.

## Pontos esperados e classificação

O Stockfish fornece WDL, convertido em pontos esperados entre 0 e 1 da perspectiva do jogador que fez o lance: `P(vitória) + 0,5 × P(empate)`. Isso não é estritamente a probabilidade de vitória quando empates são possíveis. A perda é a diferença entre a melhor continuação e a jogada realizada, sem usar variação bruta de centipeões.

| Categoria | Regra |
|---|---|
| Brilhante (!!) | Sacrifício produtivo de peça validado na continuação do Stockfish, posição com pelo menos 0,5 ponto esperado e pequena perda tolerada conforme o rating |
| Grande Lance (!) | Perda zero, ao menos 0,5 ponto esperado e segunda melhor alternativa pelo menos 0,10 inferior |
| Melhor | Perda zero |
| Excelente | Perda maior que zero e menor que 0,02 |
| Bom | De 0,02 até menos de 0,05 |
| Imprecisão | De 0,05 até menos de 0,10 |
| Erro | De 0,10 até 0,20, inclusive |
| Capivorada | Acima de 0,20 |

As regras especiais são aproximações documentadas, não o algoritmo privado do Chess.com. O sacrifício exige déficit material de pelo menos três peões mantido após duas oportunidades de resposta ou até mate; ofertas de peão e trocas equilibradas não bastam. A tolerância de perda para Brilhante diminui de 2% para 0,5% conforme o rating: `clamp(0,02 − (rating − 800) / 120000, 0,005, 0,02)`. Usa-se 1500 quando o rating não está disponível. A qualidade da classificação depende da análise WDL do Stockfish; suas probabilidades não são calibradas ao rating humano. O rating ajusta somente a tolerância de Brilhante.

O catálogo de aberturas CC0 do Lichess continua disponível como fonte, mas não sobrepõe a classificação por pontos esperados. Antes de receber a análise, lances catalogados podem mostrar o símbolo de Livro.

Precisão oficial do Chess.com é preservada quando disponível. Nos demais casos, a precisão é uma média estimada de uma curva exponencial aplicada à perda de pontos esperados; não reproduz CAPS2 nem a agregação do Lichess.

Referência conceitual: [classificação de lances do Chess.com](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc). Os limites acima seguem o pedido deste projeto, incluindo Capivorada estritamente acima de 20%.

## Publicação e testes

`Dockerfile` e `render.yaml` permitem publicar no Render. A imagem Linux instala Stockfish e define STOCKFISH_PATH. Não são necessárias credenciais de IA.

Na pasta do aplicativo, execute `.venv\Scripts\python.exe -m pytest tests -q` (Linux/macOS: `.venv/bin/python -m pytest tests -q`). A suíte cobre regras de xadrez, importação, Stockfish e fontes bibliográficas, limites de classificação, navegação sem novas avaliações, busca por faixa e reinício de táticos. Os testes opcionais de navegador usam Playwright e Edge/Chromium já instalado; não iniciam o servidor Streamlit nem baixam navegadores.
