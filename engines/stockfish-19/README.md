# Stockfish 19 — atualização de 22/10/2026

Instalado a partir da release oficial `sf_19`, publicada em 05/09/2026.

- Projeto e versão: https://github.com/official-stockfish/Stockfish/releases/tag/sf_19
- Pacote: https://github.com/official-stockfish/Stockfish/releases/download/sf_19/stockfish-windows-x86-64-universal.zip
- SHA-256 do pacote, conferido com o digest da API oficial do GitHub: `3c8bf1f9ea66a09350a40df4f632288285ac206d99f33ab5842c408fc30b48a7`.
- Executável original: `stockfish-windows-x86-64-universal.exe`, instalado como `../stockfish.exe`.
- SHA-256 do executável instalado: `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`.
- Identificação UCI verificada: `Stockfish 19`.
- Código-fonte, scripts de compilação, créditos e documentação extraídos do mesmo pacote em `source/`. A licença GPLv3 está em `source/Copying.txt`, também copiada para `../Stockfish-COPYING.txt`.
- Instruções de compilação oficiais: `source/wiki/Compiling-from-source.md`; scripts de obtenção das redes em `source/scripts/net.sh`.

O pacote baixado foi removido após a extração e verificação, sem duplicar o executável no projeto. O executável anterior está em `../backups/stockfish-17.1.exe`; nenhuma exclusão foi feita na antiga pasta `../source/`.

A versão 19 usa a integração UCI existente, aparece identificada pelo nome real nos resultados e continua sendo a escolha inicial. Berserk 14 permanece disponível como segunda opção na CPU. A troca do executável não inicia análise: peça uma nova avaliação para substituir resultados antigos.
