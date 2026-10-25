#!/usr/bin/env bash
# Backup 3-2-1 (item 7.4 do PROJETO.md):
#   1. expdp comprimido do schema INTRANET_APP
#   2. envio para o bucket decos-backup (versionado)
#   3. retenção 7 diários · 4 semanais · 12 mensais
# Agendar no cron às 02h. Backup que nunca foi restaurado não é backup:
# o teste de restauração é mensal e vira evidência na ata da sprint.
set -euo pipefail

echo "TODO: implementar conforme a seção 7.4 do PROJETO.md"
exit 1
