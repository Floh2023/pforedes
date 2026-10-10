# PFO 2: Sistema de gestión de tareas

Proyecto con una API REST Flask y SQLite, más una interfaz HTML/JavaScript estática. La interfaz se puede publicar en GitHub Pages; la API Python debe ejecutarse en un servicio de backend como Render porque Pages solo publica archivos estáticos.

## Estructura

- `servidor.py`: API Flask, SQLite, registro, inicio de sesión y tareas.
- `index.html`, `styles.css`, `app.js`: interfaz estática.
- `api-config.js`: URL pública de la API que consume la interfaz.
- `requirements.txt`: dependencias de Python.

## Ejecutar localmente

```bash
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python servidor.py
```

La API escucha en `http://127.0.0.1:5000` y crea `tareas.db` automáticamente. Para ver la bienvenida del endpoint requerido, abre `http://127.0.0.1:5000/tareas`.

Para probar la interfaz localmente, abre otra terminal y sirve la carpeta estática, por ejemplo:

```bash
python3 -m http.server 5500
```

Abre `http://localhost:5500`. La API ya permite este origen local por CORS.

## Publicar la API en Render

1. Sube este repositorio a GitHub.
2. En Render, crea **New → Web Service** y conecta el repositorio.
3. Configura:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn --bind 0.0.0.0:$PORT servidor:app`
4. En **Environment** agrega:
   - `SECRET_KEY`: un secreto aleatorio y privado.
   - `FRONTEND_ORIGINS`: `https://floh2023.github.io`
5. Crea el servicio y copia la URL pública, por ejemplo `https://pfo2-api.onrender.com`.

La base SQLite se crea automáticamente en el servidor. El filesystem de los servicios puede ser efímero: para conservar los datos después de reinicios o nuevos deploys, configura almacenamiento persistente y define `DATABASE_PATH` con una ruta dentro del disco persistente.

## Publicar la interfaz en GitHub Pages

1. Edita `api-config.js` y reemplaza la cadena vacía por la URL de Render, sin `/` al final:

   ```js
   window.API_BASE_URL = "https://pfo2-api.onrender.com";
   ```

2. Guarda y sube el cambio a GitHub (`git add api-config.js && git commit -m "Configurar URL de la API" && git push`).
3. En el repositorio `Floh2023/pforedes`, ve a **Settings → Pages**.
4. En **Build and deployment**, selecciona **Deploy from a branch**, rama `main` y carpeta `/(root)`, luego pulsa **Save**.
5. Espera el deploy. La interfaz quedará en `https://floh2023.github.io/pforedes/`.

El HTML de Pages llama a Render para registro, login y tareas. El login devuelve un token firmado con vencimiento de 24 horas, que la interfaz envía como `Authorization: Bearer ...`. El backend también admite las sesiones cookie para las pruebas con `curl`.

## Probar la API con curl

Reemplaza `http://127.0.0.1:5000` por la URL de Render para probar el servidor publicado.

```bash
curl -i -X POST http://127.0.0.1:5000/registro \
  -H 'Content-Type: application/json' \
  -d '{"usuario":"ana","contraseña":"1234"}'

curl -i -c cookies.txt -X POST http://127.0.0.1:5000/login \
  -H 'Content-Type: application/json' \
  -d '{"usuario":"ana","contraseña":"1234"}'

curl -i -b cookies.txt -X POST http://127.0.0.1:5000/api/tareas \
  -H 'Content-Type: application/json' \
  -d '{"titulo":"Entregar el trabajo práctico","descripcion":"Revisar el README"}'

curl -i -b cookies.txt http://127.0.0.1:5000/api/tareas
```

## Respuestas conceptuales

### ¿Por qué es obligatorio hashear las contraseñas?

El hash evita almacenar la contraseña original. Si alguien accede a la base de datos, no obtiene directamente las credenciales que los usuarios podrían reutilizar en otros servicios. Para iniciar sesión se compara la contraseña ingresada con el hash; no se descifra ni recupera el texto original. Werkzeug genera un hash con sal y PBKDF2. El hash sigue siendo un dato sensible y también deben protegerse la base de datos y los tokens.

### ¿Cuáles son las ventajas de SQLite en este proyecto?

SQLite viene integrado con Python, no requiere instalar ni administrar un servidor de base de datos y guarda los datos en un archivo local. Esto simplifica la instalación, el traslado y las copias de seguridad, y resulta conveniente para trabajos prácticos, prototipos y aplicaciones pequeñas. También permite definir relaciones y restricciones; aquí cada tarea está asociada a un usuario mediante una clave foránea. Si la aplicación necesitara muchas escrituras simultáneas o escalado distribuido, convendría migrar a una base de datos de servidor.
