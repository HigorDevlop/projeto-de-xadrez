# Preparar aulas, treinos e provas

No acesso **Professor**, abra **Modo Preparo**, selecione o aluno e entre em **Treino e provas**. A **Rotina individual** continua definindo metas e agenda; os materiais da aula são preparados na nova aba.

- **Linha de treino:** escolha uma linha exata do catálogo ou importe/cole seu PGN. No PGN personalizado, selecione o lado do aluno. O adversário responde com os lances preparados; o aluno pode repetir o treino.
- **Tático:** filtre o banco offline pelo tema da aula e pelo código, visualize a solução e escolha os exercícios. Também é possível montar um exercício informando FEN e solução UCI. O FEN define quem joga.
- **Partida estudada:** importe um PGN comentado. O aluno percorre a partida e os comentários; pode abri-la na análise para experimentar e fazer anotações particulares.
- **Prova:** crie até 50 perguntas abertas ou fechadas, com peso por pergunta. Nas fechadas, selecione a alternativa correta. Nas abertas, informe respostas aceitas separadas por `|`, ou deixe o gabarito vazio para corrigir manualmente.

Nas respostas abertas, a correção automática compara o texto com as respostas aceitas, ignorando maiúsculas, acentos e pontuação. Ela não interpreta o significado de textos livres. Para respostas discursivas, utilize a correção manual.

Em **Materiais e correções**, o Professor pode disponibilizar ou ocultar os materiais, consultar conclusões de treinos e corrigir provas, atribuindo pontos e comentários. Depois do envio, o aluno não pode alterar a prova. O gabarito não é incluído nos dados apresentados ao aluno.

## Sala de aula e vídeos gravados

Em **Aulas**, os controles de transmissão ficam no topo e os vídeos salvos aparecem em uma lista compacta abaixo. **Publicar vídeo** aceita um link HTTPS ou um arquivo MP4, WebM ou MOV de até 100 MB. Publicar salva a aula e deixa o player fechado; não lê nem transmite os vídeos da biblioteca ao navegador.

**Assistir** abre um único player abaixo da lista, sem reprodução automática. Trocar de aula substitui o vídeo anterior. **Fechar vídeo** remove o player e libera a cópia de reprodução da sessão. O arquivo só é lido quando solicitado e fica reutilizável durante essa reprodução, sem consultar novamente o conteúdo inteiro a cada atualização da tela. A lista e os controles de reprodução atualizam em um fragmento separado do chat e da transmissão.

## Entrada do aluno

O aluno entra com sua conta, usa **Juntar-se à sala** e informa a chave fornecida pelo Professor. Depois, abre **Modo Preparo → Treino e provas**. Só aparecem os materiais atribuídos à vaga correspondente à chave; chaves banidas e acessos revogados não abrem o conteúdo. Um Professor não pode consultar materiais ou corrigir alunos de outra sala.

## Caderno da análise

No painel ao lado do tabuleiro, selecione **Caderno**, junto da aba **Anotações**. O bloco pautado permite escrever sem cobrir as peças. Nele, registre notas da posição atual ou um resumo geral da partida. As notas são privadas por conta e ficam salvas offline. O caderno pode ser baixado em Markdown. Em **Cadernos salvos → Retomar partida anotada**, reabra a partida e as notas depois de fechar o aplicativo.

## Armazenamento e acesso entre computadores

Materiais, provas, respostas e cadernos ficam no banco local de contas do aplicativo. Os táticos usam o banco incluído na instalação e não dependem da internet. Não foi publicada uma hospedagem com esta manutenção. Para Professor e alunos em computadores diferentes compartilharem a mesma sala, precisam acessar uma instalação/servidor central comum; instalações independentes ainda não sincronizam estes materiais automaticamente.

Contas, livros e progresso existentes são preservados. Esta alteração não gera instalador nem muda a versão publicada.

## Administração e criação de cursos

O Superadministrador pode abrir **Modo Preparo** sem conta ou chave de Professor. Na primeira entrada são preparadas quatro vagas de **Laboratório**, mantendo as salas existentes.

A montagem fica em **Treino e provas**. A aba **Cursos e manutenção** foi retirada; os modelos e resultados anteriores permanecem armazenados.

