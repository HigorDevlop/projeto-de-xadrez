# Berserk 14

Motor UCI adicional para a análise do Coach Chess, executado localmente na CPU.
Binário oficial Windows x86-64, com rede NNUE incorporada. Requer POPCNT; a instalação foi testada neste computador.

- Projeto: https://github.com/jhonnold/berserk
- Versão e binários: https://github.com/jhonnold/berserk/releases/tag/14
- Executável original: `berserk-14-x86-64.exe`, salvo como `berserk.exe`.
- SHA-256 do executável: `84572e3f3c8fb345aebdc63a7658508edce16a6b5d4d144e5bd3d1bfdb909dbe`.
- Código-fonte correspondente, com scripts de compilação: `source-14.zip` (tag `14`).
- SHA-256 do código-fonte: `842d20bb0514e7fb5c33f370dc2c9e1d413a3800ab6fb5c69c392ec94870a627`.
- Rede correspondente: `berserk-9b84c340af7e.nn`; SHA-256 `9b84c340af7e45f6e07f0046235ccb327f4ae0840c8ee2c4b97b99121e5c5084`.
- Licença GPL em `COPYING.txt`; licença do componente Pyrrhic em `Pyrrhic-LICENSE.txt`, também preservadas no arquivo de fontes.

Para recompilar: extraia `source-14.zip`, copie a rede desta pasta para `berserk-14/src/` e siga as instruções de compilação do projeto (`make pgo CC=clang ARCH=native`). O binário distribuído foi obtido da publicação oficial, não recompilado pelo Coach Chess.

Para outra plataforma, instale uma compilação compatível e defina `BERSERK_PATH`; também são reconhecidos `engines/berserk/berserk`, `engines/berserk` (arquivo) ou `berserk` no PATH. Não há downloads durante a análise.
