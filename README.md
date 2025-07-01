# 💳 BancoDemoREST - API RESTful en Django

Este proyecto es una API bancaria construida con Django REST Framework. Permite registrar usuarios, gestionar cuentas, realizar transacciones (depósitos, retiros y transferencias), registrar logs y acceder a documentación automática con Swagger y ReDoc.

## 📦 Requisitos

- Python 3.10+
- MySQL
- Django 5.2+
- Django REST Framework
- Simple JWT
- drf-yasg (para documentación)

## 📁 Instalación

1. Clona el repositorio:

```bash
git clone https://github.com/tuusuario/bancodemo.git
cd bancodemo
```

2. Crea un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # o .\venv\Scripts\activate en Windows
```

3. Instala los requerimientos:
```bash
pip install -r requirements.txt
```

4. Aplica las migraciones:
```bash
python manage.py migrate
```

5. Crea un superusuario (opcional para acceso a Django Admin):
```bash
python manage.py createsuperuser
```
    
6. Ejecuta el servidor:
```bash
python manage.py runserver
```

## 🔐 Autenticación

Usamos JSON Web Tokens (JWT). Para obtener tokens:

### POST ``/api/users/login/``
```json
{
  "correo_electronico": "cliente@banco.com",
  "password": "tu_contraseña",
  "rol": "Cliente"
}
```

## 🧩 Endpoints Principales
| Recurso |	Método |	Ruta |	Descripción |
| --- | --- | --- | --- |
| Crear Usuario | 	POST |	/api/users/create/ | 	Registro de nuevo usuario |
| Login JWT	| POST |	/api/users/login/ |	Obtener tokens de acceso |
| Crear Cuenta |	POST |	/api/cuentas/crear/ |	Solo operadores |
| Mis Cuentas |	GET | 	/api/cuentas/mis-cuentas/ |	Ver cuentas del cliente autenticado |
| Crear Transacción | 	POST |	/api/transacciones/crear/ |	Solo operadores (depósitos/retiros) |
| Transferencia |	POST |	/api/transacciones/transferir/ |	Solo clientes |
| Lista Transacciones |	GET |	/api/transacciones/ |	Lista según rol |
| Cancelar Transacción |	PUT |	/api/transacciones/cancelar/<id>/ |	Solo si está en estado "Pendiente" |
| Buscar Cliente |	GET |	/api/clientes/buscar/?q= |	Buscar por nombre o correo |
| Buscar Cuenta |	GET	| /api/cuentas/buscar/?numero= |	Buscar por número de cuenta |
| Logs |	GET |	/api/logs/ |	Ver historial de acciones |
| Reporte Transacciones| 	GET |	/api/transacciones/reporte/ |	Filtrar por tipo, fecha, operador, etc. |

## 📄 Documentación Interactiva

* Swagger UI: /docs/
* ReDoc: /redoc/

# #🛡️ Roles del Sistema

* Cliente: Puede ver sus cuentas, hacer transferencias, ver sus transacciones.
* Operador: Puede crear cuentas, hacer depósitos/retiros, ver todos los clientes, logs y transacciones.

## 📝 Licencia

Este proyecto es solo con fines educativos y puede ser adaptado libremente.

## 🙋‍♂️ Autor

Desarrollado por Oscar Palomino - 2025