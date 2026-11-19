# Mapa de evolução

Em **Partida → Mostrar mapa de evolução**, escolha 7 ou 30 dias. O mapa compara
o período selecionado, incluindo hoje, com o período imediatamente anterior de
igual duração. Datas locais seguem `preparation_state.today()`.

## Fontes e fórmulas

| Indicador | Fonte existente | Associação à conta | Cálculo |
|---|---|---|---|
| Partidas por fase e motor | `analysis_archive`: PGN e `MoveReview`; fase de `game_phase_diagnostics.phase` | Arquivo autenticado; lado identificado pelo nome Chess.com salvo na própria conta | Imprecisões, erros e capivoradas / lances analisados do jogador |
| Aberturas por curso | `phase_results` de `opening_course_state` / `opening_rounds` | Plano `user:<id>` ou `classroom:<id>` | Média simples do percentual de acerto inicial já salvo em cada fase concluída |
| Táticos por tema | `tactics_progress.attempts` | `owner` da identidade autenticada | Lances corretos / tentativas; inclui repetições do mesmo problema |
| Preparos | Resumo diário existente de `classroom._summary` | Apenas o próprio aluno autenticado | Soma dos minutos de atividade registrados; não mede habilidade |

As evidências exibem data, identificação e valores de origem. Partidas usam a data
do PGN. Reanalisar uma partida não a conta novamente. O curso ativo prevalece
sobre sua cópia antiga na biblioteca. O mapa não combina as quatro métricas.

Para exibir variação são exigidas, em **cada** período, 3 partidas, 3 fases,
5 problemas táticos distintos ou 3 dias ativos de preparo, respectivamente.
Esses mínimos são proteções descritivas contra amostras mínimas, não testes de
significância. Abaixo deles os valores e evidências continuam visíveis, com aviso
de dados insuficientes e sem conclusão sobre fraqueza.

## Ações e limites

- Táticos abre o tema local; aberturas abre a revisão do curso usando a navegação
  existente, que continua aplicando as restrições da rotina do aluno.
- Erros de partidas abrem o exercício personalizado existente; outros lances
  abrem a análise salva. A criação do exercício exige o clique do jogador.
- Preparos abre a área já autorizada do próprio aluno. Não expõe advertências,
  horários de entrada/saída nem justificativas privadas do professor.
- O mapa usa a identidade de treino atual. Em modo sala ela pode diferir da
  conta principal. Treinos de partidas exigem o perfil proprietário da análise.
- Planos antigos de professor/administrador e preparos identificados apenas por
  nome público Chess.com são excluídos: não existe vínculo exclusivo verificável.
- Partidas sem data/lado identificável, análises não salvas e fases sem resultado
  inicial datado não geram tendência. O mapa não reconstrói históricos ausentes.
- Versões antigas da classificação de partidas podem diferir. Motores são
  separados, mas não há normalização histórica das versões do método.
- Nenhum motor, busca de rede ou análise em segundo plano é iniciado pelo mapa.
  O painel lê os arquivos e bancos locais; não é um serviço publicado.

## Testes

`python -m pytest tests/test_evolution_map.py -q`

Cobre agregação, limites de período, deduplicação, amostras pequenas, fontes,
contas com o mesmo nome público, sessão revogada, privacidade do preparo,
navegação para os quatro treinos e troca de conta na interface.
