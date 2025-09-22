
import os, sys, shutil, psutil, readline, shlex, re, subprocess
from datetime import datetime

HISTORY_FILE = os.path.expanduser("~/.pyterminal_history")
MAX_HISTORY = 2000

def safe_print(s=""):
    if isinstance(s, bytes):
        try:
            s = s.decode("utf-8", errors="replace")
        except Exception:
            s = str(s)
    print(s)

def human_size(n):
    for unit in ['B','KB','MB','GB','TB']:
        if abs(n) < 1024.0:
            return f"{n:3.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}PB"

def read_history():
    try:
        readline.read_history_file(HISTORY_FILE)
    except FileNotFoundError:
        pass

def write_history():
    try:
        readline.set_history_length(MAX_HISTORY)
        readline.write_history_file(HISTORY_FILE)
    except Exception:
        pass

class Terminal:
    def __init__(self):
        self.cwd = os.path.abspath(os.getcwd())
        self.builtins = self._discover_builtins()
        self.setup_readline()

    def _discover_builtins(self):
        cmds = {}
        for name in dir(self):
            if name.startswith("do_"):
                cmd = name[3:]
                cmds[cmd] = getattr(self, name)
        return cmds

    def setup_readline(self):
        readline.parse_and_bind('tab: complete')
        read_history()
        def completer(text, state):
            buffer = readline.get_line_buffer()
            line = shlex.split(buffer) if buffer.strip() else []
            if len(line) == 0 or (buffer.endswith(" ") and len(line) >= 1):
                offerings = self._complete_path(text)
            else:
                first_token = line[0]
                if buffer.startswith(first_token) and buffer.strip() == first_token:
                    offerings = [c for c in list(self.builtins.keys()) + self._complete_path(text) if c.startswith(text)]
                else:
                    offerings = self._complete_path(text)
            try:
                return offerings[state]
            except Exception:
                return None
        readline.set_completer(completer)

    def _complete_path(self, text):
        if not text:
            text = ''
        text_exp = os.path.expanduser(text)
        dirname = os.path.dirname(text_exp) or '.'
        basename = os.path.basename(text_exp)
        try:
            entries = os.listdir(dirname)
        except Exception:
            entries = []
        results = [os.path.join(dirname, e) for e in entries if e.startswith(basename)]
        out = []
        for r in results:
            display = r
            if text.startswith('~'):
                home = os.path.expanduser('~')
                if r.startswith(home):
                    display = '~' + r[len(home):]
            if os.path.isdir(r):
                display += os.sep
            out.append(display)
        return out

    def execute_line(self, line):
        try:
            tokens = shlex.split(line)
        except ValueError as e:
            return f"parse error: {e}"
        if not tokens:
            return ""
        cmd = tokens[0]
        args = tokens[1:]
        if cmd in self.builtins:
            try:
                result = self.builtins[cmd](args)
                return result if result is not None else ""
            except Exception as e:
                return f"error executing builtin {cmd}: {e}"
        if cmd in ("exit", "quit"):
            return "Session ended."
        return self.run_external(cmd, args)

    def run_external(self, cmd, args):
        full_cmd = [cmd] + args
        try:
            proc = subprocess.Popen(full_cmd, cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate()
            output = ""
            if out:
                output += out.decode(errors='replace')
            if err:
                output += err.decode(errors='replace')
            return output
        except FileNotFoundError:
            return f"{cmd}: command not found"
        except Exception as e:
            return f"error running external command: {e}"

    def do_pwd(self, argv):
        return self.cwd

    def do_cd(self, argv):
        target = argv[0] if argv else os.path.expanduser('~')
        target = os.path.expanduser(target)
        if not os.path.isabs(target):
            target = os.path.join(self.cwd, target)
        try:
            target = os.path.abspath(target)
            os.chdir(target)
            self.cwd = target
            return ""
        except FileNotFoundError:
            return f"cd: no such file or directory: {argv[0] if argv else '~'}"
        except NotADirectoryError:
            return f"cd: not a directory: {argv[0]}"
        except PermissionError:
            return f"cd: permission denied: {argv[0]}"
        except Exception as e:
            return f"cd: {e}"

    def do_ls(self, argv):
        path = argv[0] if argv else "."
        long = False
        show_all = False
        flags = [a for a in argv if a.startswith('-')]
        for f in flags:
            if 'l' in f:
                long = True
            if 'a' in f:
                show_all = True
        if argv and not argv[0].startswith('-'):
            path = argv[0]
        path = os.path.expanduser(path)
        if not os.path.isabs(path):
            path = os.path.join(self.cwd, path)
        try:
            if os.path.isdir(path):
                entries = os.listdir(path)
                if not show_all:
                    entries = [e for e in entries if not e.startswith('.')]
                entries.sort()
                if long:
                    lines = []
                    for e in entries:
                        full = os.path.join(path, e)
                        stat = os.stat(full)
                        mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                        perms = oct(stat.st_mode)[-3:]
                        size = human_size(stat.st_size)
                        lines.append(f"{perms}\t{size:>7}\t{mtime}\t{e}")
                    return "\n".join(lines)
                else:
                    return "  ".join(entries)
            else:
                return os.path.basename(path)
        except FileNotFoundError:
            return f"ls: cannot access '{path}': No such file or directory"
        except PermissionError:
            return f"ls: cannot open directory '{path}': Permission denied"
        except Exception as e:
            return f"ls error: {e}"

    def do_mkdir(self, argv):
        if not argv:
            return "mkdir: missing operand"
        for d in argv:
            target = os.path.expanduser(d)
            if not os.path.isabs(target):
                target = os.path.join(self.cwd, target)
            try:
                os.makedirs(target, exist_ok=False)
            except FileExistsError:
                return f"mkdir: cannot create directory '{d}': File exists"
            except PermissionError:
                return f"mkdir: cannot create directory '{d}': Permission denied"
            except Exception as e:
                return f"mkdir: {e}"
        return ""

    def do_rm(self, argv):
        if not argv:
            return "rm: missing operand"
        recursive = False
        force = False
        targets = []
        for a in argv:
            if a.startswith('-'):
                if 'r' in a:
                    recursive = True
                if 'f' in a:
                    force = True
            else:
                targets.append(a)
        for t in targets:
            target = os.path.expanduser(t)
            if not os.path.isabs(target):
                target = os.path.join(self.cwd, target)
            if os.path.isdir(target) and not os.path.islink(target):
                if not recursive:
                    return f"rm: cannot remove '{t}': Is a directory (use -r)"
                try:
                    shutil.rmtree(target)
                except Exception as e:
                    return f"rm: failed to remove directory '{t}': {e}"
            else:
                try:
                    os.remove(target)
                except FileNotFoundError:
                    if not force:
                        return f"rm: cannot remove '{t}': No such file or directory"
                except PermissionError:
                    return f"rm: cannot remove '{t}': Permission denied"
                except Exception as e:
                    return f"rm: {e}"
        return ""

    def do_cpu(self, argv):
        return f"CPU Usage: {psutil.cpu_percent()}%"

    def do_mem(self, argv):
        mem = psutil.virtual_memory()
        return f"Memory Usage: {mem.percent}% ({mem.used // (1024**2)}MB/{mem.total // (1024**2)}MB)"

    def do_ps(self, argv):
        lines = []
        for proc in psutil.process_iter(['pid', 'name']):
            lines.append(f"PID: {proc.info['pid']}, Name: {proc.info['name']}")
        return "\n".join(lines)

    def do_help(self, argv):
        return ("Supported commands:\n"
                "  ls [dir]         - List directory contents\n"
                "  cd <dir>         - Change directory\n"
                "  pwd              - Print working directory\n"
                "  mkdir <dir>      - Make directory\n"
                "  rm <target>      - Remove file or directory\n"
                "  cpu              - Show CPU usage\n"
                "  mem              - Show memory usage\n"
                "  ps               - List processes\n"
                "  history          - Show command history\n"
                "  help             - Show this help\n"
                "  exit             - Exit terminal\n"
                "Optional: AI-driven natural language (type: ai <query>)\n")

    def do_history(self, argv):
        lines = []
        for i in range(readline.get_current_history_length()):
            lines.append(readline.get_history_item(i+1))
        return "\n".join(lines)

    def do_ai(self, argv):
        return "AI-driven command interpretation is not implemented yet."
