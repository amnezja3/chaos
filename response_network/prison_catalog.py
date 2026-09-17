"""Approved gameplay destinations for future consequence sanctions.

Coordinates are the author's approved data, not release locations. Loading or
reading this catalog does not access profiles/SQLite or impose a sanction.
"""
from dataclasses import asdict, dataclass
from types import MappingProxyType


PRISON_CATALOG_VERSION = 1


@dataclass(frozen=True)
class Prison:
    id: str
    name: str
    country: str
    city: str
    lat: float
    lng: float
    type: str
    full_name: str = ""
    alias: str = ""


_PRISONS = (
    Prison("adx_florence", "ADX Florence", "USA", "Florence, Colorado",
           38.35639, -105.09528, "supermax"),
    Prison("black_dolphin", "Black Dolphin Prison", "Russia", "Sol-Iletsk",
           51.15556, 54.99306, "maximum_security"),
    Prison("cecot", "CECOT", "El Salvador", "Tecoluca",
           13.53361, -88.80500, "maximum_security",
           full_name="Terrorism Confinement Center"),
    Prison("bang_kwang", "Bang Kwang Central Prison", "Thailand", "Nonthaburi",
           13.84669, 100.49289, "maximum_security"),
    Prison("belmarsh", "HM Prison Belmarsh", "United Kingdom", "London",
           51.49666, 0.09327, "high_security"),
    Prison("altiplano", "Federal Social Readaptation Center No. 1", "Mexico",
           "Almoloya de Juárez", 19.42231, -99.75003, "maximum_security",
           alias="Altiplano"),
    Prison("qincheng", "Qincheng Prison", "China", "Beijing",
           40.24131, 116.38339, "maximum_security"),
    Prison("fuchu", "Fuchū Prison", "Japan", "Fuchū, Tokyo",
           35.68433, 139.47397, "high_security"),
    Prison("portlaoise", "Portlaoise Prison", "Ireland", "Portlaoise",
           53.0369975, -7.2874778, "high_security"),
    Prison("pelican_bay", "Pelican Bay State Prison", "USA", "Crescent City, California",
           41.85500, -124.15000, "supermax"),
)
_BY_ID = MappingProxyType({prison.id: prison for prison in _PRISONS})


def get_prison(prison_id: str) -> dict:
    """Return a detached destination; unknown IDs raise KeyError, never fallback."""
    return asdict(_BY_ID[prison_id])


def list_prisons() -> list[dict]:
    """Return the small approved catalog in stable order, without database I/O."""
    return [asdict(prison) for prison in _PRISONS]
