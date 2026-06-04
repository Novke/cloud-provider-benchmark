# SPEC — Cloud Provider Benchmark Project Roadmap

Master plan dokument koji obuhvata trenutno stanje projekta, sledece korake i sve kontekste potrebne da bilo ko (i ti i Claude u sledecoj sesiji) nastavi rad **bez chat istorije**.

> **Citaj prvo ovaj fajl** kada krenes fresh — ima sve sto ti treba da znas. Linkovi dalje u `resources/` ako treba dublja istorija.

---

## 1. Stanje projekta (2026-05-23)

### Sta JE deployovano (4/4 IaaS ✅)

| Provajder | Project / Account | Instance type | IP | Region |
|---|---|---|---|---|
| **GCP** | `cloud-benchmark-493210` (nalog `novica@gf.uns.ac.rs`) | `n2-standard-2` (dedicated) | `35.246.182.190` | `europe-west3-a` |
| **AWS** | account `981629166334` (IAM user `benchmark-cli`, profile `benchmark`) | `m6i.large` (dedicated, **Ice Lake 8375C @ 2.9 GHz** — upgrade 2026-05-23) | `18.185.48.126` | `eu-central-1` |
| **Azure** | subscription `15006c9b-8de5-49ff-aca0-a5d5ebb3fa68`, RG `benchmark-rg` | `Standard_D2s_v5` (dedicated) | `51.116.237.102` | `germanywestcentral` |
| **Hetzner** | projekat `benchmark` | `CCX13` (dedicated AMD EPYC, Ubuntu 24.04) | `178.105.101.205` | `fsn1` (Falkenstein) — deploy 2026-05-26 |

### Native object storage (4/4 deployovano ✅)

| Provajder | Bucket / container | Auth pattern |
|---|---|---|
| GCP | `gs://cloud-benchmark-native-gcp` | ADC via VM service account |
| AWS | `s3://cloud-benchmark-aws-native-981629166334` | IAM instance profile `benchmark-ec2-profile` |
| Azure | `cloudbenchaznative0001` / container `native` | System-assigned managed identity |
| Hetzner | `cloud-benchmark-native-hetzner` (`fsn1.your-objectstorage.com`) | S3 access keys, GitHub secrets `HETZNER_BENCHMARK_STORAGE_*` (per-project credentials) |

### Neutral storage (Cloudflare R2 — isti za sve)

Endpoint: `https://f849c8f064ff3760f8be2dd10d6d31d0.r2.cloudflarestorage.com`
Bucket: `cloud-benchmark`
Credentials u `.env` (lokalno, gitignored) i GitHub secrets `R2_*`.

### SSH access

```
ssh -i ~/.ssh/gcp_benchmark benchmark-deploy@35.246.182.190
ssh -i ~/.ssh/aws_benchmark ubuntu@18.185.48.126
ssh -i ~/.ssh/azure_benchmark azureuser@51.116.237.102
```

Deploy putanja na svim VM-ovima: `/srv/backend/cloud-benchmark`. Docker compose, servis `benchmark-api`, port 8000.

### Glavni nalazi do sada

1. **AWS m5.large CPU je 1.75x sporiji** od GCP/Azure ekvivalenata sa istim "2 vCPU dedicated" label-om — uzrokovano starijim Skylake 2017 hardware-om. Sysbench: 666 vs 1166-1194 events/sec. Detaljno u `resources/Nalazi i dnevnik.md`. **Resolved 2026-05-23**: upgrade na m6i.large (Ice Lake 8375C) → sysbench 1109/s, gap zatvoren do <8%.
2. **Burstable tier nije ekvivalentno preko provajdera** — GCP e2 znacajno losiji od n2 pod sustained load, Azure B2ms skoro identican B2ms vs D2s_v5. Detaljno u `resources/Burstable to Dedicated comparison.md`.
3. **AWS instance je nekad bio greskom `t3.micro` umesto `t3.large`** (1 GiB RAM); ispravilo se prelaskom na dedicated tier.
4. **Azure deploy ima vise friction-a** nego GCP/AWS (provider registration, free trial limitacije, quota requests).

