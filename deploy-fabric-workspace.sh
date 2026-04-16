#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# deploy-fabric-workspace.sh
# Deploys a Microsoft Fabric workspace with lakehouse and spark environment
# using the Fabric REST API (https://learn.microsoft.com/rest/api/fabric)
# =============================================================================

FABRIC_API="https://api.fabric.microsoft.com/v1"

# ── Defaults (override via flags or environment variables) ───────────────────
WORKSPACE_NAME="${FABRIC_WORKSPACE_NAME:-My-Fabric-Workspace}"
CAPACITY_ID="${FABRIC_CAPACITY_ID:-}"
LAKEHOUSE_NAME="${FABRIC_LAKEHOUSE_NAME:-}"
SPARK_ENV_NAME="${FABRIC_SPARK_ENV_NAME:-}"
DRY_RUN=false

# ── Color helpers ────────────────────────────────────────────────────────────
info()  { printf '\033[0;36m[INFO]\033[0m  %s\n' "$*"; }
ok()    { printf '\033[0;32m[OK]\033[0m    %s\n' "$*"; }
warn()  { printf '\033[0;33m[WARN]\033[0m  %s\n' "$*"; }
fail()  { printf '\033[0;31m[FAIL]\033[0m  %s\n' "$*"; exit 1; }

# ── Usage ────────────────────────────────────────────────────────────────────
usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Create a Microsoft Fabric workspace (and optional child resources) via REST API.

Options:
  -w, --workspace NAME       Workspace display name  (default: \$FABRIC_WORKSPACE_NAME)
  -c, --capacity  ID         Fabric capacity GUID to assign
  -l, --lakehouse NAME       Also create a Lakehouse with this name
  -s, --spark-env NAME       Also create a Spark environment with this name
  -n, --dry-run              Print API calls without executing
  -h, --help                 Show this help

Environment variables (used as fallbacks):
  FABRIC_WORKSPACE_NAME      Workspace name
  FABRIC_CAPACITY_ID         Capacity ID
  FABRIC_LAKEHOUSE_NAME      Lakehouse name
  FABRIC_SPARK_ENV_NAME      Spark env name

Prerequisites:
  • Azure CLI (az) authenticated – the script obtains a bearer token via
    az account get-access-token
  • jq for JSON parsing
  • curl

Examples:
  # Minimal – create workspace only
  ./deploy-fabric-workspace.sh -w "Analytics-Dev"

  # Full stack
  ./deploy-fabric-workspace.sh \\
      -w "Analytics-Prod" \\
      -c "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" \\
      -l "Sales_Lakehouse" \\
      -s "HighPerf_Spark"

  # Dry run to preview API calls
  ./deploy-fabric-workspace.sh -w "Test" --dry-run
EOF
  exit 0
}

# ── Parse arguments ──────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    -w|--workspace) WORKSPACE_NAME="$2"; shift 2 ;;
    -c|--capacity)  CAPACITY_ID="$2";    shift 2 ;;
    -l|--lakehouse) LAKEHOUSE_NAME="$2"; shift 2 ;;
    -s|--spark-env) SPARK_ENV_NAME="$2"; shift 2 ;;
    -n|--dry-run)   DRY_RUN=true;        shift   ;;
    -h|--help)      usage ;;
    *) fail "Unknown option: $1. Use --help for usage." ;;
  esac
done

# ── Pre-flight checks ───────────────────────────────────────────────────────
for cmd in az jq curl; do
  command -v "$cmd" &>/dev/null || fail "$cmd is required but not found. Please install it."
done

info "Acquiring Azure AD token for Fabric API..."
TOKEN=$(az account get-access-token \
  --resource "https://api.fabric.microsoft.com" \
  --query accessToken -o tsv 2>/dev/null) \
  || fail "Could not obtain token. Run 'az login' first."
ok "Token acquired"

AUTH_HEADER="Authorization: Bearer ${TOKEN}"
CONTENT_TYPE="Content-Type: application/json"

