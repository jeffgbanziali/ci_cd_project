# Bank Data Pipeline & CI/CD

Pipeline data automatisée : **génération de CSV → stockage S3 → chargement/validation → traitement (fonctions pures) → base relationnelle**, avec tests d'intégration, retry, anti-doublons et CI/CD GitHub Actions.

```
 generator ──CSV──▶ S3 (SeaweedFS) ──▶ loader (validation Pydantic) ──▶ transformer (fonctions pures)
                         ▲                                                         │
   texte brut ─▶ SLM (Ollama) ─▶ CSV ──────────────────────────────────────────────┤
                                                                                   ▼
                                                     loader_db ──(1 transaction + retry)──▶ PostgreSQL
                                                     table processed_files = anti-doublons
```

## Structure

| Fichier | Rôle |
|---|---|
| `src/pipeline/generator.py` | CSV **déterministes** (cas limites 4999.99 / 5000.00 / 5000.01) |
| `src/pipeline/loader.py` | **Chargement + validation** (Pydantic) — aucun traitement métier |
| `src/pipeline/transformer.py` | **Fonctions pures** : sommes par IBAN origine / banque / IBAN destinataire, flag `> 5000` |
| `src/pipeline/loader_db.py` | Insertion **atomique**, anti-doublons (SHA-256), retry |
| `src/storage/s3_client.py` | Accès S3 : upload, liste paginée, lecture, retry, vérification |
| `src/db/models.py` | Schéma relationnel (montants en `Numeric`, jamais `Float`) |
| `src/pipeline/slm_extractor.py` | Option 3 : texte → SLM (Ollama) → même flux que les CSV |
| `src/pipeline/main.py` | Orchestration : pipeline complète, `--process-only`, `--schedule`, `--ingest-text` |
| `src/chaos.py` | Simulation de pannes temporaires (démonstration du retry) |

## Démarrage rapide

```bash
# 1) Tests sans Docker (SQLite + faux S3 moto) — idéal en développement
pip install -r requirements-dev.txt
pytest -v

# 2) Infrastructure réelle (PostgreSQL + SeaweedFS)
docker compose up -d
docker compose --profile pipeline run --rm pipeline      # pipeline complète

# 3) Ou en local contre l'infra Docker
export DB_URL=postgresql://pipeline_user:pipeline_password@localhost:5432/financial_db
export S3_ENDPOINT=http://localhost:9000
python -m src.pipeline.main
```

Variables : voir `.env.example`. Les tests utilisent `TEST_DB_URL` / `TEST_S3_ENDPOINT` (jamais `DB_URL`, car ils vident la base).

## Niveau 1 — pipeline locale

* **Flux** : `main.py` attend S3/BDD, crée le bucket, génère, envoie, **vérifie la présence**, puis traite.
* **Anti-doublons** : `processed_files.content_hash` (SHA-256, `UNIQUE`). Le fichier, ses transactions et ses agrégats sont insérés dans **une seule transaction SQL** : en cas d'échec (même au milieu), rollback complet, donc un retry ne peut pas créer de doublon.
* **Retry base** (`tenacity`) : attente exponentielle, `RETRY_MAX_ATTEMPTS` tentatives, seulement sur les pannes **temporaires** (`OperationalError`, `InterfaceError`). Une erreur d'intégrité ou un fichier invalide n'est **jamais** retenté. Au-delà du maximum, la pipeline s'arrête (code de sortie 1).

## Niveau 2 — S3

SeaweedFS (compatible S3) démarre via `docker-compose.yml`. Upload → vérification → lecture depuis S3 (jamais depuis le disque) → traitement. Le retry S3 ne cible que les erreurs temporaires (connexion, timeout, HTTP 5xx) et **les erreurs remontent** : une panne S3 fait échouer la pipeline au lieu de la laisser « réussir » avec zéro fichier.

## Niveau 3 — améliorations choisies

**Option 1 — CD** (`cd.yml`, `docker-compose.prod.yml`) : si la CI est verte sur `main`, l'image est publiée sur GHCR puis déployée en SSH sur une VM (PostgreSQL + S3 + `scheduler` en conteneurs). Le service `scheduler` lance `--schedule 300` : un cycle toutes les 5 minutes qui traite les **nouveaux** fichiers déposés dans le bucket.
Secrets GitHub à créer : `VM_HOST`, `VM_USER`, `VM_SSH_KEY`, `PROD_POSTGRES_PASSWORD`. Prérequis VM : Docker + plugin compose, clé publique SSH autorisée.

**Option 3 — SLM** : `python -m src.pipeline.main --ingest-text "Le 12 septembre à 14h30, le compte FR761234567890 a envoyé 6200 € vers le compte DE987654321 ..."`.
Le modèle (Ollama, `qwen2.5:1.5b`) **extrait** date / IBAN / montant en JSON ; le code **déduit** les pays (préfixe IBAN) et **valide** (`TransactionRow`) — rien n'est inventé : sortie incomplète = erreur. La transaction est convertie en CSV et suit **exactement** le flux des fichiers (traitement, insertion, anti-doublon, retry).
```bash
ollama pull qwen2.5:1.5b && ollama serve        # puis la commande ci-dessus
```

## Tests

| Fichier | Vérifie |
|---|---|
| `tests/unit/test_transformer.py` | valeurs des sommes, frontière du flag, **pureté**, déterminisme |
| `tests/unit/test_loader_validation.py` | CSV invalides rejetés (colonne, montant, date, IBAN, vide), 5–10 lignes |
| `tests/unit/test_slm_extractor.py` | extraction depuis la phrase d'exemple, sortie du modèle invalide rejetée |
| `tests/integration/test_pipeline_s3_db.py` | données en base, **valeurs** exactes, flags (4999.99 / 5000.00 / 5000.01), anti-doublons, **retry DB et S3** (réussite + abandon + rollback), fichier invalide, S3 injoignable, scheduler, texte → SLM |

Les valeurs attendues (`tests/expected.py`) sont calculées à part, à partir du jeu de données déterministe (17 transactions, 6 > 5000).

## Scénario d'échec de pipeline (captures demandées)

1. `git checkout -b demo/echec-flag`
2. **Cause** — dans `src/pipeline/transformer.py`, remplacer `> threshold` par `>= threshold` (bug de frontière) puis commit + push → *capture du diff*.
3. **Échec** — l'onglet *Actions* passe au rouge → *capture*.
4. **Message d'erreur** — étape *Tests* :
   ```
   FAILED tests/unit/test_transformer.py::test_flag_boundary_is_strictly_greater_than_5000
   E  assert [False, True, True, True] == [False, False, True, True]
   FAILED tests/integration/test_pipeline_s3_db.py::test_flags_are_correct_including_boundary
   E  assert 9 == 6
   ```
   → *capture du log*.
5. **Correction** — remettre `>` , commit + push → *capture du commit*.
6. **Réussite** — la CI repasse au vert → *capture*.

Autres échecs démontrables : CSV invalide (`aaa_bad.csv` dans le bucket → `InvalidDataError`, code 1), panne définitive (`SIMULATE_DB_FAILURES=99`).

## Démonstration du retry

```bash
SIMULATE_DB_FAILURES=2 SIMULATE_S3_FAILURES=2 python -m src.pipeline.main
# logs : « Retrying ... get_file_content ... TransientError » puis « Retrying ... insert_processed ... »
# → réussit à la 3e tentative, sans doublon

SIMULATE_DB_FAILURES=99 python -m src.pipeline.main      # 3 tentatives puis arrêt, code 1, base vide
```
