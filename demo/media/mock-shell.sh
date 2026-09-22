# Sourced by walkthrough.tape before any typing starts. Shadows
# docker-compose, docker, and curl with functions that replay real,
# previously-captured output from fixtures/ instead of touching a live
# stack. Lets the recording render anywhere, instantly, and never puts a
# live Bearer token on screen. See fixtures/README.md for how these were
# captured and how to refresh them.
#
# Every branch here exists because the tape types that exact command.
# If you edit walkthrough.tape's commands, update the matching case arm.

_MOCK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_FIXTURES="$_MOCK_DIR/fixtures"

_slow_cat() {
    while IFS= read -r line; do
        printf '%s\n' "$line"
        sleep 0.04
    done < "$1"
}

_mock_miss() {
    printf '\033[1;31m[mock-shell] no fixture wired for: %s\033[0m\n' "$*" >&2
    return 1
}

# Ceremony-context narration line, printed in the terminal itself.
# See media/narration.md for the fuller companion script.
banner() {
    printf '\n\033[1;35m▸ %s\033[0m\n\n' "$*"
}

docker-compose() {
    local args="$*"
    case "$args" in
        "--env-file .env up -d keycloak")
            _slow_cat "$_FIXTURES/02a-up-keycloak.txt" ;;
        "ps")
            cat "$_FIXTURES/01-ps-healthy.txt" ;;
        "--profile candidates --env-file .env up -d combiner trustee-alice trustee-bob trustee-carol trustee-dave trustee-erin trustee-frank")
            _slow_cat "$_FIXTURES/02b-up-candidates.txt" ;;
        "logs trustee-alice")
            _slow_cat "$_FIXTURES/03-logs-alice.txt" ;;
        "pause trustee-erin")
            _slow_cat "$_FIXTURES/04-pause-erin.txt" ;;
        "logs combiner")
            _slow_cat "$_FIXTURES/05-backfill-log.txt" ;;
        "pause trustee-dave trustee-frank")
            _slow_cat "$_FIXTURES/08-pause-dave-frank.txt" ;;
        "ps -q combiner")
            echo "mock-combiner-container" ;;
        "logs -f trustee-alice trustee-bob trustee-carol")
            _slow_cat "$_FIXTURES/09-shard-log.txt" ;;
        "--profile candidates down -v")
            _slow_cat "$_FIXTURES/12-teardown.txt" ;;
        *)
            _mock_miss "docker-compose $args" ;;
    esac
}

docker() {
    local args="$*"
    case "$args" in
        "unpause demo_trustee-erin_1")
            echo "demo_trustee-erin_1" ;;
        "unpause demo_trustee-dave_1 demo_trustee-frank_1")
            printf 'demo_trustee-dave_1\ndemo_trustee-frank_1\n' ;;
        *"trustee_words"*)
            cat "$_FIXTURES/07-wrapped-check.txt" ;;
        *"diff -r /data/sample-secret"*)
            cat "$_FIXTURES/11-verify-diff.txt" ;;
        *)
            _mock_miss "docker $args" ;;
    esac
}

curl() {
    local args="$*"
    case "$args" in
        *"openid-connect/token"*)
            cat "$_FIXTURES/token-response.json" ;;
        *"group-members"*)
            cat "$_FIXTURES/03-group-members.json" ;;
        *"ceremony/initiate"*)
            cat "$_FIXTURES/04-ceremony-initiate.json" ;;
        *"vault/create"*)
            cat "$_FIXTURES/06-vault-create.json" ;;
        *"recovery/start"*)
            cat "$_FIXTURES/09-recovery-start.json" ;;
        *"recovery/finalize"*)
            cat "$_FIXTURES/10-recovery-finalize.json" ;;
        *"recovery/verify"*)
            cat "$_FIXTURES/11b-recovery-verify.json" ;;
        *)
            _mock_miss "curl $args" ;;
    esac
}

export -f docker-compose docker curl banner _slow_cat _mock_miss
