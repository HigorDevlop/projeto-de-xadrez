# Continuidade entre dispositivos — etapa local

## Inspeção e reutilização

| Fonte existente | Uso nesta etapa |
| --- | --- |
| `mobile/offline-store.js`, IndexedDB | Fila e checkpoint atômicos; UUID do evento, sequência por instalação; reenvio sem apagar antes do ACK |
| `mobile_sync.py`, SQLite configurado por `COACH_CLASSROOM_DB` | Idempotência por conta/evento, sequência por dispositivo, transação e autenticação existentes; consulta dos checkpoints da própria conta |
| `mobile_api.py`, `classroom.py` | Sessões e renovação existentes; identidade derivada do token, bloqueios e expiração verificados no servidor |
| `analysis_archive.py`, `saved_analyses` | PGN e análises arquivadas da conta no rascunho local |
| `analysis_training.py`, `analysis_exercises` e `analysis_attempts` | Exercícios, tentativas, vencimentos, nível e revisão preservados; nenhum reagendamento |
| `preparation_state.py`, JSON em `ACERVO_PREPARATION_DIR/openings` | Progresso/retomada/retenção de cursos, repertório pessoal e finais nas chaves privadas existentes |
| `tactics_progress.py`, `tactics.sqlite3` | Inspecionado, mas fora do adaptador inicial: XP, resets e deduplicação exigem contrato próprio |

Senhas são derivadas com PBKDF2 no modelo existente; tokens são consultados por
hash. Isso não cifra os dados pessoais do SQLite. JSON, IndexedDB e bases atuais
continuam sem criptografia de conteúdo. Nenhum banco privado, chave ou conta
foi adicionado ao código ou ao instalador.

## O que foi implementado

- `continuity_local.capture(token)` monta um rascunho **em memória** usando as
  fontes acima e lista permitida de campos. Não exporta tabelas de login, senhas,
  tokens, arquivos de livros ou caminhos arbitrários. Não varre diretórios de
  outras contas. Cursos legados por nome público são excluídos.
- `compare(token, local, incoming, base)` inspeciona versões por tipo/identificador
  e hash canônico. Distingue igualdade, presença somente em um lado, mudança de
  um lado e conflito. Ausência não significa exclusão. Nada é aplicado.
- `last_command` avalia a preferência confirmada pelo usuário: **última ação pelo
  horário do aparelho**, nunca pelo horário do upload. Recebe explicitamente o
  instante observado e a tolerância para horário futuro. Empate, horário ausente,
  sequência contraditória ou relógio futuro impedem escolher um vencedor.
- `continuity_crypto` produz/verifica envelopes AES-256-GCM com nonce aleatório,
  autenticando também versão, conta e metadados de recuperação. O formato v2 exige
  a chave pública RSA do Superadmin (mínimo 3072 bits): envolve a chave de conteúdo
  com RSA-OAEP/SHA-256, permitindo recuperação sem a chave ou senha do usuário.
  Sem essa configuração, recusa criar novos pacotes. Chaves aleatórias permanecem
  em memória; não são derivadas da senha de login nem gravadas pelo módulo. Pacotes alterados,
  conta/chave incorreta e tamanho acima de 512 KB são recusados. Não há truncamento.
- `recover` exige sessão local válida de Superadmin e a chave privada de recuperação.
  Recupera somente um rascunho em memória, sem sobrescrever treino. Registra ator,
  conta, identificador público da chave, horário e sucesso/falha na tabela existente
  de armazenamento SQLite `continuity_recoveries` (tabela nova, no mesmo banco).
  A auditoria não guarda conteúdo, senha, token ou chave privada.
- `GET /v1/sync/checkpoints` lista apenas os checkpoints dos dispositivos da conta
  autenticada, sem eleger o aparelho vencedor. Respostas da API usam `no-store`.
- O transporte existente exige HTTPS (HTTP só para localhost), rejeita credenciais
  na URL e redirecionamentos. O cliente rejeita ACK que não corresponde ao lote,
  preservando ações criadas durante o envio.

