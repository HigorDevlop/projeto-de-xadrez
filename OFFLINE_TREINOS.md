# Táticos e Aberturas sem internet

O treino tático usa agora `data/tactics/puzzles.jsonl.gz`: 30.033 exercícios do banco Lichess, sob CC0, com todos os temas do aplicativo. As soluções foram verificadas durante a preparação do banco. Escolha do exercício, respostas automáticas e preparação dos próximos desafios acontecem no computador, sem consultar a API.

As Aberturas usam os cursos curados em `opening_repertoires.py` e o catálogo ECO em `data/openings/*.tsv`. Linhas, demonstração, treino, revisão e progresso são locais. O motor usado no cabeçalho é o executável incluído no aplicativo.

O repertório pessoal agora usa as partidas do Chess.com importadas para selecionar as posições mais enfrentadas e calcular continuações com Stockfish local. Histórico, recomendações e progresso são guardados no computador. Buscar partidas novas exige internet; preparar linhas já importadas e estudá-las não exige. Veja [ABERTURAS_PESSOAIS.md](ABERTURAS_PESSOAIS.md).

O servidor HTTPS atende presença e administração. Uma falha de rede não cria bloqueio; um bloqueio explícito do criador continua sendo respeitado. Nenhum download inicial é necessário para os dois treinos quando os arquivos do banco local e das aberturas já acompanham a instalação.

Foram testados exercícios reais do banco e uma lição de abertura com conexões externas bloqueadas no Python e no navegador. Os dados particulares de contas, livros e progresso permanecem separados dos arquivos do programa.

## Versões e instalação

Essas alterações não geraram uma nova versão ou instalador. O instalador publicado anteriormente não foi modificado. O empacotador já inclui `data/tactics` nas próximas distribuições, que serão geradas apenas quando o proprietário pedir.

A manutenção local autorizada substitui somente arquivos do aplicativo, faz backup e mantém o número publicado. Na instalação em Arquivos de Programas, a cópia só pode acontecer após a confirmação administrativa do Windows. O resultado da aplicação fica em `%LOCALAPPDATA%\CoachChess\maintenance\local-update-result.json`.