# ── Helper: call Fabric REST API ─────────────────────────────────────────────
fabric_api() {
  local method="$1" endpoint="$2" body="${3:-}"

  if $DRY_RUN; then
    info "[DRY RUN] $method $endpoint"
    [[ -n "$body" ]] && echo "$body" | jq .
    return 0
  fi

  local args=(-s -w "\n%{http_code}" -X "$method"
              -H "$AUTH_HEADER" -H "$CONTENT_TYPE"
              "${FABRIC_API}${endpoint}")
  [[ -n "$body" ]] && args+=(-d "$body")

  local response http_code
  response=$(curl "${args[@]}")
  http_code=$(echo "$response" | tail -1)
  response=$(echo "$response" | sed '$d')

  if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
    echo "$response"
    return 0
  else
    warn "HTTP $http_code from $method $endpoint"
    echo "$response" | jq . 2>/dev/null || echo "$response"
    return 1
  fi
}

# ═════════════════════════════════════════════════════════════════════════════
# STEP 1 – Create Workspace
# ═════════════════════════════════════════════════════════════════════════════
info "Creating workspace: ${WORKSPACE_NAME}"

ws_body=$(jq -n \
  --arg name "$WORKSPACE_NAME" \
  '{displayName: $name}')

# Attach capacity in the same call if provided
if [[ -n "$CAPACITY_ID" ]]; then
  ws_body=$(echo "$ws_body" | jq --arg cap "$CAPACITY_ID" '. + {capacityId: $cap}')
  info "Attaching capacity: ${CAPACITY_ID}"
fi

ws_response=$(fabric_api POST "/workspaces" "$ws_body") \
  || fail "Workspace creation failed"

WORKSPACE_ID=$(echo "$ws_response" | jq -r '.id // empty')

if [[ -z "$WORKSPACE_ID" ]] && $DRY_RUN; then
  WORKSPACE_ID="dry-run-id"
fi

[[ -z "$WORKSPACE_ID" ]] && fail "Could not parse workspace ID from response"
ok "Workspace created — ID: ${WORKSPACE_ID}"

# ═════════════════════════════════════════════════════════════════════════════
# STEP 2 – Create Lakehouse (optional)
# ═════════════════════════════════════════════════════════════════════════════
if [[ -n "$LAKEHOUSE_NAME" ]]; then
  info "Creating lakehouse: ${LAKEHOUSE_NAME}"

  lh_body=$(jq -n \
    --arg name "$LAKEHOUSE_NAME" \
    '{displayName: $name, type: "Lakehouse"}')

  lh_response=$(fabric_api POST "/workspaces/${WORKSPACE_ID}/items" "$lh_body") \
    || warn "Lakehouse creation returned an error (see above)"

  lh_id=$(echo "$lh_response" | jq -r '.id // empty' 2>/dev/null)
  [[ -n "$lh_id" ]] && ok "Lakehouse created — ID: ${lh_id}"
fi

# ═════════════════════════════════════════════════════════════════════════════
# STEP 3 – Create Spark Environment (optional)
# ═════════════════════════════════════════════════════════════════════════════
if [[ -n "$SPARK_ENV_NAME" ]]; then
  info "Creating Spark environment: ${SPARK_ENV_NAME}"

  se_body=$(jq -n \
    --arg name "$SPARK_ENV_NAME" \
    '{displayName: $name, type: "Environment"}')

  se_response=$(fabric_api POST "/workspaces/${WORKSPACE_ID}/items" "$se_body") \
    || warn "Spark environment creation returned an error (see above)"

  se_id=$(echo "$se_response" | jq -r '.id // empty' 2>/dev/null)
  [[ -n "$se_id" ]] && ok "Spark environment created — ID: ${se_id}"
fi

# ═════════════════════════════════════════════════════════════════════════════
# Summary
# ═════════════════════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ok "Deployment complete"
echo "  Workspace : ${WORKSPACE_NAME} (${WORKSPACE_ID})"
[[ -n "$CAPACITY_ID" ]]    && echo "  Capacity  : ${CAPACITY_ID}"
[[ -n "${lh_id:-}" ]]      && echo "  Lakehouse : ${LAKEHOUSE_NAME} (${lh_id})"
[[ -n "${se_id:-}" ]]      && echo "  Spark Env : ${SPARK_ENV_NAME} (${se_id})"
echo ""
echo "  Portal    : https://app.fabric.microsoft.com"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