### Kljucni resource fajlovi

| Fajl | Sadrzaj |
|---|---|
| `resources/SPEC.md` | **OVAJ FAJL** — master roadmap |
| `resources/Specifikacije infrastrukture.md` | Tehnicki detalji svake VM/bucket-a + sve secrets |
| `resources/Nalazi i dnevnik.md` | Hronoloski log nalaza i odluka |
| `resources/Methodology improvements TODO.md` | Sve metodoloske ideje + plan za production benchmark |
| `resources/Burstable to Dedicated comparison.md` | Burstable→dedicated ablation study |
| `resources/Deployment friction.md` | Per-provider deploy friction (Azure-heavy) |
| `resources/Hetzner deploy steps.md` | Pauzirani Hetzner setup, ready za pokretanje |
| `resources/Otvorena pitanja.md` | Metodoloska pitanja za profesora |
| `resources/Plan razvoja.md` | Originalni plan |
| `resources/Finalni plan razvoja istrazivanja.md` | Originalni finalni plan |
| `resources/Struktura naucnog rada.md` | Skeleton rada |
| `resources/Plan istrazivanja.md` | Plan istrazivanja |
| `resources/VREME ZA DEPLOY.md` | Vremenska evidencija setup-a |
| `CLAUDE.md` | Code-level documentation za Claude Code |

### Memory (`~/.claude/projects/.../memory/`)

- `MEMORY.md` — index
- `feedback_command_formatting.md` — single-line commands
- `project_gcp_setup.md` — GCP nalog (faculty email), VM, bucket
- `project_vm_lifecycle.md` — stop/start procedure, IP update locations

---

## 2. ~~SLEDECE: AWS upgrade m5.large → m6i.large~~ ✅ ZAVRSENO 2026-05-23

**Rezultat**: Sysbench 666 → 1109 events/sec (+66%), mixed throughput 21.4 → 27.1 RPS (+27%), error rate 0.117% → 0%, io_native vise ne hit-uje 10s timeout. Detalji: `resources/Nalazi i dnevnik.md` unos 2026-05-23. Novi IP: `18.185.48.126`.

Sledeci aktivan TODO: **Sekcija 3 (Hetzner)** ili **Sekcija 4 (CaaS deployments)**.

<details>
<summary>Originalne komande (za referencu)</summary>

**Zasto**: m5.large koristi Intel Skylake 2017 (Xeon 8175M @ 2.5 GHz), dok GCP n2/Azure D2s_v5 koriste Ice Lake 2021. To je 1.75x manje CPU performance na istom tier label-u. m6i.large koristi Ice Lake (Xeon 8375C @ 2.9 GHz) — direct apples-to-apples sa Azure/GCP.

**Cena**: +$25/mes (m5.large ~$70 → m6i.large ~$95).

**Vreme**: ~10 min (stop, resize, start, verify, redeploy + smoke test).

### Komande (kopiraj redom)

#### Step 1: Stop instance
```
aws ec2 stop-instances --profile benchmark --region eu-central-1 --instance-ids i-02e92ffeabd7956cf
```

#### Step 2: Cekaj da bude stopped
```
aws ec2 wait instance-stopped --profile benchmark --region eu-central-1 --instance-ids i-02e92ffeabd7956cf
```

#### Step 3: Promeni tip
```
aws ec2 modify-instance-attribute --profile benchmark --region eu-central-1 --instance-id i-02e92ffeabd7956cf --instance-type "{\"Value\":\"m6i.large\"}"
```

#### Step 4: Start
```
aws ec2 start-instances --profile benchmark --region eu-central-1 --instance-ids i-02e92ffeabd7956cf
```

#### Step 5: Cekaj running + procitaj novi IP
```
aws ec2 wait instance-running --profile benchmark --region eu-central-1 --instance-ids i-02e92ffeabd7956cf
```
```
aws ec2 describe-instances --profile benchmark --region eu-central-1 --instance-ids i-02e92ffeabd7956cf --query "Reservations[0].Instances[0].{IP:PublicIpAddress,Type:InstanceType,State:State.Name}" --output table
```

