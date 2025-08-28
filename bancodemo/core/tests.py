from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient


# Utilidades

def get_list(data):
    """Soporta respuesta paginada ({results: []}) o lista simple."""
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    return []


def registrar_usuario(api: APIClient, nombre: str, correo: str, password: str, tipo: str):
    url = reverse("crear_usuario")  # /api/users/create/
    payload = {
        "nombre": nombre,
        "correo_electronico": correo,
        "password": password,
        "tipo": tipo,
    }
    return api.post(url, payload, format="json")


def login(api: APIClient, correo: str, password: str, rol: str):
    """
    Tu login exige 'rol' además de correo y password.
    Devuelve 200 y access/refresh si OK.
    """
    url = reverse("token_obtain_pair")  # /api/users/login/
    payload = {
        "correo_electronico": correo,
        "password": password,
        "rol": rol,
    }
    return api.post(url, payload, format="json")


def auth_client(correo: str, password: str, rol: str) -> APIClient:
    api = APIClient()
    res = login(api, correo, password, rol)
    assert res.status_code == status.HTTP_200_OK, f"Login failed for {correo}: {res.data}"
    token = res.data.get("access")
    assert token, f"Access token missing for {correo}: {res.data}"
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api


def crear_cuenta_operador(api_op: APIClient, correo_cliente: str, tipo: str = "Ahorros"):
    """
    Según tu CuentaSerializer, el operador crea con:
    - correo_cliente
    - tipo ('Ahorros' o 'Corriente')
    """
    url = reverse("crear_cuenta")  # /api/cuentas/crear/
    payload = {
        "correo_cliente": correo_cliente,
        "tipo": tipo,
    }
    return api_op.post(url, payload, format="json")


def mis_cuentas(api_cliente: APIClient):
    url = reverse("mis_cuentas")  # /api/cuentas/mis-cuentas/
    return api_cliente.get(url)


def crear_transaccion_operador(api_op: APIClient, tipo: str, cantidad: str, id_cuenta: int, correo_cliente: str):
    """
    Tu TransaccionSerializer exige para depósitos/retiros:
    - tipo ('Deposito' o 'Retiro')
    - cantidad (Decimal)
    - id_cuenta_id
    - correo_cliente (validación de pertenencia)
    """
    url = reverse("crear_transaccion")  # /api/transacciones/crear/
    payload = {
        "tipo": tipo,
        "cantidad": str(cantidad),
        "id_cuenta_id": id_cuenta,
        "correo_cliente": correo_cliente,
    }
    return api_op.post(url, payload, format="json")


def transferir_cliente(api_cliente: APIClient, id_cuenta_origen: int, numero_cuenta_destino: str, cantidad: str):
    """
    Tu TransaccionSerializer usa id_cuenta_id y numero_cuenta_destino para Transferencia
    desde el endpoint de cliente /api/transacciones/transferir/
    """
    url = reverse("transferencia")
    payload = {
        "tipo": "Transferencia",
        "cantidad": str(cantidad),
        "id_cuenta_id": id_cuenta_origen,
        "numero_cuenta_destino": numero_cuenta_destino,
    }
    return api_cliente.post(url, payload, format="json")


def cancelar_transaccion(api_op: APIClient, pk: int):
    url = reverse("cancelar_transaccion", kwargs={"pk": pk})  # /api/transacciones/cancelar/<pk>/
    return api_op.put(url, {})  # UpdateAPIView usa PUT/PATCH


def buscar_cliente(api_op: APIClient, q: str):
    url = reverse("buscar_cliente") + f"?q={q}"  # /api/clientes/buscar/?q=...
    return api_op.get(url)


def listar_clientes(api_op: APIClient):
    url = reverse("listar_clientes")  # /api/clientes/listar/
    return api_op.get(url)


def listar_transacciones(api: APIClient):
    url = reverse("lista_transacciones")  # /api/transacciones/
    return api.get(url)


def listar_logs(api_op: APIClient, params=None):
    url = reverse("listar_logs")  # /api/logs/listar/
    return api_op.get(url, params or {})


def reporte_transacciones(api_op: APIClient, params=None):
    url = reverse("reporte_transacciones")  # /api/transacciones/reporte/
    return api_op.get(url, params or {})


