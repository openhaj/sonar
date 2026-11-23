from __future__ import annotations

import functools
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pycparser import c_ast, c_parser

from app.cache import FileCache, get_cached_scan, put_cached_scan
from app.model import LibrarySource, ScanResult
from app.prebuilt import fetch_library
from app.sources import version_key
from app.utils import read_text
from config import SOURCES_DIR

RE_ASM_GLOB = re.compile(
    r"^\s*\.(?:global|globl)\s+([A-Za-z_][A-Za-z0-9_]*)",
    re.M,
)


RE_DEFINE = re.compile(
    r"^[ \t]*#[ \t]*define[ \t]+([A-Za-z_][A-Za-z0-9_]*)(\()?",
    re.M,
)

RE_DEFINE_LINE = re.compile(
    r"^[ \t]*#[ \t]*define\b[^\n]*"
    r"(?:\\\n[^\n]*)*"
    r"\n?",
    re.M,
)

RE_OTHER_DIRECTIVE = re.compile(
    r"^[ \t]*#[ \t]*(?:include|include_next|pragma|line|error|warning|"
    r"if|ifdef|ifndef|elif|else|endif|undef)[^\n]*"
    r"(?:\\\n[^\n]*)*"
    r"\n?",
    re.M,
)


RE_SIMD_INCLUDE = re.compile(
    r"^[ \t]*#[ \t]*include[ \t]*[<\"](?:"
    r"arm_neon\.h|emmintrin\.h|immintrin\.h|xmmintrin\.h|"
    r"smmintrin\.h|mmintrin\.h|nmmintrin\.h|pmmintrin\.h|"
    r"tmmintrin\.h|wmmintrin\.h|avxintrin\.h|avx2intrin\.h|"
    r"avx512fintrin\.h|avx512bwintrin\.h|bmiintrin\.h|bmi2intrin\.h"
    r")[>\"][^\n]*\n?",
    re.M,
)

def _find_tool(name: str) -> str | None:
    return shutil.which(name)

def _find_cpp() -> str | None:
    for cand in ("cpp", "gcc", "clang"):
        p = shutil.which(cand)
        if p:
            return p
    return None

@functools.cache
def _get_compiler_include_dirs() -> list[Path]:
    dirs: list[Path] = []
    for compiler in ("gcc", "clang"):
        exe = shutil.which(compiler)
        if exe is None:
            continue
        try:
            r = subprocess.run(
                [exe, "-print-file-name=include"],
                capture_output=True, text=True, timeout=5,
            )
        except (subprocess.TimeoutExpired, OSError):
            continue
        if r.returncode != 0:
            continue
        raw = r.stdout.strip()
        if not raw:
            continue
        p = Path(raw)
        if p.is_dir() and p not in dirs:
            dirs.append(p)
    return dirs


def _parse_depfile(text: str) -> list[str]:
    """Sortie `-MD` de cpp -> liste des prérequis (sans la cible)."""
    text = text.replace("\\\n", " ")
    _, _, deps = text.partition(":")
    return [t.replace("\0", " ") for t in deps.replace("\\ ", "\0").split()]


def _preprocess(path: Path, include_dirs: list[Path],
                deps_out: set[Path] | None = None) -> str | None:
    """
    Lance cpp sur `path`. Si `deps_out` est fourni, il est rempli avec
    les headers effectivement inclus (pour le cache fichier par fichier).
    """
    cpp = _find_cpp()
    if cpp is None:
        return None

    src = read_text(path)
    src = RE_SIMD_INCLUDE.sub("", src)

    tmp_path = path.parent / (path.name + ".hajscan")
    dep_path = path.parent / (path.name + ".hajscan.d")
    try:
        tmp_path.write_text(src)
    except OSError:
        return None

    try:
        cmd = [cpp, "-E", "-P", "-dD", "-nostdinc", "-D__hajlib__=1"]

        for d in include_dirs:
            if d.exists():
                cmd += ["-I", str(d)]

        for d in _get_compiler_include_dirs():
            cmd += ["-isystem", str(d)]

        if deps_out is not None:
            cmd += ["-MD", "-MF", str(dep_path)]

        cmd.append(str(tmp_path))

        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    finally:
        tmp_path.unlink(missing_ok=True)
        if deps_out is not None:
            try:
                for d in _parse_depfile(dep_path.read_text("utf-8", "ignore")):
                    dp = Path(d)
                    if dp.resolve() != tmp_path.resolve():
                        deps_out.add(dp)
            except OSError:
                pass
            dep_path.unlink(missing_ok=True)

    if r.returncode != 0:
        return None
    return r.stdout


