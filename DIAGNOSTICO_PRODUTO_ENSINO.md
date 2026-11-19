# Coach Chess — diagnóstico e proposta de experiência

Data: 12/11/2026. Escopo: análise; nenhuma alteração de funcionalidade ou remoção.

**Direção recomendada: organizar o produto em torno da próxima atividade pedagógica, preservando a riqueza visual dentro da aula.** O problema principal observado é dispersão entre caminhos e contextos, não falta de funcionalidades nem excesso comprovado de módulos inúteis.

## 1. Estado atual e evidências

### Método e limites

- Inventário de 155 módulos Python na raiz e 126 arquivos `test_*.py` em `tests/`; esses números não incluem todo o código de componentes, mobile e distribuição.
- Leitura das rotas, controles de acesso, jornadas de sala, autoria/publicação, exercícios, progresso, persistência, integrações e testes.
- Cruzamento de imports por AST com busca textual, incluindo referências em strings e fixtures. Ausência de import estático não foi tratada como prova suficiente de ausência de uso.
- Inspeção visual de capturas existentes e de capturas produzidas nesta análise pelos testes de interface. A conexão de navegação interativa do assistente estava indisponível; a interface foi validada por testes existentes em navegador local e por inspeção das imagens resultantes, não por uma sessão manual completa com uma turma real.
- Nenhuma leitura de conteúdo de bancos particulares foi necessária. Portanto, não há conclusão sobre frequência real de uso, quantidade de dados legados ou comportamento de professores/alunos em produção.
- Não foram instaladas dependências, publicados serviços ou alterados módulos, configurações e bases de produção. Os testes geraram artefatos locais com dados isolados.

### O ciclo pedagógico já tem peças substanciais

| Etapa | Evidência existente | Avaliação |
|---|---|---|
| Professor prepara/atribui | `classroom_materials_ui.teacher_materials`, `classroom_trail_editor`, `classroom_trails`, `classroom_training_sessions`, `classroom_challenges.publish` | Há autoria, rascunhos, prévia, publicação, biblioteca e atribuição. Valor central a destacar. |
| Aluno participa | `classroom_ui.student_workspace`, `classroom_trail_student.select_step`, `classroom_materials_ui.student_materials`, `interactive_board` | Há trilha, liberação, tabuleiro jogável e materiais diversos. O caminho passa por nomes e contextos diferentes. |
| Recebe feedback | `classroom_materials_ui` apresenta “Correto!”/“Tente outra ideia”; notas por posição e `classroom_fischer_instructor`; `classroom_challenges_ui.student` distingue gabarito de qualidade do lance | Boa fundação, com oportunidade de tornar a explicação e o próximo passo mais consistentes. |
| Vê progresso/continua | `opening_course_state`, `opening_rounds`, `opening_error_review`, `tactics_progress`, `evolution_map`, sessões salvas | Há retomada e evidência real. Falta um ponto de entrada comum que selecione o que fazer agora. |
| Professor acompanha | `classroom_ui._student_dashboard`, `classroom_challenges.results`, resultados de materiais, sessões e presença | Há dados de acompanhamento, mas a visão principal ainda exige selecionar alunos e percorrer áreas. Propor uma síntese de turma acionável. |

### Dispersão comprovada na navegação

`workspace_access.py` oferece sete entradas ao professor: Partida, Desempenho, Análise, Estudo com livros, Tático, Preparo e Aberturas. O usuário comum recebe cinco, acrescentando Preparo quando está em contexto de sala e Vídeos quando aplicável. O administrador tem entradas adicionais.

Em `classroom_ui.py:239`, Modo Preparo abre sete abas: Alunos e acessos, Rotina individual, Treino e provas, Dashboard, Presença e advertências, Conversas e Aulas. Para o aluno, `classroom_ui.py:408` abre Minha trilha, Treino e provas, Conversas e Aulas. “Preparo” passa a significar tanto gestão do professor quanto participação do aluno.

