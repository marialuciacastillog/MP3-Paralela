#!/usr/bin/env python3
"""
Ecosistema: zorros, conejos y rocas  -  interfaz grafica (Tkinter)
===================================================================

Visualiza la simulacion usando el modo ``all`` de los ejecutables C++
(secuencial u OpenMP) o, si no estan compilados, un motor Python integrado
que sigue exactamente las mismas reglas del enunciado.

Requisitos del proyecto que cubre:
  * Visualizacion de la matriz con todas las entidades.
  * Estadisticas: poblacion de conejos / zorros / rocas a lo largo del tiempo.
  * Parametros ajustables: GEN_PROC_RABBITS, GEN_PROC_FOXES, GEN_FOOD_FOXES,
    N_GEN, tamano del mundo y poblaciones iniciales (conejos, zorros, rocas).
  * Control del tiempo: iniciar / pausa, paso a paso, mas rapido, mas lento.

Uso:  python app.py          (desde cualquier carpeta)
"""
import os
import sys
import math
import time
import queue
import random
import tempfile
import threading
import subprocess

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
EXE = '.exe' if os.name == 'nt' else ''

EMPTY, ROCK, RABBIT, FOX = 0, 1, 2, 3
KIND_NAME = {'ROCK': ROCK, 'RABBIT': RABBIT, 'FOX': FOX}
KIND_WORD = {ROCK: 'ROCK', RABBIT: 'RABBIT', FOX: 'FOX'}

# ----------------------------------------------------------------------------
#  Paleta (tema oscuro)
# ----------------------------------------------------------------------------
BG = '#10161a'          # fondo de la ventana
PANEL = '#182126'       # tarjetas
PANEL2 = '#1f2b31'      # tarjetas elevadas / campos
LINE = '#2a3a42'        # bordes
TEXT = '#e8eef1'
MUTED = '#8fa3ad'
ACCENT = '#3ecf8e'
ACCENT_D = '#2ea872'
FIELD = '#27473a'       # pasto
FIELD_ALT = '#2b4e3f'
FIELD_LINE = '#355c4a'
C_RABBIT = '#f3ead9'
C_RABBIT_D = '#b9a98c'
C_PINK = '#f2a1b5'
C_FOX = '#ff7a2f'
C_FOX_D = '#b84a10'
C_ROCK = '#8c98a4'
C_ROCK_L = '#b5bfc8'
C_ROCK_D = '#5c6772'
C_DARK = '#1c1410'

FONT = 'Segoe UI' if os.name == 'nt' else 'DejaVu Sans'


