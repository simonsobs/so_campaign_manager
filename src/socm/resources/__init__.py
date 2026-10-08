from .localhost import LocalResource
from .perlmutter import PerlmutterResource
from .tiger import TigerResource
from .universe import UniverseResource

registered_resources = {
    "perlmutter": PerlmutterResource,
    "tiger3": TigerResource,
    "universe": UniverseResource,
    "localhost": LocalResource,
}
