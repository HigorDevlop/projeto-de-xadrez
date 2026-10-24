# Colocar seu painel na internet com HTTPS

O painel precisa de um computador na nuvem ligado continuamente. O treino, os livros e os motores continuam no computador de cada usuário; o servidor recebe presença e oferece seu painel privado. Ficar sem esse servidor não impede os treinos offline.

## 1. Preparar servidor e domínio

Tenha um servidor Linux com IP público, acesso SSH e Docker Engine com o plugin Compose. A instalação oficial do Docker em Ubuntu está em https://docs.docker.com/engine/install/ubuntu/ . Você também precisa controlar o DNS de um domínio. Nenhum serviço foi contratado ou publicado automaticamente.

No painel do domínio, crie um registro **A**:

| Campo | Valor de exemplo |
| --- | --- |
| Tipo | A |
| Nome | controle |
| Destino | IP público do servidor |

Assim, `controle.seudominio.com.br` aponta para o servidor. Substitua esse exemplo pelo domínio real em todos os comandos. Libere as portas TCP **80 e 443** no provedor do servidor, além da porta SSH usada por você. Não crie um registro IPv6 AAAA sem que o endereço IPv6 correspondente esteja funcionando.

O Caddy incluído no projeto obtém e renova o certificado HTTPS automaticamente quando o domínio e as portas estão corretos. Referência oficial: https://caddyserver.com/docs/quick-starts/https .

## 2. Enviar somente os arquivos necessários

Foi preparado um pacote pequeno, sem seus bancos, livros e senhas:

`.build-tools/hosting/coach-control-server.zip`

No PowerShell deste computador, dentro da pasta do projeto, envie-o para o servidor:

```powershell
scp .build-tools/hosting/coach-control-server.zip usuario@IP_DO_SERVIDOR:~/
ssh usuario@IP_DO_SERVIDOR
```

Use o usuário e o IP que seu provedor informar. Os próximos comandos são executados no servidor Linux, depois do SSH.

## 3. Preparar o painel privado

Com Docker e Compose já instalados, extraia o arquivo e entre na pasta:

```bash
unzip coach-control-server.zip
cd coach-control
printf 'COACH_DOMAIN=controle.seudominio.com.br\n' > deploy/control.env
docker compose --env-file deploy/control.env -f deploy/control.compose.yml build
docker compose --env-file deploy/control.env -f deploy/control.compose.yml run --rm api python configure_owner.py
```

Se o comando `unzip` não existir, instale-o pelo gerenciador de pacotes do Linux. No comando de configuração do criador, use o nome **superadmin** e escolha sua senha. A senha é digitada no terminal e guardada como hash, sem entrar nos arquivos distribuídos. A conta do seu computador e a conta desse servidor ficam em bancos separados: configurar uma não cria a outra automaticamente.

Depois inicie os serviços:

```bash
docker compose --env-file deploy/control.env -f deploy/control.compose.yml up -d
docker compose --env-file deploy/control.env -f deploy/control.compose.yml ps
```

## 4. Conferir o HTTPS

Abra no navegador:

`https://controle.seudominio.com.br/health`

O resultado esperado é `{"status":"ok"}`. A raiz do endereço pode retornar 404, pois o serviço é uma API; use `/health` para o teste.

Se não funcionar, consulte os registros:

```bash
docker compose --env-file deploy/control.env -f deploy/control.compose.yml logs --tail=80 https api
```

As causas mais comuns são domínio ainda apontando para outro IP, portas fechadas ou registro IPv6 incorreto. Não use `localhost` como endereço para seus amigos: em cada computador, localhost aponta para a própria máquina.

## 5. Conectar seu aplicativo

No Coach Chess, entre como **superadmin**, abra **Usuários → Conexão com o servidor central** e salve:

`https://controle.seudominio.com.br`

Informe a conta do criador configurada no servidor. O painel mostrará as instalações que se conectarem a esse endereço. Não use o sufixo `/health` no campo do aplicativo.

Para os amigos, o endereço público deve ser incluído na próxima distribuição que você solicitar, ou configurado na instalação deles. Nenhum novo instalador ou número de versão será criado automaticamente só por alterar o código. A atualização automática pelo próprio aplicativo ainda é um trabalho separado.

## 6. Manter os dados

O banco central fica no volume persistente `control-data`; mantenha backups desse volume. Reiniciar os serviços não apaga os dados. Não execute `docker compose down -v` se deseja preservar os registros. O Caddy mantém seus certificados nos volumes próprios.

Para referência técnica das rotas e do funcionamento dos sinais, consulte [PAINEL_CENTRAL.md](PAINEL_CENTRAL.md).
