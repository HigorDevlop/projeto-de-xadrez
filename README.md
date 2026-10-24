# Coach Chess

O aplicativo exige login. O criador configura seu **Superadministrador** com **Configurar Superadministrador.bat** e emite as chaves especiais que autorizam professores. Cada chave fica vinculada a um único Professor, é obrigatória em todo login manual e libera uma sala de quatro alunos. As chaves são emitidas na aba privada Superadministrador, acessada por Usuários. O Superadministrador acessa todos os professores e alunos; cada Professor gerencia apenas sua sala. O acesso automático é opcional e revogável. Consulte [TUTORIAL_LOGIN.md](TUTORIAL_LOGIN.md) e [TUTORIAL_PROFESSOR.md](TUTORIAL_PROFESSOR.md). Professor, criador e alunos precisam usar o mesmo servidor para compartilhar os dados.

Execute `python iniciar.py` nesta pasta e abra http://127.0.0.1:8501. O inicializador cria o ambiente virtual e instala as dependências. No Windows, também há `iniciar.bat` e `iniciar.ps1`.

## Versão desktop

No Windows, abra **Coach Chess Desktop.bat** com dois cliques. O aplicativo inicia localmente e abre diretamente em **Aberturas**, em uma janela própria do Edge ou Chrome, sem barra de endereço. Se nenhum deles estiver instalado, abre no navegador padrão. Em uma instalação nova, execute `iniciar.bat` primeiro para preparar as dependências. Não é necessário instalar outro motor ou informar uma chave de API.

A página de **Aberturas** usa a identidade **Coach Chess**: fundo preto, cartões em degradê escuro, tabuleiros bege e marrom, medalhas, trilha de estrelas e botões em degradê. A tela inicial separa as aberturas de brancas e negras em duas fileiras. **Ver todas** abre a busca, os filtros **Todos / e4 / d4 / Outro** e a paginação. Há 78 cursos, contando os dois lados, com 1.017 linhas legais baseadas no catálogo ECO local.

Cada curso tem as abas **Curso / Armadilhas / Variações**. Durante o treino, o tabuleiro fica à esquerda e os controles à direita; em janelas estreitas os controles passam para baixo. **Treinar** ensina cada linha inédita com setas, passa pela repetição de memória e então abre o quiz com **A Fazer / Erro / Não Sei / Certo**. Ao concluir e clicar em **Continuar**, a próxima linha inédita começa novamente pelo aprendizado. Linhas já aprendidas abrem diretamente a revisão. Um acerto de primeira conclui a posição. Um erro avança imediatamente e reinsere a posição aleatoriamente; são necessários dois acertos sem ajuda para recuperá-la (**Erro → Não Sei → Certo**). Qualquer novo erro reinicia esse ciclo. **Pausar treino** conserva a posição. A fila e os estados ficam salvos.

O progresso, as posições aprendidas e a sequência diária são reais e ficam salvos. As avaliações vêm do Stockfish local; o perfil usa o histórico de partidas carregado, sem copiar os números dos prints. As conquistas aparecem ao atingir a meta indicada no curso. As referências orientam a aparência e o fluxo; o conteúdo das linhas e as estatísticas pertencem a esta implementação local.

Veja o [tutorial para testar a versão desktop](TESTAR_DESKTOP.md).

O progresso continua em `data/preparation/openings/`. A janela usa um servidor restrito ao computador (`127.0.0.1`); não publica o aplicativo na internet. O processo local permanece ativo ao fechar a janela. O registro de inicialização fica em `data/desktop/server.log`. Para usar uma aba comum, execute `iniciar.bat`.

## Interface

O tema global usa fundo `#0a0a0a`, superfícies `#121212`, degradês discretos e bordas minimalistas. A identidade e os ícones do aplicativo são Coach Chess, com logo preto e branco. A barra lateral do aluno mostra apenas **Análise** e **Aberturas**. O **Professor** também tem **Modo Preparo**, com edição exclusiva de rotinas e dashboard da sala. O aplicativo abre em Análise; o inicializador desktop abre diretamente em Aberturas.