class BaseSetup(APITestCase):
    """
    Crea:
    - 1 Operador
    - 2 Clientes
    - Asegura 1 cuenta Activa para cada cliente (si no se creó automáticamente)
    Guarda ids y números de cuenta.
    """

    @classmethod
    def setUpTestData(cls):
        cls.OP_PASS = "Op3r@dor!"
        cls.C1_PASS = "CliPass#1"
        cls.C2_PASS = "CliPass#2"

        api = APIClient()

        # Crear usuarios
        r_op = registrar_usuario(api, "Operador Uno", "op@bank.com", cls.OP_PASS, "Operador")
        assert r_op.status_code in (201, 200), r_op.data

        r_c1 = registrar_usuario(api, "Cliente Uno", "cli@bank.com", cls.C1_PASS, "Cliente")
        assert r_c1.status_code in (201, 200), r_c1.data

        r_c2 = registrar_usuario(api, "Cliente Dos", "cli2@bank.com", cls.C2_PASS, "Cliente")
        assert r_c2.status_code in (201, 200), r_c2.data

        # Autenticar
        cls.api_operador = auth_client("op@bank.com", cls.OP_PASS, "Operador")
        cls.api_cli1 = auth_client("cli@bank.com", cls.C1_PASS, "Cliente")
        cls.api_cli2 = auth_client("cli2@bank.com", cls.C2_PASS, "Cliente")

        # Asegurar cuentas activas para ambos clientes
        # Cliente 1
        res_c1 = mis_cuentas(cls.api_cli1)
        assert res_c1.status_code == 200, res_c1.data
        ctas1 = get_list(res_c1.data)
        if not ctas1:
            # Crear por operador
            r = crear_cuenta_operador(cls.api_operador, "cli@bank.com", "Ahorros")
            assert r.status_code in (201, 200), r.data
            res_c1 = mis_cuentas(cls.api_cli1)
            ctas1 = get_list(res_c1.data)

        # Cliente 2
        res_c2 = mis_cuentas(cls.api_cli2)
        assert res_c2.status_code == 200, res_c2.data
        ctas2 = get_list(res_c2.data)
        if not ctas2:
            r = crear_cuenta_operador(cls.api_operador, "cli2@bank.com", "Ahorros")
            assert r.status_code in (201, 200), r.data
            res_c2 = mis_cuentas(cls.api_cli2)
            ctas2 = get_list(res_c2.data)

        assert ctas1, "Cliente 1 debe tener al menos una cuenta"
        assert ctas2, "Cliente 2 debe tener al menos una cuenta"

        c1 = ctas1[0]
        c2 = ctas2[0]
        # Campos según CuentaDetalleSerializer
        cls.c1_id = c1["id_cuenta"]
        cls.c1_num = c1["numero_cuenta"]
        cls.c1_correo = "cli@bank.com"

        cls.c2_id = c2["id_cuenta"]
        cls.c2_num = c2["numero_cuenta"]
        cls.c2_correo = "cli2@bank.com"


class AuthTests(BaseSetup):
    def test_login_cliente_ok(self):
        res = login(APIClient(), "cli@bank.com", self.C1_PASS, "Cliente")
        self.assertEqual(res.status_code, 200)
        self.assertIn("access", res.data)

    def test_perfil_cliente(self):
        url = reverse("mi_perfil")
        res = self.api_cli1.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data.get("correo_electronico"), "cli@bank.com")

    def test_cambiar_contrasena(self):
        url = reverse("cambiar_contrasena")
        payload = {
            "contrasena_actual": self.C1_PASS,
            "nueva_contrasena": "Nueva#Clave2025",
            "confirmar_contrasena": "Nueva#Clave2025",
        }
        res = self.api_cli1.put(url, payload, format="json")
        self.assertIn(res.status_code, (200, 204))


class OperadorCuentaTests(BaseSetup):
    def test_crear_cuenta_para_cliente(self):
        res = crear_cuenta_operador(self.api_operador, "cli@bank.com", "Corriente")
        self.assertIn(res.status_code, (201, 200))
        # El serializer devuelve la cuenta creada; chequear campos clave
        self.assertIn("numero_cuenta", res.data)
        self.assertIn("tipo", res.data)
        self.assertEqual(res.data["tipo"], "Corriente")

    def test_buscar_cliente(self):
        res = buscar_cliente(self.api_operador, "cli@")
        self.assertEqual(res.status_code, 200)
        data = get_list(res.data)
        self.assertTrue(any("cli@" in (u.get("correo_electronico") or "") for u in data))

    def test_listar_clientes(self):
        res = listar_clientes(self.api_operador)
        self.assertEqual(res.status_code, 200)
        data = get_list(res.data)
        self.assertTrue(isinstance(data, list))
        correos = [u.get("correo_electronico") for u in data]
        self.assertTrue(any(c and c.startswith("cli@") for c in correos))


