# Enviar o Coach Chess para um amigo

Envie somente `dist/CoachChess-Setup-0.2.2-Windows-x64.exe`. O amigo abre esse arquivo, conclui a instalação e usa o atalho **Coach Chess**. Não precisa instalar Python, executar comandos ou receber a pasta do projeto. O pacote é para Windows 10/11 de 64 bits.

Cada abertura pelo atalho pede tela cheia, sem as abas e a barra de endereços do navegador. O aplicativo usa um perfil próprio para que janelas pessoais já abertas não interfiram nessa configuração. Use **F11** para alternar a tela cheia durante o uso.

O instalador inclui Python, bibliotecas, imagens, cursos locais e os motores Stockfish 19 e Berserk 14, com suas licenças e fontes. Inclui também o instalador do runtime Microsoft Visual C++, usado se necessário. A janela usa Edge ou Chrome instalado no Windows. O pacote ainda não tem assinatura digital do editor.

A conta comum pode ser criada dentro do aplicativo, sem aprovação prévia. Tabuleiro, análise local e livros já adicionados funcionam sem internet. Consultas novas ao Chess.com e outros serviços externos precisam de conexão.

## Dados e atualizações

**Novas versões e instaladores serão gerados somente quando você solicitar.** As correções do código não publicam atualizações automaticamente. A manutenção local autorizada pode ser aplicada por **Aplicar correções no Coach Chess.cmd**, confirmando a solicitação administrativa do Windows; ela faz backup e preserva o número da versão publicada. O novo banco tático offline está no código atual e nessa manutenção, mas não no instalador antigo citado acima. Veja [OFFLINE_TREINOS.md](OFFLINE_TREINOS.md).

Contas locais, biblioteca e progresso ficam em `%LOCALAPPDATA%\CoachChess`, separados dos arquivos instalados. O instalador não inclui seus bancos pessoais, livros ou senhas. Cada pessoa começa com dados próprios. Faça backup dessa pasta antes de atualizar. Uma partida ainda não exportada pode existir apenas na sessão: salve o PGN antes de fechar.

Para atualizar seus amigos, gere uma versão nova e envie o novo instalador. O usuário fecha o aplicativo e executa o instalador sobre a mesma pasta. Mantenha o `AppId` em `packaging/coach-chess.iss`: ele identifica as versões como o mesmo aplicativo. Não há atualização automática pela internet nesta versão.

No computador de desenvolvimento, com as ferramentas em `.build-tools` e o runtime já preparado:

```powershell
.venv\Scripts\python.exe scripts\build_windows_installer.py --version 0.2.3 --reuse-runtime
```

Use `--reuse-runtime` somente quando as dependências não mudaram. O processo verifica o runtime, monta uma cópia sem dados pessoais, compila o instalador e gera seu arquivo `.sha256`. As ferramentas de compilação não precisam ser enviadas aos amigos. O log fica em `.build-tools/installer-build.log`.

## Seu painel de usuários

O Superadministrador administra as contas do banco ao qual seu aplicativo está conectado. Para configurar o criador na instalação Windows, abra PowerShell na pasta instalada e execute:

```powershell
.\runtime\python.exe -c "from installed_entry import configure_data; configure_data(); import configure_owner; configure_owner.main()"
```

O comando pede usuário e senha; não coloque sua senha no comando ou no instalador. Entre normalmente no aplicativo para acessar **Usuários**. O acesso comum fica livre até um bloqueio explícito.

**A versão 0.2.2 inclui a integração de presença e o painel privado de instalações.** Em **Usuários**, o criador pode consultar quem está online, a versão e a última conexão, além de bloquear ou desbloquear dispositivos. Um sinal recebido nos últimos 90 segundos significa online. Cada aparelho informa a conta local em uso; a lista não identifica pessoas que nunca se conectaram ao servidor.

Para ativar isso entre computadores diferentes, é necessário publicar o serviço em HTTPS e incluir seu endereço no instalador com `--control-url`, ou configurar o endereço nas instalações existentes. A hospedagem ainda não foi configurada. Nenhuma conta, senha ou banco do criador é incluído no pacote distribuído. Veja o passo a passo em [HOSPEDAR_HTTPS.md](HOSPEDAR_HTTPS.md) e a referência em [PAINEL_CENTRAL.md](PAINEL_CENTRAL.md).

O cadastro de uma instalação fica livre por padrão. Somente o seu bloqueio explícito muda esse acesso. Sem internet, a instalação mantém a última decisão conhecida, sem prazo de expiração automático. Um novo bloqueio só chega quando o aparelho se reconecta; a falta de conexão não cria bloqueios. Essa integração envia presença, versão e nome da conta local; a sincronização completa do histórico entre computadores permanece um trabalho separado.

## Celulares

Este `.exe` não instala em Android nem iPhone. A base de sincronização está descrita em [MOBILE_OFFLINE.md](MOBILE_OFFLINE.md); a interface móvel offline, os motores compatíveis e os instaladores APK/iOS ainda precisam ser concluídos. Não há APK ou IPA pronto nesta entrega.