#### Step 6: Update lokalni env fajl
Edituj `k6/env/aws.bat`, zameni stari IP (`35.158.173.227`) sa novim koji ti vrati Step 5.

#### Step 7: Update GitHub secret
```
gh secret set AWS_HOST --body "<NOVI-IP>" --repo Novke/cloud-provider-benchmark
```

#### Step 8: Smoke test (sacekaj ~60s posle start-a za docker compose da se podigne)
```
curl -sf --max-time 15 http://<NOVI-IP>:8000/health
```
```
curl -sf --max-time 15 http://<NOVI-IP>:8000/io-heavy/native
```

Ako health ne vrati ok za 60s, SSH na VM:
```
ssh -i ~/.ssh/aws_benchmark -o StrictHostKeyChecking=no ubuntu@<NOVI-IP> "sudo docker compose -f /srv/backend/cloud-benchmark/docker-compose.yml ps && sudo docker compose -f /srv/backend/cloud-benchmark/docker-compose.yml up -d"
```

#### Step 9: Verifikuj CPU upgrade (sanity check)
```
ssh -i ~/.ssh/aws_benchmark -o StrictHostKeyChecking=no ubuntu@<NOVI-IP> "cat /proc/cpuinfo | grep 'model name' | head -1 && sysbench cpu --cpu-max-prime=20000 --threads=2 --time=15 run 2>&1 | grep 'events per second'"
```

Treba da vidis: **`Intel(R) Xeon(R) Platinum 8375C`** (ili slican Ice Lake) i **~1200 events/sec** (umesto 666 koliko je m5 davao).

#### Step 10: Re-run mixed benchmark
```
k6\scripts\aws\aws-single.bat mixed
```

Sa rezultatima, dodaj unos u `resources/Nalazi i dnevnik.md`.

#### Step 11: Updateuj `resources/Specifikacije infrastrukture.md`
Promeni AWS red sa `m5.large` (Skylake) na `m6i.large` (Ice Lake), updateuj IP, sysbench cifre.

### Alternativa: Opcija C (drzati i m5 i m6i paralelno)

Ako hoces "tier-as-marketed vs generation-controlled" dvostruku tabelu za rad, **NE radi gornju resize** — umesto toga **kreiraj NOVU instance m6i.large** pored postojece m5.large. Trosak: dodatnih ~$95/mes ali dobijes 2 paralelne AWS rezultate za jaci paper finding.

Komande za novu instance: izlazi van scope-a ovog SPEC-a, pitaj Claude u fresh sesiji da generise.

</details>

---

## 3. TODO: Hetzner IaaS deploy

**Stanje**: pauzirano (Falkenstein nedostupan zbog visoke potraznje). Sve k6 scripte, deploy workflow, naming convention `HETZNER_BENCHMARK_*` su vec napravljeni i cekaju.

**Akcija**: pratiti `resources/Hetzner deploy steps.md` (svih 9 koraka, od kreiranja CCX13 do prvog k6 runa).

**Pre nego sto pocnes**: proveri dostupnost Falkenstein CCX13. Ako i dalje nedostupan: **prebaci se na `nbg1` (Nuremberg)** — takodje Nemacka, ~250km od Frankfurta, najveci Hetzner DC, gotovo uvek dostupan.

---

## 4. CaaS deployments (3 — bez Hetzner-a)

**Stanje 2026-05-24 — sva 3 CaaS-a deployovana**:
- ✅ **GCP Cloud Run** — `https://benchmark-caas-839326220134.europe-west3.run.app` (2 vCPU / 8 GiB, min=0, max=5)
- ✅ **AWS App Runner** — `https://ctmjikarp5.eu-central-1.awsapprunner.com` (2 vCPU / 6 GB, min=1, max=5 — App Runner nema native scale-to-zero)
- ✅ **Azure Container Apps** — `https://benchmark-caas.jollysky-1427eea1.germanywestcentral.azurecontainerapps.io` (2 vCPU / 4 GiB, min=0, max=5)

