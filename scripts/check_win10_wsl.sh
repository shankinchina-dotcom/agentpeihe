#!/usr/bin/env bash
# check_win10_wsl.sh — WSL 端到端运行面自检（不审计 Windows 防火墙，不打印密钥）
# 用法: bash agentpeihe/scripts/check_win10_wsl.sh
# 环境变量:
#   PROXY_PORT  代理端口，默认 7897
#   PROXY_GW    代理网关 IP；未设置时从 `ip route` 默认网关读取

set +e
set -u

export PATH="${HOME}/.local/bin:${HOME}/.kimi-code/bin:${PATH:-}"

PROXY_PORT="${PROXY_PORT:-7897}"
CONNECT_TIMEOUT=5
NC_TIMEOUT=3

FAIL=0
WARN=0
PASS=0

pass() { PASS=$((PASS + 1)); printf 'PASS  %s\n' "$*"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL  %s\n' "$*"; }
warn() { WARN=$((WARN + 1)); printf 'WARN  %s\n' "$*"; }
section() { printf '\n== %s ==\n' "$*"; }

yaml_value() {
  local key="$1"
  local file="$2"
  awk -v key="$key" '
    $0 ~ "^[[:space:]]*" key ":[[:space:]]*" {
      line=$0
      sub("^[[:space:]]*" key ":[[:space:]]*", "", line)
      sub(/[[:space:]]+#.*/, "", line)
      gsub(/^[[:space:]\"\047]+|[[:space:]\"\047]+$/, "", line)
      print line
      exit
    }
  ' "$file" 2>/dev/null
}

if [[ -n "${PROXY_GW:-}" ]]; then
  GW="$PROXY_GW"
else
  GW="$(ip route show default 2>/dev/null | awk '{print $3; exit}')"
fi

section "1. 网关"
if [[ -n "${GW:-}" ]]; then
  pass "网关存在: ${GW} (PROXY_PORT=${PROXY_PORT})"
else
  fail "无默认网关（ip route 无 default，且未设 PROXY_GW）"
fi

section "2. 代理 TCP (${GW:-?}:${PROXY_PORT})"
if [[ -z "${GW:-}" ]]; then
  fail "跳过 nc：无网关"
elif ! command -v nc >/dev/null 2>&1; then
  fail "nc 不可用（请安装 netcat）"
elif nc -z -w "${NC_TIMEOUT}" "$GW" "$PROXY_PORT" >/dev/null 2>&1; then
  pass "nc ${GW}:${PROXY_PORT} 通 (timeout ${NC_TIMEOUT}s)"
else
  fail "nc ${GW}:${PROXY_PORT} 不通 (timeout ${NC_TIMEOUT}s)"
fi

section "3. 经代理 HTTP（硬 FAIL）"
if [[ -z "${GW:-}" ]]; then
  fail "跳过 generate_204：无网关"
else
  code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout "${CONNECT_TIMEOUT}" \
    --max-time 15 -x "http://${GW}:${PROXY_PORT}" \
    "https://www.google.com/generate_204" 2>/dev/null || true)"
  if [[ "$code" == "204" ]]; then
    pass "proxy generate_204 → ${code}"
  else
    fail "proxy generate_204 → ${code:-curl_error}（期望 204）"
  fi
fi

section "4. 经代理 GitHub（硬 FAIL）"
if [[ -z "${GW:-}" ]]; then
  fail "跳过 github：无网关"
else
  code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout "${CONNECT_TIMEOUT}" \
    --max-time 15 -x "http://${GW}:${PROXY_PORT}" \
    "https://github.com" 2>/dev/null || true)"
  if [[ "$code" == "200" ]]; then
    pass "proxy github → ${code}"
  else
    fail "proxy github → ${code:-curl_error}（期望 200）"
  fi
fi

section "5. 国内直连 DeepSeek"
code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout "${CONNECT_TIMEOUT}" \
  --noproxy '*' "https://api.deepseek.com/v1/models" 2>/dev/null || true)"
if [[ "$code" == "401" || "$code" == "200" ]]; then
  pass "deepseek /v1/models → ${code}（通路通）"
else
  fail "deepseek /v1/models → ${code:-curl_error}（期望 401/200）"
fi

section "6. PATH 工具"
need_fail() {
  local name="$1"
  if command -v "$name" >/dev/null 2>&1; then
    pass "PATH 有 ${name}: $(command -v "$name")"
  else
    fail "PATH 无 ${name}"
  fi
}
need_warn() {
  local name="$1"
  local hint="${2:-}"
  if command -v "$name" >/dev/null 2>&1; then
    pass "PATH 有 ${name}: $(command -v "$name")"
  else
    warn "PATH 无 ${name}${hint:+ — $hint}"
  fi
}

need_fail "omnigent-zh"
need_fail "codex"
need_warn "kimi" "可选；未装则不生成 exec_moonshot（~/.kimi-code/bin）"
need_fail "claude"
need_warn "pi" "v1.1 主路径非硬依赖"

section "7. 登录 / 凭据（不打印密钥）"
if command -v codex >/dev/null 2>&1; then
  codex_out="$(codex login status 2>&1)"
  codex_rc=$?
  if [[ "$codex_rc" -eq 0 ]] && printf '%s\n' "$codex_out" | grep -qiE 'Logged in using (ChatGPT|an? API key)'; then
    if printf '%s\n' "$codex_out" | grep -qi 'Logged in using ChatGPT'; then
      pass "codex login status: Logged in using ChatGPT"
    else
      pass "codex login status: Logged in using API key"
    fi
  else
    fail "codex login status 未返回明确成功文案（rc=${codex_rc}）"
  fi
else
  fail "codex 不在 PATH，跳过 login status"
fi

kimi_cred="${HOME}/.kimi-code/credentials/kimi-code.json"
if [[ -f "$kimi_cred" ]]; then
  pass "kimi credentials present: ~/.kimi-code/credentials/kimi-code.json"
elif compgen -G "${HOME}/.kimi-code/credentials/*" >/dev/null 2>&1; then
  pass "kimi credentials 目录有文件: ~/.kimi-code/credentials/"
else
  warn "kimi credentials missing（未 login 或未装 kimi）"
fi

claude_settings="${HOME}/.claude/settings.json"
if [[ ! -f "$claude_settings" ]]; then
  fail "claude settings missing: ~/.claude/settings.json"
else
  base_status="$(python3 - <<'PY' 2>/dev/null
import json
from pathlib import Path

p = Path.home() / ".claude" / "settings.json"
try:
    env = json.loads(p.read_text(encoding="utf-8")).get("env") or {}
    url = str(env.get("ANTHROPIC_BASE_URL") or "").strip().rstrip("/").lower()
except Exception:
    print("error")
else:
    print("match" if url == "https://api.deepseek.com/anthropic" else ("missing" if not url else "mismatch"))
PY
)"
  case "$base_status" in
    match) pass "claude settings 指向 DeepSeek Anthropic 端点" ;;
    missing) fail "claude settings ANTHROPIC_BASE_URL missing" ;;
    mismatch) fail "claude settings ANTHROPIC_BASE_URL 不是规定的 DeepSeek 端点" ;;
    *) fail "claude settings 解析失败" ;;
  esac
