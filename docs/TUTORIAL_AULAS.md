# Conversas, vídeos e aulas ao vivo

## Professor

1. Entre como **Professor** e abra **Modo Preparo**.
2. Em **Conversas**, escolha **Grupo da sala** para conversar com todos. Para uma conversa privada, selecione o aluno no topo e escolha **Conversa com aluno**. O aluno recebe essas mensagens em **Meu Professor**. As mensagens ficam salvas no servidor e atualizam automaticamente.
3. Em **Aulas → Publicar vídeo**, dê um título e envie um MP4, WebM ou MOV de até 100 MB, ou informe um link HTTPS de vídeo compatível com o player (por exemplo, YouTube ou um MP4). Só o Professor publica e exclui vídeos.
4. Para uma aula ao vivo, clique em **Iniciar aula ao vivo**, depois em **Entrar na aula ao vivo** e **Transmitir câmera**. Autorize câmera e microfone no navegador.
5. Use os controles para ligar/desligar câmera e microfone. Os alunos assistem e podem interagir em **Conversa durante a aula**, sem sair da transmissão. A aula não é gravada automaticamente.
6. **Encerrar aula para todos** encerra a transmissão. **Sair da transmissão** desconecta apenas aquele participante. Trocar para outra aba do Modo Preparo também desconecta a transmissão; para conversar sem interromper o vídeo, use o chat dentro da própria aula.

## Aluno

Abra sua sala e acesse **Modo Preparo → Conversas** ou **Aulas**. Para assistir a uma aula iniciada pelo Professor, clique em **Entrar na aula ao vivo** e depois em **Ativar áudio**. O aluno não precisa liberar câmera nem microfone para assistir. Vídeos publicados ficam disponíveis em Aulas; abra o título e clique em **Assistir**.

## Celular e acesso pela rede

O layout se adapta ao tamanho da tela: cards, navegação, conversas e player se reorganizam. Professor e alunos precisam acessar o mesmo servidor, como nos demais recursos da sala.

O inicializador desktop usa localhost, onde câmera e microfone são permitidos. Em outros computadores e celulares, disponibilize o servidor por **HTTPS**, com certificado aceito pelos dispositivos. Um endereço de rede servido apenas em HTTP não libera a câmera do Professor. O navegador sempre solicita a permissão de mídia ao iniciar a transmissão.

O vídeo usa WebRTC entre os navegadores. Na rede local, pode estabelecer conexão direta. Pela internet ou em redes que bloqueiam conexões diretas, configure um servidor TURN por **COACH_WEBRTC_ICE_SERVERS** (JSON de servidores ICE, com urls, username e credential fornecidos pelo seu serviço). O padrão inclui STUN; ele não substitui TURN em redes restritas. Não há conta de videoconferência externa embutida nem hospedagem pública automática.

Exemplo de configuração do servidor, com dados do seu provedor, antes de iniciar o app:

```powershell
$env:COACH_WEBRTC_ICE_SERVERS='[{"urls":"stun:stun.l.google.com:19302"},{"urls":"turn:seu-servidor:3478","username":"seu-usuario","credential":"sua-credencial"}]'
```

A sinalização passa pelo servidor autenticado da sala. Professores de outras salas e alunos sem acesso não podem abrir conversas, vídeos ou transmissões daquela turma.

## Chama e sequência

A sequência conta dias consecutivos de **acesso autenticado**, uma vez por dia, no horário de São Paulo. Entrar várias vezes no mesmo dia não aumenta o número; faltar um dia reinicia a sequência. A chama muda de cor e formato ao atingir **10, 20, 30, 40 e 50 dias**. Depois de 50, mantém a fase máxima e continua mostrando a contagem real.

## Assistir aos vídeos gravados a qualquer momento

Depois de vincular a conta à sala do Professor, o aluno encontra **Vídeos gravados** no menu lateral, inclusive quando estiver usando as abas comuns. As aulas publicadas continuam disponíveis após o treino ou o encerramento da aula ao vivo, sem precisar pedir outro código, registrar presença ou iniciar cronômetro. Abra o título e clique em **Assistir**. Os vídeos também continuam em **Modo Preparo → Aulas**. O acesso continua restrito aos membros autorizados da sala; o Professor pode excluir um vídeo quando desejar.
