# Distribuição móvel offline: estado real da implementação

## O que já está implementado

- Em **Usuários → Usuários**, o Superadministrador vê cadastro, último login, última atividade e pode autorizar ou bloquear contas comuns. A lista de dispositivos mostra somente aparelhos efetivamente identificados pela sincronização, com plataforma, versão e último envio.
- `mobile_sync.py`: serviço transacional de histórico e ponto atual, isolado por conta e por instalação. Um reenvio após queda da conexão não duplica eventos. Eventos fora de ordem ou alterados são recusados sem apagar o estado já salvo.
- `mobile_api.py`: API de cadastro, login, renovação e sincronização. O cadastro móvel fica ativo imediatamente. Somente um bloqueio explícito do criador restringe o acesso. A identidade vem do token, nunca de um identificador de conta enviado pelo aparelho.
- `mobile/offline-store.js`: armazenamento local IndexedDB com fila persistente. A gravação do histórico e do ponto atual é atômica. Ao reconectar, a fila pode ser enviada automaticamente; os eventos só são removidos depois da confirmação do servidor. Uma falha de rede ou autenticação preserva o histórico local. A resposta do servidor não substitui um ponto local mais novo.

**Esses componentes são a base da versão móvel. O aplicativo Streamlit atual ainda não foi convertido em um aplicativo móvel offline. Não há APK ou IPA pronto nesta pasta.** O módulo JavaScript não é um instalador e ainda não está ligado a uma interface móvel com todas as funções do desktop.

## Regra de funcionamento acordada

1. Instalar uma versão assinada, com o código móvel, conteúdo básico e motor compatível embarcados.
2. Identificar a conta pela internet quando a sincronização estiver configurada; não é exigida aprovação prévia do criador.
3. Depois da ativação, estudar e jogar offline sem expiração periódica que interrompa o estudo.
4. Ao reencontrar a internet, autenticar a sincronização, enviar a fila na ordem original e confirmar o ponto atual. Um login expirado pede nova autenticação para sincronizar; não deve apagar o trabalho offline.
5. Um bloqueio seu passa a ser conhecido pelo telefone na próxima conexão. Não há como transmitir esse bloqueio ou consultar atividades novas enquanto o telefone permanece sem rede.

As informações exibidas ao criador são de cadastros, dispositivos identificados e última sincronização. Não é possível descobrir a identidade de alguém que apenas recebeu o arquivo e nunca ativou a conta. “Última sincronização” não significa que todo o período offline foi observado em tempo real.

## Como testar a base de sincronização neste computador

Instale as dependências opcionais com `.venv\Scripts\python.exe -m pip install -r requirements-mobile-server.txt`. Execute a API local com `.venv\Scripts\python.exe -m uvicorn mobile_api:app --host 127.0.0.1 --port 8502`.

Rotas:

- `POST /v1/register`: `{name, password}`; retorna `201` com acesso liberado; o criador pode bloquear a conta posteriormente.
- `POST /v1/login`: retorna uma sessão, identificador da conta e token de renovação.
- `POST /v1/refresh`: recebe `{device_token}` e renova o acesso ao serviço.
- `POST /v1/sync`: exige `Authorization: Bearer <sessão>` e recebe `{device, platform, version, events}`. Cada evento tem UUID, sequência crescente e `payload.checkpoint`. Máximo de 100 eventos por lote e 1 MB por evento.

Para integrar o cliente, abra `OfflineStore` com o identificador retornado no login. Após cada alteração, aguarde `save(checkpoint, activity)` antes de considerar o ponto salvo. Configure `syncTransport` com o endereço HTTPS e uma função que forneça uma sessão válida. O módulo não guarda senhas nem resolve a tela de ativação automaticamente.

O serviço local acima não é uma publicação na internet. Para uso real, a API e o painel precisam compartilhar um banco persistente em um servidor HTTPS. A antiga política de aprovação prévia foi removida: a configuração legada `COACH_REQUIRE_USER_APPROVAL` não bloqueia novos cadastros. Configure `COACH_MOBILE_ORIGINS` com as origens exatas dos aplicativos aprovados. Não inclua o banco do criador, senhas, certificados de assinatura ou chaves privadas dentro de um instalador.

## O que falta para entregar o aplicativo do telefone

É preciso construir e testar a interface móvel offline e integrar tabuleiro, motores móveis/WebAssembly, editor, cursos e biblioteca local a essa fila. Os executáveis Windows `stockfish.exe` e `berserk.exe` não podem ser usados diretamente em Android/iPhone. Importações do Chess.com, novos táticos de serviços externos e salas compartilhadas só podem atualizar dados quando houver conexão; não se tornam offline simplesmente ao criar o instalador.

- **Android:** preparar o projeto nativo, incluir os recursos e motor compatível, testar sem rede e gerar APK de distribuição assinado. Guardar a chave original: as próximas versões precisam manter a identidade de assinatura.
- **iPhone:** preparar o projeto iOS, compilar com Xcode em macOS e configurar assinatura/distribuição Apple, por exemplo TestFlight para os amigos. Não funciona enviar um APK ou um arquivo Windows ao iPhone.
- **Servidor:** definir hospedagem e endereço HTTPS para sua autorização, painel e sincronização. Até isso existir, um amigo fora desta máquina não consegue ativar nem sincronizar com o seu painel.

Você informou que ainda não tem servidor/endereço HTTPS nem conta/estrutura de compilação Apple. Esses pontos permanecem pendentes; nenhum servidor foi contratado, conta foi criada ou aplicativo foi publicado.

## Como atualizar quando a versão móvel estiver pronta

1. Aumentar a versão e o número de compilação do aplicativo. Fazer migrações de armazenamento sem limpar o banco local, a fila pendente ou a biblioteca do usuário.
2. Gerar e testar a atualização com a mesma identificação e assinatura da versão distribuída. Testar especialmente a atualização com eventos ainda não sincronizados.
3. Android: publicar nova versão na loja/faixa de testes ou enviar um APK assinado compatível. iPhone: publicar nova compilação via TestFlight/App Store, conforme o canal adotado.
4. O usuário precisa se conectar para baixar a nova versão. Não existe atualização remota enquanto estiver totalmente offline.
5. Atualizar também a API mantendo compatibilidade com os aplicativos anteriores. Fazer backup do banco central antes de mudanças de esquema. Uma atualização do servidor não substitui automaticamente o motor e o código que estão embarcados no celular.

Referências oficiais: [Android: assinatura e atualizações](https://developer.android.com/studio/publish/app-signing), [Apple: requisitos do Xcode](https://developer.apple.com/xcode/system-requirements), [Capacitor: requisitos Android/iOS](https://capacitorjs.com/docs/getting-started/environment-setup).
