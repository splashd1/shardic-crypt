"""
wordgen.py

Generates the human-typeable codeword(s) used to protect each Shamir
shard. Three modes:

  * memorable mode (--memorable, or the default when --word-length is
    omitted): whole, real words pulled from a dictionary -- the
    bundled EFF long wordlist unless --dictionary overrides it -- with
    no length filtering, case randomization, or digit suffixes. This
    optimizes for a trustee actually being able to *recall* their
    codeword instead of writing it down, at the same (or better)
    entropy as the other modes: real words engage semantic memory in a
    way random syllables and mixed-case/digit noise don't, so the
    entropy-per-character tradeoff that favors synthetic mode below
    doesn't translate into an equivalent memorability advantage. See
    bundled_memorable_wordlist() / eff_wordlist_words.py.
  * dictionary mode (--dictionary + --word-length): words of exactly
    length N are pulled from that file (one word per line). Useful if
    you want every codeword the same visible length/shape.
  * synthetic mode (--word-length alone, no --dictionary): pronounceable
    random words of exact length N are generated from a
    consonant/vowel pattern. Provides *far* more candidates per length
    than a natural-language dictionary does -- a real dictionary
    filtered to, say, 6-letter words might only have a few hundred
    entries (~8-9 bits of entropy), whereas the synthetic generator
    below has on the order of 26 * 5 * 21 * 5 * 21 ... combinations
    depending on length. Denser per character, but the syllables don't
    mean anything, so they're harder to actually remember -- prefer
    memorable mode unless you specifically want that density (e.g.
    codewords are stored, not memorized).

Security note: whichever mode you use, a single short word is weak
entropy on its own. Use --word-count > 1 to concatenate multiple
words per shard if you want a real security margin -- see the
--word-count flag on vault_create.py.

Opt-in strong mode (randomize_case / digit_suffix_len): the plain
alternating-consonant-vowel scheme only carries ~3.36 bits/char
(21-option consonant slots, 5-option vowel slots) because the vowel
slot is a hard bottleneck. Two cheap additions raise that density a
lot without changing the pronounceable skeleton:

  * randomize_case: independently upper/lowercases each generated
    letter, doubling the alphabet at every slot for +1 bit/char with
    zero added length. Only worth it if codewords get typed/pasted
    rather than read aloud or handwritten, since case is the first
    thing lost in dictation or sloppy transcription.
  * digit_suffix_len: appends N random digits after each word.
    Digits carry ~3.32 bits/char -- denser than the vowel slot -- and
    are unambiguous to speak, write, and type.

Purely a generation-time choice: recovery never regenerates a
codeword, it just tries whatever string the trustee enters against
each shard's KDF+AES-GCM check (see vault_core.try_match_word), so
enabling this mode doesn't touch the .krypt format or break
compatibility with codewords generated before it existed.
"""

import math
import secrets

_VOWELS = "aeiou"
_CONSONANTS = "bcdfghjklmnpqrstvwxyz"
_DIGITS = "0123456789"


def load_dictionary(path: str, length: int | None = None):
    """Load candidate words from `path`, one per line. If `length` is
    given, only words of exactly that length are kept (the fixed-length
    codeword mode); if it's None, every alphabetic word is kept
    regardless of length (the `--memorable` mode uses this -- real
    words are memorable at whatever length they naturally are, and
    length-filtering a dictionary down to one length throws away most
    of its candidates for no security benefit)."""
    words = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            w = line.strip().lower()
            if not w.isalpha():
                continue
            if length is not None and len(w) != length:
                continue
            words.append(w)
    if not words:
        detail = f"of length {length} " if length is not None else ""
        raise ValueError(f"No words {detail}found in dictionary file: {path}")
    return words


def bundled_memorable_wordlist() -> list[str]:
    """The default word source for --memorable mode: the EFF long
    wordlist (7,772 whole, real, unfiltered-by-length words), embedded
    in eff_wordlist_words.py rather than read from
    wordlists/eff_large_wordlist.txt at runtime -- see that module's
    docstring for why (PyInstaller onefile builds don't bundle loose
    data files automatically, but do bundle any imported .py module)."""
    from eff_wordlist_words import WORDS
    return list(WORDS)


def synthetic_word(length: int, randomize_case: bool = False) -> str:
    """Generate one pronounceable random word of exactly `length` chars,
    alternating consonant/vowel starting with a consonant."""
    chars = []
    for i in range(length):
        pool = _CONSONANTS if i % 2 == 0 else _VOWELS
        ch = pool[secrets.randbelow(len(pool))]
        if randomize_case and secrets.randbelow(2):
            ch = ch.upper()
        chars.append(ch)
    return "".join(chars)


def _randomize_word_case(word: str) -> str:
    return "".join(c.upper() if secrets.randbelow(2) else c for c in word)


def random_digits(n: int) -> str:
    """`n` random decimal digits, e.g. for a codeword suffix."""
    return "".join(_DIGITS[secrets.randbelow(10)] for _ in range(n))


def pick_words(
    length: int,
    count: int,
    dictionary_words=None,
    randomize_case: bool = False,
    digit_suffix_len: int = 0,
) -> str:
    """
    Return a codeword string made of `count` words of `length`
    characters each, joined by hyphens. If dictionary_words is given,
    words are drawn from it (without replacement within the phrase
    when possible); otherwise synthetic pronounceable words are used.

    randomize_case and digit_suffix_len are the opt-in strong mode
    described in the module docstring -- both default off so existing
    callers/behavior are unchanged.
    """
    parts = []
    if dictionary_words:
        pool = list(dictionary_words)
        for _ in range(count):
            if not pool:
                pool = list(dictionary_words)  # allow reuse if we run out
            idx = secrets.randbelow(len(pool))
            word = pool.pop(idx)
            if randomize_case:
                word = _randomize_word_case(word)
            parts.append(word)
    else:
        for _ in range(count):
            parts.append(synthetic_word(length, randomize_case=randomize_case))

    if digit_suffix_len:
        parts = [w + random_digits(digit_suffix_len) for w in parts]

    return "-".join(parts)


def _synthetic_word_bits(length: int) -> float:
    consonant_slots = (length + 1) // 2
    vowel_slots = length // 2
    return consonant_slots * math.log2(len(_CONSONANTS)) + vowel_slots * math.log2(len(_VOWELS))


def estimate_word_entropy_bits(
    length: int,
    count: int,
    dictionary_size: int | None = None,
    randomize_case: bool = False,
    digit_suffix_len: int = 0,
) -> float:
    """
    Rough combinatorial entropy estimate, in bits, for ONE trustee's
    codeword phrase (all `count` words together). This is deliberately
    just the size of the guessing space -- it does NOT include any KDF
    stretching bonus (see kdf.py), which is a separate and much fuzzier
    adjustment.

    dictionary_size, if given, is the number of candidate words of
    `length` chars available in the dictionary file (i.e.
    len(load_dictionary(path, length))) -- dictionary mode's entropy
    is log2(dictionary_size) per word, not the synthetic formula.
    """
    per_word = math.log2(dictionary_size) if dictionary_size else _synthetic_word_bits(length)

    if randomize_case:
        per_word += length  # each letter independently doubles its alphabet

    if digit_suffix_len:
        per_word += digit_suffix_len * math.log2(len(_DIGITS))

    return count * per_word
