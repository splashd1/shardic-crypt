#!/usr/bin/env bash
# shardic-envelope portable demo -- container engine detection.
#
# Goal: whatever's already on this PC (Docker, Podman, either one aliased
# as "docker", docker-compose v1, the `docker compose` v2 plugin,
# podman-compose, or podman's own `compose` subcommand) gets used as-is.
# The bundled installer in docker-installers/ is a last resort, only
# reached if nothing usable is already present.
#
# Either `source` this script (recommended -- PATH changes apply to your
# current shell) or run it directly (it hands you back a new interactive
# shell with the right PATH set). Either way, once it prints "ready",
# follow PORTABLE-DEMO.md Step 2 onward exactly as written -- the plain
# `docker` / `docker-compose` commands in that doc and in
# repo-files/demo/README.md resolve correctly no matter which engine won
# detection.

_shardic_demo_setup() {
    local here bundled_bin engine compose_cmd

    if [ -n "${BASH_SOURCE[0]:-}" ]; then
        here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    else
        here="$(pwd)"
    fi
    bundled_bin="$here/.bundled-bin"
    mkdir -p "$bundled_bin"

    engine=""
    compose_cmd=""

    _try_docker() {
        command -v docker >/dev/null 2>&1 || return 1
        docker info >/dev/null 2>&1 || return 1
        if command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
            compose_cmd="docker-compose"
        elif docker compose version >/dev/null 2>&1; then
            compose_cmd="docker compose"
        else
            return 1
        fi
        engine="docker"
        return 0
    }

    _try_podman() {
        command -v podman >/dev/null 2>&1 || return 1
        podman info >/dev/null 2>&1 || return 1
        if command -v podman-compose >/dev/null 2>&1 && podman-compose version >/dev/null 2>&1; then
            compose_cmd="podman-compose"
        elif podman compose version >/dev/null 2>&1; then
            compose_cmd="podman compose"
        else
            return 1
        fi
        engine="podman"
        return 0
    }

    _resolve_docker_host_sock() {
        if [ -n "${DOCKER_HOST:-}" ]; then
            printf '%s' "${DOCKER_HOST#unix://}"
        else
            printf '%s' "/var/run/docker.sock"
        fi
    }

    _socket_reachable() {
        local sock="$1"
        [ -S "$sock" ] || return 1
        command -v python3 >/dev/null 2>&1 || return 1
        python3 -c '
import socket, sys
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    s.connect(sys.argv[1])
except OSError:
    sys.exit(1)
s.close()
' "$sock" 2>/dev/null
    }

    _fix_rootless_podman_socket() {
        # docker-compose v1 and podman-compose talk to the daemon over a
        # unix socket via docker-py/podman-py -- neither goes through the
        # `docker`/`podman` CLI (which, on a podman-docker install, is
        # just a shell shim exec'ing podman directly and never touches a
        # socket). So a rootful-only /var/run/docker.sock or
        # /run/podman/podman.sock that this user can't reach breaks
        # docker-compose even though `docker info`/`podman info` above
        # succeeded. Prefer this user's own rootless podman.socket if
        # it's reachable and the currently-configured one isn't.
        local sock rootless_sock
        sock="$(_resolve_docker_host_sock)"
        _socket_reachable "$sock" && return 0
        rootless_sock="/run/user/$(id -u)/podman/podman.sock"
        if [ "$rootless_sock" != "$sock" ] && _socket_reachable "$rootless_sock"; then
            echo "Default container socket ($sock) isn't reachable by this user -- using the rootless Podman socket ($rootless_sock) instead."
            export DOCKER_HOST="unix://$rootless_sock"
        fi
    }

    _use_bundled() {
        echo "No working Docker or Podman found -- falling back to the bundled offline Docker Engine + Compose (docker-installers/)."
        if [ ! -x "$bundled_bin/dockerd" ]; then
            tar xzf "$here/docker-installers/docker-29.6.2-linux-x86_64.tgz" -C "$here/docker-installers"
            cp "$here"/docker-installers/docker/* "$bundled_bin/"
        fi
        if [ ! -x "$bundled_bin/docker-compose" ]; then
            cp "$here/docker-installers/docker-compose-linux-x86_64" "$bundled_bin/docker-compose"
            chmod +x "$bundled_bin/docker-compose"
        fi
        export PATH="$bundled_bin:$PATH"

        if ! docker info >/dev/null 2>&1; then
            echo "Starting bundled dockerd in the background (needs sudo; logs at $here/dockerd.log)..."
            sudo "$bundled_bin/dockerd" >"$here/dockerd.log" 2>&1 &
            local i
            for i in $(seq 1 30); do
                docker info >/dev/null 2>&1 && break
                sleep 1
            done
            docker info >/dev/null 2>&1 || {
                echo "dockerd didn't come up in time -- check $here/dockerd.log" >&2
                return 1
            }
        fi
        engine="docker"
        compose_cmd="docker-compose"
    }

    if _try_docker; then
        echo "Detected a working Docker install -- using it (bundled installer not needed)."
        _fix_rootless_podman_socket
    elif _try_podman; then
        echo "Detected a working Podman install -- using it (bundled installer not needed)."
        _fix_rootless_podman_socket
    else
        _use_bundled || return 1
    fi

    # Make sure a literal `docker-compose` on PATH always resolves to
    # whatever we picked, since PORTABLE-DEMO.md and demo/README.md both
    # call it literally throughout.
    if [ "$compose_cmd" != "docker-compose" ] || ! command -v docker-compose >/dev/null 2>&1; then
        cat >"$bundled_bin/docker-compose" <<EOF
#!/usr/bin/env bash
exec $compose_cmd "\$@"
EOF
        chmod +x "$bundled_bin/docker-compose"
    fi

    # Same idea for `docker` itself (README also uses `docker exec`,
    # `docker images`) when only a bare podman binary was found.
    if [ "$engine" = "podman" ] && ! command -v docker >/dev/null 2>&1; then
        cat >"$bundled_bin/docker" <<'EOF'
#!/usr/bin/env bash
exec podman "$@"
EOF
        chmod +x "$bundled_bin/docker"
    fi

    export PATH="$bundled_bin:$PATH"
    echo "ready: engine=$engine compose='$compose_cmd'"
    echo "docker  -> $(command -v docker)"
    echo "docker-compose -> $(command -v docker-compose)"
}

_shardic_demo_setup
_status=$?

if [ "${BASH_SOURCE[0]:-}" != "$0" ]; then
    unset -f _shardic_demo_setup
    return $_status 2>/dev/null || true
else
    if [ "$_status" -ne 0 ]; then
        exit "$_status"
    fi
    echo
    echo "Dropping you into a new shell with PATH set up for the demo."
    echo "Continue with PORTABLE-DEMO.md Step 2 (docker load ...), then Step 3."
    echo "Type 'exit' to leave this shell when you're done."
    exec "${SHELL:-bash}" -i
fi