**Sva 3 CaaS-a koriste identican image digest** `sha256:bc766fb264758217145fd56ee4b68d0db5d7b09638912af28ed9ca4b4debe5b` — built once lokalno (neutral Docker Desktop), pushed u 3 native registry-ja (GCR / ECR / ACR).

**Smoke test prve cifre (single warm call)**:
| Endpoint | Cloud Run | App Runner | Container Apps |
|---|---|---|---|
| `/io-heavy/native` write | 568ms (GCS) | 253ms (S3) | 290ms (Azure Blob) |
| `/io-heavy/neutral` (R2) | 1273ms | 876ms | 877ms |

App Runner dominantan u storage call-ovima — konzistentno sa IaaS findng-om #1 da AWS network ka R2 i intra-AWS S3 je najbrzi. Kompletna analiza ce uslediti posle systematic k6 benchmark-a.

**Metodoloska odluka**: image se gradi **jednom u neutralnom okruzenju** (lokalni Docker Desktop) → push istog digest-a u sva 3 native registry-ja. Asimetrija u sizing-u (Cloud Run 8 GiB, App Runner 6 GB, Container Apps 4 GiB) je odluka Opcije A — drzati 2 vCPU svuda, koristiti max RAM po provajderu. Detalji u `resources/CaaS deployments.md`.

Sledeci aktivan TODO: **Sekcija 3 (Hetzner)**, **Sekcija 5 (FaaS)**, ili pisanje k6 CaaS scripts-a za systematic benchmark.

Hetzner nema commercial CaaS — out of scope, dokumentovano kao limitation u `Specifikacije infrastrukture.md`.

### GCP — Cloud Run

- **Region**: `europe-west3` (Frankfurt)
- **Image source**: Container Registry / Artifact Registry (`gcr.io/cloud-benchmark-493210/benchmark-api`)
- **Build & push**: 
  ```
  gcloud auth configure-docker europe-west3-docker.pkg.dev
  docker build -t europe-west3-docker.pkg.dev/cloud-benchmark-493210/benchmark/api:latest .
  docker push europe-west3-docker.pkg.dev/cloud-benchmark-493210/benchmark/api:latest
  ```
- **Deploy**:
  ```
  gcloud run deploy benchmark-caas --image=europe-west3-docker.pkg.dev/cloud-benchmark-493210/benchmark/api:latest --region=europe-west3 --port=8000 --min-instances=0 --max-instances=10 --cpu=2 --memory=8Gi --service-account=839326220134-compute@developer.gserviceaccount.com --allow-unauthenticated --set-env-vars="STORAGE_BACKEND_NATIVE=gcs,GCS_BUCKET_NAME=cloud-benchmark-native-gcp,..."
  ```
- **min-instances=0** je kljucno — daje cold start ponasanje koje merimo
- **Cold start detection**: nas `/health` endpoint vraca `cold_start: true/false` flag

### AWS — App Runner ili ECS Fargate

**App Runner** je laksi (jedna komanda, slicno Cloud Run-u), ali manje fleksibilan.
**ECS Fargate** je pravi enterprise CaaS, vise koraka ali daje vise kontrolu.

Predlog: **App Runner** za prvi go (mozes uvek migrirati na Fargate kasnije).

- **Region**: `eu-central-1`
- **Image source**: ECR (`<account>.dkr.ecr.eu-central-1.amazonaws.com/benchmark-api:latest`)
- **Auth za S3**: App Runner instance role
- Setup detalji TBD — pitaj Claude da generise korake

### Azure — Container Apps

- **Region**: `germanywestcentral`
- **Image source**: ACR (`cloudbenchacr.azurecr.io/benchmark-api:latest`)
- **Auth za Blob**: User-assigned managed identity
- **min-replicas=0** za cold start ponasanje

Detalji TBD.

