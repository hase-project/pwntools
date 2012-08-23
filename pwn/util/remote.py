import pwn, socket, time, sys
from threading import Thread
from excepthook import addexcepthook
from .consts import *

_DEFAULT_REMOTE_TIMEOUT = 10

class remote:
    def __init__(self, host, port = 1337, fam = None, typ = socket.SOCK_STREAM, proto = 0, **kwargs):
        self.target = (host, port)
        if fam is None:
            if host.find(':') <> -1:
                self.family = socket.AF_INET6
            else:
                self.family = socket.AF_INET
        self.type = typ
        self.proto = proto
        self.sock = None
        self.debug = pwn.DEBUG
        self.timeout = kwargs.get('timeout', _DEFAULT_REMOTE_TIMEOUT)
        self.checked = kwargs.get('checked', True)
        self.connect()

    def connect(self):
        self.close()
        self.sock = socket.socket(self.family, self.type, self.proto)
        if self.timeout is not None:
            self.sock.settimeout(self.timeout)
        if self.checked:
            try:
                self.sock.connect(self.target)
            except socket.error, e:
                if e.errno == 111:
                    pwn.trace(' [-] Connection to %s on port %d refused\n' % self.target)
                    exit(PWN_UNAVAILABLE)
                else:
                    raise
            except socket.timeout:
                pwn.trace(' [-] Timed out while connecting to %s on port %d\n' % self.target)
                exit(PWN_UNAVAILABLE)
        else:
            self.sock.connect(self.target)
        pwn.trace(' [+] Opened connection to %s on port %d\n' % self.target)

    def settimeout(self, n):
        self.timeout = n
        self.sock.settimeout(n)

    def setblocking(self, b):
        self.sock.setblocking(b)

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
            pwn.trace(' [+] Closed connection to %s on port %d\n' % self.target)

    def send(self, dat):
        if self.checked:
            try:
                return self.sock.send(dat)
            except socket.error, e:
                if e.errno == 32:
                    pwn.trace(' [-] Broken pipe\n')
                    exit(PWN_UNAVAILABLE)
                else:
                    raise
        else:
            return self.sock.send(dat)

    def recv(self, numb = 1024):
        if self.checked:
            try:
                res = self.sock.recv(numb)
            except socket.timeout:
                pwn.trace(' [-] Connection timed out\n')
                exit(PWN_UNAVAILABLE)
        else:
            res = self.sock.recv(numb)
        if self.debug:
            sys.stdout.write(res)
            sys.stdout.flush()
        return res

    def recvn(self, numb):
        res = []
        n = 0
        while n < numb:
            c = self.recv(1)
            if not c:
                break
            res.append(c)
            n += 1
        return ''.join(res)

    def recvuntil(self, delim):
        d = list(delim)
        res = []
        while d:
            c = self.recv(1)
            if not c:
                break
            res.append(c)
            if c == d[0]:
                d.pop(0)
            else:
                d = list(delim)
        return ''.join(res)

    def recvline(self, lines = 1):
        res = []
        for _ in range(lines):
            res.append(self.recvuntil('\n'))
        return ''.join(res)

    def interactive(self, prompt = '> '):
        pwn.trace(' [+] Switching to interactive mode\n')
        self.debug = True
        def loop():
            while True:
                self.recv()
        t = Thread(target = loop)
        t.daemon = True
        t.start()
        while True:
            try:
                time.sleep(0.1)
                self.send(raw_input(prompt) + '\n')
            except KeyboardInterrupt:
                break