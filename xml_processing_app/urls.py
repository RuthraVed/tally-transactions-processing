from rest_framework.routers import SimpleRouter
from .views import ProcessedTransactionViewset
router = SimpleRouter()
router.register('accounts', ProcessedTransactionViewset)
urlpatterns = router.urls