### Sta treba pre svakog CaaS deploy-a

1. **Docker image push u provider container registry** (GCR/ECR/ACR)
2. **CaaS service create** sa `min-instances=0` za cold start mjerenje
3. **Auth pattern**: managed identity ili service account za pristup nativnom storage-u
4. **Endpoint URL** dobijes nazad iz CaaS deploy komande
5. **`k6/env/<provider>-caas.bat`** — novi env fajl sa CaaS URL-om
6. **k6 scripts** — nova `k6/scripts/<provider>-caas/` folder ili reuse postojecih sa parametrom
7. **Update `Specifikacije infrastrukture.md`** sa CaaS detaljima

---

## 5. FaaS deployments (3 — bez Hetzner-a)

**Stanje 2026-05-25 — sva 3 FaaS-a deployovana**:
- ✅ **GCP Cloud Functions Gen 2** — `https://europe-west3-cloud-benchmark-493210.cloudfunctions.net/benchmark-faas` (2 vCPU / 4 GiB, min=0, max=5, concurrency=1)
- ✅ **AWS Lambda + API Gateway HTTP API** — `https://dhaisequ9l.execute-api.eu-central-1.amazonaws.com` (container image, 3008 MB ~1.7 vCPU, scale-to-zero)
- ✅ **Azure Functions Consumption Y1** — `https://benchmark-faas.azurewebsites.net` (Python 3.11, 1.5 GB / 1 vCPU hard cap, scale-to-zero)

**Metodologija**: source-deploy + provajder-specifican thin wrapper koji mount-uje istu FastAPI ASGI aplikaciju (`app/main.py`). Detalji u `resources/FaaS deployments.md`.

**Image neutrality kompromis**: pokusana je "build once, deploy svuda" kao kod CaaS-a — blokirano jer **Azure Functions Consumption Y1 ne podrzava custom containers** (samo Premium/Flex Consumption, koji su drugi pricing tier). Stoga: source deploy uniformno, sa identicnim `app/` paketom + provajder-specifican adapter.

**Wrapper-i**:
- GCP CF Gen 2: `functions_framework.http` handler + Starlette `TestClient` koji sinhrono invocira ASGI app (a2wsgi adapter visi na lifespan deadlock-u)
- AWS Lambda: Mangum (ASGI→Lambda payload bridge), Container Image sa `public.ecr.aws/lambda/python:3.11` base
- Azure Functions: `azure.functions.AsgiFunctionApp` (v2 programming model + EnableWorkerIndexing), `routePrefix=""` u host.json (workaround za AspNetCore.Routing bug sa `api//{*route}`)

**Sizing asimetrija (Opcija A4 — max po FaaS tier-u svakog provajdera)**:

| Sloj | GCP | AWS | Azure | Span |
|---|---|---|---|---|
| IaaS | 2 vCPU / 8 GB | 2 vCPU / 8 GB | 2 vCPU / 8 GiB | 1× |
| CaaS | 2 vCPU / 8 GiB | 2 vCPU / 6 GB | 2 vCPU / 4 GiB | ~2× |
| FaaS | 2 vCPU / 4 GiB | 1.7 vCPU / 3008 MB | 1 vCPU / 1.5 GB | **~3×** |

Asimetrija raste sa serverless dubinom — dokumentovano kao novi paper finding.

**Smoke test prve cifre (single warm call)**:
| Endpoint | CF Gen 2 | Lambda (APIGW) | Azure Y1 |
|---|---|---|---|
| `/quick?hold=0` | 470 ms | **386 ms** | 500 ms |
| `/compute` (10K) | 400 ms | 408 ms | 505 ms |
| `/io-heavy/native` (1KB) | 662 ms (GCS) | **355 ms** (S3) | 2841 ms (Blob, first-call MI auth) |
| `/io-heavy/neutral` (R2, 1KB) | 1575 ms | **778 ms** | 1264 ms |

Lambda dominantna u storage. Azure native ima first-call MI auth penalty (~2.8s) — isti pattern kao CaaS Container Apps, ne pripada container cold start-u nego SDK token acquisition-u.