A biblioteca criptográfica é uma dependência opcional em
`requirements-continuity.txt`. Referência técnica:
[AES-GCM da biblioteca cryptography](https://cryptography.io/en/latest/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM).

## Contrato offline-first e conflitos

Gravar a ação e o ponto local atomicamente antes de tentar enviar. Cada comando
novo deverá registrar UUID, dispositivo, sequência e `authored_at` no instante da
ação. Não usar o horário de exportação como se fosse o horário da ação antiga.
Uma tentativa nova é um evento independente, não uma cópia que soma XP novamente.

Reenviar o mesmo evento/envelope, sem regenerar UUID ou cifragem a cada tentativa.
O ACK só libera a fila confirmada. Falha de rede, sessão expirada ou bloqueio não
apagam o trabalho local. Dois aparelhos mantêm suas versões; a inspeção pode
indicar prioridade, mas a etapa atual não altera os armazenamentos de treino.
Exclusões, resets, revisão e progresso não são mesclados por soma nem por máximo.

Relógios offline plausíveis, mas incorretos, não podem ser detectados com certeza.
Registros antigos sem horário de ação não ganham timestamps inventados. A aplicação
futura deverá preservar histórico para desfazer uma escolha e impedir replay de
pacotes antigos. Abrir um envelope nesta etapa apenas permite inspecioná-lo.

## Proteção escolhida e etapas pendentes

Após a orientação do usuário, a política é **criptografia com recuperação pelo
Superadmin**, não sigilo exclusivo ao usuário. Todo novo envelope exige recuperação
administrativa. O serviço de transporte não precisa custodiar a chave privada de
recuperação; ela deverá ficar em cofre separado, acessível apenas ao Superadmin.
Metadados de conta, dispositivo, sequência e tamanho continuam visíveis. TLS é
obrigatório. Perder a chave do usuário não impede recuperar pelo Superadmin.
Perder também todas as cópias da chave privada administrativa, ou o próprio pacote,
impede a recuperação: manter backups protegidos e testar restauração é requisito.

1. **Identidade e chaves:** configurar uma autoridade de conta; vincular cada
   instalação por login/pairing autenticado. Mesmo nome ou Chess.com não prova que
   contas locais de bancos diferentes são a mesma pessoa. Integrar cofre do SO,
   pareamento, recuperação, revogação e rotação. A chave pública de recuperação deve
   vir de configuração administrativa autenticada, não de uma escolha livre do
   cliente. Guardar a privada fora do instalador/código, com backups protegidos;
   reter chaves antigas enquanto existirem pacotes vinculados a elas. O helper local
   recebe objetos de chave em memória; não implementa esse provisionamento.
2. **Persistência protegida:** integrar os envelopes à fila e ao armazenamento;
   planejar a migração das bases locais existentes e a proteção dos backups.
   O envelope implementado não criptografa retroativamente SQLite/JSON/IndexedDB.
   O protocolo mobile legado ainda aceita checkpoints em claro; esta entrega não
   declara esse protocolo como ponta a ponta e não envia os novos rascunhos a ele.
3. **Aplicação dos dados:** integrar timestamps de comando aos escritores existentes,
   implementar restauração transacional por módulo e recuperação após interrupção,
   prévia de conflitos e histórico recuperável. Rascunhos maiores exigirão lotes
   versionados; não dividir silenciosamente nem perder registros.
4. **Infraestrutura:** escolher explicitamente hospedagem, domínio, TLS, origens,
   limites, backups, retenção e monitoramento. Sem provedor escolhido ou publicação.
5. **Clientes:** integrar desktop/mobile ao fluxo de login, chave, fila e retomada.
   A interface móvel completa e um botão de sincronização no desktop não foram
   disponibilizados nesta etapa. O estudo offline existente continua independente.

## Limites do adaptador inicial

Inclui partidas **arquivadas**, não todo PGN aberto em memória ou caches externos.
Inclui exercícios/revisões de análise e repertório e progresso de cursos/finais;
não inclui táticos, salas, livros, anexos ou definições completas de cursos pessoais.
É um rascunho de continuidade, não um backup integral restaurável. A leitura SQLite
é consistente dentro da transação; JSON usa seu lock local, sem prometer atomicidade
entre processos e entre todos os arquivos. Não há análise de motor nem acesso à rede
na captura, comparação ou cifragem.

## Testes locais

`.venv\Scripts\python.exe -m pytest tests/test_continuity_local.py tests/test_mobile_sync.py tests/test_offline_mobile_store.py -q`

Cobertura: isolamento e revogação, leitura das fontes existentes, deduplicação,
concorrência e falha de lote, checkpoints por dispositivo, autorização HTTP,
fila offline após reabertura, ACK durante edição, política de relógio, integridade
criptográfica, conta/chave incorreta, nonces distintos e limites de tamanho.
Inclui recuperação pelo Superadmin sem a chave do usuário, recusa de outros papéis,
pacote/chave de recuperação incorretos e auditoria de sucesso/falha. O formato
experimental v1 sem recuperação não é aceito como v2; não há migração automática.

**Não há serviço público implantado nem sincronização ponta a ponta pronta para uso.**
