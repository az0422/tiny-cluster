import subprocess
import multiprocessing
import threading
import datetime
import os
import signal
import sqlite3
import base64

class LogCollector(threading.Thread):
    def __init__(self, pipe, queue, ltype):
        super().__init__()
        self.pipe = pipe
        self.queue = queue
        self.ltype = ltype
    
    def run(self):
        while True:
            chunk = self.pipe.read1(1024)

            if not chunk:
                break

            self.queue.put({
                "type": self.ltype,
                "message": base64.b64encode(chunk).decode("UTF-8"),
            })

class LogWriter(multiprocessing.Process):
    def __init__(self, name):
        super().__init__()
        self.queue = multiprocessing.Queue()
        self.name = name
    
    def run(self):
        conn = sqlite3.connect("%s.sqlite3" % self.name)
        cursor = conn.cursor()
        
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, type TEXT, message TEXT)")
        conn.commit()

        maximum = int(os.environ["MAX_LOG_LENGTH"])

        while True:
            ret = self.queue.get()
            ltype = ret["type"]
            message = ret["message"]

            cursor.execute("INSERT INTO logs (type, message) values (?, ?)", (ltype, message))
            cursor.execute("SELECT count(id) FROM logs")
            fetch = cursor.fetchone()[0]

            if maximum + (maximum // 2) < fetch:
                cursor.execute("DELETE FROM logs WHERE id IN (SELECT id FROM logs ORDER BY ASC LIMIT ?)", (fetch - maximum))
                cursor.execute("VACUUM")
            
            conn.commit()

            if ltype.lower() == "exit":
                break
        
        cursor.close()
        conn.close()

class JobRunner(multiprocessing.Process):
    def __init__(self, job_cfg):
        super().__init__()

        venv_path = job_cfg["venv"]
        if venv_path is not None:
            venv_path = os.path.expandvars(venv_path)
            venv_path = os.path.expanduser(venv_path)
            self.cmd = [job_cfg["exec"]] if ("pip" not in job_cfg["exec"] and "python" not in job_cfg["exec"]) else [os.path.join(venv_path, "bin", job_cfg["exec"])]
        else:
            self.cmd = [job_cfg["exec"]]

        self.path = os.path.expanduser(os.path.expandvars(job_cfg["path"])) if job_cfg["path"] is not None else os.environ["HOME"]
        self.environment = job_cfg["env"]
        self.args = [os.path.expandvars(arg) for arg in job_cfg["args"]] if job_cfg["args"] is not None else []

        self.job_pid = multiprocessing.Value("i", 0)
        created_at = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.name = "%s-%s" % (created_at, job_cfg["name"])

        self.log_writer = None

    def start(self):
        self.log_writer = LogWriter(self.name)
        self.log_writer.start()
        super().start()
    
    def get_name(self):
        return self.name
    
    def set_name(self, name):
        self.name = name
    
    def set_proc(self):
        return None

    def run(self):
        proc = self.set_proc()

        stdout = LogCollector(proc.stdout, self.log_writer.queue, "STDOUT")
        stderr = LogCollector(proc.stderr, self.log_writer.queue, "STDERR")

        self.job_pid.value = proc.pid

        stdout.start()
        stderr.start()

        proc.wait()

        self.log_writer.queue.put({"type": "EXIT", "message": str(proc.returncode)})

    def terminate(self):
        self.log_writer.terminate()

        if self.job_pid.value == 0:
            super().terminate()
        
        try:
            os.killpg(
                os.getpgid(self.job_pid.value),
                signal.SIGINT,
            )
        except:
            pass

        super().terminate()

class RunJob(JobRunner):
    def set_proc(self):
        return subprocess.Popen(
            self.cmd + self.args,
            env=self.environment,
            cwd=self.path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1024,
            preexec_fn=os.setsid
        )