from .perlmutter import PerlmutterResource  # noqa: F401
from .tiger import TigerResource  # noqa: F401

registered_resources = {"perlmutter": PerlmutterResource, "tiger3": TigerResource}