A **Prévia como aluno** funciona nas vagas do laboratório do administrador, evitando registrar testes em nome de alunos reais. Os Professores continuam restritos às próprias salas e aos próprios modelos de curso.

Em Treino e provas, arraste uma opção da faixa superior para a trilha abaixo e clique na linha para configurar, nomear e revisar seus eventos. A montagem é publicada pelo botão abaixo da trilha. As prévias de tabuleiro só são montadas ao abrir Conferir tabuleiro e comentários; a biblioteca e suas correções são carregadas ao selecionar Materiais e correções. A publicação, as permissões de sala e o gabarito permanecem iguais.


## Montador de trilhas do treinador

Em **Treino e provas → Preparar material**, as opções **Linha**, **Tático**, **Vídeo**, **Prova**, **Partida** e **Anotação** ficam todas na faixa superior. A trilha já aparece desenhada abaixo, mesmo vazia. Arrastar uma opção para o próximo espaço cria uma linha; arrastar sobre uma linha existente acrescenta um evento a ela. O botão Adicionar oferece a mesma operação sem arraste. Os espaços vazios são guias visuais; a trilha pode receber até 50 linhas.

Clique no círculo de uma linha para abrir o editor. Nele, o treinador pode renomear a linha, escrever anotações gerais, acrescentar eventos, retirar atividades e escolher a ordem pelas setas. Por exemplo, Vídeo → Linha → Tático → Anotação. Cada evento pode ser aberto e alterado novamente; **Salvar atividade** guarda a configuração e marca a revisão. As opções são adicionadas inicialmente como rascunho; a publicação exige que todos os eventos tenham sido configurados e revisados. Uma linha pode conter até 60 eventos e a trilha até 200 atividades.

Para mudar a ordem das próprias linhas, arraste seus círculos. O rascunho é salvo no banco local por vaga. Trocar de seleção, de aba ou reabrir o app mantém as linhas já montadas. **Disponibilizar trilha ao aluno** publica a sequência na ordem escolhida pelo professor. Anotações gerais e notas como eventos também aparecem ao aluno. Editar um conteúdo já publicado cria uma nova versão da atividade quando necessário, mantendo as respostas da versão anterior; renomear, reordenar ou editar anotações gerais não apaga o progresso.

O cadeado fica dentro do editor de cada linha. Ele bloqueia a linha e todas as seguintes até o treinador liberar. Em linhas já publicadas, bloquear/desbloquear é imediato no servidor; o aluno acompanha a alteração em até três segundos. Alterações de conteúdo ou ordem só aparecem ao aluno após disponibilizar novamente. Arquivos de vídeo continuam carregando para reprodução somente após o clique em Assistir; links externos dependem de conexão. Os cursos reutilizáveis preservam agrupamentos, ordem e anotações sem copiar respostas de alunos.


## Edição simplificada de linhas

Ao abrir uma linha já configurada, o editor mostra somente a sequência de atividades. Clique em uma atividade para ajustar seu conteúdo e use **Voltar às atividades** para organizar a sequência. As setas mudam a ordem; o menu de cada atividade permite removê-la. **Nome e notas** reúne o título e as anotações gerais. **Opções** contém o cadeado e a exclusão da linha. Conteúdos novos abrem diretamente na configuração; **Salvar atividade** confirma a revisão.

## Blocos contínuos de uma linha

Em uma atividade **Linha de treino**, escolha **Quantos lances neste bloco?** (1 a 100). Um lance inclui a jogada das brancas e a resposta das pretas. O PGN completo é preservado; o trecho mostrado e treinado termina na quantidade escolhida, ou no fim da sequência disponível.

No bloco seguinte, selecione **Continuar linha anterior**. O treino começa na posição final da última linha salva antes dele na trilha, mantendo o lado do aluno. Vídeos, notas e outras atividades entre as duas linhas não interrompem a sequência. Escolha a quantidade de lances novos deste bloco. Em **Ver ou ampliar a sequência completa**, acrescente ao PGN a continuação que desejar quando os lances preparados acabarem; mantenha o prefixo já ensinado.

Cada bloco guarda seu próprio trecho, anotações e progresso. Ao editar um bloco anterior ou mudar a ordem, confira e salve as continuações; a publicação rejeita uma sequência que não corresponda ao novo prefixo. O aluno joga a partir do FEN correto do trecho, inclusive em posições personalizadas e quando as pretas iniciam.

