#!/usr/bin/env bash
# Create a Model Armor template (Layer 3). API surface may evolve — if the gcloud
# subcommand differs in your SDK, create the template in the console (Security ->
# Model Armor) with prompt-injection + data-loss + malicious-URL filters and paste
# its resource name into .env as MODEL_ARMOR_TEMPLATE.
set -euo pipefail
source ../.env 2>/dev/null || source .env
REGION="$GOOGLE_CLOUD_LOCATION"
TEMPLATE_ID="reguguard-shield"

set +e
gcloud model-armor templates create "$TEMPLATE_ID" \
  --location "$REGION" \
  --pi-and-jailbreak-filter-settings-enforcement=enabled \
  --pi-and-jailbreak-filter-settings-confidence-level=LOW_AND_ABOVE \
  --malicious-uri-filter-settings-enforcement=enabled \
  --basic-config-filter-enforcement=enabled 2>/tmp/ma_err
RC=$?
set -e
if [ $RC -ne 0 ]; then
  echo "!! gcloud model-armor create failed (SDK version mismatch is common)."
  echo "   Create the template in the console and set MODEL_ARMOR_TEMPLATE in .env."
  cat /tmp/ma_err
  exit 0
fi
echo ">>> Set in .env:"
echo "export MODEL_ARMOR_TEMPLATE=\"projects/$GOOGLE_CLOUD_PROJECT/locations/$REGION/templates/$TEMPLATE_ID\""
echo "export MODEL_ARMOR_ENABLED=\"true\""