Há sobreposição concreta: a aba Dashboard e a página Desempenho do professor chamam a mesma função `_student_dashboard` (`classroom_ui.py:353`, `:382`). Isso favorece integrar acessos; não exige apagar o serviço.

“Partida” também não descreve toda a página: `app.py:387` renderiza mapa de evolução, comparação de repertório e últimas partidas. Finais são acessados dentro de Aberturas (`opening_practice.py:143`). Essas escolhas aumentam o esforço para prever onde algo está.

### Identidade visual: preservar, hierarquizar e medir

As capturas atuais [desktop](tests/artifacts/redesign-routine-desktop.png) e [celular](tests/artifacts/redesign-routine-mobile.png), produzidas em 12/11, mostram fundo azul escuro, acentos ciano, cartões, boa separação dos blocos e uma marca reconhecível. No celular, a faixa de abas é parcialmente visível e exige navegação horizontal; passar no teste de largura não significa que a descoberta das funções esteja resolvida.

As capturas anteriores [catálogo de aberturas](tests/artifacts/coach-openings-desktop.png), [alunos](tests/artifacts/student-roster-desktop.png) e [prévia de conclusão](tests/artifacts/classroom-completion-choice.png) ajudam a compreender as superfícies, mas não substituem uma nova validação de todos esses estados.

Preservar tabuleiro como centro da atividade, cartões de conteúdo, trilhas visuais e celebrações. Evitar que cada atividade obrigue o aluno a atravessar uma apresentação decorativa. “Continuar aula” precisa levar diretamente ao estado correto.

Já existe suporte a movimento reduzido em `interactive_board.py`, `tactics_orbit.py`, `tactics_workspace.py` e no personagem de instrução. O tabuleiro também tem mensagens `aria-live` e tratamento de teclado. Isso é evidência de cuidado, não certificação de acessibilidade completa. Ainda é necessário verificar uso integral sem mouse, foco, zoom, contraste e equivalência entre arrastar, clicar e teclado.

O personagem em `classroom_fischer_instructor.py` lê comentários preparados pelo professor, usa voz local em português e preserva texto quando a voz não está disponível. É uma aplicação pedagógica concreta. Não deve ser apresentado como professor autônomo ou como garantia de avaliação por IA.

### Fricções pedagógicas específicas

1. **Objetivo menos visível que quantidade.** A rotina configura linhas, posições, táticos e minutos. Acrescentar objetivo compreensível — por exemplo, “identificar a peça indefesa” — ajuda a interpretar esses números.
2. **Gabarito único não equivale a avaliação completa.** O desafio de sala aceita uma tentativa e compara o lance ao esperado, sem motor (`classroom_challenges_ui.py`). A ressalva existente é correta. Propor discussão posterior, não chamar toda alternativa de lance ruim.
3. **Bloqueio exige recuperação.** Blocos táticos pedem pelo menos 90% para liberar progressão (`classroom_tactic_blocks.py:34`, `classroom_trail_student.py`). Preservar regras existentes nesta etapa; propor recuperação orientada e critérios configuráveis apenas em fase posterior.
4. **Advertência tem destaque permanente.** O cabeçalho do aluno mostra advertências; a terceira revoga acesso. Separar gestão de acesso do feedback de aprendizagem. Qualquer mudança na política de advertências requer decisão explícita, pois altera comportamento e autorização.
5. **Duas identidades de treino.** `training_token()` e `classroom_mode` alternam contexto pessoal/sala; aberturas usam `user:<id>` e `classroom:<id>`. Tornar o contexto visível. Não fundir progresso automaticamente para simplificar a aparência.

### Arquitetura e dependências

