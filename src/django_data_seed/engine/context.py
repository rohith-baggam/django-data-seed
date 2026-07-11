"""
The generation context shared by every provider.

Everything that produces a value for a field reaches for a ``GenContext``: it
carries the seeded random source, the Mimesis providers for the chosen locale,
and a handful of statistical helpers that make seeded data look less uniform
than ``random.randint`` ever will. Keeping all of that on one object is what
lets the whole run be reproducible from a single ``--seed`` value.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from mimesis import Generic
from mimesis.locales import Locale


def resolve_locale(locale: str | Locale | None) -> Locale:
    """
    Turns a user-supplied locale (``"de"``, ``"de_DE"``, a ``Locale`` member,
    or ``None``) into a concrete ``mimesis.locales.Locale``.

    Args:
        - locale: A locale code string, a ``Locale`` enum member, or ``None``.

    Returns:
        - The matching ``Locale`` member, falling back to ``Locale.EN`` when the
          value is missing or unrecognised.
    """
    if isinstance(locale, Locale):
        return locale
    if not locale:
        return Locale.DEFAULT_LOCALE if hasattr(Locale, "DEFAULT_LOCALE") else Locale.EN

    wanted = str(locale).replace("-", "_").lower()
    for member in Locale:
        if member.value.lower() == wanted or member.value.lower().split("_")[0] == wanted:
            return member
    return Locale.EN


@dataclass
class GenContext:
    """
    The bag of everything a provider needs to generate one value.

    Attributes:
        - locale: The resolved Mimesis locale driving realistic text/address data.
        - seed: The RNG seed, or ``None`` for a non-reproducible run.
        - rng: A dedicated ``random.Random`` so we never touch the global RNG.
        - generic: The Mimesis ``Generic`` bundle (person, address, finance, ...).
        - use_tz: Mirrors Django's ``USE_TZ`` so datetimes come out aware or naive.
        - null_probability: Chance a nullable, non-required field is left NULL.
        - realism: ``"smart"`` uses distributions/temporal shapes; ``"uniform"``
          falls back to dumb-fast uniform noise.
        - make_files: Whether file/image providers write tiny real files.
        - media_root: Where those files land (defaults to Django's ``MEDIA_ROOT``).
    """

    locale: Locale = Locale.EN
    seed: int | None = None
    use_tz: bool = True
    null_probability: float = 0.1
    realism: str = "smart"
    make_files: bool = True
    media_root: str | None = None
    rng: random.Random = field(init=False)
    generic: Generic = field(init=False)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)
        # ? Mimesis takes its own seed so its stream is reproducible alongside ours.
        self.generic = Generic(locale=self.locale, seed=self.seed)

    # * Convenience accessors for the Mimesis sub-providers we lean on the most.
    @property
    def person(self):
        return self.generic.person

    @property
    def address(self):
        return self.generic.address

    @property
    def finance(self):
        return self.generic.finance

    @property
    def internet(self):
        return self.generic.internet

    @property
    def text(self):
        return self.generic.text

    @property
    def numeric(self):
        return self.generic.numeric

    @property
    def datetime(self):
        return self.generic.datetime

    @property
    def cryptographic(self):
        return self.generic.cryptographic

    # * Statistical helpers -- the layer that keeps aggregate data believable.
    def smart(self) -> bool:
        """Whether the realism layer is switched on for this run."""
        return self.realism != "uniform"

    def maybe_null(self) -> bool:
        """Returns True roughly ``null_probability`` of the time."""
        return self.rng.random() < self.null_probability

    def weighted_choice(self, options: Sequence[Any]) -> Any:
        """
        Picks from ``options`` with a decaying weight so the first option is the
        most common -- real status/choice columns are lopsided, not uniform.

        Args:
            - options: The candidate values, most-likely first.

        Returns:
            - One value from ``options``.
        """
        options = list(options)
        if not options:
            raise ValueError("weighted_choice() needs at least one option")
        if not self.smart() or len(options) == 1:
            return self.rng.choice(options)
        # ? Geometric-ish decay: 0.55, 0.24, 0.11, ... normalised over the set.
        weights = [0.55 ** i for i in range(len(options))]
        return self.rng.choices(options, weights=weights, k=1)[0]

    def lognormal(self, mean: float, sigma: float = 0.9) -> float:
        """
        Draws a positive, right-skewed number the way prices and salaries behave.

        Args:
            - mean: The rough centre of the distribution (a plain currency amount).
            - sigma: The spread; larger means a longer tail of big values.

        Returns:
            - A positive float clustered near ``mean`` with a long upper tail.
        """
        if not self.smart():
            return float(self.rng.uniform(0, mean * 2))
        mu = math.log(max(mean, 1e-9))
        return math.exp(self.rng.normalvariate(mu, sigma))

    def zipf_index(self, size: int) -> int:
        """
        Returns an index into a pool of ``size`` items, heavily favouring the
        low indices -- the "20% of parents get 80% of the children" shape used
        when reusing foreign keys.

        Args:
            - size: The number of items in the pool.

        Returns:
            - An integer in ``range(size)``, biased toward 0.
        """
        if size <= 1:
            return 0
        if not self.smart():
            return self.rng.randrange(size)
        # ? Sample a rank from a truncated Zipf and clamp into range.
        weights = [1.0 / (i + 1) for i in range(size)]
        return self.rng.choices(range(size), weights=weights, k=1)[0]
