# Alternativas com iniciativa

Em **Aberturas → Seu repertório · histórico do Chess.com**, use **Preparar linhas do meu histórico** para recalcular as recomendações. O material já salvo antes desta mudança não é silenciosamente reavaliado.

O aplicativo conta quais lances o usuário escolheu em cada posição dos primeiros dez lances completos das partidas importadas. A comparação parte da mesma posição e do mesmo lado a jogar. O lance mais frequente do usuário também é avaliado, mesmo quando não aparece entre as quatro primeiras opções do motor. As frequências não são confundidas com qualidade de jogo.

O Stockfish local pesquisa até quatro continuações com MultiPV. Entre as opções a até **25 centipeões da melhor avaliação pesquisada**, o aplicativo prioriza desenvolvimento, controle central, lances forçantes e segurança do próprio rei. Os critérios de estilo são heurísticas: não provam iniciativa duradoura nem substituem a avaliação do motor. Eles observam a resposta prevista do adversário e não premiam simplesmente uma ameaça sem resposta.

São oferecidas até três escolhas distintas por posição: **Iniciativa com segurança**, **Opção sólida** e, quando ainda não estiver representada, **Principal do motor**. A primeira opção busca ser diferente do lance habitual, quando houver uma alternativa dentro desse limite. Uma única continuação verificada, um mate forçado ou avaliações sem comparação adequada não recebem alternativas inventadas. Nenhuma promessa de ataque ou vantagem é feita para toda posição.

Cada opção mostra o lance habitual, a frequência, a sugestão, os motivos observáveis e as avaliações estimadas para o lado a jogar. O usuário escolhe explicitamente qual estudar. Concluir uma recomendação pessoal não inicia outra abertura automaticamente. Os aprofundamentos dos cursos também usam a preferência por iniciativa quando o motor precisa escolher uma resposta nova do usuário, mantendo a abertura e as respostas já fixadas no repertório.

A importação de novas partidas precisa de internet. Preparar, comparar e estudar o histórico já importado usa o motor e os arquivos locais. Conquistas já obtidas são preservadas ao recalcular o repertório pessoal.

Referência da integração MultiPV: https://python-chess.readthedocs.io/en/latest/engine.html#analysing-and-evaluating-a-position . A margem de 25 centipeões e os critérios de estilo são regras do Coach Chess, não uma recomendação oficial dessa biblioteca.

Nenhuma versão ou instalador novo foi gerado. Para aplicar estas correções à instalação existente, execute **Aplicar correções no Coach Chess.cmd** novamente, confirme a manutenção do Windows e reabra o aplicativo.