- Aplicativo desktop: Streamlit 1.63.0, Python, `python-chess`, componentes JavaScript/HTML/CSS, motores locais e recursos incluídos.
- Livros: `pypdf`, `pypdfium2`, Pillow e `chessvision`; leitura e reconhecimento têm finalidade própria e não são candidatos a descarte por estarem fora da sala.
- Orquestração: `app.py` concentra roteamento, estado, carregamento de partidas e análise; módulos de domínio separam boa parte das regras. Isso favorece migração de navegação por adaptadores, sem reescrita.
- Persistência: SQLite para contas/salas, biblioteca, atividades e resultados; JSON para planos de abertura/preparo; SQLite próprio para táticos. Caminhos configuráveis e isolamento de identidade precisam ser preservados.
- Conectividade: histórico Chess.com depende de rede; Táticos e Aberturas têm conteúdo offline. Conversas, vídeos e sinalização de aulas existem em `classroom_community`; clientes separados precisam acessar um serviço comum para compartilhar estado.
- API: FastAPI/Uvicorn são dependências separadas em `requirements-mobile-server.txt`. A base mobile contém IndexedDB e fila de eventos; isso não equivale a aplicativo mobile completo distribuído.
- Continuidade: `continuity_local`, `continuity_crypto` e testes são uma base local deliberada. `CONTINUIDADE_DISPOSITIVOS.md` declara que não há sincronização ponta a ponta pronta. `PAINEL_CENTRAL.md` distingue integração local e hospedagem pendente. Não foi comprovado serviço público ativo nesta análise.

### Validação executada

Rodada de domínio/integração: **108 aprovados, 3 falhas e 2 erros de preparação**, em 170,40 s. Arquivos: `test_workspace_access`, `test_classroom`, `test_classroom_materials`, `test_classroom_trails`, `test_classroom_challenges`, `test_training_sessions`, `test_opening_course`, `test_opening_error_review`, `test_evolution_map`, `test_analysis_training`, `test_offline_training`, `test_mobile_sync`, `test_continuity_local`.

- O teste de navegador offline procura um link `<a>` “Táticos”, mas a navegação atual usa `st.button` em `app.py:1388`. O timeout ocorre antes de validar o treino offline. É uma incompatibilidade do teste com o controle atual; não demonstra que o treino depende de internet.
- Duas falhas: `fastapi` ausente no Python usado na análise.
- Dois erros de preparação: `cryptography` ausente. Está declarada como dependência opcional. Não concluir que esses serviços estejam quebrados; a validação correspondente ficou incompleta.

Rodada de interface/prévia: **5 aprovados**, em 56,93 s, nos arquivos `test_classroom_redesign_ui.py` e `test_classroom_player_preview.py`. Inclui navegador real para abas do professor em 1440/390 px e AppTest para prévias. **Total: 113 aprovados; não foi executada a suíte completa.**

## 2. Jornadas propostas

### Professor

1. Entra em **Hoje**: próxima aula, atividades atribuídas e alunos que precisam de ajuda.
2. Escolhe **Preparar aula**: objetivo → turma/aluno → materiais → sequência. Reutiliza trilhas e biblioteca existentes.
3. Usa **Experimentar como aluno**, preservando a separação já existente entre simulação e resultado real.
4. Confere o resumo: destinatários, objetivo, etapas, critério e disponibilidade; então publica. Rascunho e publicação continuam distintos.
5. Conduz a aula por etapas: explicar → perguntar → jogar → discutir → aplicar em outra posição.
6. Acompanha participação por atividade e abre evidências de dificuldade, não somente tempo de tela.
7. Encerra com síntese e atribui um próximo passo pequeno a cada necessidade identificada.

### Aluno

1. Entra em **Hoje** e vê “Continuar aula do professor”, com objetivo, estado e contexto da sala.
2. Abre diretamente a etapa atual; texto/voz introduzem uma pergunta curta e o tabuleiro permite experimentar.
3. Recebe confirmação do que fez, explicação relevante e possibilidade de tentar novamente conforme o tipo de atividade.
4. Vê o que aprendeu e o que ainda será revisado. “Concluído com ajuda” e “resolvido sem ajuda” não precisam ser confundidos.
5. Escolhe continuar, revisar ou encerrar. Ao voltar, retoma do ponto salvo e entende por que a revisão foi sugerida.

O aluno sem sala mantém treino autônomo e entrada por chave. A ausência de professor não deve produzir uma tela vazia ou impedir treino offline.

## 3. Navegação proposta

