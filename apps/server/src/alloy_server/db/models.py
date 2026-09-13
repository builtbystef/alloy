"""Every model, so `Base.metadata` and the mapper registry are complete.

Imported by the package init. Kept apart from `db/base.py`: the models import
`Base`, so importing them from there is a cycle for any process that reaches
a model before `Base`.
"""

from alloy_server.agent import models as _agent_models  # noqa: F401
from alloy_server.auth import models as _auth_models  # noqa: F401
from alloy_server.crm.attachments import models as _attachment_models  # noqa: F401
from alloy_server.crm.companies import models as _company_models  # noqa: F401
from alloy_server.crm.contacts import models as _contact_models  # noqa: F401
from alloy_server.crm.imports import models as _import_models  # noqa: F401
from alloy_server.crm.tasks import models as _task_models  # noqa: F401
from alloy_server.db.base import Base
from alloy_server.workspaces import models as _workspace_models  # noqa: F401

__all__ = ["Base"]
