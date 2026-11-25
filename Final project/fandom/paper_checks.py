"""Run the paper's standalone scripts with Fandom inputs in an isolated working directory."""
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "results"


def main():
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as work:
        tmp = Path(work)
        (tmp / "investigations").mkdir()
        (tmp / "figures").mkdir()
        for d in (Path("."), Path("investigations")):
            for src in (ROOT / d).glob("*.py"):
                shutil.copyfile(src, tmp / d / src.name)
        (tmp / "data").symlink_to(ROOT / "data", target_is_directory=True)
        (tmp / "passages.csv").symlink_to(HERE / "passages.csv")
        (tmp / "film_directors.csv").symlink_to(ROOT / "film_directors.csv")
        env = dict(os.environ, MPLCONFIGDIR=work, MPLBACKEND="Agg", OPENBLAS_NUM_THREADS="1")
        jobs = [
            ("check_descriptors.py", ["--roles","passages.csv"]),
            ("typecast.py", ["--roles","passages.csv","--text","role_text_blind"]),
            ("within_nolan.py", ["--roles","passages.csv","--text","role_text_blind"]),
            ("director_test.py", ["--roles","passages.csv","--text","role_text_blind","--min-roles","3"]),
        ]
        for name in ("returning_placebo","placebo_checks","explore_film_vocab","film_confound",
                     "sequel_control","robustness","actor_signal","link_film_network","link_homophily","link_regulars"):
            jobs.append((f"investigations/{name}.py", []))

        def run(job):
            script, args = job
            proc = subprocess.run([sys.executable,script,*args], cwd=tmp, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            print(f"{Path(script).stem} ({proc.returncode})", flush=True)
            return script,proc

        with ThreadPoolExecutor(3) as pool:
            completed = list(pool.map(run,jobs))
        failures = []
        reports = []
        for script, proc in completed:
            if proc.returncode:
                failures.append(script)
            reports.append(f"===== {script} =====\n{proc.stdout.strip()}\n")
        (OUT / "paper_checks.txt").write_text("\n".join(reports))
        for filename in ("director_test.json","director_results.csv","within_nolan.json","within_nolan.csv","typecast_results.csv"):
            if (tmp / filename).exists():
                shutil.copyfile(tmp / filename, OUT / filename)
        for src in (tmp / "investigations").glob("*.json"):
            shutil.copyfile(src, OUT / src.name)
        if failures:
            raise SystemExit("Check results/paper_checks.txt for: " + ", ".join(failures))


if __name__ == "__main__":
    main()