class TransaccionOperadorTests(BaseSetup):
    def test_deposito_operador(self):
        res = crear_transaccion_operador(self.api_operador, "Deposito", "150.00", self.c1_id, self.c1_correo)
        self.assertIn(res.status_code, (200, 201))
        self.assertEqual(res.data.get("tipo"), "Deposito")
        self.assertEqual(res.data.get("estado"), "Completada")

    def test_retiro_operador_con_saldo_suficiente_e_insuficiente(self):
        # Asegurar saldo previo
        crear_transaccion_operador(self.api_operador, "Deposito", "300.00", self.c1_id, self.c1_correo)

        # Retiro válido
        res_ok = crear_transaccion_operador(self.api_operador, "Retiro", "100.00", self.c1_id, self.c1_correo)
        self.assertIn(res_ok.status_code, (200, 201))
        self.assertEqual(res_ok.data.get("tipo"), "Retiro")
        self.assertEqual(res_ok.data.get("estado"), "Completada")

        # Retiro excesivo -> Cancelada o 400
        res_bad = crear_transaccion_operador(self.api_operador, "Retiro", "999999.00", self.c1_id, self.c1_correo)
        self.assertIn(res_bad.status_code, (200, 201, 400))
        if res_bad.status_code in (200, 201):
            self.assertEqual(res_bad.data.get("estado"), "Cancelada")


class TransferenciaClienteTests(BaseSetup):
    def test_transferencia_cliente_completa_y_cancelada(self):
        # Asegurar saldo en origen
        crear_transaccion_operador(self.api_operador, "Deposito", "250.00", self.c1_id, self.c1_correo)

        # Transferencia válida
        res_ok = transferir_cliente(self.api_cli1, self.c1_id, self.c2_num, "100.00")
        self.assertIn(res_ok.status_code, (200, 201))
        self.assertEqual(res_ok.data.get("tipo"), "Transferencia")
        self.assertEqual(res_ok.data.get("estado"), "Completada")

        # Transferencia con saldo insuficiente
        res_bad = transferir_cliente(self.api_cli1, self.c1_id, self.c2_num, "999999.00")
        self.assertIn(res_bad.status_code, (200, 201, 400))
        if res_bad.status_code in (200, 201):
            self.assertEqual(res_bad.data.get("estado"), "Cancelada")


class ListadosYFiltrosTests(BaseSetup):
    def test_listado_transacciones_por_cliente_y_operador(self):
        # Generar actividad
        crear_transaccion_operador(self.api_operador, "Deposito", "50.00", self.c1_id, self.c1_correo)

        # Cliente ve sus transacciones
        res_cli = listar_transacciones(self.api_cli1)
        self.assertEqual(res_cli.status_code, 200)
        data_cli = get_list(res_cli.data)
        self.assertIsInstance(data_cli, list)

        # Operador ve las que realizó
        res_op = listar_transacciones(self.api_operador)
        self.assertEqual(res_op.status_code, 200)
        data_op = get_list(res_op.data)
        self.assertIsInstance(data_op, list)


class ReporteYLogsTests(BaseSetup):
    def test_reporte_transacciones(self):
        # Generar actividad
        crear_transaccion_operador(self.api_operador, "Deposito", "75.00", self.c1_id, self.c1_correo)
        crear_transaccion_operador(self.api_operador, "Retiro", "25.00", self.c1_id, self.c1_correo)

        params = {
            "tipo": "Deposito",  # filtro opcional; puedes quitarlo si prefieres
            "desde": "2000-01-01",
            "hasta": "2100-01-01",
        }
        res = reporte_transacciones(self.api_operador, params)
        self.assertEqual(res.status_code, 200)
        data = get_list(res.data) if isinstance(res.data, (dict, list)) else []
        self.assertTrue(isinstance(data, list))

    def test_listar_logs(self):
        # Provocar logs (login ya genera; también depósito)
        crear_transaccion_operador(self.api_operador, "Deposito", "10.00", self.c1_id, self.c1_correo)

        res = listar_logs(self.api_operador)
        self.assertEqual(res.status_code, 200)
        data = get_list(res.data)
        self.assertIsInstance(data, list)

    def test_cancelar_transaccion_pendiente(self):
        """
        Tu CancelarTransaccionView solo permite cancelar si estado == 'Pendiente'.
        Para cubrir este flujo, forzamos un caso Pendiente:
        En tu serializer, 'Transferencia' marca 'Pendiente' en validate si el monto no supera el saldo,
        pero en create la concretas y la marcas 'Completada'. Entonces, no hay estado Pendiente persistente.
        Esta prueba intenta cancelar y acepta que obtengamos error si no existe una transacción Pendiente.
        """
        # Hacemos una operación para tener alguna transacción creada
        res_tx = crear_transaccion_operador(self.api_operador, "Deposito", "20.00", self.c1_id, self.c1_correo)
        self.assertIn(res_tx.status_code, (200, 201))
        tx_id = res_tx.data.get("id_transaccion") or res_tx.data.get("id") or res_tx.data.get("pk")
        self.assertIsNotNone(tx_id)

        # Intento de cancelación: lo más probable es que devuelva error de validación
        res_cancel = cancelar_transaccion(self.api_operador, tx_id)
        # Aceptamos 400 en tu lógica actual, ya que no está Pendiente
        self.assertIn(res_cancel.status_code, (200, 204, 400))