from alloy_server.db.base import Base
from alloy_server.integrations.ai import models as _ai_models  # noqa: F401
from alloy_server.integrations.rate_limit import models as _rate_limit_models  # noqa: F401
from alloy_server.modules.assistant import models as _assistant_models  # noqa: F401
from alloy_server.modules.auth import models as _auth_models  # noqa: F401
from alloy_server.modules.crm.attachments import models as _attachment_models  # noqa: F401
from alloy_server.modules.crm.companies import models as _company_models  # noqa: F401
from alloy_server.modules.crm.contacts import models as _contact_models  # noqa: F401
from alloy_server.modules.crm.imports import models as _import_models  # noqa: F401
from alloy_server.modules.crm.tasks import models as _task_models  # noqa: F401
from alloy_server.modules.workspaces import models as _workspace_models  # noqa: F401

__all__ = ["Base"]
