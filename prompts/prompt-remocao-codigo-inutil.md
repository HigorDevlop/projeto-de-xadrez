# Prompt: identificar e remover código realmente inútil

## Contexto

O Coach Chess é um app de ensino para professores e alunos. Seu diferencial desejado é tornar o xadrez visualmente marcante, interativo, acolhedor e social, reduzindo a sensação de repetição e rigidez. Não confunda código visual ou interativo com código dispensável.

## Prompt pronto para usar

“Faça uma revisão cuidadosa do código do Coach Chess para identificar código morto ou redundante que possa ser removido sem prejudicar o ensino, a experiência visual/interativa, o professor, os alunos ou os dados existentes.

Antes de sugerir qualquer remoção:
1. mapeie o fluxo e as funcionalidades principais do professor e do aluno;
2. procure todas as referências a cada módulo, função, classe, rota, recurso e arquivo;
3. confira imports dinâmicos, registro de páginas, callbacks, testes, scripts, configuração, documentação e uso por outros módulos;
4. classifique cada candidato como: código morto comprovado, duplicação, funcionalidade secundária válida ou incerteza;
5. procure efeitos sobre dados salvos, migrações, instalações desktop e compatibilidade.

Não conclua que um arquivo é inútil apenas porque não aparece na navegação principal ou porque seu nome parece antigo. Não remova funções de interação, assets, personagens, animações ou estilos só por serem visuais: avalie se contribuem para a identidade e o engajamento pedagógico.

Apresente primeiro uma tabela com: candidato, evidência de não uso, dependências verificadas, risco, benefício e recomendação. Não altere nem apague nada até eu aprovar a lista.

Após aprovação, faça remoções pequenas e reversíveis; atualize referências e documentação relacionadas; execute os testes mais próximos e depois a validação apropriada do app. Relate exatamente o que foi removido, o que foi preservado e os resultados dos testes. Não faça limpeza em massa, não remova dados e não esconda erros.”

## Regra de segurança

“Não usado” deve ser comprovado por rastreamento de referências e comportamento, não deduzido pela aparência, tamanho, antiguidade ou localização do arquivo.
