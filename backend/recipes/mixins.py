from rest_framework import mixins, viewsets


class ListRetrieveModelMixin(viewsets.GenericViewSet,
                             mixins.ListModelMixin,
                             mixins.RetrieveModelMixin):
    pass