**Quatro entradas principais por perfil**, com nomes estáveis e conteúdo adequado ao papel:

| Entrada | Professor | Aluno |
|---|---|---|
| **Hoje** | Próxima aula, preparar/continuar, pendências da turma | Próxima atividade, continuar, revisões e conquistas recentes |
| **Sala** | Aulas e desafios, alunos, acompanhamento, conversas | Minha trilha, desafios, aula ao vivo, conversas e devolutivas |
| **Treinar** | Explorar conteúdo e experimentar atividades | Táticos, aberturas, finais e treino livre |
| **Revisar** | Analisar partidas e transformar posições em atividades | Partidas, erros, caderno e exercícios de revisão |

Biblioteca de livros/vídeos/modelos: acesso contextual em Preparar, Treinar e Revisar, com atalho secundário persistente. Conta, aparência e acesso ficam no menu de perfil. Administração global continua exclusiva do administrador e fora da jornada pedagógica.

Progresso resumido fica em Hoje, com detalhes por evidência; progresso da turma fica em Sala → Acompanhamento. Não substituir medidas diferentes por uma pontuação única.

Durante a atividade, mostrar objetivo, etapa, ajuda e saída/retomada; reduzir o peso da navegação global. Preservar URLs antigas por redirecionamento e autorização. Agrupar menus não é fundir módulos ou dados.

## 4. Destino das funcionalidades

| Funcionalidade | Decisão proposta | Motivo e cuidado |
|---|---|---|
| Tabuleiro interativo, promoção e feedback | **Manter e destacar** | Interface central compartilhada; preservar eventos, teclado e revisões de estado. |
| Trilhas do professor, notas por posição e prévia | **Manter e destacar** | Condução pedagógica e validação antes de publicar. |
| Rascunhos, publicação, agenda e retomada | **Manter e destacar** | Dão controle ao professor e continuidade ao aluno. |
| Desafios da sala | **Manter e destacar** | Participação real; explicitar tentativa única/gabarito e oferecer discussão posterior. |
| Táticos, aberturas, finais | **Integrar em Treinar** | Domínios válidos; finais precisam ser encontráveis fora do rótulo Aberturas. |
| Rotina individual e Treino e provas | **Integrar no fluxo de aula** | Objetivos/metas e materiais são complementares, não duplicatas equivalentes. |
| Dashboard da sala e Desempenho do professor | **Integrar em Acompanhamento** | Mesmo renderizador atual; manter filtros e acesso a evidências. |
| Partidas, análise, caderno e erros | **Integrar em Revisar** | Fechar ciclo “joguei → entendi → pratiquei”; preservar arquivos e análises salvas. |
| Mapa de evolução, XP e conquistas | **Integrar sem misturar métricas** | Mostrar progresso significativo; XP não é rating, tempo não é domínio. |
| Personagem e leitura de comentários | **Manter contextual** | Ajuda a explicar posições; áudio opcional e texto sempre disponível. |
| Máquina/carrossel tático e celebrações | **Manter com acesso direto à atividade** | Identidade visual valiosa; medir atraso, distração e benefício antes de mudar. |
| Livros, vídeos e modelos reutilizáveis | **Deixar secundários e acessíveis** | Recursos de preparo/consulta; ligar ao objetivo da aula. |
| Motores, profundidade, PGN/FEN e personalização | **Deixar secundários** | Controles avançados contextuais; não exigir configuração técnica para começar. |
| Presença, advertências, gestão de chaves | **Deixar em gestão da sala** | Necessidade administrativa válida; evitar protagonismo na experiência de aprendizagem. |
| Painel central, dispositivos e infraestrutura | **Deixar na administração** | Não é entrada principal de aula, treino ou revisão. |
| Código/recursos sem uso comprovado | **Nenhuma remoção autorizada** | Aplicar investigação descrita abaixo antes de propor exclusão concreta. |

## 5. Candidatos a código morto e limites da prova

