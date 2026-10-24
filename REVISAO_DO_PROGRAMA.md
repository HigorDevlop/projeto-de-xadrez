# Revisão do programa — 21/10/2026

Foram verificados os 140 arquivos Python, as dependências instaladas e os fluxos cobertos pelos testes do projeto: análise, edição, livros, aberturas, táticos, progresso, perfis, salas e inicialização desktop.

## Falhas corrigidas

1. **PDF danificado interrompia o envio.** A leitura agora converte os erros do parser em uma mensagem de arquivo inválido, tratada pela biblioteca.
2. **Editor de livros mantinha roques impossíveis.** Mover ou retirar reis e torres atualiza os direitos de roque disponíveis, permitindo salvar a posição válida.
3. **Trocar o lado a jogar podia impedir o salvamento.** Nos dois editores, a troca remove a casa de en passant pertencente ao turno anterior.
4. **Progresso com JSON inválido podia derrubar o carregamento.** Valores como lista, número, `null` e nome de usuário inválido são recusados sem interromper a tela.
5. **Gravações simultâneas disputavam o mesmo arquivo temporário.** O progresso usa arquivos temporários exclusivos, substituição atômica e sincronização de leitura e escrita no processo.
6. **Trocar de conta mantinha dados da sessão anterior.** Partidas, análises, livros em memória, uploads e histórico de navegação são limpos; tarefas pendentes são canceladas e eventos antigos do tabuleiro são invalidados. Os arquivos persistidos de cada conta continuam separados.
7. **Movimento reduzido ainda permitia transições no tabuleiro.** As transições e animações CSS agora respeitam essa preferência.

## Testes de regressão

Os dez casos em `tests/test_review_regressions.py` reproduzem falhas de arquivos, editores, gravação concorrente e troca de conta. Os testes existentes verificam também movimento reduzido e os menus em desktop e celular.

Os testes antigos de interface foram atualizados para usar contas de teste isoladas, o login obrigatório, a profundidade por controle segmentado e a análise solicitada explicitamente. O estudo com livros continua separado da análise.

A verificação estática não encontrou erros de sintaxe ou nomes indefinidos. `pip check` não encontrou conflitos nas dependências instaladas.


## Leitor e validação final

O livro inteiro e o tabuleiro têm a mesma altura, com topo e base alinhados. Os controles ficam recolhidos em **Opções de estudo**. As posições são reconhecidas em segundo plano; selecionar um diagrama ou passar páginas não modifica o tabuleiro. O carregamento exige **Carregar posição da página**. As setas seguem a última área clicada.

A rodada geral executou **452 casos**: 433 passaram inicialmente. Os 19 casos que falharam foram corrigidos ou atualizados para o fluxo atual e reexecutados nos arquivos afetados. As rechecagens finais passaram, incluindo os sete últimos cenários de cursos, filtros e repetição em desktop/celular. Os quatro testes do leitor no navegador também passaram, verificando geometria, opções recolhidas, carregamento explícito e navegação por teclado.

Os resultados estão em `tests/artifacts/review-final.xml`, `review-recheck.xml` e `review-last.xml`, com logs correspondentes. Os XMLs preservam o diagnóstico inicial (19 falhas), a etapa intermediária (8 falhas) e a rechecagem final dos sete cenários de navegador (7 aprovados). O outro caso, de restauração do preparo, foi reexecutado isoladamente e passou. Os quatro testes do leitor foram reexecutados após a mudança final de layout e carregamento manual.

Para repetir toda a suíte: `.venv/Scripts/python.exe -m pytest tests -q`.
Para a verificação da interface: `.venv/Scripts/python.exe tests/browser_smoke.py`.
