# Professor — Mestre da Sala

## Criar a sala e entrar

O aplicativo exige login. O criador deve primeiro configurar seu Superadministrador com **Configurar Superadministrador.bat** e emitir uma chave especial de Professor. Veja [TUTORIAL_LOGIN.md](TUTORIAL_LOGIN.md).

1. Abra **Coach Chess Desktop.bat** e selecione **Professor** na tela de login.
2. Preencha o campo **Chave especial do Professor (obrigatória)** com a chave entregue pelo criador.
3. No primeiro acesso, escolha seu usuário e uma senha com pelo menos 10 caracteres e clique em **Entrar**.
4. Nas próximas entradas manuais, informe seu usuário, sua senha e a mesma chave obrigatória. Para lembrar a conta neste navegador, marque **Entrar automaticamente neste navegador**.
5. O menu do Professor mostra as áreas comuns, **Desempenho** (dashboard individual de seus alunos) e **Modo Preparo** (gerenciamento da sala). O criador, com seu Superadministrador, pode supervisionar e editar todas as salas.

Não existe mais cadastro público de Professor. Contas criadas pelo fluxo anterior aguardam aprovação do criador. Informar um nome público do Chess.com não concede permissões.

## As quatro vagas

Em **Modo Preparo → 4 chaves de acesso**, cada vaga tem sua própria chave. Entregue uma chave para cada aluno. Selecione a vaga, preencha o nome do aluno e vincule seu usuário Chess.com para consultar as partidas.

O aluno entra por **Usuário** (ou cria sua conta), abre **Juntar-se à sala** na lateral e informa o código fornecido pelo Professor. Ele tem acesso a **Partida**, **Análise**, **Táticos**, **Estudo com livros** e **Aberturas**. Dentro da sala, também aparece **Modo Preparo**, que abre sua rotina sem controles de edição. O Professor acessa o dashboard de cada aluno em **Desempenho** ou em **Modo Preparo → Dashboard**. O botão de táticos nessa rotina abre os exercícios existentes do aplicativo. **Usar abas comuns** libera o catálogo completo e a análise; **Abrir sala do Professor** retorna à rotina, sem novo login.

Para testar contas diferentes simultaneamente no mesmo computador, use janelas de navegador com perfis separados ou uma janela anônima. A sessão expira em 12 horas; o acesso automático, quando marcado, permite renovar o login por até 30 dias, sujeito à validação do servidor.

## Montar a rotina

1. Selecione o aluno e abra **Rotina individual**.
2. Selecione até quatro aberturas, incluindo o lado a estudar.
3. Defina o total de linhas por dia, a meta de posições concluídas, os táticos, os minutos, os dias da semana e o início.
4. Clique em **Salvar rotina**.

As linhas são distribuídas entre as aberturas escolhidas, com pelo menos uma por abertura. A quantidade é limitada pelo conteúdo real disponível. O aluno recebe apenas as linhas atribuídas no curso. Linhas novas começam automaticamente pelo aprendizado com setas; depois vêm memorização e quiz.

A trilha é concluída quando o aluno termina as linhas atribuídas, atinge a meta de posições em **Certo** e resolve os táticos. A conclusão fica verde e encerra o cronômetro, mesmo antes do limite; o painel preserva a duração e a meta de tempo separadamente. Repetir a mesma linha ou o mesmo tático não infla a quantidade concluída naquele dia.

## Conferir o dashboard e a presença

Em **Dashboard**, escolha o aluno e a data. Use **Atualizar dashboard** para consultar o progresso mais recente sem sair da conta. Confira:

- Linhas, táticos e tempo ativo em relação às metas.
- Posições nos estados **A Fazer / Erro / Não Sei / Certo**.
- Precisão separada de aberturas e táticos: acertos divididos pelas tentativas válidas. O aprendizado guiado não entra nessa precisão; sem tentativas aparece “sem tentativas”, em vez de um valor inventado.
- **Carregar / atualizar últimas 20 partidas** consulta a conta Chess.com vinculada. O relatório apresenta uma linha por partida, com a abertura identificada pelo PGN e pelo catálogo ECO local. Se existirem menos de 20 partidas, apresenta somente as disponíveis.

Entrar no **Modo Preparo** registra presença e inicia o cronômetro definido na rotina. Ele acompanha as aberturas e os táticos da sala enquanto a janela permanece visível. Voltar às abas comuns, sair da conta ou ocultar a aba interrompe a sessão; ao retornar, uma nova sessão começa. O histórico privado, atualizado a cada cinco segundos, mostra entrada, saída e duração. **Verde** indica trilha concluída; **vermelho**, saída antes do tempo com trilha incompleta; **laranja**, treino em andamento ou tempo cumprido sem concluir a trilha. Fechamentos e desconexões são detectados após cerca de 25 segundos sem sinal, encerrando o registro no último sinal confirmado. Alunos não acessam o histórico de saídas. Tempo offline e janelas duplicadas não somam tempo extra. Os táticos e a consulta de partidas precisam de internet; o catálogo de aberturas funciona localmente.

Em **Presença e advertências**, o histórico dos últimos 30 dias mostra dias cumpridos, pendentes ou faltantes/incompletos. Um dia futuro ou não previsto não é classificado como falta. Editar a rotina não reescreve as metas de dias anteriores.

## Advertências e banimento

1. Selecione o aluno e confira o histórico de presença.
2. Escreva o motivo e clique em **Aplicar advertência**.
3. As duas primeiras advertências mostram **1/3** e **2/3**.
4. Na terceira, o aluno é banido automaticamente desta sala: a chave é apagada e todas as suas sessões na sala são revogadas. As outras três vagas continuam funcionando.

As advertências guardam a data e o motivo. Não há aplicação automática de advertências por falta: o Professor verifica e aplica cada uma.

## Dados compartilhados da sala

Contas, chaves, rotinas e auditoria ficam no banco **data/classrooms.sqlite3** da instalação que executa o servidor. Faça backup desse arquivo com o aplicativo fechado. O progresso pessoal das aberturas permanece em **data/preparation/openings/**, com uma identidade separada para cada aluno.

Professor e alunos precisam usar o **mesmo servidor** para compartilhar a sala. Cópias independentes do aplicativo em computadores diferentes não sincronizam automaticamente. Para usar a mesma instalação pela rede local, execute **Iniciar Sala Coach Chess.bat** no computador que ficará ligado. Nesse computador, abra **http://127.0.0.1:8510**; nos outros computadores, abra o endereço da rede local mostrado pelo inicializador. A porta 8510 fica separada da janela desktop normal. O acesso à sala exige a senha do Professor ou a chave individual do aluno.