| Candidato | Evidência de chamadas, rotas e testes | Classificação / impacto |
|---|---|---|
| Segundo ramo `elif name == 'Preparo'` de `app.py:1352` | `app.py:1290` já trata o mesmo nome e retorna antes de chegar a esse ramo | **Trecho inalcançável comprovado no fluxo atual.** Sua retirada futura não autoriza excluir `preparation_workspace`. |
| `preparation_workspace.render_preparation` | Chamada da rota acima inalcançável, porém usada por `tests/preparation_fixture.py`, `tests/repertoire_fixture.py` e testes AppTest; `pause_preparation` é importada por `app.py:1436` | **Módulo com consumidores válidos.** Investigar destino do preparo autônomo e planos persistidos. |
| `dashboard_hud.py` | Nenhum import/chamada externa do módulo encontrado no conjunto inspecionado; `performance_dashboard.py:208` importa `console` de `dashboard_purple`, não deste arquivo | **Candidato forte a renderizador substituído**, não autorização para excluir. A cópia de distribuição ainda o inclui. Conferir consumidores externos/dinâmicos antes. |
| `opening_desktop_ui.py` | Sem import do módulo nem chamadas de `lesson_panel`/`move_history` encontrados. O teste com nome semelhante exercita catálogo via `course_server` e não prova consumo deste módulo | **Candidato a apresentação desconectada.** Confirmar cobertura por rota e contrato antes de retirar. |
| `classroom_courses_ui.py` | Sem chamada encontrada para `courses_workspace`; usa serviço `classroom_courses` | **UI desconectada com valor potencial.** O serviço tem tabela persistente e testes em `test_admin_courses_notebook.py`; não apagar serviço ou dados. Avaliar reconectar à biblioteca de modelos. |
| `cat_mascot`, `tactics_forge`, `study_entrance`, `tactic_demo`, `opening_tutorial` | Sem rota ativa encontrada para os respectivos renderizadores, mas `test_browser_components.py`/`test_opening_tutorial_ui.py` montam componentes por nome de arquivo | **Componentes preservados/testados, possivelmente fora do fluxo atual.** Não chamar de sem consumidores. Decidir reutilização pelo valor visual e pedagógico. |
| `personal_openings_ui.py` | Consumido por código de teste embutido em string em `test_lesson_and_repertoire_redesign.py:83`, que a busca só de AST não reconhece como import do módulo principal | **Uso em teste confirmado.** Investigar acesso ao repertório pessoal e migração de planos antes de qualquer decisão. |
| `continuity_local` / `continuity_crypto` | Dependência entre módulos, testes específicos e documentação de etapa local | **Fundação planejada, não código morto comprovado.** Fora do fluxo principal até existir integração ponta a ponta validada. |

`scripts/build_windows_installer.py:34` copia todos os `.py` da raiz. `files.json` de manutenção também inclui candidatos. Isso é consumo de empacotamento, não prova de execução, mas faz parte do impacto de uma futura remoção.

Antes de qualquer exclusão: identificar símbolos e imports dinâmicos/strings, rotas normais e diretas, fixtures, scripts, empacotamento, assets compartilhados, tabelas/JSON e compatibilidade com instalações anteriores; apresentar lista exata, substituto, impacto e reversão; pedir aprovação. Não apagar testes para transformar ausência de cobertura em aparente segurança.

## 6. Plano incremental, do menor risco ao maior

