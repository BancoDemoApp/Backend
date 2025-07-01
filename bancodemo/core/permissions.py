from rest_framework.permissions import BasePermission

class EsOperador(BasePermission):
    """
    Permite el acceso solo a usuarios con tipo 'Operador'.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.tipo == 'Operador'
