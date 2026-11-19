# Painel privado de instalações

A integração Windows e a API estão implementadas e foram testadas com dois serviços locais separados. A hospedagem pública ainda não foi contratada ou configurada. Sem um servidor HTTPS disponível, o painel informa que a conexão central está pendente e não apresenta instalações fictícias como online.

## O que o criador vê

Entre no aplicativo como seu Superadministrador local e abra **Usuários**. Configure o endereço em **Conexão com o servidor central** e entre com a conta do criador cadastrada nesse servidor. O painel consulta instalações, nome da conta local em uso, sistema, versão, acesso e última conexão. A lista é exclusiva do criador; uma credencial de instalação não dá acesso administrativo.

Os dispositivos enviam um sinal em segundo plano, aproximadamente a cada 15 segundos enquanto o app está aberto. O painel considera online um sinal recebido há até 90 segundos e atualiza sua consulta a cada 15 segundos. Fechar o aplicativo, perder a rede ou suspender o computador faz a indicação expirar. Essa lista representa instalações que se identificaram, e não pessoas que apenas receberam o arquivo sem nunca abri-lo com conexão.

Cada instalação é livre até um bloqueio explícito. **Bloquear dispositivo** controla aquela instalação; não revoga automaticamente outras instalações com o mesmo nome de conta. A identidade técnica é um identificador aleatório e uma credencial própria do aparelho. O nome informado é o nome da conta local em uso, sem verificação de identidade civil.

Uma falha de rede não bloqueia o uso. Um bloqueio recebido fica guardado localmente até o servidor confirmar seu desbloqueio. Os livros e demais dados locais não são apagados. O criador local mantém acesso ao painel para administrar os dispositivos.

## Publicar o serviço

É preciso um servidor Linux com Docker Compose, um domínio apontando para ele e portas 80/443 disponíveis. Os arquivos de implantação estão em `deploy/`. A configuração usa banco SQLite em volume persistente e Caddy na frente da API. A API não expõe publicamente uma função para criar o Superadministrador.

No servidor, a partir da raiz do projeto:

```sh
export COACH_DOMAIN=controle.seu-dominio.example
docker compose -f deploy/control.compose.yml build
docker compose -f deploy/control.compose.yml run --rm api python configure_owner.py
docker compose -f deploy/control.compose.yml up -d
```

O segundo comando de execução pede o usuário do criador e sua senha sem gravá-los no código. Crie somente sua conta de Superadministrador. Não coloque senhas em Dockerfiles, no domínio, no comando de compilação ou dentro do instalador. O domínio de exemplo precisa ser substituído pelo domínio real antes da publicação. Os arquivos de implantação foram preparados; o serviço público não foi publicado nesta máquina.

Faça backup do volume `control-data` antes de atualizar o servidor. Não use `docker compose down -v` em uma instalação com dados que deseja manter.

## Conectar os aplicativos dos amigos

Depois que o endereço real estiver funcionando, gere o instalador com ele:

```powershell
.venv\Scripts\python.exe scripts\build_windows_installer.py --version 0.2.3 --reuse-runtime --control-url https://controle.seu-dominio.example
```

O instalador recebe somente o endereço público. As credenciais de cada instalação são geradas no próprio computador, fora da pasta do programa. Seus amigos não precisam configurar o servidor: o app instalado envia os sinais automaticamente depois do login. Bibliotecas e senhas locais permanecem nos computadores.

Em uma instalação existente, o Superadministrador local pode ajustar o endereço no próprio painel. Esse ajuste altera somente aquele computador; para distribuir o endereço a todos, inclua-o no instalador. Uma atualização automática pelo próprio app ainda não está implementada.

## Testar a API sem publicação

Use um banco separado e configure uma conta do criador nele antes de iniciar:

```powershell
$env:COACH_CLASSROOM_DB = "$env:LOCALAPPDATA\CoachChess\central-test.sqlite3"
.venv\Scripts\python.exe configure_owner.py
.venv\Scripts\python.exe -m uvicorn mobile_api:app --host 127.0.0.1 --port 8502
```

`http://127.0.0.1:8502` é aceito para testes locais. As conexões públicas exigem HTTPS. Esse endereço local não pode ser usado pelos seus amigos em outros computadores como se fosse o servidor público.