| Etapa | Mudança proposta | Validação / critério | Reversão |
|---|---|---|---|
| 0 — Base verificável | Atualizar seletores antigos de testes; documentar ambientes core/API/continuidade; guardar capturas de referência | Reexecutar offline com bloqueio real de rede; testes de papel, sala, publicação e retomada | Alterações restritas aos testes/documentação, em commit separado |
| 1 — Clareza sem migração | Padronizar nomes, hierarquia e ações; indicar contexto pessoal/sala; acrescentar objetivo e próximo passo com dados existentes | Professor encontra/publica aula e aluno retoma sem orientação; desktop, celular, teclado e zoom | Chave de configuração para navegação anterior; nenhum dado movido |
| 2 — Quatro entradas | Agrupar destinos existentes em Hoje/Sala/Treinar/Revisar; manter URLs antigas | Testar todas as rotas por perfil, links diretos, voltar, troca de conta e estado de sessão | Mapa de rotas anterior preservado; mesmos serviços e IDs |
| 3 — Ciclo completo de aula | Preparar → experimentar → publicar → participar → feedback → próximo passo → acompanhar | Um teste integrado com professor e dois alunos; rascunho invisível, resultados isolados, reenvio sem duplicação, retomada após fechar | Interface anterior disponível; adições de dados versionadas, sem exclusão de registros |
| 4 — Acompanhamento pedagógico | Síntese da turma, dificuldades por atividade, recuperação orientada e revisão espaçada | Cada alerta permite abrir evidência; distinguir ausência de dados, conexão e dificuldade; testar limites/contrapontos | Desativar recomendações e conservar eventos; política antiga permanece recuperável |
| 5 — Conexão entre dispositivos | Completar contrato de conta/sala, fila offline, ACK, conflitos e serviço comum; publicar apenas mediante escopo específico | Dois aparelhos, reconexão, revogação, duplicação, relógios diferentes, backup/restauração e teste de carga | Desligar transporte, manter operação local e não perder fila |
| 6 — Limpeza aprovada | Remover apenas arquivos/trechos da lista aprovada após comprovar ausência de consumidores | Importação, rotas, empacotamento, testes de regressão e acesso a dados legados | Commit pequeno, inventário e retorno à versão anterior; sem apagar bases |

Métricas propostas para um piloto, ainda sem valores medidos: tempo até a primeira atividade; sucesso ao retomar; conclusão da sequência atribuída; acerto independente em revisão posterior; quantidade de alunos cuja dificuldade o professor consegue identificar e atender. Retorno ao app deve ser interpretado junto com aprendizagem e contexto, não como objetivo isolado de tempo de tela.

## 7. Interações para participação e retorno

| Ideia | Benefício pretendido | Limite e validação |
|---|---|---|
| **Pergunta → lance → explicação** | O aluno toma uma decisão antes de receber a resposta; reaproveita tabuleiro e notas do professor | Instrução curta; resposta por texto/voz; verificar compreensão numa posição nova |
| **Duas tentativas com papéis diferentes** | Primeira revela pensamento; segunda aplica uma pista e consolida | Para treino formativo, sem alterar silenciosamente provas/desafios de tentativa única |
| **Desafio coletivo sem placar de velocidade** | Turma compara ideias e participa da discussão | Professor vê dificuldades; agregação anonimizada para turma; não premiar apenas rapidez |
| **Um erro virou uma missão** | Uma posição da revisão reaparece numa atividade curta | Reutilizar `analysis_training`; explicar a origem e respeitar revisões/identidade existentes |
| **Personagem como guia de raciocínio** | Lê a orientação e aponta o que observar | Texto equivalente, parar áudio, reduzir movimento; nenhuma fala decorativa sobrepondo a tarefa |
| **Conquista por evidência** | Reconhece retenção, explicação e aplicação, além de volume | Critérios transparentes; separar ajuda, primeira tentativa e revisão; não inflar rating |
| **Encerramento com continuidade** | “Hoje você praticou X; depois retomaremos Y” dá sentido ao retorno | Próxima ação clara, pausa legítima e possibilidade de encerrar sem punição |
| **Professor devolve uma orientação curta** | Faz o aluno perceber acompanhamento real | Vincular ao exercício; não inventar mensagem automática como se fosse autoria do professor |

Essas interações são hipóteses de produto a validar com professores e alunos. Nenhuma afirmação de aumento comprovado de retenção ou aprendizagem decorre apenas da inspeção técnica.

## Decisão recomendada para a próxima etapa

Começar pela base de testes e por um protótipo de navegação usando os renderizadores existentes. Dar destaque ao fluxo de aula, à retomada e à visão de turma. Manter a identidade escura/ciano, os tabuleiros e a linguagem visual; concentrar animação nos momentos em que comunica ação, resultado ou progresso. Nenhuma remoção é necessária para iniciar essa simplificação.