## Instruções com o tabuleiro à vista

No editor de uma linha ou partida estudada, abra **Conferir tabuleiro e comentários**. Use **Percorrer lances para anotar** para escolher a posição. O tabuleiro fica à esquerda e **Instrução nesta posição** à direita. Escreva a orientação olhando as peças, percorra outros lances e acrescente outras instruções. Confirme todas em **Salvar atividade**, depois disponibilize a trilha ao aluno.

As instruções guardam o lance e o FEN exato. Ao reabrir a atividade, elas reaparecem nas posições correspondentes. No treino, o aluno vê a orientação da posição atual e a do lance imediatamente anterior, identificadas pelo lance; isso também conserva a explicação da jogada do aluno quando o adversário responde automaticamente. Na partida estudada, cada orientação aparece ao percorrer a posição correspondente. As orientações gerais continuam disponíveis separadamente.

## Personagem e leitura da explicação

A prévia por posição inclui uma representação artística de Bobby Fischer junto da instrução. No treino do aluno e nas partidas estudadas, o personagem apresenta os comentários do professor. **Ouvir explicação** lê o texto; **Parar** interrompe a fala; **Ler automaticamente** permite acompanhar a mudança das posições após ativação pelo usuário. A preferência fica no navegador do aplicativo.

A leitura utiliza uma voz local em português do aparelho, com preferência por pt-BR. Vozes online não são utilizadas; quando não existe voz local compatível, a explicação permanece escrita. A imagem já está incluída na instalação. A mudança de comentário interrompe a leitura anterior, e sair da tela também interrompe a fala. A animação respeita a preferência do sistema por menos movimento.

## Testar o preparo antes de disponibilizar

No editor de **Linha de treino** ou **Tático**, abra **Testar como aluno**. Jogue no tabuleiro: o adversário responde com a sequência preparada, os lances incorretos são rejeitados e as instruções aparecem como no treino. **Recomeçar simulação** reinicia a linha. A simulação funciona antes da publicação e fica somente na sessão do professor, sem gravar resultados, respostas ou progresso em nome do aluno. Nas atividades já salvas, o menu da atividade também permite abrir esse teste.

## Vários táticos em um único bloco e requisito de 90%

Selecione quantos exercícios quiser no banco offline e clique em **Adicionar selecionados ao bloco**. Pode mudar o tema ou buscar outros códigos e acrescentar novos exercícios ao mesmo bloco. Em **Criar uma posição**, **Adicionar posição ao bloco** reúne FENs personalizados na mesma atividade. **Revisar táticos do bloco** permite percorrer os escolhidos e retirar um exercício. **Salvar atividade** guarda o conjunto; não há o limite anterior de um exercício por bloco.

Durante o treino, os dados do conjunto ficam carregados localmente e até três próximas posições são preparadas em segundo plano. A passagem entre exercícios ocorre em um fragmento, mantendo o tabuleiro interativo. O aluno deve terminar a rodada com pelo menos 90% dos exercícios concluídos sem erro. Um lance errado ou pular o exercício tira o crédito daquele tático na rodada, mesmo que depois seja corrigido. A porcentagem considera exercícios, não tentativas repetidas do mesmo lance; em um bloco de dez, nove precisam estar sem erro. Abaixo da meta, **Nova tentativa do bloco** reinicia uma rodada, conservando o histórico recente. Uma aprovação já conquistada não é revogada ao treinar novamente.

As atividades posteriores, inclusive dentro da mesma etapa, ficam indisponíveis até a aprovação. O servidor também recusa acesso direto a provas, vídeos e treinos posteriores. Os cadeados manuais do professor continuam valendo. Ao aprovar, **Continuar para a próxima atividade** segue a ordem montada pelo professor. Materiais antigos de tático individual continuam disponíveis com seu formato e progresso preservados; o requisito é aplicado aos blocos novos.

## Configuração e teste das linhas

