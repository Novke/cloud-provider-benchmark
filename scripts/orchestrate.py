"""Sequential randomized round-robin benchmark orchestrator.

Phase 1 + Phase 2 deliverable. Pokrece k6 scenarije preko nz provajdera x arhitektura x
scenarija u sequential redu sa randomizovanim per-session redosledom. Eliminise
first-mover bias, odbacuje warm-up, tagira mjerenja.

Output: standardni k6 layout `k6/results/<provider>/<arch>/<scenario>/<timestamp>__s<session>_n<iter>/`
gde je session sesijski ID i iter iteracijski broj (0=warm-up, 1..N=mjerenje).

Vazno za cold-start: orchestrator pokrece sve `cold-start` scenarije PRVI u sesiji
(pre warmup-a i pre ostalih scenarija) jer inter-session gap od 6-11h izmedju
stratified slot-ova (09/15/22) garantovano scale-uje FaaS instance i CaaS-min=0
instance na zero. Time je prvi cold-start poziv sesije pravo mjerenje
scale-from-zero latencije. Ako bismo cold-start ostavili u randomized fazi,
prethodni scenariji bi vec zagrejali instance i merenje bi bilo beskorisno.

Usage:
    python scripts/orchestrate.py --config scripts/orchestrate.config.yaml
    python scripts/orchestrate.py --config <cfg> --session-id morning --warmup 1 --iterations 10
    python scripts/orchestrate.py --config <cfg> --dry-run

Konfiguracioni fajl (YAML):

    iterations: 10               # N mjerenja per cell (provider x arch x scenario)
    warmup_runs: 1               # broj warm-up runova koji se odbacuju
    inter_run_sleep_sec: 5       # pauza izmedju runova (post-curl, da se reset-uje)
    health_check_timeout_sec: 30
    health_check_retries: 2
    targets:
      - provider: gcp
        arch: iaas
        url: http://35.246.182.190:8000
        region: europe-west3
        profile: cloud
        scenarios: [mixed, low-traffic, heavy-compute, io-native, io-neutral]
      - provider: gcp
        arch: faas
        url: https://europe-west3-cloud-benchmark-493210.cloudfunctions.net/benchmark-faas
        region: europe-west3
        profile: faas
        scenarios: [cold-start, low-traffic, heavy-compute, io-native, io-neutral]
      # ... rest

Phase 2 dodatak: kad se ovo pokrece kroz systemd timer (vidi deploy/systemd/), session-id
postaje SLOT_NAME (morning/afternoon/night) iz timer-a, sto u kombinaciji sa timestamp-om
omogucava stratified time-of-day analizu u Phase 3 (vidi scripts/analyze.ipynb).
"""
from __future__ import annotations

import argparse
import itertools
import json
import logging
import os
import random
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ImportError:
    sys.stderr.write("ERROR: PyYAML not installed. Run: pip install PyYAML\n")
    sys.exit(1)


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger("orchestrate")


@dataclass(frozen=True)
class ScenarioSpec:
    """Jedan scenario unos iz config-a — ime + opcioni parametarski sweep.

    Config moze dati scenario kao obican string (`low-traffic`) ili kao dict sa
    sweep-om:  `{name: io-native, sweep: {IO_BYTES: [1024, 10240, 102400]}}`.
    Sweep se ekspanduje u 1 run po vrednosti (cartesian product ako vise param-a).
    `sweep` je tuple parova (param, tuple_vrednosti) da bi dataclass ostao hashable.
    """

    name: str
    sweep: tuple[tuple[str, tuple], ...] = ()


@dataclass(frozen=True)
class Target:
    """Jedan (provider, arch, url) target sa listom scenarija."""

    provider: str
    arch: str
    url: str
    region: str
    profile: str
    scenarios: tuple[ScenarioSpec, ...]


