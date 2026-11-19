# Desafios de posição — primeira versão

No **Modo Preparo**, o professor abre **Desafios de posição da minha sala**,
informa título, FEN, instrução e um lance esperado em UCI, e publica para os
alunos não revogados da sala naquele momento. O superadministrador pode usar
sua própria sala de laboratório; este painel não agrega outras salas.

O aluno entra com sua sessão de sala e abre **Desafios de posição da sala**.
Jogar no tabuleiro envia uma tentativa única, como informado na interface.
Depois do envio, são mostrados o lance tentado e o lance esperado. O professor
consulta pendências, participação e resultados da própria sala.

## Integração e garantias

- Usa o mesmo SQLite, autenticação e atribuições `lesson_materials` existentes.
  A correção usa `lesson_results`, com chave única `(material, student)` e a
  mesma política imutável da primeira resposta usada nas provas.
- `BEGIN IMMEDIATE` torna publicação e correção atômicas. Repetir a publicação
  com o mesmo identificador não cria cópias; usar esse identificador para outro
  conteúdo é rejeitado. Envios simultâneos retornam a primeira resposta salva.
- O servidor confere sessão, papel, aluno destinatário, sala, publicação,
  bloqueios de trilha, FEN atual e legalidade do lance. Nenhuma decisão de acesso
  depende apenas do componente visual.
- Os desafios são excluídos da listagem genérica de materiais. A listagem própria
  do aluno usa campos explícitos e não inclui solução antes de existir resultado.
  O tabuleiro não recebe `training_expected`, dica ou variação do gabarito.
- Não altera metas da rotina, notas de provas nem conclusões das trilhas.

## Limites e infraestrutura

- Desafios de um lance, com um gabarito definido pelo professor, sem avaliação
  de motor. Um lance diferente não é automaticamente um erro enxadrístico.
- Destinatários são os alunos existentes na publicação. Novos alunos precisam
  de uma nova publicação. Para outra rodada, use **Preparar novo desafio**.
- O professor controla o texto da instrução: não inclua o gabarito nela se quiser
  mantê-lo oculto. Não há detecção automática desse tipo de revelação editorial.
- Funciona na instalação local. Para professor e alunos compartilharem dados,
  precisam acessar a mesma instância do aplicativo e seu banco persistente.
  Instalações separadas não sincronizam este recurso automaticamente.
- Não foi publicada hospedagem nem criado serviço global. Uso remoto ainda exige
  implantação de uma instância acessível, HTTPS, operação e backup do SQLite,
  gerenciamento de sessões e proteção da infraestrutura. O banco privado não
  deve ser distribuído em instaladores.

## Testes

`python -m pytest tests/test_classroom_challenges.py tests/test_classroom_materials.py -q`

Cobrem permissões, isolamento entre salas e alunos, gabarito oculto, posição e
lance inválidos, promoção pelas pretas, publicação idempotente, tentativa única,
concorrência, revogação, resultados e interface do professor/aluno.
