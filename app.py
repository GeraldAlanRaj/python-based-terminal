#!/usr/bin/env python3
"""
pyterm.py - A Python-based command terminal (single-file)

Features:
- Python backend for command execution
- Built-in file/directory commands: ls, cd, pwd, mkdir, rmdir, rm, touch, cat, mv, cp, stat, echo, head, tail
- Runs external system commands if command is unknown
- Error handling for invalid args/permissions
- System monitoring via psutil (if installed) or subprocess fallbacks
- Command history and tab auto-completion (readline)
- Simple natural language interpreter (heuristic-based)
- Extensible: add new built-in methods to Terminal class

Usage:
    python pyterm.py

Security note:
- This program executes filesystem changes and external commands. Run it in a safe environment.
"""

import os

# Enhanced Python Terminal
import os
import sys
import shutil
import psutil
import readline
import shlex
import re
import subprocess
from datetime import datetime

HISTORY_FILE = os.path.expanduser("~/.pyterminal_history")

def save_history():
    readline.write_history_file(HISTORY_FILE)

def load_history():
    if os.path.exists(HISTORY_FILE):
        readline.read_history_file(HISTORY_FILE)

def list_dir(args):
    path = args[0] if args else '.'
    try:
        for entry in os.listdir(path):
            print(entry)
    except Exception as e:
        print(f"Error: {e}")

def change_dir(args):
    if not args:
        print("Usage: cd <directory>")
        return
    try:
        os.chdir(args[0])
    except Exception as e:
        print(f"Error: {e}")

def print_working_dir(args):
    print(os.getcwd())

def make_dir(args):
    if not args:
        print("Usage: mkdir <directory>")
        return
    try:
        os.makedirs(args[0], exist_ok=True)
    except Exception as e:
        print(f"Error: {e}")

def remove(args):
    if not args:
        print("Usage: rm <file/directory>")
        return
    target = args[0]
    try:
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
    except Exception as e:
        print(f"Error: {e}")

def show_cpu(args):
    print(f"CPU Usage: {psutil.cpu_percent()}%")

def show_mem(args):
    mem = psutil.virtual_memory()
    print(f"Memory Usage: {mem.percent}% ({mem.used // (1024**2)}MB/{mem.total // (1024**2)}MB)")

def show_ps(args):
    for proc in psutil.process_iter(['pid', 'name']):
        print(f"PID: {proc.info['pid']}, Name: {proc.info['name']}")

def help_cmd(args):
    print("""
Supported commands:
  ls [dir]         - List directory contents
  cd <dir>         - Change directory
  pwd              - Print working directory
  mkdir <dir>      - Make directory
  rm <target>      - Remove file or directory
  cpu              - Show CPU usage
  mem              - Show memory usage
  ps               - List processes
  history          - Show command history
  help             - Show this help
  exit             - Exit terminal
Optional: AI-driven natural language (type: ai <query>)
""")

def show_history(args):
    for i in range(readline.get_current_history_length()):
        print(readline.get_history_item(i+1))

def ai_interpret(args):
    # Stub for AI-driven command interpretation
    print("AI-driven command interpretation is not implemented yet.")

COMMANDS = {
    'ls': list_dir,
    'cd': change_dir,
    'pwd': print_working_dir,
    'mkdir': make_dir,
    'rm': remove,
    'cpu': show_cpu,
    'mem': show_mem,
    'ps': show_ps,
    'help': help_cmd,
    'history': show_history,
    'ai': ai_interpret,
}

def parse_and_execute(cmdline):
    if not cmdline.strip():
        return
    parts = cmdline.strip().split()
    cmd = parts[0]
    args = parts[1:]
    if cmd == 'exit':
        print("Exiting terminal.")
        save_history()
        sys.exit(0)
    func = COMMANDS.get(cmd)
    if func:
        func(args)
    else:
        # Try to execute as system command
        try:
            os.system(cmdline)
        except Exception as e:
            print(f"Error: {e}")