@dataclass(frozen=True)
class RunSpec:
    """Jedan konkretan benchmark run (Target × scenario × iteration [× sweep])."""

    target: Target
    scenario: str
    iteration: int  # 0 = warmup, 1..N = mjerenje
    session_id: str
    session_timestamp: str  # session-level timestamp za output path
    # Sweep parametri za ovaj run (npr. (("IO_BYTES","1048576"),)) — prazno za obicne.
    env_overrides: tuple[tuple[str, str], ...] = ()
    # Filesystem-safe tag sweep-a za results-dir (npr. "io_bytes-1048576") — prazno za obicne.
    sweep_tag: str = ""

    @property
    def is_warmup(self) -> bool:
        return self.iteration == 0

    @property
    def results_dir(self) -> Path:
        tag = f"{self.session_timestamp}__s{self.session_id}_n{self.iteration:02d}"
        if self.is_warmup:
            tag = f"{self.session_timestamp}__s{self.session_id}_warmup"
        base = Path("k6") / "results" / self.target.provider / self.target.arch / self.scenario
        # Sweep run-ovi dobijaju zaseban pod-folder po parametru da se ne prepisuju.
        if self.sweep_tag:
            base = base / self.sweep_tag
        return base / tag


@dataclass
class Config:
    iterations: int = 10
    warmup_runs: int = 1
    inter_run_sleep_sec: float = 5.0
    health_check_timeout_sec: int = 30
    health_check_retries: int = 2
    targets: list[Target] = field(default_factory=list)


def _parse_scenario(entry) -> ScenarioSpec:
    """Parsira jedan scenario unos: string ili {name, sweep} dict."""
    if isinstance(entry, str):
        return ScenarioSpec(name=entry)
    if isinstance(entry, dict):
        name = entry["name"]
        sweep_raw = entry.get("sweep", {}) or {}
        sweep = tuple((str(k), tuple(v)) for k, v in sweep_raw.items())
        return ScenarioSpec(name=name, sweep=sweep)
    raise ValueError(f"Neispravan scenario unos: {entry!r} (mora biti string ili {{name, sweep}})")


def expand_sweep(sweep: tuple[tuple[str, tuple], ...]) -> list[tuple[tuple[tuple[str, str], ...], str]]:
    """Ekspanduje sweep u listu (env_overrides, sweep_tag) parova.

    Bez sweep-a → [((), "")] (jedan run, prazni override). Sa sweep-om → cartesian
    product svih param vrednosti. env_overrides je tuple (PARAM, str(value)) parova;
    sweep_tag je filesystem-safe (npr. "io_bytes-1048576").
    """
    if not sweep:
        return [((), "")]
    params = [p for p, _ in sweep]
    value_lists = [vals for _, vals in sweep]
    out = []
    for combo in itertools.product(*value_lists):
        env = tuple((p, str(v)) for p, v in zip(params, combo))
        tag = "_".join(f"{p.lower()}-{v}" for p, v in zip(params, combo))
        out.append((env, tag))
    return out


def parse_config(path: Path) -> Config:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    targets = []
    for t in raw.get("targets", []):
        targets.append(
            Target(
                provider=t["provider"],
                arch=t["arch"],
                url=t["url"],
                region=t["region"],
                profile=t["profile"],
                scenarios=tuple(_parse_scenario(s) for s in t["scenarios"]),
            )
        )
    return Config(
        iterations=raw.get("iterations", 10),
        warmup_runs=raw.get("warmup_runs", 1),
        inter_run_sleep_sec=raw.get("inter_run_sleep_sec", 5.0),
        health_check_timeout_sec=raw.get("health_check_timeout_sec", 30),
        health_check_retries=raw.get("health_check_retries", 2),
        targets=targets,
    )


def health_check(url: str, timeout_sec: int, retries: int) -> bool:
    """Vraca True ako /health odgovara 200 unutar timeout-a + retries puta."""
    health_url = f"{url.rstrip('/')}/health"
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(
                ["curl", "-sf", "--max-time", str(timeout_sec), health_url],
                capture_output=True,
                text=True,
                timeout=timeout_sec + 5,
            )
            if result.returncode == 0:
                return True
        except subprocess.TimeoutExpired:
            pass
        if attempt < retries:
            log.warning("Health check %s failed, retry %d/%d", health_url, attempt + 1, retries)
            time.sleep(3)
    return False


