# Banco local de táticos

30.033 exercícios extraídos do banco público Lichess, com todos os temas do aplicativo e soluções conferidas por python-chess. A primeira jogada da linha original, que pertence ao adversário, já está aplicada na FEN guardada para o treino.

Fonte: https://database.lichess.org/#puzzles
Download original: https://database.lichess.org/lichess_db_puzzle.csv.zst
Licença: CC0 1.0 — https://creativecommons.org/publicdomain/zero/1.0/

O arquivo `manifest.json` informa quantidade por tema, data de preparação, origem e hash SHA-256 do arquivo compactado. A seleção, a validação das respostas e o carregamento dos próximos exercícios não usam internet. Essa amostra não representa os milhões de exercícios do banco completo.

O importador `scripts/prepare_offline_tactics.py` é uma ferramenta do desenvolvedor e usa zstandard para ler parte do arquivo original. O aplicativo instalado usa somente gzip da biblioteca padrão; não precisa de zstandard nem baixar o banco ao abrir.
