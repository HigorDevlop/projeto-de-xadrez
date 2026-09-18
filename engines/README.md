# Stockfish

O Windows usa `stockfish.exe` (Stockfish 17.1 AVX2), restaurado da cópia existente em `xadrez/stockfish-windows-x86-64-avx2/stockfish`. O computador precisa suportar AVX2. SHA-256: `5F95EAEA0D4EB697381989187CE6EB4D6AD59283C34421765ECC73CDB09BA766`.

A licença está em `Stockfish-COPYING.txt`; o código-fonte correspondente e os scripts de compilação acompanham o motor em `source/`. Fonte oficial: [Stockfish 17.1](https://github.com/official-stockfish/Stockfish/tree/sf_17.1). Para outro processador ou plataforma, obtenha um binário compatível em [Stockfish](https://stockfishchess.org/download/) e configure `STOCKFISH_PATH`.

No Linux/macOS o app também procura `engines/stockfish`, `stockfish-linux`, `stockfish-mac` e o comando `stockfish` no PATH. O Docker instala o pacote Linux e usa `/usr/games/stockfish`.

O app usa um processo por vez, uma thread, hash de 64 MB e `UCI_ShowWDL`. Pontos esperados são vitória + metade dos empates. A classificação usa perdas nessa expectativa, com aproximações para Brilhante e Grande Lance; ela não reproduz o algoritmo privado do Chess.com. As probabilidades WDL do motor se referem ao seu modelo de jogo, não ao rating humano. Referência: [modelo WDL oficial](https://github.com/official-stockfish/WDL_model).

Livros são indexados pelo aplicativo antes da avaliação, sem modificar ou treinar o Stockfish. Explicações usam trechos reais e composição por regras; não há modelo textual adicional.