def build_run_specs(cfg: Config, session_id: str, rng: random.Random) -> list[RunSpec]:
    """
    Konstruise listu runova za jednu sesiju.

    Strategija randomizacije (3 faze):
      Phase 0 — cold-start scenariji PRVI, jedan po target-u, NEMA warmup-a.
                Razlog: cold-start meri prvu invokaciju nove instance. Inter-session
                gap (6-11h izmedju stratified slot-ova) je >> warm-window svih FaaS-a
                (5-15 min) i CaaS-ova sa min=0, pa je instanca garantovano hladna.
                Warmup pre cold-start-a bi defeat-ovao smisao. Redosled medju
                target-ima je shuffle-ovan da nijedan provajder nije konzistentno prvi.

      Phase 1 — warmup runovi za sve non-cold-start cell-e (jedan po Target × scenario)
                redom kako su definisani. Po convention, warmup je marker da se DNS,
                connection pool i JIT zagreju za sledece mjerno fakticko mjerenje.

      Phase 2 — mjerni runovi za sve non-cold-start (Target × scenario × iteration)
                kombinacije, shuffle-ovani kao jedna lista. Eliminise first-mover bias
                tako sto provajderi i scenariji se prepliću random redom.
    """
    session_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")

    cold_starts: list[RunSpec] = []   # Phase 0
    warmups: list[RunSpec] = []        # Phase 1
    measurements: list[RunSpec] = []    # Phase 2

    for target in cfg.targets:
        for sspec in target.scenarios:
            # Svaki sweep unos se ekspanduje u 1+ (env_overrides, tag) — bez sweep-a
            # je [((), "")] pa je ponasanje identicno ranijem (glavna kampanja netaknuta).
            for env_overrides, sweep_tag in expand_sweep(sspec.sweep):
                if sspec.name == "cold-start":
                    # Phase 0 — cold-start preko target-a. Bez warmup-a (cilj je hladno).
                    # Iteration broj je samo 1..N (svaka sesija po jednu mjerenje na cold instanci;
                    # za vise cold mjerenja u kratkom periodu treba namerno cekanje 5-15 min,
                    # sto se postize dedicated full-mode runom van orchestrator-a).
                    for n in range(1, cfg.iterations + 1):
                        cold_starts.append(
                            RunSpec(
                                target=target,
                                scenario=sspec.name,
                                iteration=n,
                                session_id=session_id,
                                session_timestamp=session_ts,
                                env_overrides=env_overrides,
                                sweep_tag=sweep_tag,
                            )
                        )
                    continue

                # Phase 1 + 2 za non-cold-start scenarije
                for w in range(cfg.warmup_runs):
                    warmups.append(
                        RunSpec(
                            target=target,
                            scenario=sspec.name,
                            iteration=0,
                            session_id=session_id,
                            session_timestamp=session_ts,
                            env_overrides=env_overrides,
                            sweep_tag=sweep_tag,
                        )
                    )
                for n in range(1, cfg.iterations + 1):
                    measurements.append(
                        RunSpec(
                            target=target,
                            scenario=sspec.name,
                            iteration=n,
                            session_id=session_id,
                            session_timestamp=session_ts,
                            env_overrides=env_overrides,
                            sweep_tag=sweep_tag,
                        )
                    )

    rng.shuffle(cold_starts)
    rng.shuffle(measurements)
    return cold_starts + warmups + measurements