**Friction nalazi (kratko)**:
- AWS Lambda Function URL vraca 403 i pored ispravne resource policy → pivot na API Gateway HTTP API (radi out-of-the-box)
- Azure Functions Compress-Archive PowerShell-a stavlja backslash-eve u zip filename-e (ne path separator) → ModuleNotFoundError; resenje: zip kroz Python `zipfile` modul
- `AsgiFunctionApp` u kombinaciji sa default `routePrefix=api` daje nelegalan template `api//{*route}` → host failure; resenje: `routePrefix=""` u host.json (endpoint bez `/api/` prefix-a)
- Auto-classifier blokirao ECR token transit + Azure RBAC grant-ove + Key Vault-ref app settings → korisnik manualno pokrenuo (ista pattern kao CaaS deploy)

Detalji svake friction tacke i kompletne deploy komande: `resources/FaaS deployments.md`.

Sledeci aktivan TODO: **Sekcija 3 (Hetzner)**, **Sekcija 6 (Methodology Phase 1 — sequential randomized N=10)** ili pisanje k6 FaaS scripts-a za systematic benchmark.

Hetzner nema FaaS — out of scope (vidi `Specifikacije infrastrukture.md`).

---

## 6. Methodology Phase 1 — sequential randomized N=10 wrapper ✅ SKRIPTA NAPRAVLJENA

**Stanje 2026-05-25**: Python orchestrator (`scripts/orchestrate.py`) napravljen, dry-run testiran.

- ✅ Wrapper Python skripta — `scripts/orchestrate.py` (sequential randomized round-robin)
- ✅ Warm-up run koji se odbacuje (results dir tagged `_warmup`)
- ✅ N=10 konfigurabilno preko YAML config-a + CLI override
- ✅ Output u standardnu `k6/results/<provider>/<arch>/<scenario>/<sessionTs>__s<session>_n<iter>/` putanju
- ✅ Per-session log JSON u `k6/results/_sessions/<sessionTs>__<session>.json` — audit trail
- ✅ Pre-run health check sa retry logikom
- ✅ Random seed override-iv preko `--seed` za reproducibility
- ✅ `scripts/orchestrate.config.example.yaml` sa svim trenutnim endpoint-ima

Run examples:
```
# Lokalno, jedna manuelna sesija
python scripts/orchestrate.py --config scripts/orchestrate.config.yaml --session-id morning --iterations 10 --warmup 1

# Dry-run (ispisi komande bez izvrsavanja)
python scripts/orchestrate.py --config scripts/orchestrate.config.yaml --dry-run

# Reduced za testing
python scripts/orchestrate.py --config scripts/orchestrate.config.example.yaml --session-id test --iterations 2 --warmup 0 --seed 42
```

Sledeci korak: pokretanje stvarne N=10 sesije, ili prelazak na Phase 2 (VPS automation).

---

## 7. Methodology Phase 2 — cloud test client + DuckDB ✅ SKRIPTE I TEMPLATES SPREMNI

**Stanje 2026-05-25**: aggregator + systemd templates napravljeni i testirani.

- ✅ DuckDB aggregation layer — `scripts/aggregate.py` (rekurzivno cita `k6/results/**/analysis.json`, idempotent upsert u `benchmark.duckdb`)
- ✅ systemd timer + service templates — `deploy/systemd/`:
  - `benchmark@.service` (instantiated, `%i`=session-id)
  - `benchmark-morning.timer` (09:00)
  - `benchmark-afternoon.timer` (15:00)
  - `benchmark-night.timer` (22:00)
