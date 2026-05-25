# systemd timer setup — stratified time-slot benchmark

Phase 2 deployment artifakti za pokretanje `scripts/orchestrate.py` 3 puta dnevno
sa nezavisne Linux VPS instance (neutralan test client, eliminise home-ISP varijancu —
vidi `resources/Methodology improvements TODO.md` Phase 2 sekciju za razloge).

## Sta su ovi fajlovi

| Fajl | Uloga |
|---|---|
| `benchmark@.service` | instantiated systemd service — `%i` postaje session-id (morning/afternoon/night) |
| `benchmark-morning.timer` | OnCalendar 09:00 -> `benchmark@morning.service` |
| `benchmark-afternoon.timer` | OnCalendar 15:00 -> `benchmark@afternoon.service` |
| `benchmark-night.timer` | OnCalendar 22:00 -> `benchmark@night.service` |

Service runs `orchestrate.py` jednom (1 sesija = jedan kompletan randomized round-robin
kroz sve targets × scenarios × N iteracija) pa odmah pokrece `aggregate.py` da
ubaci nove rezultate u DuckDB. Sledeci timer slot pokrece sledecu sesiju.

## Install na VPS-u (Ubuntu/Debian)

```bash
# 1. Code i Python deps
sudo useradd -r -m -s /usr/sbin/nologin benchmark
sudo mkdir -p /opt/cloud-provider-benchmark
sudo chown benchmark:benchmark /opt/cloud-provider-benchmark
sudo -u benchmark git clone https://github.com/Novke/cloud-provider-benchmark /opt/cloud-provider-benchmark
sudo apt install -y python3-pip
sudo -u benchmark python3 -m pip install --user -r /opt/cloud-provider-benchmark/scripts/requirements.txt

# 2. k6 binary
curl -fsSL https://dl.k6.io/key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/k6-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt update && sudo apt install -y k6

# 3. Config (kopirati sa primer-a, prilagoditi URL-ove)
sudo -u benchmark cp /opt/cloud-provider-benchmark/scripts/orchestrate.config.example.yaml /opt/cloud-provider-benchmark/scripts/orchestrate.config.yaml
sudo -u benchmark vi /opt/cloud-provider-benchmark/scripts/orchestrate.config.yaml

# 4. Install systemd units
sudo cp /opt/cloud-provider-benchmark/deploy/systemd/benchmark@.service /etc/systemd/system/
sudo cp /opt/cloud-provider-benchmark/deploy/systemd/benchmark-*.timer /etc/systemd/system/
sudo systemctl daemon-reload

# 5. Enable + start timers
sudo systemctl enable --now benchmark-morning.timer benchmark-afternoon.timer benchmark-night.timer

# 6. Verify
systemctl list-timers benchmark-*           # show next firing times
journalctl -u benchmark@morning.service -f  # follow active session log
```

## Manuelno pokretanje (debug)

```bash
sudo systemctl start benchmark@morning.service   # ne ceka timer, pokrece odmah
journalctl -u benchmark@morning.service -n 200   # poslednjih 200 linija
```

## Cost cap

Pre nego sto enable-uje timer-e, postavi billing alert kod svakog provajdera:

- GCP: Billing -> Budgets & alerts -> Create budget, $50/mes po projektu, alert at 50%/90%/100%
- AWS: Billing -> Budgets -> Create budget, $50/mes, alert at 80%
- Azure: Cost Management -> Budgets -> Create, $50/mes, alert at 80%
- Cloudflare R2: zero egress fee, ali pazi na storage (cap $1)

Estimated cost za 14 dana × 3 sesije/dan: ~$50-120 ukupno (vidi `Methodology improvements TODO.md`).

## Sta da uradis posle benchmark-a

Posle 7-14 dana:

```bash
# 1. Sinhronizuj DuckDB lokalno
scp benchmark@vps:/opt/cloud-provider-benchmark/benchmark.duckdb .

# 2. Otvori Jupyter notebook
jupyter notebook scripts/analyze.ipynb

# 3. Stop timer-i (vise ne treba sakupljati)
ssh benchmark@vps "sudo systemctl disable --now benchmark-{morning,afternoon,night}.timer"
```