A referência principal é [Refactoring UI, de Adam Wathan e Steve Schoger](https://refactoringui.com/), com apoio dos princípios de contraste, repetição, alinhamento e proximidade apresentados na descrição de [The Non-Designer’s Design Book, de Robin Williams](https://www.pearson.com/en-us/subject-catalog/p/non-designers-design-book-the/P200000000691?view=educator). A reforma aplica os princípios publicados nas apresentações dessas obras; não depende de reproduzir páginas nem pressupõe a leitura integral dos livros.

O vídeo de entrada foi removido. O aplicativo abre diretamente na Análise, inclusive quando existe uma preferência antiga de exibição da abertura. O vídeo do ferreiro continua pertencendo aos exercícios táticos.

## Stockfish e livros

O motor principal é o **Stockfish 19**, atualizado a partir da release oficial para Windows, em `engines/stockfish.exe`. **Berserk 14** também está integrado como opção de análise local na CPU. Para outra instalação ou sistema operacional, configure `STOCKFISH_PATH` ou coloque o binário nativo em `engines/stockfish`. Não há Ollama, modelo de linguagem, API de análise ou chave necessária. Veja [engines/README.md](engines/README.md).

O aplicativo primeiro extrai o texto dos livros e indexa comentários PGN por posição, além de temas em português/inglês (centro, desenvolvimento, roque, estrutura de peões, finais etc.). Os arquivos em **Configurações → Livros** e os anexados à página **Estudo com livros** são combinados. Esse índice é preparado antes de iniciar o motor e reutilizado enquanto os livros não mudarem.

Ao solicitar **Analisar Partida**, o motor escolhido avalia a melhor jogada, a segunda alternativa e o lance realizado. O aplicativo aplica as faixas do indicador de chances abaixo e compõe explicações em português com arquivo/página, temas relacionados e fatos verificáveis do tabuleiro. Trechos em outros idiomas ficam preservados no índice interno, sem aparecer na explicação. O resumo temático não é apresentado como tradução literal. Comentários PGN de uma posição exata têm prioridade; correspondências temáticas são identificadas como tal. Se nenhum trecho corresponder, isso aparece explicitamente. Livros Polyglot contêm jogadas, não prosa.

**O Stockfish não lê nem é treinado pelos livros.** A consulta bibliográfica é feita pelo aplicativo; o cálculo enxadrístico é feito pelo motor. Não há compreensão semântica por um modelo de linguagem. O material orienta as explicações, mas não substitui nem altera arbitrariamente os cálculos. As referências e explicações em português também acompanham o PGN exportado. Sem Stockfish, **Estudar** prepara descrições factuais, sem atribuir avaliações do motor.

As explicações são preparadas sob demanda em um único lote em segundo plano. O painel de texto só aparece quando o lote inteiro fica pronto. Posições e explicações são pré-carregadas no navegador; as setas atualizam ambos imediatamente, sem esperar uma nova análise ou a confirmação do servidor. Eventos têm uma sequência e um identificador da partida, impedindo que respostas atrasadas desfaçam a navegação. Trocar partida, variante, livros, rating ou qualidade invalida o lote. O trabalho anterior é cancelado entre buscas; respostas antigas não substituem a partida atual. Há apenas um processo Stockfish ativo por aplicativo, com **1 thread e 64 MB de hash** (o consumo total inclui também o executável e suas redes NNUE). O processo encerra ao concluir, falhar ou cancelar.

As qualidades Rápida, Equilibrada e Profunda limitam cada busca a 0,08 s, 0,25 s e 0,7 s, respectivamente, além de limites de profundidade. Isso implica uma aproximação dependente do tempo disponível. Não é preciso conexão para avaliar uma partida com os livros já carregados; histórico Chess.com e táticos Lichess continuam usando suas APIs públicas.

## Perfil e tabuleiro

- A página principal mostra **oito tabuleiros com as últimas partidas do Chess.com**, em ordem da mais recente, e a precisão abaixo de cada um. Os botões de cada partida abrem o tabuleiro ou suas opções de análise; **Análise** também está no menu lateral. Sem oito partidas disponíveis, os espaços restantes indicam isso. A precisão oficial é preservada; quando ausente, o Stockfish calcula uma **estimativa identificada** em segundo plano, sem inventar valores enquanto o cálculo está pendente.
- **Desempenho** abre um dashboard compacto roxo: filtros de 7 e 30 dias, aberturas mais usadas, taxas de vitória/derrota/empate em rosca, evolução diária e qualidade dos seus lances. O histórico do período é buscado em segundo plano sem o limite de 100 partidas. As análises concluídas salvam as contagens por classificação em `data/performance/`; partidas sem avaliação ficam fora do gráfico de qualidade. Abrir o dashboard não inicia o Stockfish.
- O avatar, o nick e o rating ficam no topo da barra lateral. **Minha conta** abre o perfil público do Chess.com ou permite entrar/trocar de usuário sem senha.
- Para trocar a foto, clique no avatar do canto superior esquerdo. Arraste e ajuste o zoom; **Usar foto** envia somente o corte quadrado. PNG, JPEG e WebP são aceitos, até 10 MB e 20 milhões de pixels. A foto permanece na sessão.
- Arraste peças, escolha promoções e use as setas ←/→ ou Home/End para navegar. Alternativas preservam a linha anterior como variante no PGN exportado.
- **Anotações** abre os lances em duas colunas clicáveis, **Brancas** e **Pretas**, incluindo partidas iniciadas por FEN. A sub-aba **PGN** mostra a partida completa com **Copiar PGN**, que usa a área de transferência do navegador e oferece seleção manual caso ela esteja bloqueada. Clique em qualquer lance ou em **Posição inicial** para atualizar o tabuleiro e a explicação. A aba **Anotações** também contém a lista e o tabuleiro.
- O seletor **Escolher partida no histórico**, logo acima do tabuleiro, consulta até 100 partidas públicas recentes, em até 12 meses com partidas. Selecione uma partida para abri-la automaticamente.
- Livros PDF, TXT, Markdown, PGN comentado e Polyglot podem ser carregados. Os trechos são indexados localmente e as fontes usadas são exibidas com a explicação. PDFs digitalizados podem ser lidos visualmente; precisam de OCR para a busca textual.

## Estudo, perguntas e aparência

A página **Análise** apresenta o tabuleiro centralizado e ampliado, com o gato acomodado abaixo. A barra de ações reúne **Analisar Partida**, **Estudar** e **Anotações**. **Estudar** abre as explicações; **Fechar estudo** recolhe o texto. **Analisar Partida** abre as opções **Análise Rápida**, **Análise Mediana** e **Análise Profunda**; essa análise só inicia após **Iniciar análise**. A caixa **Resumo da qualidade dos lances** acompanha o processamento e, ao concluir, mostra as sete classificações, contagens e proporções por jogador, além das precisões oficiais ou estimadas identificadas. Os resultados continuam nos lances e no PGN.

Antes de iniciar, o formulário permite escolher **Stockfish** ou **Berserk**. Os dois são executados localmente; o Berserk 14 para Windows acompanha esta instalação em `engines/berserk/`, com fonte e licenças. O resumo e as explicações identificam o motor realmente usado. A escolha não dispara análise automática e uma falha não troca de motor silenciosamente. Uma posição montada no editor também pode ser analisada sem uma partida com lances. A seleção fica preservada durante a sessão; a preparação de aulas continua usando Stockfish.


Em **Estudo com livros**, os uploads são adicionados à biblioteca sem apagar os anteriores. Cada PDF mostra sua primeira página como capa; arquivos de texto recebem uma capa com o título. **Abrir livro** começa na primeira página. O leitor conserva a diagramação original dos PDFs e oferece páginas anterior/próxima e salto por número. Ao lado, um tabuleiro independente permite jogar e navegar sem perder a página lida. **Editar posição** permite arrastar, colocar ou apagar peças, limpar tudo, restaurar a posição inicial e importar FEN; lado a jogar e direitos de roque também são editáveis. A posição é validada ao concluir a edição. Livros e posições permanecem na sessão ao trocar de aba; não são salvos como biblioteca permanente no disco.

Uma **lupa no canto superior direito** abre **Pergunta rápida**. A caixa fica escondida até esse clique. Ela valida a posição atual, inclusive a do exercício tático aberto, e responde localmente sobre lances em SAN/UCI, material, ameaças, roque, casas e o último lance. Não chama serviços de IA nem espera o Stockfish. O objetivo é processar em menos de 5 segundos; o tempo medido aparece com a resposta. É um interpretador de perguntas enxadrísticas comuns, sem a compreensão geral de um modelo de linguagem. Perguntas fora desse escopo recebem uma indicação dos assuntos disponíveis. A duração da análise completa depende da partida e da qualidade escolhida e não está sujeita a esse prazo.

**Configurações**, com a engrenagem na barra esquerda, reúne o tema **Claro/Escuro**, o **Fundo de tela**, a biblioteca de **Livros** e as opções de tabuleiro, treino e exportação. O fundo padrão é discreto e liso; **Restaurar fundo do tema** remove uma imagem personalizada. O tema aplica uma paleta única a formulários, menus, anotações, avaliações, recorte da foto e explicações; a preferência é salva localmente. A barra lateral inicia recolhida; ao abri-la, aparecem o perfil, o atalho para a conta e os quatro destinos principais.

A barra lateral principal apresenta **Partida, Análise, Tático, Preparo e Aberturas**. Anotações continuam disponíveis na área de análise e o estudo de livros também pode ser aberto pelo atalho do painel.

**Aberturas** oferece treino livre de um repertório: escolha a abertura e o lado, aprenda com setas e repita de memória. Você pode continuar o treino em outro dia ou começar novamente. Esse progresso é salvo em `data/preparation/openings/`, separado do calendário de preparo.

Na aula de aberturas, o jogador executa todos os seus lances: **Aprender** orienta com uma seta e a notação do lance, depois **Memorizar** e o quiz verificam o aprendizado. Somente o adversário responde automaticamente. Os quadrados no painel de treino mostram acertos em verde, erros em vermelho e dicas solicitadas em amarelo. No aprendizado, um erro mantém a posição para tentar novamente; na memorização, a linha reinicia, e no quiz a pergunta se repete. A confirmação do servidor libera cada nova tentativa. Se ela demorar, a recuperação confere a revisão e a posição: um lance que não chegou é processado, e uma tentativa já recebida é ignorada, sem executar o lance duas vezes ou duplicar pontos.

O tabuleiro fica sobre uma mesa de madeira, que pode ser ocultada em **Configurações → Mostrar mesa sob o tabuleiro**. A preferência é salva localmente. O gato ocupa uma área próxima à do tabuleiro: espia pela esquerda, olha para cima, recua, entra pela direita, senta, observa e se deita. Os passos acompanham o deslocamento; deitado, mantém o corpo estável e balança a cauda separadamente, devagar. Na análise ampliada, acomoda-se abaixo do tabuleiro e da barra de navegação. A sequência não reinicia ao navegar pelos lances e respeita movimento reduzido.

Arraste com o **botão direito** em qualquer tabuleiro interativo para desenhar setas. Repetir a mesma origem e destino apaga a seta. As marcações são locais, permanecem durante atualizações da análise e somem ao mover uma peça ou navegar para outra posição.

## Preparo

Novos preparos usam o catálogo de repertórios prontos: selecione até quatro aberturas e um período para criar a trilha de revisões. Os dias aparecem em um caminho com círculos; o dia atual abre o treino. Cada linha começa com uma aula guiada e depois retorna para memorização. Linhas com erros ou ajuda voltam à fila até serem concluídas sem assistência. As revisões seguintes são agendadas conforme a retenção.

A tela de aberturas usa fundo escuro, tabuleiro em tons de madeira, progresso laranja e marcadores dos lances. Durante a memorização, os contadores **A fazer, Erro, Não sei e Certo** mostram a primeira tentativa de cada lance. Ao terminar uma linha, o tabuleiro permanece visível até clicar em **Repetir de memória**, **Próxima linha** ou **Ver resultado**. A tela só atualiza após uma ação ou uma transição da animação, sem consultas contínuas enquanto o jogador pensa.

Preparos antigos já salvos com análise do histórico continuam com o fluxo descrito abaixo.

Informe as datas e selecione **até quatro aberturas nos cards** do seu histórico Chess.com. A quinta seleção fica bloqueada; desmarcar uma libera outra escolha. O limite também é validado ao criar o plano. O gráfico comparativo oferece filtros semanais, mensais e do ciclo atual.

O Stockfish examina até **12 partidas recentes** relevantes por lote para identificar pontos a melhorar. As fraquezas mostram os temas e as fases dos erros encontrados nessa amostra, sem tratar uma amostra pequena como diagnóstico de todo o histórico. Ao criar o preparo, o aplicativo calcula linhas recomendadas e soluções de erros reais nas aberturas selecionadas. São consideradas perdas de pelo menos 5 pontos percentuais dos pontos esperados; sem motor ou sem erros identificados, não são inventados exercícios.

Depois de criar o plano, aparecem apenas a **trilha contínua com quadrados por dia** e o card de imagem/status. Clique no dia atual para abrir a próxima fase disponível: **Aberturas → Meio-jogo → Táticos**, 30 minutos cada e no máximo 10 táticos. Os dias futuros ficam bloqueados até a data correspondente, no horário de Brasília. O treino ocupa uma tela dedicada, sem menus, perfil ou busca, com o cronômetro fixo no topo.

Em **Aberturas**, as novas variações podem chegar a 12 decisões do jogador, com respostas adversárias automáticas. Cada linha inédita começa com setas, passa pela repetição de memória e termina no quiz de quatro estados. No quiz, os erros retornam aleatoriamente e exigem dois acertos sem ajuda para serem concluídos. Após **Continuar**, a próxima linha inédita começa pelo aprendizado com setas. O progresso e a posição da aula ficam salvos.

O **Meio-jogo** apresenta posições dos erros do próprio jogador na abertura escolhida. Após uma tentativa errada, a explicação ao lado mostra a alternativa calculada e a continuação para comparar. Os **Táticos** também vêm desses erros reais, com a opção de rever a partida antes de resolver. Quando não há posições disponíveis em uma fase, o aplicativo informa isso e permite concluir essa revisão.

**Encerrar Preparo** no mapa ou **Concluir Treino** na aula encerra o ciclo e abre um modal central sobre o fundo desfocado. A precisão é a porcentagem de acertos sobre as tentativas válidas feitas pelo jogador, incluindo as tentativas guiadas; sem tentativas, mostra “—”. Uma linha só conta como aprendida ao concluir aula, repetição e quiz, sem duplicar linhas revisitadas. A única ação do modal é **Iniciar Novo Preparo**, que limpa o ciclo e volta à seleção. O encerramento também acontece ao terminar o período ou todas as fases do último dia.

Plano, material e progresso são salvos por jogador em `data/preparation/`; `ACERVO_PREPARATION_DIR` muda essa pasta. Recarregar conserva a posição e volta ao mapa sem cobrar tempo offline. O resultado final também persiste ao recarregar.

## Táticos

Antes de escolher um tema, um tabuleiro grande e central reproduz soluções legais automaticamente, com uma opção de pausar. Escolha um dos 20 cards ilustrados para iniciar a sessão. O tabuleiro usa casas verdes e claras. Os ratings inicial e final ficam em **Faixa de rating · opcional**: campos vazios permitem qualquer rating. O menu **Tema tático** permite trocar de tema a qualquer momento.

A [API pública do Lichess](https://lichess-org.github.io/api/#tag/Puzzles/operation/apiPuzzleNext) oferece dificuldade relativa, com referência 1500 para visitantes anônimos, e não um filtro numérico exato. O cliente faz no máximo três tentativas sequenciais, valida tema e rating e **não apresenta exercícios fora da faixa como resultados compatíveis**. Se não encontrar, informa o motivo e permite ampliar a faixa ou tentar novamente. Não baixa o banco de táticos. Faixas extremas ou estreitas podem não retornar resultados.

O carregamento inicial prepara **dois exercícios diferentes** antes de exibir o primeiro. Durante a resolução, a fila mantém até dois próximos exercícios em segundo plano. Ao validar o último lance, o próximo já preparado substitui o atual, sem consulta de rede nesse avanço. São excluídos o exercício atual, os da fila e até 100 exercícios recentes. Falhas de conexão ou limites da API podem esgotar a fila; nesse caso, o aplicativo mostra o motivo e permite tentar novamente, sem repetir silenciosamente um tático. Trocar tema ou faixa descarta a fila antiga e ignora resultados atrasados.

**Recomeçar tático** restaura a posição inicial sem acesso à rede. Cada tentativa tem uma revisão de estado: eventos antigos são ignorados, e seleção, promoção e animação são limpas. O menu de temas conserva o filtro opcional de rating. A partida principal permanece preservada.

O ferreiro acompanha o exercício sem um título acima do vídeo: a cada lance correto apresenta uma nova frase de motivação. A leitura em voz alta pode ser desativada em **Configurações → Voz do ferreiro** e depende das vozes disponíveis no navegador. Ao concluir sem erros, a lâmina ganha brilho e recebe uma martelada com faíscas. Um erro mostra um comentário explicando que a espada foi prejudicada. A martelada acontece na conclusão; frases e reações não se repetem durante atualizações de carregamento. O indicador **Fio da lâmina** é apenas um recurso lúdico da sessão, sem alterar o rating ou a seleção dos exercícios.

## Pontos esperados e classificação

O indicador da revisão usa a curva pública do Lichess: `1 / (1 + exp(-0,00368208 × cp))`, com centipeões limitados a ±1000 e mates tratados como vitória ou derrota. Ele é calculado da perspectiva de quem jogou. Não é o WDL de partidas entre motores nem uma probabilidade calibrada ao rating humano. O WDL continua disponível para a explicação da posição inicial, mas não é misturado com esse indicador na classificação.

O lance jogado e a melhor alternativa são comparados na mesma busca MultiPV, reaproveitando a avaliação se o lance já estiver entre os candidatos. Perdas a partir de cinco pontos percentuais passam por uma confirmação com maior profundidade e tempo. Isso reduz a influência de buscas rápidas inconsistentes; não elimina todas as limitações de uma análise com orçamento finito.

| Categoria | Cor | Regra |
|---|---|---|
| ♞✧ Brilhante | Turquesa | Sacrifício produtivo de peça confirmado, com perda de no máximo 0,005 |
| ♛◇ Melhor | Violeta | Primeira escolha do motor, com perda zero |
| ♜◈ Excelente | Verde escuro | Perda menor que 0,02, incluindo alternativas empatadas na avaliação arredondada |
| ♝⋄ Bom | Verde-lima | De 0,02 até menos de 0,05 |
| ♟⌁ Imprecisão | Amarelo | De 0,05 até menos de 0,10 |
| ♚⨯ Erro | Laranja | De 0,10 até 0,20, inclusive |
| ♟‼ Capivorada | Vermelho | Acima de 0,20 |

São exatamente **sete avaliações**, com símbolos distintos e contraste de texto de pelo menos 4,5:1. A legenda, a peça, o rótulo sob o tabuleiro, o resumo e as anotações usam o mesmo registro. O PGN exportado recebe o nome e o símbolo nos comentários. Antes do cálculo, nenhum selo de qualidade é atribuído. **Livro** permanece uma referência bibliográfica, sem substituir a avaliação enxadrística.

Somente após solicitar uma análise, lances **Brilhante** recebem efeitos especiais: raio e aura azul para a peça branca, meteoro e aura vermelha para a peça preta. A orientação do tabuleiro não muda a cor do efeito. Atualizações da mesma posição não repetem o impacto; navegar a outro lance limpa o efeito anterior. A preferência do sistema por movimento reduzido mantém apenas a aura estática. Táticos e edição de posições não exibem esses efeitos.

As regras especiais são aproximações documentadas, não o algoritmo privado do Chess.com. **Encontrar a única boa jogada não basta para receber Brilhante.** O detector conservador exige que a peça do lance seja capturada na resposta e mantenha um déficit de pelo menos 1,5 peão por duas oportunidades de recuperar material, ou até dar mate. Isso inclui sacrifícios de qualidade e peça por peão, mas exclui ofertas de peão, trocas equilibradas e perdas de outras peças ocorridas depois. Sacrifícios com aceitação mais tardia podem não ser reconhecidos.

Brilhante exige ainda uma busca de confirmação, posição ao menos equilibrada, perda de no máximo 0,5 ponto percentual, segunda alternativa global abaixo de 95% no indicador e ausência do lance no catálogo de aberturas. O rating não torna essas condições mais permissivas. Uma comparação restrita a dois lances não comprova qual é a segunda alternativa global e não habilita o selo.

O catálogo de aberturas CC0 do Lichess continua disponível como fonte, mas não sobrepõe a classificação por perda de chances. Uma alternativa com pontuação arredondada igual à melhor não recebe automaticamente Melhor ou Brilhante: Melhor exige a primeira escolha do motor; Brilhante exige as condições de sacrifício descritas acima.

Precisão oficial do Chess.com é preservada quando disponível. Nos demais casos, a precisão é uma média estimada de uma curva exponencial aplicada à perda do indicador de chances; não reproduz CAPS2 nem a agregação do Lichess.

Referência conceitual: [classificação de lances do Chess.com](https://support.chess.com/en/articles/8572705-how-are-moves-classified-what-is-a-blunder-or-brilliant-etc). Os limites acima seguem o pedido deste projeto, incluindo Capivorada estritamente acima de 20%.

## Publicação e testes

`Dockerfile` e `render.yaml` permitem publicar no Render. A imagem Linux instala Stockfish e define STOCKFISH_PATH. Não são necessárias credenciais de IA.

Na pasta do aplicativo, execute `.venv\Scripts\python.exe -m pytest tests -q` (Linux/macOS: `.venv/bin/python -m pytest tests -q`). A suíte cobre regras de xadrez, importação, Stockfish e fontes bibliográficas, limites de classificação, navegação sem novas avaliações, busca por faixa e reinício de táticos. Os testes de componentes usam Playwright e Edge/Chromium já instalado e não iniciam servidor nem baixam navegadores. Para verificar a interface integrada, execute `.venv\Scripts\python.exe tests/browser_smoke.py`: o comando executa os testes atuais de login, análise, livros, aberturas e perfis, com servidores temporários e dados isolados. As capturas ficam em `tests/artifacts/`, e os servidores são encerrados ao terminar.

## Preparo por repertórios fechados

A página **Preparo** oferece 12 cursos locais (72 linhas) em duas abas: **Brancas** e **Pretas**. Escolha de 1 a 4 cards e confirme para abrir a trilha visual dos dias. Clique no dia atual ou em **Começar preparo do dia** para treinar. O catálogo e o treino funcionam sem histórico do Chess.com ou Stockfish. Os totais dos cards correspondem aos caminhos realmente empacotados; não representam cobertura exaustiva de todas as respostas legais.

O treino usa uma tela focada: tabuleiro centralizado, progresso discreto acima e instruções e ações abaixo. As estatísticas ficam no resultado do dia. O tabuleiro vira para o lado do repertório e joga as respostas do adversário automaticamente. Cada linha nova começa em **Aprender**, com seta e o botão **Jogar lance sugerido**. A posição final fica visível até clicar em **Repetir de memória**; depois da memorização, **Próxima linha** continua o treino e **Ver resultado** encerra o dia. A dica está disponível desde o primeiro lance e aparece automaticamente após um erro. Erros não entram no histórico. Uma linha com erro ou ajuda na memorização retorna ao fim da fila e só sai após uma execução completa sem ajuda. Quando resta apenas essa linha, ela é repetida em seguida.

A precisão diária é `acertos na primeira tentativa / decisões testadas`, considerando apenas a memorização: o aprendizado guiado não altera as métricas e pedir ajuda não conta como acerto. Insistir na mesma posição não aumenta o denominador, enquanto uma nova passagem na repetição é um novo teste. Linhas dominadas são caminhos concluídos sem erro ou ajuda na primeira passagem de memória do dia; linhas recuperadas na repetição aparecem separadamente. Revisões limpas são agendadas em 1, 3, 7, 14 e 30 dias; erros reiniciam o intervalo em 1 dia. A conclusão exige esvaziar a fila e apresenta um modal com as métricas.

O progresso é salvo por usuário em `data/preparation/` (visitantes sem usuário compartilham o perfil local vazio). Planos antigos continuam disponíveis; o botão **Criar novo preparo com repertórios prontos** permite substituí-los. Os novos módulos são `opening_repertoires.py`, `opening_training_state.py`, `opening_catalog_ui.py` e `opening_training_ui.py`.

Validação: `.venv\Scripts\python.exe -m pytest tests/test_opening_training.py tests/test_opening_training_ui.py tests/test_opening_catalog_tabs.py -q`. Os testes visuais precisam de Playwright e Edge/Chromium; os testes integrados abrem e encerram servidores temporários com armazenamento isolado e cobrem a continuação após o quinto lance, dicas, repetição de memória e retomada pela trilha.


## Posições dos livros sincronizadas com a leitura

O leitor apresenta o livro ampliado na metade esquerda e o tabuleiro na metade direita, com os ajustes abaixo. A página inteira mantém sua proporção em uma área da mesma altura do tabuleiro; topo e base ficam alinhados. Ao abrir um novo livro, o tabuleiro começa na posição inicial; passar páginas preserva os lances do usuário. As configurações ficam recolhidas em **Opções de estudo**. O seletor e os botões de próximo/anterior apenas escolhem o diagrama; **Carregar posição da página** aplica a escolha. As posições são preparadas automaticamente em segundo plano, mas nunca substituem o tabuleiro sem essa ação explícita. **Reexaminar página** tenta o reconhecimento em maior resolução, preservando os diagramas existentes.

As setas **← / →** seguem a última área clicada: no livro, mudam páginas; no tabuleiro, percorrem os lances. Essa seleção permanece durante as atualizações e funciona também no modo foco. Campos de texto e seletores mantêm seus próprios atalhos.

Os livros ficam salvos por conta em `data/book_library.sqlite3`, com limite global de 500 MB para seus arquivos; o envio é atômico e não duplica um livro já salvo. A preparação local cobre todas as páginas em segundo plano, com progresso na biblioteca, prioridade para a página atual/próximas e cache em `data/book_positions/` (ambos ignorados pelo Git). Continuações SAN são anexadas aos diagramas somente quando os lances são legais nessa posição. Abaixo do tabuleiro, é possível restaurar o diagrama ou a linha original depois de testar alternativas. A partida principal e suas análises permanecem independentes do tabuleiro do livro.

O reconhecimento visual usa [chessvision 0.13.0](https://github.com/harshitpawar64/chessvision) (GPL-3.0), com seu classificador ONNX incluído no pacote e OpenCV. Nenhuma página ou imagem é enviada a serviços externos. As posições reconhecidas passam por limites de confiança e validação de xadrez; páginas sem reconhecimento seguro mantêm o tabuleiro atual. Turno e roques ausentes são indicados na interface. PGNs são divididos por partidas completas, preservando posições iniciais personalizadas e a navegação dos lances.

Validação: `.venv/Scripts/python.exe -m pytest tests/test_book_positions.py tests/test_book_positions_ui.py tests/test_library_home.py -q`. Os testes incluem reconhecimento real de PDF digitalizado, vários diagramas, cache/preparação antecipada e navegação entre páginas pela interface.
