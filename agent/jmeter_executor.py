import subprocess
from pathlib import Path


class JMeterExecutor:

    def __init__(self):
        self.project_dir = Path(__file__).resolve().parent.parent

        self.jmeter_cmd = (
            r"C:\Loadmagic\apache-jmeter-5.6.3"
            r"\apache-jmeter-5.6.3\bin\jmeter.bat"
        )

        self.jmx_file = self.project_dir / "scripts" / "ai_perf_test.jmx"
        self.jtl_file = self.project_dir / "scripts" / "results.jtl"

    def run(self, users, ramp_up, duration):

        print("\n===================================")
        print("       REAL JMETER EXECUTION")
        print("===================================")

        print(f"Users     : {users}")
        print(f"Ramp-up   : {ramp_up}s")
        print(f"Duration  : {duration}s")
        print(f"JMX       : {self.jmx_file}")
        print(f"JTL       : {self.jtl_file}")

        if not Path(self.jmeter_cmd).exists():
            raise FileNotFoundError(
                f"JMeter not found: {self.jmeter_cmd}"
            )

        if not self.jmx_file.exists():
            raise FileNotFoundError(
                f"JMX not found: {self.jmx_file}"
            )

        # Remove previous result
        if self.jtl_file.exists():
            self.jtl_file.unlink()

        command = [
            self.jmeter_cmd,
            "-n",
            f"-JTEST_USERS={users}",
            f"-JRAMP_UP={ramp_up}",
            f"-JDURATION={duration}",
            "-t",
            str(self.jmx_file),
            "-l",
            str(self.jtl_file),
        ]

        print("\nExecuting:")
        print(" ".join(f'"{x}"' if " " in x else x for x in command))
        print()

        result = subprocess.run(
            command,
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )

        print(result.stdout)

        if result.stderr:
            print(result.stderr)

        if result.returncode != 0:
            raise RuntimeError(
                f"JMeter execution failed with exit code "
                f"{result.returncode}"
            )

        if not self.jtl_file.exists():
            raise RuntimeError(
                "JMeter completed but results.jtl was not created."
            )

        print("JMeter execution completed successfully.")
        print(f"Results: {self.jtl_file}")

        return self.jtl_file


if __name__ == "__main__":

    executor = JMeterExecutor()

    executor.run(
        users=10,
        ramp_up=30,
        duration=60
    )