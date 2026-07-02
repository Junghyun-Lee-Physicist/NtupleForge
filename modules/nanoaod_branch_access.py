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
nanoAOD-tools ``Event`` wrapper, which in newer CMSSW releases (observed in
CMSSW_14_2_1, ROOT >= 6.30) exposes vector branches as **raw**
``ROOT.TTreeReaderArray<T>`` proxies rather than wrapped Python lists.  These
raw proxies have surprising behaviours that have caused real silent-failure
and hard-crash bugs in this project:

1. ``UChar_t`` element representation
   ROOT exposes ``unsigned char`` elements not as Python ``int`` but as
   1-byte ``bytes`` objects (e.g. ``b'\\x05'``). Direct comparison with an
   integer literal **always returns False**::

       event.GenJet_hadronFlavour[j] == 5    # b'\\x05' == 5  ->  False

   The cut silently kills every event. Use ``to_int`` at every ``UChar_t``
   comparison site. Affected branches include (non-exhaustive)::

       GenJet_hadronFlavour, GenJet_partonFlavour
       Jet_hadronFlavour, Jet_partonFlavour, Jet_jetId, Jet_puId
       FatJet_hadronFlavour, FatJet_jetId, SubJet_hadronFlavour
       GenJetAK8_hadronFlavour, some Muon_*Id / Electron_*Id

2. Getting a collection length — USE THE COUNT BRANCH
   Python ``len()`` raises ``TypeError`` on a raw ``TTreeReaderArray<T>``.
   Do **not** try to recover the length by probing the array with
   out-of-bounds indexing: ``TTreeReaderArray::At(i)`` for ``i >= size`` is
   undefined behaviour in ROOT and **segfaults** — it does not raise a
   catchable Python exception. (That footgun caused the CMSSW_14_2_1 CRAB
   segfault documented in ``docs/05_troubleshooting.md`` A12.)

   The correct, crash-free length of any NanoAOD collection ``X`` is its
   **count branch** ``event.nX`` — a scalar the framework reads cleanly, and
   the value NanoAOD guarantees equals ``len(X_*)``. Use ``count(event, "X")``
   (or the standard ``len(Collection(event, "X"))``, which reads the same
   ``nX`` internally). Read individual elements only **in-bounds**
   (``arr[i]`` for ``i in range(count)``), which is safe once the entry is
   loaded.

   HISTORICAL NOTE (corrected). Earlier docs claimed the ``nX`` count branch
   was "unreliable as a length" and told callers to derive the length from
   the array instead. That was a mis-attribution: the observed zero-length
   counters were a symptom of the *input keep/drop filtering* bug (the driver
   used to pass ``branchsel=<file>``, zombie-ing input branches — see
   ``05_troubleshooting.md`` A4). That root cause was fixed
   (``branchsel=None``; the input tree is read in full), so ``nX`` is the
   canonical, reliable length again. Deriving length from the array is now
   both unnecessary and dangerous (see #2 above).

The C++ analyzer side is **not affected** by either issue.

History
=======
UChar_t/bytes and the counter confusion were discovered during ttbar
categorizer debugging (2026-04). The out-of-bounds-probe segfault surfaced in
the CPV (TopCPVCategorizer) CRAB run on 2026-07-01.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# UChar_t -> int coercion
# ---------------------------------------------------------------------------

def to_int(x: Any) -> int:
    """Coerce a NanoAOD scalar element to a Python ``int``.

    Handles the shapes that ``TTreeReaderArray`` element access can return
    depending on the ROOT type of the underlying branch:

    * already ``int``  -> returned as-is (fast path)
    * 1-byte ``bytes``/``bytearray`` (the UChar_t case) -> first byte
    * multi-byte ``bytes``  -> little-endian decode (defensive)
    * 1-character ``str`` (some PyROOT versions)  -> ``ord``
    * anything else  -> ``int(x)``

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
# Collection length — from the count branch (the ONLY safe way)
# ---------------------------------------------------------------------------

def count(event: Any, collection: str) -> int:
    """Return the multiplicity of a NanoAOD collection from its count branch.

    ``count(event, "GenPart")`` reads the scalar ``event.nGenPart`` and coerces
    it to ``int``. This is the canonical NanoAOD length (NanoAOD guarantees
    ``len(GenPart_*) == nGenPart``) and is crash-free: it never touches a raw
    ``TTreeReaderArray`` proxy, so it cannot trigger the out-of-bounds
    ``At()`` segfault (see module docstring #2).

    Equivalent to ``len(Collection(event, "<collection>"))`` from
    ``PhysicsTools.NanoAODTools...datamodel`` (which reads ``n<collection>``
    the same way); we use the count branch directly to keep the hot event
    loop free of per-collection ``Object`` construction.

    Accepts either the bare collection name (``"GenPart"``) or the counter
    branch name (``"nGenPart"``).
    """
    name = collection if collection.startswith("n") and collection[1:2].isupper() \
        else "n" + collection
    return to_int(getattr(event, name))


def opt_count(event: Any, collection: str) -> int:
    """Like :func:`count`, but returns 0 if the count branch is absent."""
    try:
        return count(event, collection)
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# safe_len — DEPRECATED for NanoAOD collections; kept for genuine sequences
# ---------------------------------------------------------------------------

def safe_len(branch: Any, *, branch_name: str | None = None) -> int:
    """Length of a genuine Python sequence, or a raw proxy via ``GetSize()``.

    DEPRECATED for NanoAOD collection lengths: use :func:`count` (the count
    branch) instead. This function no longer performs the out-of-bounds
    indexing probe that previously segfaulted on real ``TTreeReaderArray``
    proxies (``05_troubleshooting.md`` A12). It now does only:

    1. Python ``len()`` — works on wrapped arrays and any sequence.
    2. ``branch.GetSize()`` — for a raw proxy that has already been read.

    If neither works it raises ``TypeError`` (fail fast) rather than probing
    memory. Prefer :func:`count`.
    """
    try:
        return len(branch)
    except TypeError:
        getsize = getattr(branch, "GetSize", None)
        if getsize is not None:
            return int(getsize())
        raise TypeError(
            f"safe_len: cannot determine length of {branch_name or type(branch).__name__!r}; "
            "use count(event, collection) with the NanoAOD count branch instead."
        )


# ---------------------------------------------------------------------------
# Self-test (run as `python -m nanoaod_branch_access`)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    assert to_int(5) == 5
    assert to_int(b"\x05") == 5
    assert to_int(bytearray(b"\x05")) == 5
    assert to_int("\x05") == 5
    assert to_int(b"\x00\x01") == 256  # little-endian
    print("to_int: OK")

    class _FakeEvent:
        nGenPart = 7
        nGenVisTau = 3
    assert count(_FakeEvent(), "GenPart") == 7
    assert count(_FakeEvent(), "nGenPart") == 7
    assert count(_FakeEvent(), "GenVisTau") == 3
    assert opt_count(_FakeEvent(), "GenJet") == 0   # absent -> 0
    print("count/opt_count: OK")

    assert safe_len([1, 2, 3]) == 3
    class _Proxy:
        def GetSize(self): return 5
    assert safe_len(_Proxy(), branch_name="p") == 5
    try:
        safe_len(object(), branch_name="broken")
        raise SystemExit("safe_len should have raised")
    except TypeError:
        pass
    print("safe_len: OK")
    print("All self-tests passed.")