- ✅ Deploy install vodic — `deploy/systemd/README.md` (Ubuntu/Debian step-by-step)
- ✅ Auto-derivane stratifikacione kolone u DuckDB: `time_of_day_slot`, `day_of_week`, `is_weekend`
- ✅ Phase 1 + Phase 2 cleanly povezane: `benchmark@.service` ExecStartPost pokrece aggregator automatski
- ✅ Setup Linux VPS — **DigitalOcean Frankfurt** (`104.248.251.238`, s-1vcpu-1gb) deployed 2026-05-29 (vidi Sekciju 10 + `resources/Specifikacije infrastrukture.md`)
- 🔜 Cost cap setup (billing alerts kod sva 3 cloud provajdera) — safety net, korisnik postavlja preko portala (trosak ~$150 omeđen)

Verifikacija na postojecim podacima:
```
$ python scripts/aggregate.py
Scanning 17 analysis.json files under k6\results
Inserted/replaced: 17 | Skipped: 0
Coverage:
  aws/faas/cold-start: N=1
  aws/iaas/mixed: N=5
  azure/iaas/mixed: N=4
  gcp/iaas/mixed: N=4
  ...
```

---

## 8. Statistical Analysis & Write-up ✅ SKRIPTA NAPRAVLJENA

**Stanje 2026-05-25**: `scripts/analyze.py` (Python skripta sa `# %%` cell markerima — radi i kao Jupyter notebook kroz jupytext/VSCode) napravljena i testirana.

- ✅ Coverage matrix po (provider, arch, scenario)
- ✅ Summary tabela sa medianom + p95 + p99 + bootstrap 95% CI
- ✅ Mann-Whitney U test pair-by-pair (non-parametric, robust na heavy-tail latency)
- ✅ Kruskal-Wallis za 4-way poredjenje
- ✅ Box plots, timeline plots, heatmaps (time-of-day × provider)
- ✅ LaTeX export za rad
- ✅ Auto-output u `k6/results/_analysis/` (CSV + PNG + .tex)
- 🔜 Write-up u rad — koristiti `resources/Struktura naucnog rada.md` kao skeleton (posle prikupljanja N>=10 po cell-u)

Verifikacija na postojecim podacima (N=4-5 po IaaS mixed cell-u):
```
Mann-Whitney AWS vs Azure: p=0.0159  (significant — AWS sistematski sporiji)
Mann-Whitney AWS vs GCP:   p=0.0159  (significant)
Mann-Whitney Azure vs GCP: p=0.6857  (NOT significant — Azure ~ GCP)
Kruskal-Wallis 4-way:      p=0.0129  (significant difference somewhere)
```

Postojeci nalaz #1 (AWS spor) je sad **statisticki potvrdjen** vec sa malim sample-om.

Run:
```
pip install -r scripts/requirements.txt
python scripts/aggregate.py
python scripts/analyze.py
```

Output u `k6/results/_analysis/`: `summary.csv`, `mannwhitney_pairs.csv`, `kruskal_wallis.csv`, `summary.tex`, plus boxplot/timeline/heatmap PNG-ovi po (arch, scenario).

---

## 10. PRODUKCIJSKA KAMPANJA — LIVE (start 2026-06-03) 🟢

