# Login obrigatório e controle do criador

## 1. Configurar seu Superadministrador

No computador que hospeda o aplicativo, dê dois cliques em **Configurar Superadministrador.bat**. Escolha seu usuário e uma senha com pelo menos 8 caracteres e confirme a senha.

Essa configuração só funciona uma vez. Não existe senha padrão nem cadastro de Superadministrador pela tela pública. O aplicativo não exibe a senha escolhida. Guarde-a para os próximos acessos.

Depois abra **Coach Chess Desktop.bat**, selecione **Usuário** na tela de login e entre com as credenciais que você acabou de definir.

## 2. Autorizar professores

1. Entre por **Usuário** com suas credenciais de criador para abrir o painel de Superadministrador.
2. Clique em **Criar chave**, no topo do painel. Não é necessário informar um nome. Você pode gerar novas chaves a qualquer momento.
3. Copie a chave exibida e entregue somente ao Professor escolhido. Cada chave ativa uma única conta. Depois de sair da sessão, o texto da chave não pode ser recuperado do banco; se ainda não tiver sido utilizada, revogue-a e emita outra.
4. O Professor abre o aplicativo e seleciona **Professor**. O campo **Chave especial do Professor (obrigatória)** aparece sempre; não existe ativação opcional.
5. No primeiro acesso, ele escolhe um usuário e uma senha com pelo menos 10 caracteres, informa a chave e clica em **Entrar**.
6. A conta é criada com sua sala de quatro alunos. Em toda entrada manual seguinte, o Professor informa novamente **usuário, senha e a mesma chave**. A chave fica vinculada àquela conta e não pode cadastrar outro Professor.

Somente o Superadministrador emite ou revoga essas chaves. Revogar uma chave já vinculada encerra as sessões e os acessos automáticos do Professor e de sua sala. Um Professor não pode emitir uma chave de Professor, visualizar salas de outros professores ou criar uma conta de administrador.

## 3. Contas antigas e supervisão

As contas de Professor cadastradas pelo fluxo público anterior ficam **sem autorização** na atualização. Seus dados e alunos são preservados, mas o acesso à sala é bloqueado até sua aprovação.

Em **Usuários → Professores**, você pode autorizar essas contas ou suspender qualquer Professor. Para uma conta antiga sem chave, clique em **Nova chave** e entregue a nova chave ao titular. Essa ação também serve para substituir uma chave perdida; a anterior é revogada. Suspender revoga as sessões e os acessos automáticos do Professor e de seus alunos. Reautorizar exige um novo login; os acessos antigos não são reativados.

Em **Modo Preparo**, seu Superadministrador seleciona qualquer aluno de qualquer sala para editar rotinas, visualizar precisão, presença, partidas e advertências. A lista de alunos identifica o Professor de cada sala. Seu menu também oferece as demais áreas do aplicativo.

## 4. Usuário comum e ingresso na sala

A tela inicial oferece somente **Usuário** e **Professor**. Em **Usuário**, marque **Criar conta de usuário**, escolha usuário e senha (mínimo 10 caracteres) e clique em **Entrar**. Nas próximas entradas, use os mesmos dados sem marcar o cadastro. O criador também entra por **Usuário**, com sua conta já configurada; suas permissões são identificadas internamente.

Depois de entrar, abra **Juntar-se à sala** na lateral, informe o **Código da sala** entregue pelo Professor e confirme. O aplicativo abre a sala e a rotina daquele Professor. Cada código ocupa uma das quatro vagas e só pode ser vinculado a uma conta; cada conta participa de uma sala.

Use **Usar abas comuns** para voltar ao catálogo completo de aberturas e à análise. Use **Abrir sala do Professor** para retornar à rotina. Não é necessário sair da conta ou digitar o código novamente. Os progressos pessoais e da sala ficam separados, e somente o treino dentro da sala entra nas metas do Professor. A foto permanece vinculada à conta pessoal.

Na terceira advertência, o acesso à sala é revogado. A conta pessoal e suas abas comuns continuam disponíveis. A suspensão do Professor também bloqueia apenas a sala para os usuários comuns.

## 5. Acesso automático

Na primeira entrada, marque **Entrar automaticamente neste navegador**. Um identificador aleatório de dispositivo é salvo nesse navegador; sua senha não é salva. O identificador expira em até 30 dias e é validado no servidor em cada nova entrada.

Feche e reabra a janela ou recarregue a página: a conta deve entrar automaticamente. Use o mesmo navegador, perfil e endereço do servidor. O inicializador desktop reutiliza o servidor da instalação para manter esse endereço. Outro navegador, uma janela anônima ou outra porta exige um login separado.

Em **Minha sessão**, use **Sair e esquecer este navegador** para encerrar a sessão e remover o acesso automático atual. **Revogar meus acessos automáticos** impede novas entradas automáticas em todos os seus navegadores, mantendo a sessão atual aberta. Banimentos e suspensões continuam valendo mesmo quando o acesso automático está marcado.

## 6. Teste do controle de acesso

1. Abra uma janela anônima: somente a tela de login deve aparecer.
2. Selecione Professor sem ativar uma chave válida: não deve ser possível criar conta nem acessar o Modo Preparo.
3. Entre como Superadministrador, emita uma chave e ative um Professor com ela.
4. Tente utilizar a mesma chave para outra conta: a segunda ativação deve ser recusada.
5. Entre como Usuário, junte-se à sala com o código e confirme a rotina. Alterne para **Usar abas comuns**, abra Análise e confira o catálogo completo; retorne em **Abrir sala do Professor**. Dentro da sala, Modo Preparo mostra somente a rotina do próprio aluno; editar rotinas continua exclusivo dos professores e do criador.
6. Teste a entrada automática e depois **Sair e esquecer este navegador**.
7. Suspenda um Professor pela sua conta de Superadministrador e confirme que ele não consegue entrar, inclusive com acesso automático. Os usuários perdem acesso à sala, mantendo suas contas pessoais.

Professor, alunos e criador precisam usar o mesmo servidor/banco de dados. Para computadores na mesma rede, use **Iniciar Sala Coach Chess.bat**, conforme o [tutorial das salas](TUTORIAL_PROFESSOR.md).

Chaves de Professor não utilizadas expiram **15 minutos após a criação**, inclusive se o aplicativo estiver fechado. O registro continua na aba **Chaves**, com status **Expirada**, mas a chave deixa de ativar contas. Se for usada antes do prazo, fica vinculada ao Professor e continua válida. **Excluir** remove a chave da lista e revoga seu uso; se estiver em uso, também encerra os acessos daquela sala. O histórico interno é preservado.
