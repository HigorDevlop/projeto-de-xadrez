# Motores de avaliação

O Windows usa `stockfish.exe`, atualizado para **Stockfish 19**, na compilação oficial **Windows x86-64 universal**. A inicialização e a análise MultiPV foram testadas neste computador. SHA-256 do executável: `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`.

O pacote foi obtido da [release oficial sf_19](https://github.com/official-stockfish/Stockfish/releases/tag/sf_19) e conferido contra seu SHA-256 publicado: `3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7`. A licença está em `Stockfish-COPYING.txt`; o código-fonte correspondente, os scripts e a documentação oficiais acompanham o motor em `stockfish-19/source/`. Consulte [os detalhes da atualização](stockfish-19/README.md). O executável 17.1 anterior foi preservado em `backups/stockfish-17.1.exe` para recuperação; a pasta antiga `source/` corresponde à versão anterior.

Para outra plataforma ou instalação, configure `STOCKFISH_PATH` com um binário compatível.

No Linux/macOS o app também procura `engines/stockfish`, `stockfish-linux`, `stockfish-mac` e o comando `stockfish` no PATH. O Docker instala o pacote Linux e usa `/usr/games/stockfish`.

Em **Análise → Analisar Partida → Motor de avaliação**, escolha **Stockfish** ou **Berserk** antes de iniciar. O Stockfish continua sendo a opção inicial; o Berserk 14 para Windows está em `berserk/`, com a rede, licenças e código-fonte correspondente. Consulte [Berserk](berserk/README.md). `BERSERK_PATH` permite configurar outra instalação desse motor.

O app usa um processo por vez e configura somente opções oferecidas pelo motor: uma thread, hash de 64 MB e WDL quando disponíveis. A comparação dos lances exige MultiPV. O nome real do motor acompanha cada avaliação, o resumo e as explicações. Trocar a seleção não inicia uma busca nem mistura resultados de motores diferentes. Um motor ausente ou com erro não é substituído silenciosamente.

A revisão usa a curva pública de chances do Lichess, com faixas e heurística de sacrifício próprias documentadas no README principal. Isso não reproduz o algoritmo privado do Chess.com. A preparação personalizada continua usando o Stockfish; a seleção é destinada à revisão na aba Análise.

Livros são indexados pelo aplicativo antes da avaliação, sem modificar ou treinar o Stockfish. Explicações usam trechos reais e composição por regras; não há modelo textual adicional.
