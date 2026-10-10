# PFO 2: Sistema de gestión de tareas

API REST desarrollada con Flask y SQLite. Incluye registro de usuarios con contraseñas hasheadas, inicio y cierre de sesión, una página HTML de bienvenida y endpoints JSON para crear y listar tareas del usuario autenticado.

## Requisitos

- Python 3.10 o superior.
- `pip`.

## Instalación y ejecución

Desde la carpeta del proyecto:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

La base `tareas.db` se crea automáticamente al iniciar el servidor; también se puede inicializar por separado:

```bash
python -c "from servidor import inicializar_db; inicializar_db()"
```

Inicia la API:

```bash
python servidor.py
```

Por defecto escucha en `http://127.0.0.1:5000`. Se puede configurar `DATABASE_PATH`, `PORT` y `SECRET_KEY` mediante variables de entorno. Para un entorno real, define `SECRET_KEY` con un valor aleatorio y privado.

## Probar los endpoints

### Página HTML

Abre `http://127.0.0.1:5000/tareas` en el navegador. Devuelve una página HTML simple de bienvenida.

### Registro

```bash
curl -i -X POST http://127.0.0.1:5000/registro \
  -H 'Content-Type: application/json' \
  -d '{"usuario":"ana","contraseña":"1234"}'
```

Si el registro es correcto, responde `201 Created`. Un nombre de usuario repetido responde `409 Conflict`. También se acepta `contrasena` sin tilde como nombre alternativo del campo.

### Inicio de sesión

La respuesta establece una cookie de sesión. Guarda la cookie para usar los endpoints de tareas:

```bash
curl -i -c cookies.txt -X POST http://127.0.0.1:5000/login \
  -H 'Content-Type: application/json' \
  -d '{"usuario":"ana","contraseña":"1234"}'
```

Credenciales inválidas responden `401 Unauthorized`.

### Crear y listar tareas

```bash
curl -i -b cookies.txt -X POST http://127.0.0.1:5000/api/tareas \
  -H 'Content-Type: application/json' \
  -d '{"titulo":"Entregar el trabajo práctico","descripcion":"Revisar el README"}'

curl -i -b cookies.txt http://127.0.0.1:5000/api/tareas
```

Las tareas se asocian al usuario que inició sesión. Sin sesión, estos endpoints responden `401 Unauthorized`. Para cerrar la sesión:

```bash
curl -i -b cookies.txt -X POST http://127.0.0.1:5000/logout
```

## Respuestas conceptuales

### 1. ¿Por qué es obligatorio hashear las contraseñas?

El hash evita almacenar la contraseña original. Si alguien accede a la base de datos, no obtiene directamente las credenciales que los usuarios podrían reutilizar en otros servicios. Al iniciar sesión, el servidor compara la contraseña ingresada con el hash usando la función de verificación; no necesita descifrar ni recuperar el texto original. En esta implementación, Werkzeug genera hashes con sal y un algoritmo adecuado para contraseñas. El hash sigue siendo un dato sensible y la aplicación también debe proteger la base y las sesiones.

### 2. ¿Cuáles son las ventajas de SQLite en este proyecto?

SQLite viene integrado con Python, no requiere instalar ni administrar un servidor de base de datos y guarda los datos en un archivo local. Esto simplifica la instalación, el traslado y las copias de seguridad, y resulta conveniente para trabajos prácticos, prototipos y aplicaciones pequeñas o de uso moderado. Además, permite aplicar restricciones y relaciones entre tablas, como la clave foránea que vincula cada tarea con su usuario. Si la aplicación necesitara muchas escrituras concurrentes o escalado distribuido, sería razonable migrar a un servidor de base de datos.
