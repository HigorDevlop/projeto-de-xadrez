# Táticos: seletor e painel compacto

Os temas aparecem em esferas. Segure e arraste horizontalmente para girar; setas do teclado, botões laterais e toque também estão disponíveis. Cada esfera tem um pequeno símbolo dourado do tema, com peças e setas, sem tabuleiro ao fundo. Clique numa esfera ou em **Começar** para abrir. A transição fica preta enquanto o exercício é preparado e é liberada quando o tabuleiro está disponível. Um limite de 15 segundos libera a tela em caso de falha no carregamento.

O tabuleiro mantém as respostas pré-carregadas e o próximo exercício é preparado em segundo plano. O painel exibe somente os dados e as três ações principais: **Dica**, **Recomeçar** e **Pular**. Tema e limites de rating ficam dentro de **Ajustes**, no rodapé.

## Indicadores de cada treino

- **Pizza:** acertos e erros dos lances enviados. A porcentagem usa acertos / tentativas.
- **Preparo:** exercícios diferentes concluídos na categoria / meta. A meta é 20 por tema e 50 no Aleatório; o painel exibe também a quantidade real.
- **Tempo:** cronômetro local do exercício em curso e média até a conclusão. Recomeçar zera o cronômetro. Ao concluir, o tempo é registrado e fica parado enquanto o próximo tático é preparado; o próximo começa do zero.
- **Últimos táticos:** os cinco últimos tempos de resolução ficam abaixo do cronômetro, com o mais recente em destaque. A cada conclusão, os anteriores ficam mais discretos e o sexto sai do painel. O histórico completo continua salvo por conta.
Ao clicar em **Táticos** no menu, a tela de **Começar** reaparece. O novo treino zera acertos, erros, preparo, cronômetro, média e a lista dos últimos tempos. O histórico completo permanece no banco local.

- **Rank tático:** níveis pessoais por XP: Bronze (0), Prata (200), Ouro (600), Platina (1.500), Diamante (3.000) e Mestre (6.000).

Concluir um exercício novo concede 30 XP sem erro ou dica, ou 20 XP após ajuda ou erro. Resolver novamente um exercício rende 5 XP por conclusão, incentivando a revisão. Eventos repetidos de comunicação não duplicam resultados nem pontos.

Os registros ficam no banco local `tactics.sqlite3`, dentro da pasta de progresso do usuário. Na instalação Windows padrão: `%LOCALAPPDATA%\CoachChess\preparation`. Funcionam offline e persistem ao fechar e reabrir o aplicativo. A contabilização começa com os exercícios registrados por esta interface.

**Fechar app** fica no canto superior direito, inclusive na entrada e no modo foco. **Fechar aplicativo** também aparece no menu lateral da versão desktop. Ambos solicitam o fechamento da janela dedicada do Coach Chess.

Esta manutenção preserva contas, livros, preferências e progresso existentes, sem gerar versão ou instalador.
