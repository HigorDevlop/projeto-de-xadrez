# Stockfish

O binário oficial para Windows 64-bit já está incluído nesta pasta como `stockfish.exe`. Assim, clones usados no Windows ficam prontos para analisar partidas.

Para outros sistemas, coloque o executável correspondente nesta pasta para manter o mesmo caminho relativo:

- Windows: `engines/stockfish.exe`
- Linux: `engines/stockfish`
- macOS: `engines/stockfish-mac`

O arquivo precisa ser executável no sistema do usuário. Baixe o binário oficial correspondente à plataforma em [stockfishchess.org](https://stockfishchess.org/download/) e mantenha a licença GPL distribuída com ele.

O aplicativo procura primeiro o binário nativo desta pasta. `STOCKFISH_PATH` e um executável `stockfish` instalado no sistema são alternativas de compatibilidade.