_NM_FUNC_TYPES = frozenset("TtWw")
_NM_OBJ_TYPES  = frozenset("DdBbRrVv")


def _make(root: Path, *args: str, timeout: int) -> None:
    make = _find_tool("make")
    if make is None:
        return
    try:
        subprocess.run([make, "-C", str(root), "-j", "4", *args], capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        pass


def _library_of(version: str, root: Path, tmpdir: Path) -> tuple[Path, LibrarySource] | None:
    """A static library of the release, copied into `tmpdir`, and where it
    comes from. In order of preference:

    1. built here from the release's sources;
    2. the prebuilt library of the release on GitHub, when it no longer
       builds here (old tag with a newer toolchain or missing headers);
    3. as a last resort (offline, no release), the objects that did compile,
       which misses the functions of the files that did not.
    """
    if (root / "Makefile").is_file():
        _make(root, timeout=120)
        built = sorted(root.glob("*.a"))
        if built:
            return Path(shutil.copy(built[0], tmpdir)), "local"

    released = fetch_library(version)
    if released is not None:
        return Path(shutil.copy(released, tmpdir)), "release"

    if (root / "Makefile").is_file():
        _make(root, "-k", timeout=300)  # keep going past the failing files
        built = sorted(root.glob("*.a"))
        if built:
            return Path(shutil.copy(built[0], tmpdir)), "local"
        objects = [str(o) for o in root.rglob("*.o")]
        ar = _find_tool("ar")
        if objects and ar:
            partial = tmpdir / "partial.a"
            subprocess.run([ar, "rcs", str(partial), *objects], capture_output=True)
            if partial.exists():
                print(f"  [analyze]   incomplete: only {len(objects)} objects compiled, some functions are missed")
                return partial, "partial"
    return None


def _run_nm(archive: Path) -> dict[str, set[str]]:
    nm = _find_tool("nm")
    if nm is None:
        return {"functions": set(), "globals": set()}

    try:
        r = subprocess.run(
            [nm, "-g", "--defined-only", str(archive)],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, OSError):
        return {"functions": set(), "globals": set()}

    if r.returncode != 0:
        return {"functions": set(), "globals": set()}

    functions: set[str] = set()
    globals_: set[str] = set()

    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        if len(parts) == 2:
            sym_type, name = parts[0], parts[1]
        else:
            sym_type, name = parts[1], parts[2]

        if not name or not sym_type:
            continue

        if name.startswith("."):
            continue

        if sym_type in _NM_FUNC_TYPES:
            functions.add(name)
        elif sym_type in _NM_OBJ_TYPES:
            globals_.add(name)

    return {"functions": functions, "globals": globals_}

class SymbolVisitor(c_ast.NodeVisitor):
    """Names of the types, tags, enumerators and globals a file declares
    (functions come from `nm`)."""

    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Typedef(self, node: c_ast.Typedef) -> None:
        if node.name:
            self.names.add(node.name)
        self.generic_visit(node)

    def visit_Struct(self, node: c_ast.Struct) -> None:
        if node.name:
            self.names.add(node.name)
        self.generic_visit(node)

    def visit_Union(self, node: c_ast.Union) -> None:
        if node.name:
            self.names.add(node.name)
        self.generic_visit(node)

    def visit_Enum(self, node: c_ast.Enum) -> None:
        if node.name:
            self.names.add(node.name)
        if node.values is not None:
            self.names.update(e.name for e in node.values.enumerators if e.name)
        self.generic_visit(node)

    # no visit_FuncDef / visit_FuncDecl: functions are skipped

    def visit_Decl(self, node: c_ast.Decl) -> None:
        if isinstance(node.type, c_ast.FuncDecl):
            return
        if node.name:
            self.names.add(node.name)
        self.visit(node.type)

def _skip_parens(text: str, j: int) -> int:
    """`text[j] == '('` -> index juste après la `)` correspondante."""
    n = len(text)
    depth = 1
    k = j + 1
    in_str: str | None = None
    while k < n and depth > 0:
        c = text[k]
        if in_str:
            if c == '\\':
                k += 2
                continue
            if c == in_str:
                in_str = None
        elif c in ('"', "'"):
            in_str = c
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
        k += 1
    return k


def _strip_balanced_re(text: str, pattern: re.Pattern[str], repl: str = "") -> str:
    """Remplace chaque `<pattern>( ... )` (parenthèses équilibrées) par `repl`.
    `pattern` doit se terminer par la `(` ouvrante."""
    out: list[str] = []
    pos = 0
    while True:
        m = pattern.search(text, pos)
        if m is None:
            break
        out.append(text[pos:m.start()])
        out.append(repl)
        pos = _skip_parens(text, m.end() - 1)
    out.append(text[pos:])
    return ''.join(out)


def _strip_balanced(text: str, keyword: str, repl: str = "") -> str:
    pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(keyword) + r"\s*\(")
    return _strip_balanced_re(text, pat, repl)


