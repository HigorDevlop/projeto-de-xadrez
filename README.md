# Acervo de xadrez

Depois de clonar o repositório, execute `python iniciar.py` na pasta do projeto e abra http://127.0.0.1:8501. O inicializador multiplataforma cria o ambiente virtual e instala as dependências necessárias automaticamente.

No Windows, `iniciar.bat` e `iniciar.ps1` continuam disponíveis como atalhos equivalentes.

- Arraste as peças ou clique em origem e destino. A peça acompanha o ponteiro, desliza ao soltar e retorna à origem se o destino for ilegal; a animação respeita a preferência por movimento reduzido. Promoções permitem escolher a peça. Em **Nova partida · jogar livremente**, jogue pelos dois lados sem precisar analisar antes.
- **Classificar ao mover peças** usa o Stockfish configurado para avaliar cada novo lance. O símbolo aparece na casa de destino e na lista de lances. Sem engine, as peças continuam funcionando; avaliações não são inventadas.
- As setas **←/→** navegam pelos lances; **Home/End** levam ao início/final. Os atalhos não atuam durante a edição de textos ou seletores. O tabuleiro não exibe coordenadas.
- **Análise da partida** fica compacta logo abaixo do tabuleiro, com precisão e contagens por jogador, sem centipeões. As seções separadas de leitura e resumo do lance foram removidas. Ao testar uma alternativa, a linha anterior é preservada como variante no PGN exportado.
- No **Histórico de partidas · Chess.com**, busque o usuário e selecione a partida: ela abre automaticamente no tabuleiro. O aplicativo carrega até 100 partidas recentes, consultando automaticamente até 12 arquivos mensais com partidas, sem exigir seleção de mês nem outro botão para abrir. São consultados dados públicos; não é preciso senha.

## Tutor e livros

O painel mostra somente o nome **Bobby Fischer**, o retrato realista e uma explicação em parágrafo único, atualizada automaticamente ao trocar o lance. O texto descreve o movimento concreto, desenvolvimento, controle de casas, capturas, ameaças, resposta adversária e uma melhoria pertinente. Sem modelo de linguagem, o texto usa efeitos verificados no tabuleiro; com Ollama, esses fatos e os trechos recuperados orientam a explicação. O [prompt e a origem do retrato](assets/IMAGE_GENERATION.md) estão documentados. Carregue livros PDF com texto selecionável, TXT/Markdown, PGN comentado ou livros Polyglot (`.bin`). As fontes e páginas aparecem em **Referências consultadas**. PDFs digitalizados precisam de OCR; Polyglot contém jogadas, sem explicações em prosa.

A busca do Chess.com fica no topo. As configurações ficam recolhidas no menu lateral; use a seta no canto superior esquerdo para abri-las. A aba **Estudo com livros** contém somente um tabuleiro inicial e o campo de upload, sem processamento do livro nesta etapa e sem alterar a partida da aba Análise.

## Classificação e aberturas

Os limites seguem a [tabela pública do Chess.com](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc): perdas de pontos esperados abaixo de 0,02 são Excelente; de 0,02 a 0,05, Bom; de 0,05 a 0,10, Imprecisão; de 0,10 a 0,20, Erro; a partir de 0,20, Erro grave. Limites inferiores inclusivos. O primeiro lance da engine é Melhor quando não recebe categoria especial.

**É uma aproximação, não o algoritmo idêntico do Chess.com.** As probabilidades vêm da distribuição vitória/empate/derrota do Stockfish (com fallback do python-chess para engines antigas), não do modelo privado ajustado ao rating. Brilhante, Ótimo e Oportunidade perdida usam heurísticas locais e podem divergir do site. Oportunidade perdida precisa da análise da sequência, pois depende do erro adversário anterior.

O [catálogo de aberturas CC0 do Lichess](data/openings/README.md) é incluído automaticamente, além dos livros PGN/Polyglot carregados. Todo lance encontrado recebe prioridade de Livro e o símbolo 📖, mesmo antes da análise. Textos de PDF, sem linhas de jogadas indexáveis, servem como referências do tutor e não como prova automática de lance de abertura.

A continuação de até três jogadas completas (seis meios-lances) é calculada automaticamente com Stockfish e incorporada ao texto corrido. **Reexplicar lance** permite tentar novamente a IA. A profundidade real depende da qualidade selecionada. A linha é uma possibilidade de jogo, não uma previsão.

Para gerar explicações por IA, instale e inicie [Ollama](https://ollama.com), com um modelo de texto adequado ao seu computador. Em **Configurações → IA local · Ollama**, clique em **Detectar modelos locais** ou informe o nome exato mostrado por `ollama list`. O app usa a API local em `127.0.0.1:11434`; envia a posição, a linha da engine e até três trechos relevantes ao modelo. Sem Ollama, continua mostrando orientação básica identificada como tal. A integração não instala nem baixa modelos automaticamente.

Os livros e partidas importados permanecem na sessão e nos caches locais do Streamlit; baixe o PGN para guardar a partida. O tutor consulta trechos, não treina um modelo com o livro inteiro.

## Precisão

Quando o arquivo público inclui `accuracies`, os valores são exibidos como **Precisão**, com fonte Chess.com. Testar uma variante descarta esses valores, porque já não representam a partida modificada. Quando não há valores oficiais, **Precisão estimada** calcula a média aritmética da precisão dos lances avaliados usando as curvas públicas de probabilidade de vitória e precisão por lance do [Lichess](https://lichess.org/page/accuracy). A comparação usa a melhor continuação versus a jogada realizada. A agregação é local e não reproduz nem CAPS2 nem a agregação ponderada do Lichess. Análises incompletas são identificadas como parciais; sem lances avaliados, aparece `—`.

## Verificação

Com pytest instalado: `.venv\Scripts\python.exe -m pytest tests -q`. Os testes cobrem jogadas especiais, variantes, exportação parcial, leitura PDF/PGN, contexto da IA, erros da API e fluxos de interface. Testes de Stockfish são ignorados quando o executável não está disponível.

Referências: [API pública do Chess.com](https://www.chess.com/news/view/published-data-api), [API de chat do Ollama](https://docs.ollama.com/api/chat).
