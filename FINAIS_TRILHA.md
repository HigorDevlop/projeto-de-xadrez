# Trilha inicial de finais

Acesso: **Aberturas → Finais**. Três lições locais, liberadas em sequência:

1. **Oposição direta:** colocar o rei em e4 diante do rei em e6.
2. **O rei à frente do peão:** levar o rei a e6 antes de avançar o peão de e4.
3. **Promoção com xeque:** promover e7–e8 a dama; distinguir xeque de mate e afogamento.

Cada lição apresenta objetivo, posição válida, três dicas graduais, tentativa no
tabuleiro e solução explicada com continuação navegável. Após uma tentativa,
o tabuleiro mostra a posição realmente produzida pelo lance. Uma alternativa
legal que não satisfaz o objetivo não é anunciada como derrota.

## Reutilização e persistência

- `interactive_board`: tabuleiro, eventos com FEN/revisão, promoção e peças locais.
- `preparation_repetition`: validação de lances e estados de recuperação por posição.
  O parâmetro opcional `assisted` impede concluir com dica; seu padrão preserva
  o comportamento dos treinos existentes.
- `preparation_state`: formato de plano e gravação atômica sob o lock existente.
  Os arquivos ficam no namespace de cursos, com chave `endgames:<perfil>:<id>`.
- `opening_training_state.schedule_review`: intervalos existentes de 1, 3, 7, 14
  e 30 dias. Erro ou ajuda mantém a próxima revisão em um dia.
- `classroom._identity` e `training_token`: autenticação da conta de treino,
  incluindo a identidade de aluno quando o modo sala estiver ativo.

Tentativas, dicas, solução aberta e conclusão são gravadas após cada ação.
A retomada recarrega o plano autenticado; eventos duplicados ou antigos não
sobrescrevem progresso. Duas respostas corretas são necessárias, e a última
deve ser sem ajuda. Revisões só reiniciam ao abrir a lição na data devida.

## Conteúdo e limites

Posições organizadas e textos redigidos originalmente para esta contribuição.
Não foram incorporados livros, PGNs de terceiros, imagens, tablebases ou saídas
de motor. O material acompanha os termos de distribuição do projeto.
Não há download, consulta externa ou execução de motor ao abrir ou praticar.

Esta primeira fatia treina um objetivo de um lance por lição. As continuações
são exemplos legais, não uma árvore de todas as defesas nem provas gerais de
vitória. Não há adversário automático ou avaliação livre de alternativas.
Todas as posições iniciais pedem um lance das brancas. Os antigos exemplos
isolados de mate foram substituídos por esta trilha persistente.

## Validação

`python -m pytest tests/test_endgame_training.py tests/test_preparation_repetition.py tests/test_opening_reference_state.py -q`

`python -m pytest tests/test_opening_reference_ui.py::test_reference_endgame_is_playable -q`

Os testes verificam regras, objetivos, desbloqueio, ajuda, conclusão, revisão,
retomada, isolamento, rejeição de eventos antigos e indisponibilidade de rede/motor.
O teste de navegador bloqueia requisições externas e joga no tabuleiro real.