Posle validacione faze (svi pipeline/storage/cold-start fixovi rešeni + verifikovani — vidi `resources/Nalazi i dnevnik.md` #11/#12/#13), prava merna kampanja je **zakazana i radi automatski**.

**Validaciona faza — rešeni problemi:**
- ✅ `8a7837b` orchestrate exit-code (partial fail više ne maskira uspeh / ne preskače aggregate)
- ✅ `b0d1471` storage client-reuse (redeploy ×10; IaaS verifikacija: Azure native @50VU 11354→129ms 88×, AWS S3 10656ms+23%err→68ms+0err 156×) — storage confound eliminisan
- ✅ `3d62ec0` cold-start health-skip (sad hvata prave cold start-ove: Lambda 1.6s … Azure Container Apps 26.5s)
- ✅ `31577cc` orchestrate sweep support (parametrizovani scenariji) + `orchestrate.config.sweep.example.yaml`

**Kampanja (dizajn — finalan, vidi `Metodologija testiranja.md` §4):**
- **2 slota/dan** (`day` 09:00 + `night` 21:00 CEST) × **14 dana = N=28/cell**. (2 ne 3 slota: sesija ~8h, 3×8h ne staje u 24h.)
- 10 targeta × 5 scenarija (low-traffic, heavy-compute, io-native, io-neutral, cold-start), io=1KB, compute=100K.
- VPS systemd: `benchmark-day.timer`@09:00 + `benchmark-night.timer`@21:00 → `benchmark@.service` (campaign config = validirani sanity; ExecStartPost aggregate).
- ✅ `1b9387d` systemd `TimeoutStartSec` 3h→10h fix — oneshot servis je ubijao ~8h sesiju na 3h; prva 2 slota (Jun 3) izgubljena. Detalji: `Nalazi i dnevnik.md` #14.
- **Efektivni start Jun 4 09:00** (Jun 3 slotovi pali na timeout) → kraj ~Jun 18.

**Ostaje (post-kampanja, nije hitno):**
- 🔜 Sweep pipeline finiš: `aggregate.py` kolone (io_bytes/compute_iterations/max_vus) + `analyze.py` scaling plotovi + `loadcurve`/`coldstart-window` config-ovi. Sweepovi (Eksp 2-5) se pokreću POSLE 14-dnevne kampanje (dedicated batch).
- 🔜 Write-up (`resources/Struktura naucnog rada.md`) posle prikupljanja N=28.

**Monitoring** (`Metodologija testiranja.md` §11): `systemctl list-timers benchmark*`, `journalctl -u 'benchmark@*'`, dnevni DuckDB N-check. Sync baze: `scp ...:/opt/cloud-provider-benchmark/benchmark.duckdb .`

---

## 9. Kako da nastavis fresh

1. **Procitaj ovaj SPEC.md prvi** (cita se za ~5 min) — **Sekcija 10 je trenutno stanje (kampanja LIVE)**
2. Otvori `resources/Nalazi i dnevnik.md` — najnoviji unos je trenutno stanje
3. Identificuj na koji TODO si stao (Section 2-8 above)
4. Pitaj Claude (ili sam pokreni) i kreni dalje

### Komande za "sanity check sve radi"

```
curl -sf http://35.246.182.190:8000/health
curl -sf http://35.158.173.227:8000/health    # ili novi IP ako si vec upgrade-ovao
curl -sf http://51.116.237.102:8000/health
```

```
gcloud compute instances describe benchmark-vm --zone=europe-west3-a --format="value(status,machineType.basename())"
aws ec2 describe-instances --profile benchmark --region eu-central-1 --filters "Name=instance-state-name,Values=running" --query "Reservations[].Instances[].{ID:InstanceId,Type:InstanceType,IP:PublicIpAddress}" --output table
az vm show --resource-group benchmark-rg --name benchmark-vm --show-details --query "{type:hardwareProfile.vmSize,state:powerState,ip:publicIps}" --output tsv
```

---

## 10. Cost estimate (do kraja projekta)

| Kategorija | Trenutno | Posle AWS upgrade | Posle CaaS+FaaS | Posle 14-day benchmark |
|---|---|---|---|---|
| GCP VM | ~$70/mes | ~$70/mes | ~$70/mes | ~$32 (14 dana) |
| AWS VM | ~$70/mes | ~$95/mes | ~$95/mes | ~$45 (14 dana) |
| Azure VM | ~$90/mes | ~$90/mes | ~$90/mes | ~$42 (14 dana) |
| Hetzner VM | $0 | $0 | $0 | ~$15 (14 dana) |
| CaaS (scale-to-zero) | $0 | $0 | ~$5-10 | ~$5 |
| FaaS (per-invocation) | $0 | $0 | ~$5 | ~$5 |
| Storage (4 buckets) | ~$1 | ~$1 | ~$1 | ~$1 |
| **Mesecno running** | ~$230 | ~$255 | ~$265 | — |
| **14-day benchmark total** | — | — | — | **~$145** |

Realisticna projekcija ukupno (~30 dana running + 14 day intensive benchmark): **~$300-400**.

PhD budget-prihvatljivo.
