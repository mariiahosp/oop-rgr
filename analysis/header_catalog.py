from enum import Enum


class HeaderCategory(Enum):
    WINDOWS_MAIN = "windows_main"
    WINDOWS_API = "windows_api"
    STANDARD = "standard"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class HeaderCatalog:
    _WINDOWS_MAIN = "windows.h"

    _WINDOWS_API = frozenset({
        "afx.h", "afxext.h", "afxwin.h", "atlbase.h", "atlstr.h",
        "comdef.h", "commctrl.h", "commdlg.h", "commoncontrols.h",
        "d2d1.h", "d3d11.h", "dbghelp.h", "dwmapi.h", "dwrite.h",
        "gdiplus.h", "mmsystem.h", "objbase.h", "ole2.h", "oleauto.h",
        "olectl.h", "prsht.h", "psapi.h", "richedit.h", "sdkddkver.h",
        "setupapi.h", "shellapi.h", "shlobj.h", "shlwapi.h", "shtypes.h",
        "strsafe.h", "tlhelp32.h", "uxtheme.h", "verrsrc.h", "winbase.h",
        "wincodec.h", "windef.h", "windowsx.h", "winerror.h", "wingdi.h",
        "winhttp.h", "wininet.h", "winnt.h", "winreg.h", "winres.h",
        "winresrc.h", "winsock.h", "winsock2.h", "winuser.h", "winver.h",
        "ws2tcpip.h",
    })

    _STANDARD = frozenset({
        # C++ standard library
        "algorithm", "any", "array", "atomic", "bit", "bitset", "cassert",
        "cctype", "cerrno", "cfloat", "charconv", "chrono", "climits",
        "clocale", "cmath", "codecvt", "compare", "complex", "concepts",
        "condition_variable", "coroutine", "csetjmp", "csignal", "cstdarg",
        "cstddef", "cstdint", "cstdio", "cstdlib", "cstring", "ctime",
        "cuchar", "cwchar", "cwctype", "deque", "exception", "execution",
        "expected", "filesystem", "format", "forward_list", "fstream",
        "functional", "future", "initializer_list", "iomanip", "ios",
        "iosfwd", "iostream", "istream", "iterator", "limits", "list",
        "locale", "map", "memory", "memory_resource", "mutex", "new",
        "numbers", "numeric", "optional", "ostream", "print", "queue",
        "random", "ranges", "ratio", "regex", "scoped_allocator", "set",
        "shared_mutex", "source_location", "span", "sstream", "stack",
        "stdexcept", "stop_token", "streambuf", "string", "string_view",
        "syncstream", "system_error", "thread", "tuple", "type_traits",
        "typeindex", "typeinfo", "unordered_map", "unordered_set",
        "utility", "valarray", "variant", "vector", "version",
        # C standard library
        "assert.h", "ctype.h", "errno.h", "float.h", "inttypes.h",
        "limits.h", "locale.h", "math.h", "setjmp.h", "signal.h",
        "stdarg.h", "stdbool.h", "stddef.h", "stdint.h", "stdio.h",
        "stdlib.h", "string.h", "time.h", "uchar.h", "wchar.h", "wctype.h",
        # Microsoft C runtime
        "conio.h", "crtdbg.h", "io.h", "malloc.h", "memory.h", "process.h",
        "tchar.h",
    })

    def classify(self, name: str, is_system: bool) -> HeaderCategory:
        key = name.replace("\\", "/").strip().lower()
        if key == self._WINDOWS_MAIN:
            return HeaderCategory.WINDOWS_MAIN
        if key in self._WINDOWS_API:
            return HeaderCategory.WINDOWS_API
        if key in self._STANDARD:
            return HeaderCategory.STANDARD
        return HeaderCategory.EXTERNAL if is_system else HeaderCategory.UNKNOWN