RE_GNU_INLINE  = re.compile(r"\b__inline\b|\b__inline__\b")
RE_GNU_EXT     = re.compile(r"\b__extension__\b")
RE_ASM_LABEL   = re.compile(r"\b__asm__\s*\([^)]*\)")
RE_ASM_STMT    = re.compile(
    r"\b(?:__asm__|__asm|asm)\b"
    r"(?:\s+(?:volatile|__volatile__|__volatile|goto|inline))*\s*\(")
RE_C11_ATOMIC  = re.compile(r"\b_Atomic\b")
RE_C11_ATOMIC_SPEC = re.compile(r"\b_Atomic\s*\(([^()]*)\)")
RE_C23_BOOL    = re.compile(r"\bbool\b")
RE_HAJ_NORET   = re.compile(r"\b__HAJ_NORETURN\b")
RE_HAJ_TLS     = re.compile(r"\b__HAJ_THREAD_LOCAL\b")
RE_HAJ_INLINE  = re.compile(r"\b__HAJ_INLINE\b")
RE_HAJ_RESTR   = re.compile(r"\b__HAJ_RESTRICT\b")
RE_HAJ_USED    = re.compile(r"\b__HAJ_USED\b")
RE_HAJ_UNUSED  = re.compile(r"\b__HAJ_UNUSED\b")
RE_HAJ_UNALIGNED = re.compile(r"\b__HAJ_UNALIGNED_WORD\b")

# Types builtin : doivent rester des *types* pour pycparser, sinon
# `typedef __builtin_va_list va_list;` casse le parse de tout le fichier.
RE_GNU_BUILTIN_VA = re.compile(r"\b__builtin_va_list\b")
RE_GNU_BUILTIN = re.compile(r"\b__builtin_[A-Za-z0-9_]+")
RE_GNU_BUILTIN_CALL = re.compile(r"\b__builtin_[A-Za-z0-9_]+\s*\(")
RE_GNU_TYPEOF  = re.compile(r"\b__typeof__\b|\b__typeof\b")

RE_HAJ_LOCAL_MACROS = re.compile(
    r"\bHAJ_(?:FUNC_NAME|VEC_TYPE|VEC_SIZE|LOAD|STORE|TARGET|"
    r"ATTR_UNUSED|MEMCPY_IMPL)\b"
)

# Types SIMD et internes remplacés par un type C standard.
RE_SIMD_TYPE_NAMES = re.compile(
    r"\b(?:"
    r"uint8x16_t|uint16x8_t|uint32x4_t|uint64x2_t|"
    r"int8x16_t|int16x8_t|int32x4_t|int64x2_t|"
    r"__m128i|__m256i|__m512i|"
    r"__m128i_u|__m256i_u|"
    r"__mfp8|mfloat8_t|fpm_t|bfloat16_t|float16_t"
    r")\b"
)

RE_SIMD_INTRINSICS = re.compile(
    r"\b(?:"
    r"_mm_loadu_si128|_mm_storeu_si128|_mm_store_si128|"
    r"_mm256_loadu_si256|_mm256_storeu_si256|_mm256_store_si256|"
    r"_mm512_loadu_si512|_mm512_storeu_si512|"
    r"vld1q_u8|vst1q_u8"
    r")\b"
)

