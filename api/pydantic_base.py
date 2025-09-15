from pydantic import BaseModel
from pydantic import ConfigDict


class AppModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


