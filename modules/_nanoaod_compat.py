"""
NanoAOD compatibility helpers for PyROOT-level branch access.

Background
==========
NanoAOD ntuples use compact ROOT storage types (``UChar_t``, ``UShort_t``,
flat C-style arrays) for disk efficiency.  When read from C++ via
``treestream``/``makeClass``-generated wrappers (the analyzer side), these
types are widened to ``int``/``vector<int>`` transparently by ROOT's typed
``SetBranchAddress<int>`` calls — the analyzer never sees the underlying
representation.

The Python side, however, accesses the same branches through the
nanoAOD-tools ``Event`` wrapper, which in newer CMSSW releases (observed
in CMSSW_14_2_1, ROOT >= 6.30) exposes vector branches as **raw**
``ROOT.TTreeReaderArray<T>`` proxies rather than wrapped Python lists.
These raw proxies have two surprising behaviours that have caused real
silent-failure bugs in NtupleForge modules:

1. ``UChar_t`` element representation
   ROOT exposes ``unsigned char`` elements not as Python ``int`` but as
   1-byte ``bytes`` objects (e.g. ``b'\\x05'``). Direct comparison with
   integer literals **always returns False**::

       event.GenJet_hadronFlavour[j] == 5    # b'\\x05' == 5  →  False

   The cut silently kills every event. NanoAOD branches affected
   include (non-exhaustive)::

       GenJet_hadronFlavour, GenJet_partonFlavour
       Jet_hadronFlavour, Jet_partonFlavour, Jet_jetId, Jet_puId
       FatJet_hadronFlavour, FatJet_jetId
       SubJet_hadronFlavour
       GenJetAK8_hadronFlavour
       Muon_*Id, Electron_*Id (some)

   Verify a suspect branch with::

       leaf = tree.GetBranch(name).GetLeaf(name)
       print(leaf.GetTypeName())   # 'UChar_t' is the danger flag

2. No ``len()`` on raw ``TTreeReaderArray<T>``
   Python ``len()`` raises ``TypeError`` on the raw proxy. The proxy
   does support ROOT's ``GetSize()`` method and integer indexing, so
   the size must be queried through one of those fallback paths.

The C++ analyzer side is **not affected** by either issue: ``treestream``
binds NanoAOD ``UChar_t`` branches to ``vector<int>`` and ROOT performs
the type widening at read time.

This module is a tiny, self-contained shim that provides safe accessors
for both quirks. All NtupleForge Python modules that touch NanoAOD vector
branches should import from here, never re-implement the conversion
inline. If you find yourself writing ``int(event.SomeBranch[i])`` or
``len(event.SomeVector)`` raw, stop and use these helpers instead.

History
=======
Discovered during ttbarCategorizer debugging (project transcript
2026-04-07). Five distinct infrastructure bugs were found in sequence;
the two captured here are the ones that recur outside categorization.
"""
from __future__ import annotations

from typing import Any
import sys


# ---------------------------------------------------------------------------
# UChar_t → int coercion
# ---------------------------------------------------------------------------

def to_int(x: Any) -> int:
    """Coerce a NanoAOD scalar element to a Python ``int``.

    Handles the four shapes that ``TTreeReaderArray`` element access can
    return depending on the ROOT type of the underlying branch:

    * already ``int``  → returned as-is (fast path)
    * 1-byte ``bytes``/``bytearray`` (the UChar_t case) → first byte
    * multi-byte ``bytes``  → little-endian decode (defensive; not
      expected for any current NanoAOD branch but cheap to support)
    * 1-character ``str`` (some PyROOT versions)  → ``ord``
    * anything else  → ``int(x)``

    Idempotent: ``to_int(to_int(x)) == to_int(x)`` for all valid inputs.

    Use at every comparison site for ``UChar_t`` branches::

        if to_int(event.Jet_jetId[j]) < 4:
            continue
        if to_int(event.GenJet_hadronFlavour[j]) == 5:
            ...
    """
    if isinstance(x, int):
        return x
    if isinstance(x, (bytes, bytearray)):
        if len(x) == 1:
            return x[0]
        return int.from_bytes(bytes(x), "little")
    if isinstance(x, str):
        if len(x) == 1:
            return ord(x)
        return int(x)
    return int(x)


# ---------------------------------------------------------------------------
# Vector length probing
# ---------------------------------------------------------------------------

# One-shot warning state: report the first time len() fails on each
# distinct branch type, then stay quiet to avoid log spam.
_LEN_FALLBACK_REPORTED: set[str] = set()


def safe_len(branch: Any, *, branch_name: str | None = None) -> int:
    """Return the length of a NanoAOD vector branch, tolerating raw proxies.

    Three-tier fallback:

    1. Python ``len()`` — works on nanoAOD-tools wrapped arrays and on
       any sequence-like object. The fast path.
    2. ``branch.GetSize()`` — ROOT's standard API for ``TTreeReaderArray``.
       The middle path; activates on raw proxies in newer CMSSW.
    3. Integer-indexing probe — increments an index until ``IndexError``
       or ``RuntimeError``. The last-resort path, capped at 100k to
       prevent runaway loops on broken inputs.

    The first time path 1 fails for a given branch type (or branch name,
    if supplied), a single warning is emitted to stderr identifying which
    fallback was used. Subsequent calls are silent.

    Always prefer this over raw ``len()`` for any NanoAOD vector branch
    accessed from Python.
    """
    # Path 1: Python len()
    try:
        return len(branch)
    except TypeError:
        key = branch_name or type(branch).__name__
        if key not in _LEN_FALLBACK_REPORTED:
            _LEN_FALLBACK_REPORTED.add(key)
            sys.stderr.write(
                f"[_nanoaod_compat.safe_len] len() unsupported for "
                f"{key!r}, falling back to GetSize()/probe.\n"
            )

    # Path 2: TTreeReaderArray.GetSize()
    getsize = getattr(branch, "GetSize", None)
    if getsize is not None:
        try:
            return int(getsize())
        except Exception:
            pass

    # Path 3: indexing probe
    for i in range(100_000):
        try:
            _ = branch[i]
        except (IndexError, RuntimeError):
            return i
    return 100_000


# ---------------------------------------------------------------------------
# Self-test (run as `python -m modules._nanoaod_compat`)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # to_int
    assert to_int(5) == 5
    assert to_int(b"\x05") == 5
    assert to_int(bytearray(b"\x05")) == 5
    assert to_int("\x05") == 5
    assert to_int(b"\x00\x01") == 256  # little-endian
    print("to_int: OK")

    # safe_len fallback paths
    class _FakeProxy:
        """Mimics raw TTreeReaderArray: no len(), has GetSize(), indexable."""
        def __init__(self, n: int):
            self._n = n
        def GetSize(self) -> int:
            return self._n
        def __getitem__(self, i: int) -> int:
            if 0 <= i < self._n:
                return i
            raise IndexError(i)

    assert safe_len([1, 2, 3]) == 3                         # path 1
    assert safe_len(_FakeProxy(7), branch_name="fake") == 7 # path 2
    print("safe_len: OK")

    print("All self-tests passed.")