def _clean_for_pycparser(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)

    text = _strip_balanced(text, "__attribute__")
    text = _strip_balanced(text, "__attribute")
    text = _strip_balanced(text, "__HAJ_IFUNC")
    text = _strip_balanced(text, "__HAJ_ALIAS")

    text = RE_GNU_INLINE.sub("inline", text)
    text = RE_GNU_EXT.sub("", text)
    # asm inline (`__asm__ volatile ("..." : ...)`) -> supprimé (parenthèses
    # équilibrées, couvre aussi les labels `__asm__("sym")`).
    text = _strip_balanced_re(text, RE_ASM_STMT)
    text = RE_ASM_LABEL.sub("", text)
    text = RE_C11_ATOMIC_SPEC.sub(r"\1", text)
    text = RE_C11_ATOMIC.sub("", text)
    text = RE_C23_BOOL.sub("_Bool", text)
    text = RE_GNU_BUILTIN_VA.sub("char *", text)
    # _Static_assert(...) ; -> supprimé (pycparser ne gère pas les
    # builtins à argument de type qu'on y trouve souvent).
    text = _strip_balanced(text, "_Static_assert", "__haj_static_assert")
    text = re.sub(r"__haj_static_assert\s*;?", "", text)
    # Appels builtin (offsetof, va_arg, expect…) -> expression neutre.
    text = _strip_balanced_re(text, RE_GNU_BUILTIN_CALL, "0")
    text = RE_GNU_BUILTIN.sub("__haj_builtin", text)
    text = RE_GNU_TYPEOF.sub("__haj_typeof", text)

    text = RE_HAJ_NORET.sub("", text)
    text = RE_HAJ_TLS.sub("", text)
    text = RE_HAJ_INLINE.sub("inline", text)
    text = RE_HAJ_RESTR.sub("restrict", text)
    text = RE_HAJ_USED.sub("", text)
    text = RE_HAJ_UNUSED.sub("", text)
    text = RE_HAJ_UNALIGNED.sub("", text)

    text = RE_HAJ_LOCAL_MACROS.sub("hajMacro", text)

    text = RE_SIMD_TYPE_NAMES.sub("unsigned long", text)
    text = RE_SIMD_INTRINSICS.sub("hajSimdOp", text)

    text = re.sub(r"\n\s*\n+", "\n", text)
    return text

def _collect_defines(text: str) -> set[str]:
    return {m.group(1) for m in RE_DEFINE.finditer(text)}


def _strip_directives(text: str) -> str:
    text = RE_DEFINE_LINE.sub("", text)
    text = RE_OTHER_DIRECTIVE.sub("", text)
    return text


def _parse_c(text: str) -> set[str]:
    """
    Parse du C et retourne les TYPES et GLOBALS (pas les fonctions).
    """
    names: set[str] = set()

    names |= _collect_defines(text)

    text = _strip_directives(text)

    cleaned = _clean_for_pycparser(text)
    parser = c_parser.CParser()

    try:
        ast = parser.parse(cleaned, filename="<hajlib>")
        v = SymbolVisitor()
        v.visit(ast)
        names |= v.names
    except Exception:
        names |= _parse_c_regex_fallback(text)

    return names

RE_TYPEDEF = re.compile(
    r"\btypedef\b[^;{}]*?\b([A-Za-z_][A-Za-z0-9_]*)\s*;",
    re.S,
)
RE_STRUCT = re.compile(r"\bstruct\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")
RE_UNION  = re.compile(r"\bunion\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")
RE_ENUM   = re.compile(r"\benum\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{")
# `typedef struct { ... } name;` / `typedef union {...} name[1];`
RE_TYPEDEF_BODY = re.compile(
    r"\btypedef\s+(?:struct|union|enum)\b[^;{]*\{"
    r"(?:[^{}]|\{[^{}]*\})*\}\s*\**\s*([A-Za-z_][A-Za-z0-9_]*)",
    re.S,
)
# `extern FILE *stdin;` / `extern char **environ;` (hors prototypes)
RE_EXTERN_VAR = re.compile(
    r"\bextern\b[^;(){}]*?\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\[[^\]]*\]\s*)*;",
)


def _parse_c_regex_fallback(text: str) -> set[str]:
    names: set[str] = set()
    names |= set(RE_TYPEDEF.findall(text))
    names |= {m.group(1) for m in RE_STRUCT.finditer(text)}
    names |= {m.group(1) for m in RE_UNION.finditer(text)}
    names |= {m.group(1) for m in RE_ENUM.finditer(text)}
    names |= {m.group(1) for m in RE_TYPEDEF_BODY.finditer(text)}
    names |= {m.group(1) for m in RE_EXTERN_VAR.finditer(text)}
    return names

