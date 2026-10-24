# Tabuleiro, anotações e rodadas de aberturas

- A barra lateral da análise usa a avaliação já calculada pelo motor escolhido. A parte clara representa as brancas; a escura, as pretas. A orientação acompanha o tabuleiro. Sem análise disponível, aparece «—». Jogar um lance novo não inicia o motor nem reaproveita a avaliação da posição anterior.
- Os relógios do PGN aparecem como «◷ 3:01», indicando tempo restante. Comandos como `[%clk ...]` deixam de aparecer como comentários.
- O arraste usa os limites reais das casas, incluindo tabuleiros sem borda e com zoom. A animação de um movimento anterior não pode apagar a peça de um novo arraste. Os movimentos recebem uma transição curta; a preferência de reduzir movimento é respeitada.

## Trilha de aberturas

A apresentação atual usa [50 fases numeradas](TRILHA_50_FASES.md). Cada quinta fase é um boss de **50 perguntas**, independentemente das quotas comuns da tabela abaixo, e concede uma conquista. A conclusão e a precisão na primeira tentativa ficam salvas por fase.

A trilha mantém até cinco linhas da mesma abertura. Cada linha passa por ensino, repetição completa sem erros e quiz próprio. Erros e dicas exigem revisão da pergunta.

| Rodada | Lances do aluno em cada linha | Acertos no quiz de cada linha |
| --- | --- | --- |
| 1 | 5 | 5 |
| 2 | 5 novamente | 10 |
| 3 | 7 | 20 |
| 4 | 9 | 40 |
| 5 | 11 | 50 |
| Seguintes | +2 por rodada | 50 |

Todas as linhas da rodada devem ser concluídas antes do aumento. A rodada seguinte recomeça na linha 1, desde o início da posição. Quizzes maiores repetem posições da própria linha, usando perguntas independentes e recuperando os erros. Conquistas continuam vinculadas a quizzes efetivamente concluídos.

Continuações ausentes são preparadas com o Stockfish local, preservando o início de cada linha. Cursos com menos linhas disponíveis usam as linhas existentes, sem misturar outra abertura. Recomendações pessoais do histórico e atividades de sala mantêm seus fluxos próprios.

## Aplicar na instalação existente

Feche o Coach Chess e execute **Aplicar correções no Coach Chess.cmd** pelo Explorador. A manutenção preserva contas, livros e progresso; não publica uma versão nem gera instalador.