- Clique na linha da trilha e escolha **Testar linha** ou **Configurar linha**.
- Em Configurar, clique no nome da atividade para editar. **Remover** retira somente aquela atividade; a linha e as demais atividades permanecem. A ordem fica no menu de cada atividade.
- Escolha **Brancas** ou **Pretas** em **Lado que o aluno vai treinar**, inclusive para as linhas do catálogo.
- O teste usa o mesmo jogador de treino e as mesmas regras de validação do aluno, incluindo respostas automáticas, instruções por posição e reinício. As tentativas do professor são particulares e não alteram o progresso do aluno.
- No teste da linha, atividades após um bloco de táticos ficam indisponíveis até a aprovação particular de pelo menos 90%. Configure as atividades na ordem antes de testar.
- Salve a atividade antes de testar e disponibilize a trilha para enviar as alterações ao aluno.
- O catálogo mostra somente os repertórios do lado selecionado. Ao trocar o lado, uma seleção incompatível é substituída pelo repertório correspondente, quando disponível.
- Linhas preparadas exibem a mesma seta verde de orientação do modo Aberturas, no treino do aluno e no teste do Professor. Ela acompanha o próximo lance e desaparece ao concluir o bloco; táticos continuam sem revelar a solução.


### Provas fechadas e sequência automática

Nas perguntas fechadas, preencha o enunciado e os campos Alternativa A, B etc. Escolha de 2 a 8 alternativas e marque a letra correta; não é necessário separar respostas por quebras de linha.

As linhas passam por aprendizado com dicas, repetição sem dicas (uma rodada sem erros) e quiz das posições do aluno. Posições erradas voltam no quiz. Ao concluir, a próxima atividade disponível é selecionada automaticamente, tanto para o aluno quanto em Testar linha. A entrega de prova e a aprovação de um bloco de táticos também avançam. Anotações, vídeos e partidas têm o botão Concluir e continuar. Bloqueios definidos pelo professor continuam valendo.


### Encerramento do treino

Depois do quiz, a linha permanece aberta com o resultado. **Continuar para a próxima linha** avança para a próxima atividade disponível; **Parar por aqui** encerra a simulação ou pausa a tela do aluno. O fechamento do tabuleiro remove a peça temporária usada no arraste.


### Continuação e liberação programada

- **Continuar linha anterior** recupera o PGN completo, começa no FEN final do último bloco e propõe dois lances completos novos. Quando não há continuação salva, o Stockfish instalado completa somente o final; os lances anteriores permanecem intactos. A sugestão pode ser editada no PGN.
- A seleção de sequência fica ao lado da abertura, permitindo trocar a variante.
- **Opções → Bloquear avanço** permite bloqueio manual ou liberação em data e hora de Brasília. O acesso às atividades é verificado no servidor local, incluindo chamadas diretas de treino e prova. A liberação ocorre automaticamente no horário salvo.

### Sessões, biblioteca e acompanhamento

- Em **Treino e provas → Sessões de treino e biblioteca**, salve a montagem antes de publicá-la, salve e comece outra trilha ou carregue um modelo da sua biblioteca. Novas sessões recebem identificadores próprios e começam sem respostas copiadas.
- Uma nova montagem permanece particular até **Disponibilizar trilha ao aluno**. Nesse momento, a sessão anterior é registrada no histórico e a nova trilha substitui a disponível para esse aluno.
- **Reiniciar trilha do zero** exige marcar a confirmação e limpa somente os materiais e resultados atuais do aluno selecionado. O cadastro, a biblioteca, os registros de presença e o histórico de sessões permanecem salvos.
- A ficha do aluno mostra a trilha atual, a etapa em andamento e o progresso por atividade. **Abrir e editar a trilha deste aluno** seleciona a vaga correta em Treino e provas, permitindo acrescentar linhas, táticos, provas e outros materiais.
- O aluno encontra o campo **Chave de acesso do professor** em destaque na tela principal e o acesso **Tenho uma chave do professor** na barra lateral.

### Partidas recentes

Na análise e na tela de partidas, a consulta automática verifica novas partidas a cada 30 segundos e mescla os resultados sem trocar a partida em revisão. Os meses recente e anterior são consultados diretamente; uma lista de arquivos em cache não esconde partidas recentes. Falhas de conexão preservam a lista carregada e a consulta é retomada depois. A disponibilidade continua sujeita ao cache e à publicação da API pública do Chess.com.