def k6_command(spec: RunSpec) -> list[str]:
    """Konstruise k6 run komandu za jedan RunSpec."""
    if spec.scenario.startswith("io-"):
        backend = spec.scenario.split("-", 1)[1]  # native ili neutral
        script = "k6/scenario-io.js"
        scenario_args = ["-e", f"IO_BACKEND={backend}"]
    else:
        script = f"k6/scenario-{spec.scenario}.js"
        scenario_args = []

    env_args = [
        "-e", f"BASE_URL={spec.target.url}",
        "-e", f"PROFILE={spec.target.profile}",
        "-e", f"PROVIDER={spec.target.provider}",
        "-e", f"ARCH={spec.target.arch}",
        "-e", f"REGION={spec.target.region}",
        "-e", f"K6_RESULTS_DIR={spec.results_dir.as_posix()}",
        "-e", f"RUN_NUMBER={spec.iteration}",
    ]
    # Sweep parametri (npr. -e IO_BYTES=1048576) — prazno za obicne scenarije.
    sweep_args = []
    for param, val in spec.env_overrides:
        sweep_args += ["-e", f"{param}={val}"]

    # --no-thresholds: k6 thresholds (p95<2000 itd.) su CI-gating koncept; za
    # benchmark zelimo da zabelezimo latenciju BEZ OBZIRA koliko je visoka.
    # Bez ovog flag-a, spori runovi (npr. AWS io-native ~7s) vracaju exit 99
    # (threshold crossed) i orchestrator ih lazno markira kao failure iako su
    # podaci validni i kompletni. Error rate / latencija se ionako belaze kao
    # metrike u analysis.json.
    return ["k6", "run", "--no-thresholds", *env_args, *scenario_args, *sweep_args, script]


def execute(spec: RunSpec, cfg: Config, dry_run: bool) -> dict:
    """Pokrece jedan run, vraca log entry sa status-om."""
    spec.results_dir.mkdir(parents=True, exist_ok=True)

    label = "WARMUP" if spec.is_warmup else f"RUN n={spec.iteration}"
    log.info(
        "%s | %s/%s/%s @ %s",
        label, spec.target.provider, spec.target.arch, spec.scenario, spec.target.url,
    )

    entry = {
        "session_id": spec.session_id,
        "session_timestamp": spec.session_timestamp,
        "provider": spec.target.provider,
        "arch": spec.target.arch,
        "scenario": spec.scenario,
        "iteration": spec.iteration,
        "is_warmup": spec.is_warmup,
        "url": spec.target.url,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "results_dir": spec.results_dir.as_posix(),
    }

    # Cold-start scenario: NE radimo pre-run health-check. Health-check pinguje
    # /health sto bi zagrejalo scale-to-zero instancu (FaaS/CaaS min=0) PRE nego sto
    # k6 izmeri cold start → cold start bi bio apsorbovan u health-check i izgubljen
    # (empirijski: cold_starts_detected ~0 dok je health-check bio aktivan). k6
    # cold-start skripta i onako salje /health kao svoj prvi request, sto sluzi i kao
    # liveness provera i kao samo cold-start merenje. Za sve ostale scenarije zelimo
    # warm instancu, pa health-check ostaje (i sluzi kao implicitni warmup).
    if spec.scenario != "cold-start":
        if not health_check(spec.target.url, cfg.health_check_timeout_sec, cfg.health_check_retries):
            log.error("HEALTH FAIL — preskacem run")
            entry["status"] = "health_check_failed"
            entry["finished_at"] = datetime.now(timezone.utc).isoformat()
            return entry

    cmd = k6_command(spec)
    log.debug("$ %s", " ".join(cmd))

    if dry_run:
        log.info("[DRY-RUN] %s", " ".join(cmd))
        entry["status"] = "dry_run"
        entry["finished_at"] = datetime.now(timezone.utc).isoformat()
        return entry

    t0 = time.time()
    try:
        result = subprocess.run(cmd, check=False)
        entry["k6_exit_code"] = result.returncode
        entry["status"] = "ok" if result.returncode == 0 else "k6_nonzero_exit"
    except FileNotFoundError:
        log.error("k6 binary not found in PATH")
        entry["status"] = "k6_not_found"
    entry["duration_sec"] = round(time.time() - t0, 1)
    entry["finished_at"] = datetime.now(timezone.utc).isoformat()
    return entry


