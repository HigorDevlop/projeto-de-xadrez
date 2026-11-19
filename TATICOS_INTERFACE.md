# Táticos: seletor e painel compacto

Os temas permanecem no carrossel de esferas douradas: segure e puxe horizontalmente para girar, use as setas do teclado ou os botões laterais. Selecione **1 min**, **3 min** (padrão) ou **5 min**, escolha **Automático** ou **Manual**, e clique numa esfera ou em **Começar**. No automático, a moeda entra e a roda gira sozinhas. No manual, arraste a moeda para a fenda e depois segure a roda e faça uma volta. Também há botões e suporte a Enter/Espaço. A escolha fica lembrada no navegador. **Voltar** retorna ao carrossel sem começar o treino. A máquina espera o usuário pelo tempo necessário; o limite de segurança de 20 segundos só é iniciado depois da interação manual. O chiclete escolhido sai, ganha zoom e dá lugar à contagem **3, 2, 1**. Tudo funciona offline.

O tempo da sessão começa quando o primeiro tabuleiro está pronto. A barra **Tempo do treino** mostra o tempo restante, separado do tempo por exercício. Recomeçar um exercício não reinicia a sessão. Ao acabar, o tabuleiro deixa de aceitar respostas e aparece o resumo com a opção **Escolher próximo treino**. O XP e o rank permanecem salvos.

A transição usa a arte local `assets/tactics-gumball-cinematic.png`. Os temas estão nos chicletes, e a moeda entra na fenda externa. O chiclete que sai preserva o símbolo do tema selecionado. A apresentação dura quatro segundos antes da contagem; o cronômetro do treino não corre durante a animação. O sistema respeita a preferência de movimento reduzido. Arte e prompt estão documentados em `assets/TACTICS_CINEMATIC.md`.

O tabuleiro mantém as respostas pré-carregadas e o próximo exercício é preparado em segundo plano. O painel exibe somente os dados e as três ações principais: **Dica**, **Recomeçar** e **Pular**. Tema e limites de rating ficam dentro de **Ajustes**, no rodapé.

## Indicadores de cada treino

- **Pizza:** acertos e erros dos lances enviados. A porcentagem usa acertos / tentativas.
- **Preparo:** exercícios diferentes concluídos na categoria / meta. A meta é 20 por tema e 50 no Aleatório; o painel exibe também a quantidade real.
- **Tempo:** cronômetro local do exercício em curso e média até a conclusão. Recomeçar zera o cronômetro. Ao concluir, o tempo é registrado e fica parado enquanto o próximo tático é preparado; o próximo começa do zero.
- **Últimos táticos:** os cinco últimos tempos de resolução ficam abaixo do cronômetro, com o mais recente em destaque. A cada conclusão, os anteriores ficam mais discretos e o sexto sai do painel. O histórico completo continua salvo por conta.
Ao clicar em **Táticos** no menu, a tela de **Começar** reaparece. O novo treino zera acertos, erros, preparo, cronômetro, média e a lista dos últimos tempos. O histórico completo permanece no banco local.

- **Rank tático:** Bronze, Prata, Ouro, Platina, Diamante e Mestre têm divisões **1 a 5**. Os limiares das categorias e o XP anterior foram preservados. Bronze 1 começa em 0 XP; Bronze 2 em 40, Bronze 3 em 80, Bronze 4 em 120 e Bronze 5 em 160. Prata 1 começa em 200. A barra mostra o progresso até a próxima divisão. Mestre 5 começa em 10.800 XP.

A dificuldade começa com alvo de **500 de rating** em cada treino e sobe **100 pontos a cada dois exercícios diferentes resolvidos sem erro nem dica**, até alvo 3.000. Repetir, pular ou pedir ajuda não aumenta a dificuldade. Temas com poucos exercícios usam a faixa disponível mais próxima do alvo. Os limites opcionais de rating continuam sendo respeitados. O próximo exercício é preparado em segundo plano; os exercícios já preparados são preservados para evitar pausas. O novo alvo é aplicado às próximas seleções do banco local.

Concluir um exercício novo concede **5 XP sem erro ou dica**, ou **1 XP após ajuda ou erro**. Resolver novamente um exercício não concede XP; a revisão continua sendo registrada no histórico. Eventos repetidos de comunicação não duplicam resultados nem pontos. O primeiro avanço, de Bronze para Prata (200 XP), exige ao menos 40 exercícios diferentes concluídos sem ajuda.

Toda a tela de táticos tem um cenário local inspirado em **Shadows of Evil**, com néon azul, iluminação âmbar e detalhes urbanos escuros. Os painéis translúcidos preservam a leitura. O cenário desaparece ao trocar de aba. Os chicletes ficam em uma pilha irregular dentro do vidro, com símbolos, cores e rotações próprias.

Ao promover um peão, uma roda sobre o tabuleiro permite escolher dama, torre, bispo ou cavalo. É possível clicar, arrastar para girar ou usar as setas e Enter. Escape cancela; o lance só é enviado depois da escolha.

Uma manutenção solicitada pelo proprietário pode zerar os pontos de uma conta sem apagar tentativas, exercícios resolvidos, tempos ou histórico. O reset é auditado localmente e não se repete ao reabrir o aplicativo.

Os registros ficam no banco local `tactics.sqlite3`, dentro da pasta de progresso do usuário. Na instalação Windows padrão: `%LOCALAPPDATA%\CoachChess\preparation`. Funcionam offline e persistem ao fechar e reabrir o aplicativo. A contabilização começa com os exercícios registrados por esta interface.

**Fechar app** fica no canto superior direito, inclusive na entrada e no modo foco. **Fechar aplicativo** também aparece no menu lateral da versão desktop. Ambos solicitam o fechamento da janela dedicada do Coach Chess.

Esta manutenção preserva contas, livros, preferências e progresso existentes, sem gerar versão ou instalador.
