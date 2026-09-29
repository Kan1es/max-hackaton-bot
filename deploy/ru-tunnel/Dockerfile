# SOCKS5 proxy into Russia over plain SSH: government portals refuse foreign
# IPs, and this way the Russian VPS needs nothing but an SSH login.
FROM alpine:3.20
RUN apk add --no-cache openssh-client autossh
ENV AUTOSSH_GATETIME=0
EXPOSE 1080
CMD ["sh", "-c", "exec autossh -M 0 -N -D 0.0.0.0:1080 \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes \
  -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/tmp/known_hosts \
  -i /run/ru_tunnel_key -p ${RU_SSH_PORT:-22} ${RU_SSH_USER:-root}@${RU_SSH_HOST:?set RU_SSH_HOST}"]
