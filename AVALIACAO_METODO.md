# Avaliação de partidas

O motor UCI local avalia a posição inicial e cada posição efetivamente alcançada. O gráfico e a precisão usam essa sequência, com perspectiva consistente. A comparação do lance jogado com a melhor opção continua a usar MultiPV e verifica perdas importantes.

A precisão implementa a curva de chances em centipawns, a curva exponencial com bônus de incerteza, as janelas de volatilidade e a combinação das médias ponderada e harmônica publicadas pelo Lichess. Os dados vêm do motor local; não são resultados oficiais dos sites. Análises antigas sem a sequência preservam a estimativa anterior até uma nova análise.

Referências consultadas em 03/11/2026:
- https://lichess.org/page/accuracy
- https://github.com/lichess-org/lila/blob/master/modules/analyse/src/main/AccuracyPercent.scala
- https://www.chessigma.com/products/analysis

O ChessSigma descreve comparação com a melhor jogada, perda em centipawns e análise local com Stockfish. A documentação consultada não publica a fórmula numérica completa de precisão; não foi inventada uma réplica. As sete categorias adicionais do Coach Chess continuam identificadas pelas regras locais, não como classificações oficiais do Lichess ou ChessSigma.

Os novos ícones SVG são autorais e compartilhados pelo resumo, legenda, anotações e marcas do tabuleiro. A notação textual de PGN é preservada para interoperabilidade.

## Diagnóstico das fases no dashboard

O painel classifica automaticamente todos os lances do jogador nas partidas concluídas do período selecionado (7 ou 30 dias). A fila usa Stockfish local e a mesma comparação MultiPV na posição original e as mesmas sete categorias da análise individual: até profundidade 16 e 80 ms, com verificação das perdas importantes e sacrifícios até profundidade 18 e pelo menos 250 ms. A classificação também alimenta o diagnóstico por fase dos últimos sete dias. Relatórios completos individuais têm preferência; relatórios antigos de triagem rápida são substituídos conforme a fila avança. Limites de tempo podem produzir diferenças de busca em relação a outros aplicativos.

As partidas novas entram antes das antigas ainda na fila. A consulta ao Chess.com ocorre a cada 30 segundos enquanto o aplicativo está aberto, sujeita ao cache e à publicação pela API. Os gráficos e a cobertura são relidos a cada cinco segundos. Só partidas inteiramente avaliadas são salvas na nova classificação; falhas preservam os dados existentes e recebem nova tentativa após dois minutos. O progresso fica no diretório de dados local e sobrevive a reinicializações.

A fase é calculada na posição anterior ao lance. O final é identificado quando as peças (sem peões e reis) somam no máximo 13 pontos, ou quando não há damas e somam no máximo 20. Com mais material, os lances até o número 10 são abertura e os demais meio-jogo. A fase pode mudar antes de um número fixo de lances se a posição for simplificada.

Somente os lances do jogador entram no diagnóstico. As taxas dividem os erros pelo número de decisões efetivamente avaliadas em cada fase. Imprecisões (perda de 5 a menos de 10 pontos no indicador de chances) aparecem separadas dos erros e erros graves (a partir de 10 pontos). Taxas de fases com diferença inferior a dois pontos percentuais são sinalizadas como próximas.

O número de lance destacado exige uma amostra mínima: 20% das partidas avaliadas, limitada entre 3 e 10 ocorrências. O painel mostra numerador e denominador, além das posições críticas que podem ser abertas no tabuleiro. A cobertura avança conforme cada partida é concluída; partidas não avaliadas nunca recebem classificações inventadas. Resultados ficam no diretório de dados do aplicativo e não integram o instalador.

## Análises detalhadas salvas

As análises individuais concluídas, incluindo posições FEN sem lances, são arquivadas automaticamente no SQLite local da conta. São preservados os valores do motor, mates, variantes, classificações, explicações, referências de livros, precisão e posição selecionada. Ao entrar novamente, a última análise é restaurada; outras ficam em «Análises salvas», na tela de análise. Reabrir ou mudar as opções do motor não recalcula um relatório salvo: uma nova busca exige «Iniciar análise». Relatórios parciais ou cancelados não substituem análises completas. O arquivo pertence ao diretório de dados do usuário e nunca integra a distribuição.


## Atualização sem recarregar o painel

O dashboard observa os arquivos de resultados a cada cinco segundos e redesenha os gráficos somente quando um relatório salvo muda. O progresso da fila usa um espaço separado e não recria os gráficos. A coleta de tarefas ignora resultados obsoletos e não recarrega o dashboard quando terminam estimativas destinadas à tela inicial. A consulta a partidas novas continua ativa; um histórico idêntico não reinicia a página.