def _scan_asm(text: str) -> set[str]:
    return set(RE_ASM_GLOB.findall(text))

def scan_c_file(path: Path, include_dirs: list[Path],
                cache: FileCache | None = None) -> set[str]:
    if cache is not None:
        hit = cache.lookup(path)
        if hit is not None:
            return set(hit)

    deps: set[Path] = set()
    pre = _preprocess(path, include_dirs, deps)
    if pre is None:
        print(f"  [warn] cpp failed on {path}, falling back to raw text")
        pre = read_text(path)
    names = _parse_c(pre)

    if cache is not None:
        cache.store(path, deps, names)
    return names


def _scan_asm_file(path: Path, cache: FileCache | None = None) -> set[str]:
    if cache is not None:
        hit = cache.lookup(path)
        if hit is not None:
            return set(hit)
    names = _scan_asm(read_text(path))
    if cache is not None:
        cache.store(path, set(), names)
    return names

def scan_release(version: str, use_file_cache: bool = True) -> ScanResult:
    """
    Retourne :
        {
          "version":         str,
          "defined":         list[str],
          "headers_present": list[str],
        }

    - Fonctions et globals : via `nm` sur l'archive compilée.
    - Types et macros       : via cpp + pycparser sur les sources.
    - Assembly (.global)    : via regex.

    Si la compilation échoue, on tombe en fallback : analyse
    cpp+pycparser uniquement, sans nm.
    """
    root    = SOURCES_DIR / version
    inc_dir = root / "include"
    src_dir = root / "src"

    defined: set[str] = set()
    headers_present: set[str] = set()
    # Le cache est toujours réécrit ; `use_file_cache=False` (--force)
    # ignore seulement les entrées existantes.
    fcache = FileCache(version)
    if not use_file_cache:
        fcache.entries.clear()

    include_dirs: list[Path] = []
    if inc_dir.exists():
        include_dirs.append(inc_dir)
        bits = inc_dir / "bits"
        if bits.exists():
            include_dirs.append(bits)

    # --- 1. Types & macros (cpp + pycparser sur headers + sources)
    if inc_dir.exists():
        for p in inc_dir.rglob("*"):
            if not p.is_file() or p.suffix not in {".h", ".hpp"}:
                continue
            headers_present.add(p.relative_to(inc_dir).as_posix())
            defined |= scan_c_file(p, include_dirs, fcache)

    if src_dir.exists():
        for p in src_dir.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix in {".c", ".h"}:
                defined |= scan_c_file(p, include_dirs, fcache)
            elif p.suffix == ".S":
                defined |= _scan_asm_file(p, fcache)

    fcache.save()
    print(f"  [analyze]   fichiers : {fcache.misses} scannés, "
          f"{fcache.hits} depuis le cache")

    # --- 2. Functions & globals: `nm` on the release's static library
    library_source: LibrarySource = "none"
    tmpdir = Path(tempfile.mkdtemp(prefix="hajscan_lib_"))
    try:
        library = _library_of(version, root, tmpdir)
        if library is not None:
            archive, library_source = library
            symbols = _run_nm(archive)
            defined |= symbols["functions"] | symbols["globals"]
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"  [analyze]   functions from: {library_source}")

    return {
        "version":         version,
        "defined":         sorted(defined),
        "headers_present": sorted(headers_present),
        "library":         library_source,
    }


def scan_all(force: bool = False) -> dict[str, ScanResult]:
    """
    Scanne toutes les releases.

    force=False (défaut) : utilise le cache si l'empreinte du dossier
                           correspond, sinon rescanne.
    force=True            : rescanne tout, ignore le cache.
    """
    out: dict[str, ScanResult] = {}
    if not SOURCES_DIR.exists():
        return out

    for d in sorted(SOURCES_DIR.iterdir(), key=lambda d: version_key(d.name)):
        if not d.is_dir():
            continue

        if not force:
            cached = get_cached_scan(d.name)
            if cached is not None:
                print(f"  [analyze] release {d.name} (cache)")
                out[d.name] = cached
                continue

        print(f"  [analyze] release {d.name} (scan)")
        scan = scan_release(d.name, use_file_cache=not force)
        put_cached_scan(d.name, scan)
        out[d.name] = scan

    return out