fi

section "8. controller bundle"
bundle_cfg="${HOME}/.omnigent/agents/controller/config.yaml"
workers_dir="${HOME}/.omnigent/agents/controller/agents"

if [[ ! -f "$bundle_cfg" ]]; then
  fail "bundle config 不存在: ~/.omnigent/agents/controller/config.yaml"
else
  controller_harness="$(yaml_value harness "$bundle_cfg")"
  case "$controller_harness" in
    codex|claude-sdk|pi)
      pass "controller harness=${controller_harness}（非 native）"
      ;;
    "")
      fail "controller config 未找到 harness"
      ;;
    *)
      fail "controller harness=${controller_harness}（仅允许 codex/claude-sdk/pi）"
      ;;
  esac
fi

worker_count=0
declare -A vendors=()
if [[ ! -d "$workers_dir" ]]; then
  fail "workers 目录不存在: ~/.omnigent/agents/controller/agents"
else
  mapfile -t worker_list < <(find "$workers_dir" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort)
  for worker in "${worker_list[@]:-}"; do
    [[ -z "${worker:-}" ]] && continue
    worker_count=$((worker_count + 1))
    worker_cfg="${workers_dir}/${worker}/config.yaml"
    if [[ ! -f "$worker_cfg" ]]; then
      fail "worker ${worker} 缺 config.yaml"
      continue
    fi

    harness="$(yaml_value harness "$worker_cfg")"
    permission_mode="$(yaml_value permission_mode "$worker_cfg")"
    worker_valid=1
    vendor=""
    case "$worker" in
      exec_deepseek)
        vendor="deepseek"
        if [[ "$harness" != "claude-native" || "$permission_mode" != "auto" ]]; then
          fail "exec_deepseek 必须 harness=claude-native 且 permission_mode=auto"
          worker_valid=0
        else
          pass "exec_deepseek 通道配置正确"
        fi
        ;;
      exec_openai)
        vendor="openai"
        if [[ "$harness" != "codex" ]]; then
          fail "exec_openai 必须 harness=codex"
          worker_valid=0
        else
          pass "exec_openai 通道配置正确"
        fi
        ;;
      exec_moonshot)
        vendor="moonshot"
        if [[ "$harness" != "kimi-native" ]]; then
          fail "exec_moonshot 必须 harness=kimi-native"
          worker_valid=0
        else
          pass "exec_moonshot 通道配置正确"
        fi
        ;;
      exec_xai) vendor="xai" ;;
      exec_anthropic) vendor="anthropic" ;;
      exec_zhipu) vendor="zhipu" ;;
      exec_alibaba) vendor="alibaba" ;;
      *)
        warn "未知 worker ${worker}：不计入 vendor 数"
        worker_valid=0
        ;;
    esac

    if [[ "$worker_valid" -eq 1 && -n "$vendor" ]]; then
      vendors["$vendor"]=1
    fi
  done

  if [[ "$worker_count" -ge 2 ]]; then
    pass "workers 数量 ${worker_count} >= 2"
  else
    fail "workers 数量 ${worker_count} < 2"
  fi

  vendor_count=${#vendors[@]}
  if [[ "$vendor_count" -ge 2 ]]; then
    pass "已验证 worker 覆盖 ${vendor_count} 个不同 vendor"
  else
    fail "已验证 worker 仅覆盖 ${vendor_count} 个 vendor（至少需要 2）"
  fi
fi

section "9. omnigent server :6767"
code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout "${CONNECT_TIMEOUT}" \
  "http://127.0.0.1:6767" 2>/dev/null || true)"
case "$code" in
  2??|3??|401|403) pass "server 127.0.0.1:6767 → ${code}（可达）" ;;
  *) fail "server 127.0.0.1:6767 → ${code:-unreachable}（期望 2xx/3xx/401/403）" ;;
esac

printf '\n========== 运行面检查摘要 ==========\n'
printf 'PASS=%s  WARN=%s  FAIL=%s\n' "$PASS" "$WARN" "$FAIL"
printf 'GW=%s  PROXY_PORT=%s\n' "${GW:--}" "$PROXY_PORT"
printf '说明: 代理 HTTP、登录、通道配置和 bundle 结构均按明确证据判定。\n'
printf '8/8 业务验收与 Windows 防火墙审计不在本脚本范围内。\n'
printf '====================================\n'

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
exit 0
