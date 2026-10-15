# Como testar a versão desktop

## 1. Abrir

1. Na pasta do projeto, dê dois cliques em **Acervo Desktop.bat**. Você também pode usar o atalho **Acervo Desktop** da Área de Trabalho.
2. Aguarde a janela abrir em **Aberturas**. Se já estiver aberta com o visual antigo, pressione **Ctrl + R**.
3. Maximize a janela. A tela deve mostrar **LotusChess PRO**, as fileiras **Aberturas de Brancas** e **Aberturas de Negras**, cartões cinza e tabuleiros bege e marrom.

Se precisar preparar as dependências em outro computador, execute **iniciar.bat** uma vez antes de abrir a versão desktop. Nesta instalação, as dependências já estão disponíveis.

## 2. Conferir catálogo e curso

1. Clique em **Ver todas** na fileira de brancas.
2. Selecione **Outro** e pesquise **English**.
3. Abra **English Opening**. Você verá o cartão de ranking, as abas **Curso / Armadilhas / Variações**, o banner em degradê e a trilha de estrelas.
4. Clique na estrela com **COMEÇAR** ou no botão **Treinar**.

O catálogo separa o lado que você treina. Por exemplo, Sicilian Defense aparece tanto para aprender a jogar contra a defesa com as brancas quanto para praticá-la com as negras.

## 3. Testar os lances, o erro e a revisão

1. Siga a seta verde: clique na peça e na casa de destino, ou arraste a peça.
2. A resposta do adversário aparece automaticamente. Continue jogando os seus lances.
3. Para testar um erro, faça um lance legal diferente do indicado. A seta vermelha mostra a tentativa, e a verde mostra o lance da linha. Clique em **Próximo** e corrija.
4. Ao terminar a primeira passagem, clique em **Continuar**. Agora repita os lances de memória.
5. Se precisar, use **Não sei**. A posição será revisada novamente antes da conclusão.
6. Continue até a revisão com os quatro contadores: **A FAZER / ERRO / NÃO SEI / CERTO**.
7. Ao aparecer **Bom trabalho!**, clique em **Continuar**. A conclusão registra a atividade do dia e libera a próxima linha. A conquista da medalha aparece quando você atinge a meta de posições do curso.

**Pausar treino** interrompe a interação sem perder a posição. **Retomar treino** libera o tabuleiro. A lupa **Analisar posição** mostra a avaliação local e o lance da linha.

## 4. Conferir se ficou salvo

1. Volte ao curso e observe a estrela concluída e o progresso.
2. Feche e abra a janela novamente.
3. Abra a mesma abertura: o progresso deve continuar salvo. Uma aula interrompida também pode ser retomada por **Treinar**.
4. Use o ícone de chama para conferir sua sequência diária. Vários treinos no mesmo dia contam como um dia de atividade.

Os arquivos de progresso ficam em **data/preparation/openings/**. Mantenha a mesma conta para retomar o mesmo histórico; o modo sem conta também tem seu próprio progresso local.

## 5. Conferir as outras telas

- **Variações:** mostra os lances e permite explorá-los no tabuleiro sem alterar o progresso do curso.
- **Armadilhas:** mostra as armadilhas encontradas no catálogo local para aquela abertura. Algumas aberturas não têm armadilhas cadastradas.
- **Perfil:** mostra o gráfico e as taxas de vitória do histórico carregado. Se ainda não houver partidas, a tela informa isso. Para carregar sua conta, entre por **Partidas → Minha conta**, no menu lateral.
- **Finais:** oferece três exercícios jogáveis de mate em um lance, incluindo promoção.
- **Partidas** e **Puzzles:** abrem as áreas já existentes do aplicativo.

Os valores de rating, avaliações, vitórias e sequência diária refletem os seus dados e o motor local. Por isso, não precisam coincidir com os números das imagens de referência.

## Se a janela não abrir

Abra **iniciar.bat** e use o endereço informado no terminal. O registro do inicializador desktop fica em **data/desktop/server.log**. Fechar a janela mantém o servidor local ativo; abrir o inicializador novamente pode usar outra porta disponível.
