# Referências do sistema de aberturas

Consulta: 3 de outubro de 2026.

## Fontes públicas

- https://www.lotus-chess.com/ — descrição oficial do ensino linha por linha, domínio progressivo e personalização.
- https://apps.apple.com/us/app/lotus-chess-trainer/id6738741464 — descrição publicada pelo desenvolvedor, revisão de posições e biblioteca de aberturas.
- Capturas oficiais vinculadas pelo site: “Screenshot of the Lotus Learning View”, “Chess Openings made easy” e “Actually Master Opening Lines”. As capturas mostram níveis atual/próximo, abas Learn / Master / Dive Deeper, trilha com nós circulares, ação Train, gradiente violeta/vermelho/laranja e domínio de 0 a 10.

## Adaptação implementada na aba Aberturas

- Catálogo por brancas e pretas, com os repertórios curados que já existem neste projeto.
- Página do curso com níveis, progresso, trilha e abas Aprender / Dominar / Aprofundar.
- Aprender: demonstração com setas, repetição de memória e quiz de posições.
- Dominar: revisões agendadas e domínio por linha, de 0 a 10.
- Aprofundar: consulta da sequência completa e exploração no tabuleiro sem alterar o domínio.
- Estado persistente por usuário, abertura, linha e modalidade; namespace independente do Preparo.

## Regras locais e limites da equivalência

O código, o algoritmo de personalização, os limites dos níveis e a seleção de linhas do Lotus não são públicos. A implementação não usa seus serviços nem reproduz seu catálogo proprietário. Os intervalos de 1, 3, 7, 14 e 30 dias reutilizam as regras locais do projeto. O domínio cresce no máximo uma vez por dia, com redução após uma revisão com erros em outro dia. A trilha libera a próxima linha após demonstração, memorização e quiz da anterior. Os níveis são proporcionais ao domínio acumulado. Essas regras são uma implementação equivalente, não regras internas verificadas do Lotus.

Não há análise de partida nem inicialização do motor durante as respostas. O tabuleiro e a validação legal são os componentes existentes do projeto.