# ----------------------------------------------------------------------------
#  Escenario (parametros + objetos iniciales)
# ----------------------------------------------------------------------------
class Scenario:
    """Parametros de las reglas, tamano del mundo y objetos iniciales."""

    def __init__(self, gpr=2, gpf=4, gff=3, ngen=100, rows=10, cols=10, objects=None):
        self.gpr, self.gpf, self.gff, self.ngen = gpr, gpf, gff, ngen
        self.rows, self.cols = rows, cols
        self.objects = list(objects or [])      # [(tipo, fila, columna)]

    def copy(self):
        return Scenario(self.gpr, self.gpf, self.gff, self.ngen, self.rows, self.cols,
                        self.objects)

    def counts(self):
        c = {ROCK: 0, RABBIT: 0, FOX: 0}
        for k, _, _ in self.objects:
            c[k] += 1
        return c

    def validate(self):
        if self.rows < 1 or self.cols < 1:
            raise ValueError('R y C deben ser al menos 1.')
        if self.ngen < 0:
            raise ValueError('N_GEN no puede ser negativo.')
        seen = set()
        for k, x, y in self.objects:
            if not (0 <= x < self.rows and 0 <= y < self.cols):
                raise ValueError('El objeto %s en (%d, %d) queda fuera de la matriz %dx%d.\n'
                                 'Aumenta R/C o genera un mundo nuevo.'
                                 % (KIND_WORD[k], x, y, self.rows, self.cols))
            if (x, y) in seen:
                raise ValueError('Hay dos objetos en la misma celda (%d, %d).' % (x, y))
            seen.add((x, y))

    def to_text(self):
        """Texto en el formato de entrada del enunciado."""
        out = ['%d %d %d %d %d %d %d' % (self.gpr, self.gpf, self.gff, self.ngen,
                                         self.rows, self.cols, len(self.objects))]
        out += ['%s %d %d' % (KIND_WORD[k], x, y) for k, x, y in self.objects]
        return '\n'.join(out) + '\n'

    def world_rows(self):
        """Generacion 0 como lista de cadenas (' ', '*', 'R', 'F')."""
        grid = [[' '] * self.cols for _ in range(self.rows)]
        ch = {ROCK: '*', RABBIT: 'R', FOX: 'F'}
        for k, x, y in self.objects:
            grid[x][y] = ch[k]
        return [''.join(r) for r in grid]

    @staticmethod
    def from_text(text):
        tok = text.split()
        if len(tok) < 7:
            raise ValueError('La primera linea debe tener 7 numeros:\n'
                             'GEN_PROC_RABBITS GEN_PROC_FOXES GEN_FOOD_FOXES N_GEN R C N')
        try:
            gpr, gpf, gff, ngen, rows, cols, n = [int(t) for t in tok[:7]]
        except ValueError:
            raise ValueError('Los parametros de la primera linea deben ser enteros.')
        rest = tok[7:]
        if len(rest) < 3 * n:
            raise ValueError('El archivo dice que hay %d objetos pero tiene menos.' % n)
        objs = []
        for i in range(n):
            name, x, y = rest[3 * i], rest[3 * i + 1], rest[3 * i + 2]
            if name not in KIND_NAME:
                raise ValueError('Objeto desconocido: %r (usa ROCK, RABBIT o FOX).' % name)
            objs.append((KIND_NAME[name], int(x), int(y)))
        scn = Scenario(gpr, gpf, gff, ngen, rows, cols, objs)
        scn.validate()
        return scn

    @staticmethod
    def random(rows, cols, n_rabbits, n_foxes, n_rocks, seed, gpr, gpf, gff, ngen):
        total = n_rabbits + n_foxes + n_rocks
        if total > rows * cols:
            raise ValueError('Hay mas animales/rocas (%d) que celdas (%d).' % (total, rows * cols))
        rng = random.Random(seed)
        cells = rng.sample(range(rows * cols), total)
        kinds = [ROCK] * n_rocks + [RABBIT] * n_rabbits + [FOX] * n_foxes
        objs = [(k, c // cols, c % cols) for k, c in zip(kinds, cells)]
        objs.sort(key=lambda o: (o[1], o[2]))
        return Scenario(gpr, gpf, gff, ngen, rows, cols, objs)


# ----------------------------------------------------------------------------
#  Motor Python integrado (mismas reglas que el C++; solo para visualizar)
# ----------------------------------------------------------------------------
DIRS = ((-1, 0), (0, 1), (1, 0), (0, -1))   # norte, este, sur, oeste (sentido horario)


def py_engine_lines(scn):
    """Genera las lineas del modo ``all`` del programa C++ (una por vez)."""
    R, C = scn.rows, scn.cols
    t = [[EMPTY] * C for _ in range(R)]
    pa = [[0] * C for _ in range(R)]       # edad de reproduccion
    fa = [[0] * C for _ in range(R)]       # hambre
    for k, x, y in scn.objects:
        t[x][y] = k

    def choose(x, y, wanted, g):
        opts = [(x + dx, y + dy) for dx, dy in DIRS
                if 0 <= x + dx < R and 0 <= y + dy < C and t[x + dx][y + dy] == wanted]
        return opts[(g + x + y) % len(opts)] if opts else None

    def move_rabbits(g):
        nt = [row[:] for row in t]
        npa = [row[:] for row in pa]
        nfa = [row[:] for row in fa]
        for x in range(R):
            for y in range(C):
                if t[x][y] == RABBIT:
                    nt[x][y], npa[x][y], nfa[x][y] = EMPTY, 0, 0
        for x in range(R):
            for y in range(C):
                if t[x][y] != RABBIT:
                    continue
                age = pa[x][y]
                dest = choose(x, y, EMPTY, g)
                if dest is None:
                    nt[x][y], npa[x][y], nfa[x][y] = RABBIT, age + 1, 0
                    continue
                if age >= scn.gpr:
                    nt[x][y], npa[x][y], nfa[x][y] = RABBIT, 0, 0
                    age = 0
                else:
                    age += 1
                dx, dy = dest
                if nt[dx][dy] != RABBIT or age > npa[dx][dy]:
                    nt[dx][dy], npa[dx][dy], nfa[dx][dy] = RABBIT, age, 0
        return nt, npa, nfa

    def move_foxes(g):
        nt = [row[:] for row in t]
        npa = [row[:] for row in pa]
        nfa = [row[:] for row in fa]
        for x in range(R):
            for y in range(C):
                if t[x][y] == FOX:
                    nt[x][y], npa[x][y], nfa[x][y] = EMPTY, 0, 0
        for x in range(R):
            for y in range(C):
                if t[x][y] != FOX:
                    continue
                age, hunger = pa[x][y], fa[x][y]
                dest = choose(x, y, RABBIT, g)
                alive = True
                if dest is not None:
                    hunger = 0
                else:
                    hunger += 1
                    if hunger >= scn.gff:
                        alive = False
                    else:
                        dest = choose(x, y, EMPTY, g)
                if not alive:
                    continue
                if dest is None:
                    nt[x][y], npa[x][y], nfa[x][y] = FOX, age + 1, hunger
                    continue
                if age >= scn.gpf:
                    nt[x][y], npa[x][y], nfa[x][y] = FOX, 0, 0
                    age = 0
                else:
                    age += 1
                dx, dy = dest
                keep = True
                if nt[dx][dy] == FOX:
                    if age < npa[dx][dy]:
                        keep = False
                    elif age == npa[dx][dy] and hunger >= nfa[dx][dy]:
                        keep = False
                if keep:
                    nt[dx][dy], npa[dx][dy], nfa[dx][dy] = FOX, age, hunger
        return nt, npa, nfa

    border = '-' * (C + 2)
    border = border + '   ' + border + ' ' + border
    for g in range(scn.ngen + 1):
        if g > 0:
            yield ''
        yield 'Generation %d' % g
        yield border
        for x in range(R):
            w, a, f = [], [], []
            for y in range(C):
                k = t[x][y]
                if k == EMPTY:
                    w.append(' '); a.append(' '); f.append(' ')
                elif k == ROCK:
                    w.append('*'); a.append('*'); f.append('*')
                elif k == RABBIT:
                    w.append('R'); a.append(str(pa[x][y])); f.append('R')
                else:
                    w.append('F'); a.append(str(pa[x][y])); f.append(str(fa[x][y]))
            yield '|%s|   |%s| |%s|' % (''.join(w), ''.join(a), ''.join(f))
        yield border
        if g < scn.ngen:
            t, pa, fa = move_rabbits(g)
            t, pa, fa = move_foxes(g)


# ----------------------------------------------------------------------------
#  Frames (una generacion ya interpretada)
# ----------------------------------------------------------------------------
class Frame:
    __slots__ = ('gen', 'world', 'ages', 'foods', 'rabbits', 'foxes', 'rocks')

    def __init__(self, gen, world, ages, foods):
        self.gen = gen
        self.world = world
        self.ages = ages
        self.foods = foods
        self.rabbits = sum(r.count('R') for r in world)
        self.foxes = sum(r.count('F') for r in world)
        self.rocks = sum(r.count('*') for r in world)


def parse_row(line):
    """'|mundo|   |edades| |hambre|'  ->  (mundo, edades, hambre) o None."""
    parts = line.split('|')
    if len(parts) < 7:
        return None
    return parts[1], parts[3], parts[5]


def default_exe(kind):
    """Busca el ejecutable compilado (build/ o junto a las fuentes)."""
    if kind == 'seq':
        names = [os.path.join(REPO, 'build', 'ecosistema_seq' + EXE),
                 os.path.join(REPO, 'secuencial', 'ecosistema' + EXE)]
    else:
        names = [os.path.join(REPO, 'build', 'ecosistema_par' + EXE),
                 os.path.join(REPO, 'paralela', 'ecosistema' + EXE)]
    for n in names:
        if os.path.isfile(n):
            return n
    return names[0]


# ----------------------------------------------------------------------------
#  Una ejecucion (proceso C++ o motor Python) leida en un hilo aparte
# ----------------------------------------------------------------------------
class Run:
    """Cada ejecucion tiene su propia cola, asi un reinicio nunca mezcla datos viejos."""
    DONE = object()

    def __init__(self, scn, engine, exe=None, threads=None):
        self.scn = scn
        self.engine = engine            # 'seq' | 'par' | 'py'
        self.exe = exe
        self.threads = threads
        self.frames = queue.Queue(maxsize=300)   # cola acotada = control de flujo
        self.logs = queue.Queue()
        self.stop_evt = threading.Event()
        self.proc = None
        self.tmp = None
        self.keep_ages = scn.rows * scn.cols <= 4096
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        if self.engine != 'py':
            fd, self.tmp = tempfile.mkstemp(prefix='eco_', suffix='.txt')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(self.scn.to_text())
            env = os.environ.copy()
            # Windows: permite que los ejecutables GCC/MSYS2 encuentren sus DLL
            # aunque la GUI de Python se haya iniciado desde PowerShell/VS Code.
            if os.name == 'nt':
                dll_dirs = [
                    r'C:\msys64\ucrt64\bin',
                    r'C:\msys64\mingw64\bin',
                ]
                for dll_dir in dll_dirs:
                    if os.path.isdir(dll_dir):
                        env['PATH'] = dll_dir + os.pathsep + env.get('PATH', '')
                        break
            if self.threads and self.engine == 'par':
                env['OMP_NUM_THREADS'] = str(self.threads)
            flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            self.proc = subprocess.Popen(
                [self.exe, 'all'], stdin=open(self.tmp, 'rb'),
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace', bufsize=1,
                env=env, creationflags=flags)
        self.thread.start()

    def stop(self):
        self.stop_evt.set()
        p = self.proc
        if p is not None and p.poll() is None:
            try:
                p.kill()
            except OSError:
                pass

    def _put(self, item):
        while not self.stop_evt.is_set():
            try:
                self.frames.put(item, timeout=0.1)
                return True
            except queue.Full:
                pass
        return False

    def _read_stderr(self, sink):
        try:
            for line in self.proc.stderr:
                line = line.strip()
                if line:
                    sink.append(line)
                    self.logs.put(line)
        except Exception:
            pass

    def _run(self):
        err_lines = []
        try:
            if self.engine == 'py':
                lines = py_engine_lines(self.scn)
            else:
                threading.Thread(target=self._read_stderr, args=(err_lines,),
                                 daemon=True).start()
                lines = self.proc.stdout
            cur, world, ages, foods = None, [], [], []
            R = self.scn.rows

            def flush():
                if cur is not None and len(world) == R:
                    return self._put(Frame(cur, world, ages or None, foods or None))
                return True

            for raw in lines:
                if self.stop_evt.is_set():
                    return
                line = raw.rstrip('\r\n')
                if line.startswith('Generation '):
                    if not flush():
                        return
                    try:
                        cur = int(line.split()[1])
                    except (IndexError, ValueError):
                        cur = 0
                    world, ages, foods = [], [], []
                elif line.startswith('|'):
                    row = parse_row(line)
                    if row:
                        world.append(row[0])
                        if self.keep_ages and len(row[1]) == len(row[0]) == len(row[2]):
                            ages.append(row[1])
                            foods.append(row[2])
            if not flush():
                return
            if self.proc is not None:
                code = self.proc.wait()
                if code != 0 and not self.stop_evt.is_set():
                    self._put(('error', 'El motor termino con error (codigo %s).\n%s'
                               % (code, '\n'.join(err_lines[-5:]))))
                    return
            self._put(Run.DONE)
        except Exception as e:          # cualquier fallo se muestra en la ventana
            self._put(('error', '%s: %s' % (type(e).__name__, e)))
        finally:
            if self.proc is not None:
                try:
                    if self.proc.poll() is None:
                        self.proc.kill()
                    self.proc.wait()
                except Exception:
                    pass
            if self.tmp:
                try:
                    os.remove(self.tmp)
                except OSError:
                    pass


# ----------------------------------------------------------------------------
#  Dibujo de entidades (vectorial, no depende de fuentes de emojis)
# ----------------------------------------------------------------------------
def _oval(c, x, y, s, u1, v1, u2, v2, fill, outline='', w=1):
    return c.create_oval(x + u1 * s, y + v1 * s, x + u2 * s, y + v2 * s,
                         fill=fill, outline=outline, width=w)


def _poly(c, x, y, s, pts, fill, outline='', smooth=False, w=1):
    flat = []
    for u, v in pts:
        flat += [x + u * s, y + v * s]
    return c.create_polygon(*flat, fill=fill, outline=outline, smooth=smooth, width=w)


def draw_rabbit(c, x, y, s):
    w = max(1, s / 40)
    _oval(c, x, y, s, .22, .52, .78, .95, C_RABBIT, C_RABBIT_D, w)             # cuerpo
    _oval(c, x, y, s, .27, .02, .44, .46, C_RABBIT, C_RABBIT_D, w)             # orejas
    _oval(c, x, y, s, .56, .02, .73, .46, C_RABBIT, C_RABBIT_D, w)
    _oval(c, x, y, s, .32, .09, .39, .36, C_PINK)
    _oval(c, x, y, s, .61, .09, .68, .36, C_PINK)
    _oval(c, x, y, s, .2, .3, .8, .76, C_RABBIT, C_RABBIT_D, w)                # cabeza
    _oval(c, x, y, s, .34, .45, .42, .55, C_DARK)                              # ojos
    _oval(c, x, y, s, .58, .45, .66, .55, C_DARK)
    _oval(c, x, y, s, .45, .57, .55, .65, C_PINK)                              # nariz


def draw_fox(c, x, y, s):
    w = max(1, s / 40)
    _poly(c, x, y, s, [(.12, .06), (.42, .3), (.16, .5)], C_FOX, C_FOX_D, w=w)  # orejas
    _poly(c, x, y, s, [(.88, .06), (.58, .3), (.84, .5)], C_FOX, C_FOX_D, w=w)
    _poly(c, x, y, s, [(.2, .16), (.34, .32), (.2, .42)], C_DARK)
    _poly(c, x, y, s, [(.8, .16), (.66, .32), (.8, .42)], C_DARK)
    _poly(c, x, y, s, [(.1, .3), (.9, .3), (.92, .58), (.5, .95), (.08, .58)],
          C_FOX, C_FOX_D, smooth=True, w=w)                                    # cabeza
    _poly(c, x, y, s, [(.1, .56), (.34, .5), (.5, .6), (.66, .5), (.9, .56), (.5, .94)],
          '#fff4e8', smooth=True)                                              # mejillas
    _oval(c, x, y, s, .3, .4, .4, .52, C_DARK)                                 # ojos
    _oval(c, x, y, s, .6, .4, .7, .52, C_DARK)
    _oval(c, x, y, s, .44, .82, .56, .93, C_DARK)                              # nariz


def draw_rock(c, x, y, s):
    w = max(1, s / 40)
    _oval(c, x, y, s, .1, .74, .92, .94, '#1c2d25')                            # sombra
    _poly(c, x, y, s, [(.1, .76), (.16, .42), (.4, .2), (.68, .24), (.88, .5),
                       (.92, .78), (.7, .88), (.3, .88)],
          C_ROCK, C_ROCK_D, smooth=True, w=w)
    _poly(c, x, y, s, [(.22, .5), (.4, .3), (.6, .32), (.46, .46)], C_ROCK_L, smooth=True)


def round_rect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


# ----------------------------------------------------------------------------
#  Interfaz
# ----------------------------------------------------------------------------
ENGINES = [('Secuencial (C++)', 'seq'), ('Paralela OpenMP (C++)', 'par')]


class EcosystemGUI:
    TICK_MS = 30

    def __init__(self, root):
        self.root = root
        root.title('Ecosistema - zorros, conejos y rocas')
        root.geometry('1280x800')
        root.minsize(1100, 700)
        root.configure(bg=BG)

        self.scn = Scenario(2, 4, 3, 60, 5, 5)
        self.run = None
        self.frame = None               # frame mostrado
        self.history = []               # (gen, conejos, zorros, rocas)
        self.playing = False
        self.pending = 0                # pasos manuales pedidos
        self.acc = 0.0
        self.last_t = time.monotonic()
        self.finished = False
        self.exe = {'seq': default_exe('seq'), 'par': default_exe('par')}
        self.photo = None
        self._redraw_job = None

        self.v = {k: tk.StringVar() for k in
                  ('gpr', 'gpf', 'gff', 'ngen', 'rows', 'cols', 'rab', 'fox', 'rock', 'seed')}
        self.v_engine = tk.StringVar(value=ENGINES[0][0])
        self.v_threads = tk.StringVar(value=str(os.cpu_count() or 4))
        self.v_file = tk.StringVar(value='(ninguno)')
        self.v_exe = tk.StringVar()
        self.v_speed = tk.DoubleVar(value=1.0)      # escala log10 de gen/s
        self.v_state = tk.StringVar(value='Listo')
        self.v_hover = tk.StringVar(value='')

        self._style()
        self._build()
        self._fill_fields(self.scn)
        self._engine_changed()
        self.show_scenario()
        self.root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.root.after(self.TICK_MS, self._tick)

    # ---------------------------------------------------------------- estilo
    def _style(self):
        st = ttk.Style()
        try:
            st.theme_use('clam')
        except tk.TclError:
            pass
        st.configure('.', background=BG, foreground=TEXT, fieldbackground=PANEL2,
                     bordercolor=LINE, lightcolor=PANEL, darkcolor=PANEL,
                     troughcolor=PANEL2, font=(FONT, 10))
        st.configure('TFrame', background=BG)
        st.configure('Card.TFrame', background=PANEL)
        st.configure('TLabel', background=BG, foreground=TEXT)
        st.configure('Card.TLabel', background=PANEL, foreground=TEXT)
        st.configure('Muted.TLabel', background=PANEL, foreground=MUTED, font=(FONT, 9))
        st.configure('H.TLabel', background=PANEL, foreground=TEXT, font=(FONT, 12, 'bold'))
        st.configure('Title.TLabel', background=BG, foreground=TEXT, font=(FONT, 17, 'bold'))
        st.configure('Sub.TLabel', background=BG, foreground=MUTED, font=(FONT, 10))
        st.configure('TButton', background=PANEL2, foreground=TEXT, padding=(12, 7),
                     borderwidth=0, focusthickness=0, font=(FONT, 10, 'bold'))
        st.map('TButton', background=[('active', LINE), ('disabled', PANEL)],
               foreground=[('disabled', MUTED)])
        st.configure('Accent.TButton', background=ACCENT, foreground='#06251a')
        st.map('Accent.TButton', background=[('active', ACCENT_D), ('disabled', PANEL2)])
        st.configure('TEntry', fieldbackground=PANEL2, foreground=TEXT, insertcolor=TEXT,
                     bordercolor=LINE, padding=4)
        st.configure('TSpinbox', fieldbackground=PANEL2, foreground=TEXT, insertcolor=TEXT,
                     arrowcolor=TEXT, bordercolor=LINE, padding=3)
        st.configure('TCombobox', fieldbackground=PANEL2, foreground=TEXT, arrowcolor=TEXT,
                     bordercolor=LINE, padding=4)
        st.map('TCombobox', fieldbackground=[('readonly', PANEL2)],
               foreground=[('readonly', TEXT)], selectbackground=[('readonly', PANEL2)],
               selectforeground=[('readonly', TEXT)])
        self.root.option_add('*TCombobox*Listbox.background', PANEL2)
        self.root.option_add('*TCombobox*Listbox.foreground', TEXT)
        self.root.option_add('*TCombobox*Listbox.selectBackground', ACCENT_D)
        st.configure('Horizontal.TScale', background=PANEL, troughcolor=PANEL2)
        st.configure('Horizontal.TProgressbar', background=ACCENT, troughcolor=PANEL2,
                     bordercolor=PANEL, lightcolor=ACCENT, darkcolor=ACCENT)
        st.configure('TNotebook', background=PANEL, borderwidth=0, tabmargins=(0, 0, 0, 0))
        st.configure('TNotebook.Tab', background=PANEL, foreground=MUTED,
                     padding=(14, 8), borderwidth=0, font=(FONT, 10, 'bold'))
        st.map('TNotebook.Tab', background=[('selected', PANEL2)],
               foreground=[('selected', TEXT)])

    # ------------------------------------------------------------ construccion
    def _card(self, parent, **pack):
        f = ttk.Frame(parent, style='Card.TFrame', padding=12)
        f.pack(**pack)
        return f

    def _build(self):
        # Encabezado
        head = ttk.Frame(self.root, padding=(18, 14, 18, 4))
        head.pack(fill='x')
        left = ttk.Frame(head)
        left.pack(side='left')
        ttk.Label(left, text='Ecosistema', style='Title.TLabel').pack(anchor='w')
        ttk.Label(left, text='Zorros, conejos y rocas: dinamica depredador-presa',
                  style='Sub.TLabel').pack(anchor='w')
        self.chip = tk.Label(head, textvariable=self.v_state, bg=PANEL2, fg=ACCENT,
                             font=(FONT, 10, 'bold'), padx=14, pady=6)
        self.chip.pack(side='right')

        body = ttk.Frame(self.root, padding=(18, 8, 18, 16))
        body.pack(fill='both', expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        body.rowconfigure(0, weight=1)

        # ---------- columna izquierda: mundo + controles
        lcol = ttk.Frame(body)
        lcol.grid(row=0, column=0, sticky='nsew', padx=(0, 14))
        world = ttk.Frame(lcol, style='Card.TFrame', padding=12)
        world.pack(fill='both', expand=True)
        wh = ttk.Frame(world, style='Card.TFrame')
        wh.pack(fill='x')
        self.lbl_gen = ttk.Label(wh, text='Generacion 0', style='H.TLabel')
        self.lbl_gen.pack(side='left')
        ttk.Label(wh, textvariable=self.v_hover, style='Muted.TLabel').pack(side='right')
        self.canvas = tk.Canvas(world, bg=PANEL, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, pady=(8, 8))
        self.canvas.bind('<Configure>', lambda e: self._schedule_redraw())
        self.canvas.bind('<Motion>', self._on_hover)
        self.canvas.bind('<Leave>', lambda e: self.v_hover.set(''))
        self.legend = tk.Canvas(world, height=34, bg=PANEL, highlightthickness=0)
        self.legend.pack(fill='x')
        self._draw_legend()

        ctl = ttk.Frame(lcol, style='Card.TFrame', padding=12)
        ctl.pack(fill='x', pady=(12, 0))
        row1 = ttk.Frame(ctl, style='Card.TFrame')
        row1.pack(fill='x')
        # Selector de motor visible junto a los controles principales.
        ttk.Label(row1, text='Motor:', style='Muted.TLabel').pack(side='left', padx=(0, 6))
        self.cb_engine = ttk.Combobox(
            row1, textvariable=self.v_engine, state='readonly', width=22,
            values=[name for name, _ in ENGINES]
        )
        self.cb_engine.pack(side='left', padx=(0, 10))
        self.cb_engine.bind('<<ComboboxSelected>>', lambda e: self._engine_changed())

        self.btn_play = ttk.Button(row1, text='\u25B6  Iniciar', style='Accent.TButton',
                                   command=self.toggle_play, width=13)
        self.btn_play.pack(side='left')
        ttk.Button(row1, text='\u23ED  Paso', command=self.step, width=9).pack(side='left', padx=8)
        ttk.Button(row1, text='\u27F2  Reiniciar', command=self.restart,
                   width=12).pack(side='left')
        ttk.Button(row1, text='\u25B6\u25B6', command=lambda: self._bump_speed(+0.25),
                   width=4).pack(side='right')
        self.lbl_speed = ttk.Label(row1, text='', style='Card.TLabel', width=11, anchor='center')
        self.lbl_speed.pack(side='right', padx=4)
        ttk.Button(row1, text='\u25C0\u25C0', command=lambda: self._bump_speed(-0.25),
                   width=4).pack(side='right')
        row2 = ttk.Frame(ctl, style='Card.TFrame')
        row2.pack(fill='x', pady=(10, 0))
        ttk.Label(row2, text='Velocidad', style='Muted.TLabel').pack(side='left')
        ttk.Scale(row2, from_=-0.3, to=2.7, variable=self.v_speed, orient='horizontal',
                  command=lambda _=None: self._speed_changed()).pack(side='left', fill='x',
                                                                      expand=True, padx=10)
        self.progress = ttk.Progressbar(ctl, mode='determinate', maximum=100)
        self.progress.pack(fill='x', pady=(10, 0))

        # ---------- columna derecha: estadisticas + parametros
        rcol = ttk.Frame(body, width=420)
        rcol.grid(row=0, column=1, sticky='ns')
        rcol.pack_propagate(False)
        rcol.configure(width=420)

        cards = ttk.Frame(rcol)
        cards.pack(fill='x')
        self.stat = {}
        for i, (key, name, col) in enumerate((('rabbits', 'Conejos', C_RABBIT),
                                              ('foxes', 'Zorros', C_FOX),
                                              ('rocks', 'Rocas', C_ROCK))):
            f = tk.Frame(cards, bg=PANEL, padx=12, pady=8)
            f.grid(row=0, column=i, sticky='ew', padx=(0 if i == 0 else 8, 0))
            cards.columnconfigure(i, weight=1, uniform='s')
            tk.Label(f, text=name.upper(), bg=PANEL, fg=MUTED, font=(FONT, 8, 'bold')).pack(anchor='w')
            lbl = tk.Label(f, text='0', bg=PANEL, fg=col, font=(FONT, 22, 'bold'))
            lbl.pack(anchor='w')
            self.stat[key] = lbl

        chart_card = ttk.Frame(rcol, style='Card.TFrame', padding=12)
        chart_card.pack(fill='x', pady=(12, 0))
        ttk.Label(chart_card, text='Poblacion en el tiempo', style='H.TLabel').pack(anchor='w')
        self.chart = tk.Canvas(chart_card, height=215, bg=PANEL, highlightthickness=0)
        self.chart.pack(fill='x', pady=(6, 0))
        self.chart.bind('<Configure>', lambda e: self.draw_chart())

        nb_card = ttk.Frame(rcol, style='Card.TFrame')
        nb_card.pack(fill='both', expand=True, pady=(12, 0))
        nb = ttk.Notebook(nb_card)
        nb.pack(fill='both', expand=True)
        tab_p = ttk.Frame(nb, style='Card.TFrame', padding=12)
        tab_l = ttk.Frame(nb, style='Card.TFrame', padding=8)
        nb.add(tab_p, text='Parametros')
        nb.add(tab_l, text='Registro')
        self._build_params(tab_p)
        self.log = tk.Text(tab_l, height=8, bg=PANEL2, fg=TEXT, relief='flat', wrap='word',
                           font=(FONT, 9), state='disabled', padx=8, pady=6,
                           highlightthickness=0, insertbackground=TEXT)
        self.log.pack(fill='both', expand=True)

    def _build_params(self, p):
        def field(parent, label, key, r, c, width=7):
            ttk.Label(parent, text=label, style='Muted.TLabel').grid(row=r, column=c * 2,
                                                                    sticky='w', pady=3)
            e = ttk.Entry(parent, textvariable=self.v[key], width=width)
            e.grid(row=r, column=c * 2 + 1, sticky='w', padx=(6, 14), pady=3)
            return e

        # Escenario
        top = ttk.Frame(p, style='Card.TFrame')
        top.pack(fill='x')
        ttk.Button(top, text='Abrir archivo...', command=self.pick_input).pack(side='left')
        ttk.Label(top, textvariable=self.v_file, style='Muted.TLabel').pack(side='left', padx=10)

        ttk.Label(p, text='REGLAS', style='Muted.TLabel').pack(anchor='w', pady=(12, 0))
        g = ttk.Frame(p, style='Card.TFrame')
        g.pack(fill='x')
        field(g, 'Reprod. conejos', 'gpr', 0, 0)
        field(g, 'Reprod. zorros', 'gpf', 0, 1)
        field(g, 'Hambre zorros', 'gff', 1, 0)
        field(g, 'Generaciones', 'ngen', 1, 1)

        ttk.Label(p, text='MUNDO Y POBLACION INICIAL', style='Muted.TLabel').pack(anchor='w',
                                                                                 pady=(10, 0))
        g2 = ttk.Frame(p, style='Card.TFrame')
        g2.pack(fill='x')
        field(g2, 'Filas (R)', 'rows', 0, 0)
        field(g2, 'Columnas (C)', 'cols', 0, 1)
        field(g2, 'Conejos', 'rab', 1, 0)
        field(g2, 'Zorros', 'fox', 1, 1)
        field(g2, 'Rocas', 'rock', 2, 0)
        field(g2, 'Semilla', 'seed', 2, 1)
        b = ttk.Frame(p, style='Card.TFrame')
        b.pack(fill='x', pady=(8, 0))
        ttk.Button(b, text='Generar mundo aleatorio', command=self.generate).pack(side='left')
        ttk.Button(b, text='Aplicar reglas', command=self.apply_rules).pack(side='left', padx=8)

        # La seleccion del motor esta en la barra principal; aqui quedan
        # los ajustes especificos del motor (hilos y ruta del ejecutable).
        ttk.Label(p, text='AJUSTES DEL MOTOR', style='Muted.TLabel').pack(
            anchor='w', pady=(10, 0))
        m = ttk.Frame(p, style='Card.TFrame')
        m.pack(fill='x')
        ttk.Label(m, text='Hilos (solo OpenMP)', style='Muted.TLabel').pack(side='left')
        self.sp_threads = ttk.Spinbox(m, from_=1, to=64, width=5, textvariable=self.v_threads)
        self.sp_threads.pack(side='left', padx=(8, 0))
        e = ttk.Frame(p, style='Card.TFrame')
        e.pack(fill='x', pady=(6, 0))
        ttk.Label(e, textvariable=self.v_exe, style='Muted.TLabel', wraplength=330,
                  justify='left').pack(side='left', fill='x', expand=True)
        self.btn_exe = ttk.Button(e, text='Cambiar...', command=self.pick_exe)
        self.btn_exe.pack(side='right')
        ttk.Label(p, text='Los cambios se aplican al (re)iniciar la simulacion.',
                  style='Muted.TLabel').pack(anchor='w', pady=(8, 0))

    # ------------------------------------------------------------------ utilidades
    def log_msg(self, s):
        self.log.configure(state='normal')
        self.log.insert('end', time.strftime('%H:%M:%S  ') + s + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def set_state(self, text, color=ACCENT):
        self.v_state.set(text)
        self.chip.configure(fg=color)

    def engine_key(self):
        name = self.v_engine.get()
        for n, k in ENGINES:
            if n == name:
                return k
        return 'seq'

    def _engine_changed(self):
        k = self.engine_key()
        self.v_exe.set(self.exe[k])
        self.btn_exe.state(['!disabled'])
        self.sp_threads.state(['!disabled'] if k == 'par' else ['disabled'])

    def pick_exe(self):
        k = self.engine_key()
        p = filedialog.askopenfilename(title='Selecciona el ejecutable',
                                       initialdir=os.path.join(REPO, 'build'))
        if p:
            self.exe[k] = p
            self._engine_changed()

    def _fill_fields(self, s):
        c = s.counts()
        for key, val in (('gpr', s.gpr), ('gpf', s.gpf), ('gff', s.gff), ('ngen', s.ngen),
                         ('rows', s.rows), ('cols', s.cols), ('rab', c[RABBIT]),
                         ('fox', c[FOX]), ('rock', c[ROCK])):
            self.v[key].set(str(val))
        if not self.v['seed'].get():
            self.v['seed'].set('1')

    def _int(self, key, label, minimum=0):
        try:
            n = int(self.v[key].get().strip())
        except ValueError:
            raise ValueError('"%s" debe ser un numero entero.' % label)
        if n < minimum:
            raise ValueError('"%s" debe ser al menos %d.' % (label, minimum))
        return n

    def _read_rules(self):
        return (self._int('gpr', 'Reprod. conejos'), self._int('gpf', 'Reprod. zorros'),
                self._int('gff', 'Hambre zorros', 1), self._int('ngen', 'Generaciones'))

    # ------------------------------------------------------------ escenario
    def pick_input(self):
        init = os.path.join(REPO, 'tests')
        p = filedialog.askopenfilename(title='Selecciona un archivo de entrada',
                                       initialdir=init if os.path.isdir(init) else REPO,
                                       filetypes=[('Entradas', 'input*'), ('Todos', '*')])
        if not p:
            return
        try:
            with open(p, encoding='utf-8') as f:
                scn = Scenario.from_text(f.read())
        except (OSError, ValueError) as e:
            messagebox.showerror('Entrada no valida', str(e))
            return
        self.v_file.set(os.path.basename(p))
        self._set_scenario(scn)
        self.log_msg('Cargado %s (%dx%d, %d objetos)' % (os.path.basename(p), scn.rows,
                                                         scn.cols, len(scn.objects)))

    def generate(self):
        try:
            gpr, gpf, gff, ngen = self._read_rules()
            scn = Scenario.random(self._int('rows', 'Filas', 1), self._int('cols', 'Columnas', 1),
                                  self._int('rab', 'Conejos'), self._int('fox', 'Zorros'),
                                  self._int('rock', 'Rocas'), self._int('seed', 'Semilla'),
                                  gpr, gpf, gff, ngen)
        except ValueError as e:
            messagebox.showerror('Parametros', str(e))
            return
        self.v_file.set('(aleatorio)')
        self._set_scenario(scn)
        self.log_msg('Mundo aleatorio %dx%d: %d conejos, %d zorros, %d rocas' % (
            scn.rows, scn.cols, self.v['rab'].get() and int(self.v['rab'].get()),
            int(self.v['fox'].get()), int(self.v['rock'].get())))

    def apply_rules(self):
        try:
            gpr, gpf, gff, ngen = self._read_rules()
            rows, cols = self._int('rows', 'Filas', 1), self._int('cols', 'Columnas', 1)
        except ValueError as e:
            messagebox.showerror('Parametros', str(e))
            return
        scn = self.scn.copy()
        scn.gpr, scn.gpf, scn.gff, scn.ngen, scn.rows, scn.cols = gpr, gpf, gff, ngen, rows, cols
        try:
            scn.validate()
        except ValueError as e:
            messagebox.showerror('Parametros', str(e))
            return
        self._set_scenario(scn, refill=False)
        self.log_msg('Reglas aplicadas.')

    def _set_scenario(self, scn, refill=True):
        self.stop_run()
        self.scn = scn
        if refill:
            self._fill_fields(scn)
        self.show_scenario()

    def show_scenario(self):
        """Muestra la generacion 0 del escenario actual y reinicia estadisticas."""
        world = self.scn.world_rows()
        self.frame = Frame(0, world, None, None)
        self.history = [(0, self.frame.rabbits, self.frame.foxes, self.frame.rocks)]
        self.finished = False
        self.playing = False
        self.btn_play.configure(text='\u25B6  Iniciar')
        self.set_state('Listo')
        self._update_labels()
        self.draw_grid()
        self.draw_chart()

    # ------------------------------------------------------------- ejecucion
    def stop_run(self):
        if self.run is not None:
            self.run.stop()
            self.run = None
        self.playing = False
        self.pending = 0
        self.acc = 0.0

    def _launch(self):
        """Lanza una ejecucion nueva con los parametros actuales. True si pudo."""
        try:
            gpr, gpf, gff, ngen = self._read_rules()
            scn = self.scn.copy()
            scn.gpr, scn.gpf, scn.gff, scn.ngen = gpr, gpf, gff, ngen
            rows, cols = self._int('rows', 'Filas', 1), self._int('cols', 'Columnas', 1)
            scn.rows, scn.cols = rows, cols
            scn.validate()
        except ValueError as e:
            messagebox.showerror('No se puede iniciar', str(e))
            return False
        k = self.engine_key()
        exe = self.exe[k]
        if not os.path.isfile(exe):
            messagebox.showerror(
                'No encuentro el ejecutable',
                'No existe:\n%s\n\nCompila el motor (ver README) o usa "Cambiar..." para elegirlo.' % exe)
            return False
        threads = None
        if k == 'par':
            try:
                threads = max(1, int(self.v_threads.get()))
            except ValueError:
                threads = None
        self.scn = scn
        self.stop_run()
        self.frame = Frame(0, scn.world_rows(), None, None)
        self.history = []
        self.finished = False
        self.run = Run(scn, k, exe, threads)
        try:
            self.run.start()
        except OSError as e:
            self.run = None
            messagebox.showerror('No se pudo ejecutar el motor', str(e))
            return False
        self.log_msg('Simulacion iniciada con %s%s.' % (
            self.v_engine.get(), ' (%d hilos)' % threads if threads else ''))
        return True

    def toggle_play(self):
        if self.run is None or self.finished:
            if not self._launch():
                return
            self.playing = True
        else:
            self.playing = not self.playing
        self._refresh_play_ui()

    def _refresh_play_ui(self):
        if self.playing:
            self.btn_play.configure(text='\u23F8  Pausa')
            self.set_state('Ejecutando')
        elif self.run is not None and not self.finished:
            self.btn_play.configure(text='\u25B6  Continuar')
            self.set_state('En pausa', '#ffc857')
        else:
            self.btn_play.configure(text='\u25B6  Iniciar')

    def step(self):
        if self.run is None or self.finished:
            if not self._launch():
                return
            self.pending = 2            # generacion 0 y luego la 1
        else:
            self.pending += 1
        self.playing = False
        self._refresh_play_ui()

    def restart(self):
        self.stop_run()
        self.show_scenario()
        if self._launch():
            self.playing = True
            self._refresh_play_ui()

    def on_close(self):
        self.stop_run()
        self.root.destroy()

    # ---------------------------------------------------------- velocidad
    def gens_per_sec(self):
        return 10 ** self.v_speed.get()

    def _speed_changed(self):
        g = self.gens_per_sec()
        self.lbl_speed.configure(text='%.1f gen/s' % g if g < 10 else '%d gen/s' % round(g))

    def _bump_speed(self, d):
        self.v_speed.set(min(2.7, max(-0.3, self.v_speed.get() + d)))
        self._speed_changed()

    # ------------------------------------------------------------ bucle
    def _tick(self):
        now = time.monotonic()
        dt = min(0.25, now - self.last_t)
        self.last_t = now
        try:
            self._consume(dt)
        except Exception as e:                      # nunca dejar morir el bucle
            self.log_msg('Error interno: %s: %s' % (type(e).__name__, e))
        self.root.after(self.TICK_MS, self._tick)

    def _consume(self, dt):
        run = self.run
        if run is None:
            return
        while True:
            try:
                self.log_msg(run.logs.get_nowait())
            except queue.Empty:
                break
        n = self.pending
        self.pending = 0
        if self.playing:
            self.acc += self.gens_per_sec() * dt
            k = int(self.acc)
            self.acc -= k
            n += k
        last = None
        while n > 0 and not self.finished:
            try:
                item = run.frames.get_nowait()
            except queue.Empty:
                self.pending += n if not self.playing else 0   # esperar al motor
                break
            if item is Run.DONE:
                self._finish()
                break
            if isinstance(item, tuple):
                self.log_msg(item[1])
                self.set_state('Error', '#ff6b6b')
                self.run = None
                self.playing = False
                self._refresh_play_ui()
                messagebox.showerror('Error del motor', item[1])
                return
            last = item
            self.history.append((item.gen, item.rabbits, item.foxes, item.rocks))
            n -= 1
        if last is not None:
            self.frame = last
            self._update_labels()
            self.draw_grid()
            self.draw_chart()
            if last.gen >= self.scn.ngen and run.frames.empty() and self.run is run:
                pass            # el DONE llegara en el siguiente ciclo

    def _finish(self):
        self.finished = True
        self.playing = False
        self.set_state('Finalizado', '#8ab4ff')
        self.btn_play.configure(text='\u25B6  Repetir')
        self.log_msg('Simulacion finalizada en la generacion %d.' % (self.frame.gen if self.frame else 0))

    def _update_labels(self):
        f = self.frame
        if f is None:
            return
        self.lbl_gen.configure(text='Generacion %d  /  %d' % (f.gen, self.scn.ngen))
        self.stat['rabbits'].configure(text=str(f.rabbits))
        self.stat['foxes'].configure(text=str(f.foxes))
        self.stat['rocks'].configure(text=str(f.rocks))
        self.progress.configure(value=100.0 * f.gen / max(1, self.scn.ngen))
        self._speed_changed()

    # ------------------------------------------------------------- dibujo
    def _schedule_redraw(self):
        if self._redraw_job is not None:
            self.root.after_cancel(self._redraw_job)
        self._redraw_job = self.root.after(40, self._do_redraw)

    def _do_redraw(self):
        self._redraw_job = None
        self.draw_grid()

    def _geometry(self):
        """Tamano de celda y origen del mundo dentro del canvas."""
        c = self.canvas
        w, h = max(c.winfo_width(), 120), max(c.winfo_height(), 120)
        nr, nc = self.scn.rows, self.scn.cols
        margin = 26 if (nr <= 40 and nc <= 40) else 8
        cell = min((w - 2 * margin) / nc, (h - 2 * margin) / nr)
        if cell >= 6:
            cell = float(int(cell)) if cell > 12 else cell
        ox, oy = (w - cell * nc) / 2, (h - cell * nr) / 2
        return cell, ox, oy

    def draw_grid(self):
        c = self.canvas
        c.delete('all')
        f = self.frame
        if f is None or not f.world:
            return
        nr, nc = len(f.world), max(len(r) for r in f.world)
        cell, ox, oy = self._geometry()
        self.geom = (cell, ox, oy, nr, nc)
        occupied = f.rabbits + f.foxes + f.rocks

        if cell < 6:                                         # mundo enorme: imagen de pixeles
            self._draw_pixels(f, nr, nc, cell, ox, oy)
            return

        round_rect(c, ox - 6, oy - 6, ox + cell * nc + 6, oy + cell * nr + 6, 10,
                   fill=FIELD, outline=FIELD_LINE)
        for i in range(nr):                                  # damero suave
            for j in range((i % 2), nc, 2):
                if cell >= 10:
                    c.create_rectangle(ox + j * cell, oy + i * cell, ox + (j + 1) * cell,
                                       oy + (i + 1) * cell, fill=FIELD_ALT, outline='')
        if cell >= 10:
            for i in range(nr + 1):
                c.create_line(ox, oy + i * cell, ox + nc * cell, oy + i * cell, fill=FIELD_LINE)
            for j in range(nc + 1):
                c.create_line(ox + j * cell, oy, ox + j * cell, oy + nr * cell, fill=FIELD_LINE)

        detailed = cell >= 18 and occupied <= 1500
        if cell >= 22 and nr <= 40 and nc <= 40:             # indices de filas / columnas
            fs = max(7, min(11, int(cell * 0.32)))
            for j in range(nc):
                c.create_text(ox + (j + .5) * cell, oy - 14, text=str(j), fill=MUTED,
                              font=(FONT, fs))
            for i in range(nr):
                c.create_text(ox - 14, oy + (i + .5) * cell, text=str(i), fill=MUTED,
                              font=(FONT, fs))
        pad = cell * 0.08
        s = cell - 2 * pad
        for i, row in enumerate(f.world):
            for j, ch in enumerate(row):
                if ch == ' ':
                    continue
                x, y = ox + j * cell + pad, oy + i * cell + pad
                if detailed:
                    {'R': draw_rabbit, 'F': draw_fox, '*': draw_rock}[ch](c, x, y, s)
                elif ch == 'R':
                    c.create_oval(x, y, x + s, y + s, fill=C_RABBIT, outline=C_RABBIT_D)
                elif ch == 'F':
                    c.create_polygon(x + s / 2, y, x + s, y + s, x, y + s, fill=C_FOX,
                                     outline=C_FOX_D)
                else:
                    c.create_rectangle(x, y, x + s, y + s, fill=C_ROCK, outline=C_ROCK_D)

    def _draw_pixels(self, f, nr, nc, cell, ox, oy):
        colors = {' ': FIELD, 'R': C_RABBIT, 'F': C_FOX, '*': C_ROCK}
        z = max(1, int(cell))
        img = tk.PhotoImage(width=nc, height=nr)
        data = ' '.join('{%s}' % ' '.join(colors.get(ch, FIELD) for ch in row.ljust(nc))
                        for row in f.world)
        img.put(data)
        if z > 1:
            img = img.zoom(z, z)
        self.photo = img                                      # evita que lo recoja el GC
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        self.canvas.create_image(w / 2, h / 2, image=img)

    def _on_hover(self, ev):
        g = getattr(self, 'geom', None)
        f = self.frame
        if not g or f is None:
            return
        cell, ox, oy, nr, nc = g
        j, i = int((ev.x - ox) // cell), int((ev.y - oy) // cell)
        if not (0 <= i < nr and 0 <= j < nc and j < len(f.world[i])):
            self.v_hover.set('')
            return
        ch = f.world[i][j]
        name = {' ': 'vacio', 'R': 'conejo', 'F': 'zorro', '*': 'roca'}[ch]
        txt = '(%d, %d)  %s' % (i, j, name)
        if f.ages and ch in 'RF':
            txt += '  |  reproduccion %s' % f.ages[i][j]
            if ch == 'F':
                txt += '  |  hambre %s' % f.foods[i][j]
        self.v_hover.set(txt)

    def _draw_legend(self):
        c = self.legend
        c.delete('all')
        x = 4
        for draw, text in ((draw_fox, 'Zorro'), (draw_rabbit, 'Conejo'), (draw_rock, 'Roca')):
            draw(c, x, 3, 26)
            c.create_text(x + 34, 17, text=text, anchor='w', fill=TEXT, font=(FONT, 10))
            x += 110
        c.create_rectangle(x, 8, x + 18, 26, fill=FIELD, outline=FIELD_LINE)
        c.create_text(x + 26, 17, text='Vacio', anchor='w', fill=TEXT, font=(FONT, 10))

    def draw_chart(self):
        c = self.chart
        c.delete('all')
        w, h = max(c.winfo_width(), 240), max(c.winfo_height(), 120)
        l, r, t, b = 40, 12, 12, 30
        hist = self.history
        peak = max([1] + [max(a, f) for _, a, f, _ in hist])
        top = self._nice(peak)
        for k in range(5):                                    # rejilla y eje Y
            v = top * k / 4
            y = h - b - (h - b - t) * k / 4
            c.create_line(l, y, w - r, y, fill=LINE)
            c.create_text(l - 6, y, text=str(int(v)), anchor='e', fill=MUTED, font=(FONT, 8))
        n = max(self.scn.ngen, 1)
        for k in range(5):                                    # eje X
            g = n * k / 4
            x = l + (w - l - r) * k / 4
            c.create_text(x, h - b + 12, text=str(int(g)), fill=MUTED, font=(FONT, 8))
        c.create_text((l + w - r) / 2, h - 6, text='generacion', fill=MUTED, font=(FONT, 8))
        if not hist:
            return
        step = max(1, len(hist) // max(1, (w - l - r)))       # reduce puntos si hay muchos
        pts = hist[::step]
        if pts[-1] is not hist[-1]:
            pts = pts + [hist[-1]]
        for idx, col in ((1, C_RABBIT), (2, C_FOX)):
            flat = []
            for rec in pts:
                flat += [l + (w - l - r) * rec[0] / n,
                         h - b - (h - b - t) * rec[idx] / top]
            if len(flat) >= 4:
                c.create_line(*flat, fill=col, width=2, smooth=False)
            else:
                c.create_oval(flat[0] - 3, flat[1] - 3, flat[0] + 3, flat[1] + 3, fill=col,
                              outline='')
        gx = l + (w - l - r) * hist[-1][0] / n                # marcador de la generacion actual
        c.create_line(gx, t, gx, h - b, fill=MUTED, dash=(3, 3))

    @staticmethod
    def _nice(v):
        if v <= 4:
            return 4
        mag = 10 ** int(math.log10(v))
        for m in (1, 2, 4, 5, 8, 10):
            if m * mag >= v:
                return int(m * mag)
        return int(10 * mag)


def main():
    root = tk.Tk()
    EcosystemGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()