def write_session_log(session_id: str, session_ts: str, log_entries: Iterable[dict]) -> Path:
    out_dir = Path("k6") / "results" / "_sessions"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / f"{session_ts}__{session_id}.json"
    log_path.write_text(json.dumps(list(log_entries), indent=2), encoding="utf-8")
    log.info("Session log saved: %s", log_path)
    return log_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", type=Path, required=True, help="YAML config path")
    parser.add_argument(
        "--session-id",
        default="manual",
        help="Session identifier (e.g. 'morning', 'afternoon', 'night' for stratified slots)",
    )
    parser.add_argument("--seed", type=int, default=None, help="RNG seed (default: time-based)")
    parser.add_argument("--iterations", type=int, default=None, help="Override iterations from config")
    parser.add_argument("--warmup", type=int, default=None, help="Override warmup_runs from config")
    parser.add_argument("--dry-run", action="store_true", help="Print commands, don't execute")
    args = parser.parse_args(argv)

    if not args.config.exists():
        log.error("Config file not found: %s", args.config)
        return 2

    cfg = parse_config(args.config)
    if args.iterations is not None:
        cfg.iterations = args.iterations
    if args.warmup is not None:
        cfg.warmup_runs = args.warmup

    if not cfg.targets:
        log.error("No targets in config")
        return 2

    if not shutil.which("k6") and not args.dry_run:
        log.error("k6 not found in PATH. Install: https://k6.io/docs/get-started/installation/")
        return 2

    rng = random.Random(args.seed)
    specs = build_run_specs(cfg, args.session_id, rng)
    log.info(
        "Session %s | %d targets | %d cells | %d warmups + %d runs = %d total",
        args.session_id,
        len(cfg.targets),
        sum(len(t.scenarios) for t in cfg.targets),
        sum(1 for s in specs if s.is_warmup),
        sum(1 for s in specs if not s.is_warmup),
        len(specs),
    )

    session_ts = specs[0].session_timestamp if specs else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    log_entries: list[dict] = []
    try:
        for i, spec in enumerate(specs, start=1):
            log.info("[%d/%d]", i, len(specs))
            entry = execute(spec, cfg, args.dry_run)
            log_entries.append(entry)
            if i < len(specs) and not args.dry_run:
                time.sleep(cfg.inter_run_sleep_sec)
    except KeyboardInterrupt:
        log.warning("Interrupted — saving partial session log")
    finally:
        if log_entries:
            write_session_log(args.session_id, session_ts, log_entries)

    # Uspeh racunamo SAMO nad measurement runovima (warmup-ovi se odbacuju).
    # Raniji bug: `ok` je brojao i warmup-ove (i oni dobiju status "ok"), pa je
    # pri warmup_runs>0 uvek bilo ok>total -> exit 1, sto je (a) lazno markiralo
    # sesiju kao failed i (b) sprecavalo systemd ExecStartPost (aggregate.py) da
    # se uopste pokrene -> DuckDB ostaje neazuriran.
    measurement_entries = [e for e in log_entries if not e.get("is_warmup")]
    ok = sum(1 for e in measurement_entries if e.get("status") == "ok")
    total = len(measurement_entries)
    log.info("Done. %d/%d measurement runs OK", ok, total)
    if ok < total:
        failed = [
            f"{e['provider']}/{e['arch']}/{e['scenario']}(n={e['iteration']},{e.get('status')})"
            for e in measurement_entries
            if e.get("status") != "ok"
        ]
        log.warning("%d measurement run(s) nisu OK: %s", total - ok, ", ".join(failed))
    # Exit 0 i kad pojedinacni runovi padnu: u unattended kampanji su parcijalni
    # failovi ocekivani (FaaS throttle, prolazni health blip) i NE smeju da blokiraju
    # downstream aggregate (systemd ExecStartPost) niti da markiraju celu sesiju kao
    # failed. Pali runovi su vidljivi u session log-u + kao nizi N po cell-u u DuckDB-u.
    # Katastrofalne pre-flight greske (nema configa / targeta / k6) vec vracaju
    # non-zero PRE nego sto ijedan run krene.
    return 0


if __name__ == "__main__":
    sys.exit(main())