def main():
    load_history()
    print("Welcome to Python Terminal! Type 'help' for commands.")
    while True:
        try:
            cmdline = input(f"{os.getcwd()} $ ")
            readline.add_history(cmdline)
            parse_and_execute(cmdline)
        except KeyboardInterrupt:
            print("\nUse 'exit' to quit.")
        except EOFError:
            print("\nExiting terminal.")
            save_history()
            break

if __name__ == "__main__":
    main()
HISTORY_FILE = os.path.expanduser("~/.pyterm_history")
MAX_HISTORY = 2000

# ---------- Helper utilities ----------
def safe_print(s=""):
    """Print wrapper that handles bytes and Unicode safely."""
    if isinstance(s, bytes):
        try:
            s = s.decode("utf-8", errors="replace")
        except Exception:
            s = str(s)
    print(s)

def human_size(n):
    """Human-friendly file size"""
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

# ---------- Terminal core ----------
class Terminal:
    def __init__(self):
        self.cwd = os.path.abspath(os.getcwd())
        self.builtins = self._discover_builtins()
        self.setup_readline()

    def _discover_builtins(self):
        # map command name to method
        cmds = {}
        for name in dir(self):
            if name.startswith("do_"):
                cmd = name[3:]
                cmds[cmd] = getattr(self, name)
        return cmds

    # ---- Readline: history + completion ----
    def setup_readline(self):
        # history
        readline.parse_and_bind('tab: complete')
        read_history()

        # completion function
        def completer(text, state):
            buffer = readline.get_line_buffer()
            line = shlex.split(buffer) if buffer.strip() else []
            # if first token -> complete command names and filesystem
            if len(line) == 0 or (buffer.endswith(" ") and len(line) >= 1):
                # completing an argument: offer filesystem paths
                offerings = self._complete_path(text)
            else:
                # completing first token or partial token
                first_token = line[0]
                if buffer.startswith(first_token) and buffer.strip() == first_token:
                    # complete commands + paths
                    offerings = [c for c in list(self.builtins.keys()) + self._complete_path(text) if c.startswith(text)]
                else:
                    offerings = self._complete_path(text)
            try:
                return offerings[state]
            except Exception:
                return None

        readline.set_completer(completer)

    def _complete_path(self, text):
        # Expands ~ and returns matching files/dirs
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
        # present with ~ if originally had ~
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
        # If no real filesystem matches, also return empty list
        return out

    # ---- REPL Loop ----
    def repl(self):
        try:
            while True:
                # Removed undefined PROMPT reference
                try:
                    line = input(prompt)
                except EOFError:
                    print()
                    break
                except KeyboardInterrupt:
                    print()
                    continue
                line = line.strip()
                if not line:
                    continue
                # Save to history
                readline.add_history(line)
                # Natural-language detection: if sentence-like, try interpret
                if self._is_natural_language(line):
                    interpreted = self.nl_to_cmd(line)
                    if interpreted:
                        safe_print(f"# interpreted -> {interpreted}")
                        line = interpreted
                self.execute_line(line)
        finally:
            write_history()

    def _is_natural_language(self, t):
        # Very simple heuristic: contains spaces and verbs/keywords like "create", "move", "delete", "show"
        return bool(re.search(r'\b(create|make|move|delete|remove|show|list|display|open|read|write|copy|rename)\b', t, re.I))

    # ---- Command execution ----
    def execute_line(self, line):
        # parse command into tokens, but support quotes
        try:
            tokens = shlex.split(line)
        except ValueError as e:
            safe_print(f"parse error: {e}")
            return
        if not tokens:
            return
        cmd = tokens[0]
        args = tokens[1:]
        # built-in?
        if cmd in self.builtins:
            try:
                return self.builtins[cmd](args)
            except Exception as e:
                safe_print(f"error executing builtin {cmd}: {e}")
                return
        # special internal commands like exit
        if cmd in ("exit", "quit"):
            sys.exit(0)
        # fallback: execute external command
        return self.run_external(cmd, args)

    def run_external(self, cmd, args):
        """Runs external system command and streams output."""
        full_cmd = [cmd] + args
        try:
            proc = subprocess.Popen(full_cmd, cwd=self.cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate()
            if out:
                safe_print(out)
            if err:
                safe_print(err)
            return proc.returncode
        except FileNotFoundError:
            safe_print(f"{cmd}: command not found")
            return 127
        except Exception as e:
            safe_print(f"error running external command: {e}")
            return 1

    # ---- Built-in commands (do_<cmd>) ----
    def do_pwd(self, argv):
        safe_print(self.cwd)

    def do_cd(self, argv):
        target = argv[0] if argv else os.path.expanduser('~')
        target = os.path.expanduser(target)
        if not os.path.isabs(target):
            target = os.path.join(self.cwd, target)
        try:
            target = os.path.abspath(target)
            os.chdir(target)
            self.cwd = target
        except FileNotFoundError:
            safe_print(f"cd: no such file or directory: {argv[0] if argv else '~'}")
        except NotADirectoryError:
            safe_print(f"cd: not a directory: {argv[0]}")
        except PermissionError:
            safe_print(f"cd: permission denied: {argv[0]}")
        except Exception as e:
            safe_print(f"cd: {e}")

    def do_ls(self, argv):
        path = argv[0] if argv else "."
        long = False
        show_all = False
        # simple flags parsing
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
                    for e in entries:
                        full = os.path.join(path, e)
                        stat = os.stat(full)
                        mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M')
                        perms = oct(stat.st_mode)[-3:]
                        size = human_size(stat.st_size)
                        safe_print(f"{perms}\t{size:>7}\t{mtime}\t{e}")
                else:
                    # simple column-ish
                    safe_print("  ".join(entries))
            else:
                # path is file: print file name
                safe_print(os.path.basename(path))
        except FileNotFoundError:
            safe_print(f"ls: cannot access '{path}': No such file or directory")
        except PermissionError:
            safe_print(f"ls: cannot open directory '{path}': Permission denied")
        except Exception as e:
            safe_print(f"ls error: {e}")

    def do_mkdir(self, argv):
        if not argv:
            safe_print("mkdir: missing operand")
            return
        for d in argv:
            target = os.path.expanduser(d)
            if not os.path.isabs(target):
                target = os.path.join(self.cwd, target)
            try:
                os.makedirs(target, exist_ok=False)
            except FileExistsError:
                safe_print(f"mkdir: cannot create directory '{d}': File exists")
            except PermissionError:
                safe_print(f"mkdir: cannot create directory '{d}': Permission denied")
            except Exception as e:
                safe_print(f"mkdir: {e}")

    def do_rmdir(self, argv):
        if not argv:
            safe_print("rmdir: missing operand")
            return
        for d in argv:
            target = os.path.expanduser(d)
            if not os.path.isabs(target):
                target = os.path.join(self.cwd, target)
            try:
                os.rmdir(target)
            except FileNotFoundError:
                safe_print(f"rmdir: failed to remove '{d}': No such file or directory")
            except OSError as e:
                safe_print(f"rmdir: failed to remove '{d}': {e}")
            except Exception as e:
                safe_print(f"rmdir: {e}")

    def do_rm(self, argv):
        if not argv:
            safe_print("rm: missing operand")
            return
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
                    safe_print(f"rm: cannot remove '{t}': Is a directory (use -r)")
                    continue
                # recursive remove
                try:
                    # careful: use shutil.rmtree
                    import shutil
                    shutil.rmtree(target)
                except Exception as e:
                    safe_print(f"rm: failed to remove directory '{t}': {e}")
            else:
                try:
                    os.remove(target)
                except FileNotFoundError:
                    if not force:
                        safe_print(f"rm: cannot remove '{t}': No such file or directory")
                except PermissionError:
                    safe_print(f"rm: cannot remove '{t}': Permission denied")
                except Exception as e:
                    safe_print(f"rm: {e}")

    def do_touch(self, argv):
        if not argv:
            safe_print("touch: missing file operand")
            return
        for f in argv:
            target = os.path.expanduser(f)
            if not os.path.isabs(target):
                target = os.path.join(self.cwd, target)
            try:
                # update timestamp or create file
                with open(target, 'a'):
                    os.utime(target, None)
            except Exception as e:
                safe_print(f"touch: {e}")

    def do_cat(self, argv):
        if not argv:
            safe_print("cat: missing file operand")
            return
        for f in argv:
            target = os.path.expanduser(f)
            if not os.path.isabs(target):
                target = os.path.join(self.cwd, target)
            try:
                with open(target, 'rb') as fh:
                    data = fh.read()
                    safe_print(data)
            except FileNotFoundError:
                safe_print(f"cat: {f}: No such file or directory")
            except IsADirectoryError:
                safe_print(f"cat: {f}: Is a directory")
            except PermissionError:
                safe_print(f"cat: {f}: Permission denied")
            except Exception as e:
                safe_print(f"cat: {e}")

    def do_head(self, argv):
        lines = 10
        files = []
        if argv and argv[0].startswith('-'):
            # e.g. -n 5
            # very simple parsing
            m = re.match(r'-n(\d+)', argv[0])
            if m:
                lines = int(m.group(1))
                files = argv[1:]
            else:
                files = argv[1:]
        else:
            files = argv
        if not files:
            safe_print("head: missing file operand")
            return
        for f in files:
            target = os.path.expanduser(f)
            if not os.path.isabs(target):
                target = os.path.join(self.cwd, target)
            try:
                with open(target, 'r', encoding='utf-8', errors='replace') as fh:
                    for i, line in enumerate(fh):
                        if i >= lines:
                            break
                        safe_print(line.rstrip('\n'))
            except Exception as e:
                safe_print(f"head: {e}")

    def do_tail(self, argv):
        lines = 10
        files = []
        if argv and argv[0].startswith('-'):
            m = re.match(r'-n(\d+)', argv[0])
            if m:
                lines = int(m.group(1))
                files = argv[1:]
            else:
                files = argv[1:]
        else:
            files = argv
        if not files:
            safe_print("tail: missing file operand")
            return
        for f in files:
            target = os.path.expanduser(f)
            if not os.path.isabs(target):
                target = os.path.join(self.cwd, target)
            try:
                with open(target, 'r', encoding='utf-8', errors='replace') as fh:
                    data = fh.readlines()
                    for line in data[-lines:]:
                        safe_print(line.rstrip('\n'))
            except Exception as e:
                safe_print(f"tail: {e}")

    def do_mv(self, argv):
        if len(argv) < 2:
            safe_print("mv: missing file operand")
            return
        srcs = argv[:-1]
        dest = argv[-1]
        dest = os.path.expanduser(dest)
        if not os.path.isabs(dest):
            dest = os.path.join(self.cwd, dest)
        try:
            if len(srcs) > 1:
                # dest must be directory
                if not os.path.isdir(dest):
                    safe_print("mv: when moving multiple files, destination must be a directory")
                    return
            for s in srcs:
                src = os.path.expanduser(s)
                if not os.path.isabs(src):
                    src = os.path.join(self.cwd, src)
                base = os.path.basename(src)
                target = dest if len(srcs) == 1 and not os.path.isdir(dest) else os.path.join(dest, base)
                os.rename(src, target)
        except Exception as e:
            safe_print(f"mv: {e}")

    def do_cp(self, argv):
        if len(argv) < 2:
            safe_print("cp: missing file operand")
            return
        import shutil
        srcs = argv[:-1]
        dest = argv[-1]
        dest = os.path.expanduser(dest)
        if not os.path.isabs(dest):
            dest = os.path.join(self.cwd, dest)
        try:
            if len(srcs) > 1:
                if not os.path.isdir(dest):
                    safe_print("cp: when copying multiple files, destination must be a directory")
                    return
            for s in srcs:
                src = os.path.expanduser(s)
                if not os.path.isabs(src):
                    src = os.path.join(self.cwd, src)
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(dest, os.path.basename(src)))
                else:
                    target = dest if len(srcs) == 1 and not os.path.isdir(dest) else os.path.join(dest, os.path.basename(src))
                    shutil.copy2(src, target)
        except Exception as e:
            safe_print(f"cp: {e}")

    def do_stat(self, argv):
        if not argv:
            safe_print("stat: missing operand")
            return
        for f in argv:
            target = os.path.expanduser(f)
            if not os.path.isabs(target):
                target = os.path.join(self.cwd, target)
            try:
                st = os.stat(target)
                safe_print(f"  File: {target}")
                safe_print(f"  Size: {st.st_size}\tBlocks: {getattr(st, 'st_blocks', 'N/A')}\tIO Block: {getattr(st, 'st_blksize', 'N/A')}")
                safe_print(f"Device: {getattr(st, 'st_dev', 'N/A')}\tInode: {getattr(st, 'st_ino', 'N/A')}\tLinks: {st.st_nlink}")
                safe_print(f"Access: {oct(st.st_mode)}")
                safe_print(f"Access: {datetime.fromtimestamp(st.st_atime)}")
                safe_print(f"Modify: {datetime.fromtimestamp(st.st_mtime)}")
                safe_print(f"Change: {datetime.fromtimestamp(st.st_ctime)}")
            except Exception as e:
                safe_print(f"stat: {e}")

    def do_echo(self, argv):
        safe_print(" ".join(argv))

    # ---- System monitoring commands ----
    def do_ps(self, argv):
        """ps - show running processes (simple)"""
        for p in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            try:
                info = p.info
                safe_print(f"{info.get('pid'):>6} {info.get('username')[:10]:<10} {info.get('cpu_percent'):>5}% {info.get('memory_percent'):>5.2f}% {info.get('name')}")
            except Exception:
                continue

    def do_top(self, argv):
        """top-like single snapshot: CPU and memory summary"""
        cpu = psutil.cpu_percent(interval=0.5, percpu=False)
        cpus = psutil.cpu_percent(interval=0.0, percpu=True)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        safe_print(f"CPU: {cpu}% overall")
        safe_print(f"Per-CPU: {', '.join(f'{c}%' for c in cpus)}")
        safe_print(f"Memory: {mem.percent}% ({human_size(mem.used)} / {human_size(mem.total)})")
        safe_print(f"Swap  : {swap.percent}% ({human_size(swap.used)} / {human_size(swap.total)})")
        safe_print("\nTop processes by CPU:")
        procs = sorted(psutil.process_iter(['pid','name','cpu_percent','memory_percent']), key=lambda p: p.info.get('cpu_percent',0), reverse=True)
        for p in procs[:10]:
            info = p.info
            safe_print(f"{info.get('pid'):>6} {info.get('cpu_percent',0):>5}% {info.get('memory_percent',0):>5.2f}% {info.get('name')}")

    def do_df(self, argv):
        """df - show disk usage"""
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                safe_print(f"{part.device} on {part.mountpoint} ({part.fstype}) - {usage.percent}% used ({human_size(usage.used)}/{human_size(usage.total)})")
            except Exception:
                continue

    # ---- Utilities ----
    def do_help(self, argv):
        safe_print("Built-in commands:")
        names = sorted(self.builtins.keys())
        safe_print("  " + ", ".join(names))
        safe_print("\nExternal commands are forwarded to the system shell.")
        safe_print("Type 'exit' or 'quit' to leave.")

    def do_clear(self, argv):
        subprocess.call('clear' if os.name != 'nt' else 'cls', shell=True)

    # ---- Natural-language heuristics (optional enhancement) ----
    def nl_to_cmd(self, text):
        """
        A very small heuristic natural language -> command mapper.
        This is NOT a full NLP model. It recognizes common patterns like:
            - create a new folder called X
            - make directory X
            - move fileA into dirB
            - copy fileA to dirB
            - delete/remove file X
            - list files in X / list files
            - show processes / show cpu/memory
        Returns a string command or None.
        """
        t = text.strip().lower()
        # create/mkdir
        m = re.search(r'(create|make|new)\s+(?:a\s+)?(?:folder|directory)\s+(?:called\s+)?["\']?([^\s"\']+)["\']?', t)
        if m:
            name = m.group(2)

