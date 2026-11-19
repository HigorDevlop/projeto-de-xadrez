# Partidas e repertório

Na página Partida, ative **Comparar com meu repertório**. Selecione uma partida,
uma posição e uma linha de referência. O tabuleiro mostra a posição antes do
lance jogado. As ações abrem essa posição na Análise ou criam um exercício de
memória na lista de treinos existente, com tentativas legais e revisão espaçada.

## Fontes e método

- A identidade autenticada resolve o proprietário local e seu Chess.com salvo.
- Partidas: histórico pessoal persistido (até 200 partidas) e análises arquivadas
  da própria conta. Cabeçalhos PGN identificam o lado; metadados contraditórios
  ou partidas ilegais são excluídos.
- Linhas: repertório pessoal preparado, distinguido de estudo concluído, e
  linhas com conclusão/retenção registrada nos cursos atuais e na biblioteca.
  A versão atual do curso prevalece sobre a cópia da biblioteca.
- Compara apenas decisões do jogador em posições idênticas: peças, turno,
  direitos de roque e en passant legal; ignora contadores de lances. Respeita
  o contexto inicial das linhas pessoais. Uma alternativa presente em qualquer
  repertório correspondente é aceita.
- Uma diferença gera observação, nunca classificação de erro. Se uma posição
  posterior da partida coincidir com uma posição posterior da linha, mostra
  reentrada comprovada. A linha completa e sua continuação sustentam a observação.
- A criação revalida os identificadores na conta atual e reaproveita
  `analysis_training`, suas tabelas SQLite e seu agendamento. Repetir a criação
  para a mesma posição e lance do repertório preserva o progresso. Alternativas
  diferentes são exercícios de memória distintos; não substituem recomendações
  de motor já salvas.

## Limites

Não há download, motor ou nova análise ao comparar. É necessário ter fontes
locais e Chess.com vinculado para identificar o jogador. Não há inferência de
qualidade, intenção, semelhança estratégica ou cobertura fora das linhas salvas.
Os repertórios existentes usam sequências legais desde a posição inicial padrão;
variantes e repertórios com FEN inicial próprio não são adicionados nesta versão.
Cursos legados de professor/admin identificados apenas por nome público são
excluídos por não terem vínculo privado inequívoco. A navegação para estudo exige
que a conta efetiva seja a mesma da sessão principal da Análise.

## Validação

`python -m pytest tests/test_repertoire_comparison.py tests/test_analysis_training.py tests/test_home_startup.py tests/test_personal_openings.py -q`

Inclui transposição, reentrada, direitos de roque, múltiplos repertórios, ausência
de correspondência, lados, fontes arquivadas, isolamento por conta, navegação,
deduplicação, tentativa legal, revisão e execução local com rede/motor bloqueados
nos testes da comparação. AppTest valida os controles; o tabuleiro é substituído
por um capturador de FEN nos testes de interface.
