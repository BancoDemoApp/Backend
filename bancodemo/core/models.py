from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class Cuenta(models.Model):
    """
    Representa una cuenta bancaria asociada a un usuario.
    
    Atributos:
    - número de cuenta único
    - tipo (Ahorros o Corriente)
    - saldo actual
    - estado (Activa o Inactiva)
    """
    id_cuenta = models.AutoField(db_column='ID_Cuenta', primary_key=True)  # Field name made lowercase.
    numero_cuenta = models.CharField(db_column='Numero_Cuenta', unique=True, max_length=20)  # Field name made lowercase.
    tipo = models.CharField(db_column='Tipo', max_length=9)  # Field name made lowercase.
    saldo = models.DecimalField(db_column='Saldo', max_digits=10, decimal_places=2)  # Field name made lowercase.
    estado = models.CharField(db_column='Estado', max_length=8)  # Field name made lowercase.
    id_usuario = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='ID_Usuario')  # Field name made lowercase.

    class Meta:
        managed = True
        db_table = 'cuenta'
        ordering = ['id_cuenta']


class Log(models.Model):
    """
    Guarda acciones importantes del sistema como auditoría.

    Atributos:
    - usuario que realizó la acción
    - descripción y fecha del evento
    """
    id_log = models.AutoField(db_column='ID_Log', primary_key=True)  # Field name made lowercase.
    id_usuario = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='ID_Usuario', blank=True, null=True)  # Field name made lowercase.
    accion = models.CharField(db_column='Accion', max_length=255)  # Field name made lowercase.
    descripcion = models.TextField(db_column='Descripcion')  # Field name made lowercase.
    fecha = models.DateTimeField(db_column='Fecha', auto_now_add=True, null=False)  # Field name made lowercase.

    class Meta:
        managed = True
        db_table = 'log'


class Transaccion(models.Model):
    """
    Registra cada transacción bancaria del sistema: depósitos, retiros y transferencias.

    Atributos:
    - tipo de transacción
    - cantidad
    - fecha y estado
    - cuenta origen, destino (si aplica) y operador que la realizó
    """
    id_transaccion = models.AutoField(db_column='ID_Transaccion', primary_key=True)
    tipo = models.CharField(db_column='Tipo', max_length=13)
    cantidad = models.DecimalField(db_column='Cantidad', max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(db_column='Fecha', auto_now_add=True, null=False)
    estado = models.CharField(db_column='Estado', max_length=10)
    
    id_cuenta = models.ForeignKey(
        'Cuenta', models.DO_NOTHING,
        db_column='ID_Cuenta',
        related_name='transacciones_origen'
    )
    
    id_operador = models.ForeignKey(
        'Usuario', models.DO_NOTHING,
        db_column='ID_Operador',
        null=True, blank=True,
        related_name='transacciones_realizadas'
    )
    
    id_cuenta_destino = models.ForeignKey(
        'Cuenta', models.DO_NOTHING,
        db_column='ID_Cuenta_Destino',
        null=True, blank=True,
        related_name='transacciones_recibidas'
    )

    class Meta:
        managed = True
        db_table = 'transaccion'

class UsuarioManager(BaseUserManager):
    def create_user(self, correo_electronico, nombre, password=None, **extra_fields):
        if not correo_electronico:
            raise ValueError('El correo electrónico es obligatorio')
        correo_electronico = self.normalize_email(correo_electronico)
        user = self.model(correo_electronico=correo_electronico, nombre=nombre, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, correo_electronico, nombre, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(correo_electronico, nombre, password, **extra_fields)
    
class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Modelo de usuario para clientes y operadores del sistema bancario.
    
    - Clientes: pueden ver sus cuentas, transacciones y hacer transferencias.
    - Operadores: pueden crear cuentas y realizar depósitos o retiros.
    """
    id = models.AutoField(db_column='ID_Usuario', primary_key=True)  # Field name made lowercase.
    nombre = models.CharField(db_column='Nombre', max_length=100)  # Field name made lowercase.
    correo_electronico = models.CharField(db_column='Correo_Electronico', unique=True, max_length=100)  # Field name made lowercase.
    telefono = models.CharField(db_column='Telefono', max_length=15, blank=True, null=True)  # Field name made lowercase.
    password = models.CharField(db_column='Contrasena', max_length=255)  # Field name made lowercase.
    tipo = models.CharField(db_column='Tipo', max_length=8)  # Field name made lowercase.
    fecha_registro = models.DateTimeField(db_column='Fecha_Registro', auto_now_add=True)  # Field name made lowercase.
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
        
    objects = UsuarioManager()
    
    USERNAME_FIELD = 'correo_electronico'
    REQUIRED_FIELDS = ['nombre']

    class Meta:
        db_table = 'usuario'
        ordering = ['id']