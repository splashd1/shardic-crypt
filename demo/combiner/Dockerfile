# Build context is the repo root (see demo/docker-compose.yml's
# `context: ..`), so this can COPY the actual core crypto modules
# instead of duplicating any matching/reconstruction logic -- per
# CLAUDE.md's "don't duplicate crypto logic across frontends" rule.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY demo/combiner/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY vault_core_prime.py vault_core.py gf256_sss_prime.py gf256_sss.py \
     kdf.py krypt_container.py wordgen.py eff_wordlist_words.py \
     shardic_envelope_crypto.py ./
COPY demo/combiner/app.py demo/combiner/keycloak_client.py demo/combiner/vault_store.py \
     demo/combiner/notifications.py ./
COPY demo/combiner/dashboard ./dashboard

EXPOSE 5000
CMD ["python3", "app.py"]
