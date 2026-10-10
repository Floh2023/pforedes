"""API REST sencilla para gestionar usuarios y tareas con Flask y SQLite."""

from __future__ import annotations

import os
import sqlite3
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from flask import Flask, g, jsonify, render_template, request, session
from flask_cors import CORS
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "tareas.db"))

def conectar_db() -> sqlite3.Connection:
    """Obtiene una conexión por petición y devuelve filas como diccionarios."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def inicializar_db() -> None:
    """Crea las tablas si todavía no existen (también se puede ejecutar aparte)."""
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE) as db:
        db.execute("PRAGMA foreign_keys = ON")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                contrasena_hash TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tareas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                descripcion TEXT NOT NULL DEFAULT '',
                completada INTEGER NOT NULL DEFAULT 0 CHECK (completada IN (0, 1)),
                creada_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            );
        """)


def requiere_login(func: Callable[..., Any]) -> Callable[..., Any]:
    """Protege rutas con token Bearer (web estática) o cookie (pruebas locales)."""
    @wraps(func)
    def decorada(*args: Any, **kwargs: Any) -> Any:
        usuario_id = session.get("usuario_id")
        encabezado = request.headers.get("Authorization", "")
        if encabezado.startswith("Bearer "):
            try:
                datos_token = app.extensions["token_serializer"].loads(
                    encabezado.removeprefix("Bearer "), max_age=86400
                )
                usuario_id = datos_token["usuario_id"]
            except (BadSignature, SignatureExpired, KeyError, TypeError):
                return jsonify(error="Token inválido o vencido; inicia sesión nuevamente"), 401
        if usuario_id is None:
            return jsonify(error="Debes iniciar sesión"), 401
        g.usuario_id = usuario_id
        return func(*args, **kwargs)
    return decorada


def crear_app() -> Flask:
    app = Flask(__name__)
    # En producción, configura SECRET_KEY mediante una variable de entorno segura.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "clave-local-cambiar-en-produccion")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    # GitHub Pages y el backend tienen dominios distintos: habilitamos CORS
    # para el sitio publicado y los servidores locales habituales.
    origenes = os.environ.get(
        "FRONTEND_ORIGINS",
        "https://floh2023.github.io,http://localhost:5500,http://127.0.0.1:5500",
    )
    CORS(app, origins=[origen.strip() for origen in origenes.split(",") if origen.strip()])
    app.extensions["token_serializer"] = URLSafeTimedSerializer(
        app.config["SECRET_KEY"], salt="pfo2-api-token"
    )

    @app.teardown_appcontext
    def cerrar_db(_error: BaseException | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.post("/registro")
    def registro() -> Any:
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify(error="El cuerpo debe ser un JSON válido"), 400
        usuario = datos.get("usuario")
        contrasena = datos.get("contraseña", datos.get("contrasena"))
        if not isinstance(usuario, str) or not usuario.strip():
            return jsonify(error="El campo 'usuario' es obligatorio"), 400
        if not isinstance(contrasena, str) or len(contrasena) < 4:
            return jsonify(error="La contraseña debe tener al menos 4 caracteres"), 400

        # Solo se persiste el hash; el texto original nunca se escribe en la BD.
        # PBKDF2 evita depender de hashlib.scrypt, que no está disponible en
        # algunas instalaciones de Python 3.9 usadas en macOS.
        hash_seguro = generate_password_hash(contrasena, method="pbkdf2:sha256:600000")
        try:
            db = conectar_db()
            cursor = db.execute(
                "INSERT INTO usuarios (usuario, contrasena_hash) VALUES (?, ?)",
                (usuario.strip(), hash_seguro),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return jsonify(error="Ese nombre de usuario ya está registrado"), 409
        return jsonify(mensaje="Usuario registrado", id=cursor.lastrowid), 201

    @app.post("/login")
    def login() -> Any:
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict):
            return jsonify(error="El cuerpo debe ser un JSON válido"), 400
        usuario = datos.get("usuario")
        contrasena = datos.get("contraseña", datos.get("contrasena"))
        if not isinstance(usuario, str) or not isinstance(contrasena, str):
            return jsonify(error="Se requieren usuario y contraseña"), 400

        fila = conectar_db().execute(
            "SELECT id, usuario, contrasena_hash FROM usuarios WHERE usuario = ?",
            (usuario.strip(),),
        ).fetchone()
        if fila is None or not check_password_hash(fila["contrasena_hash"], contrasena):
            return jsonify(error="Usuario o contraseña incorrectos"), 401

        session.clear()
        session["usuario_id"] = fila["id"]
        token = app.extensions["token_serializer"].dumps({"usuario_id": fila["id"]})
        return jsonify(
            mensaje="Inicio de sesión correcto", usuario=fila["usuario"], token=token
        ), 200

    @app.post("/logout")
    def logout() -> Any:
        session.clear()
        return jsonify(mensaje="Sesión cerrada"), 200

    @app.get("/tareas")
    def pagina_tareas() -> str:
        # Sirve el archivo HTML de bienvenida exigido por la consigna.
        return render_template("bienvenida.html")

    @app.get("/api/tareas")
    @requiere_login
    def listar_tareas() -> Any:
        filas = conectar_db().execute(
            "SELECT id, titulo, descripcion, completada, creada_en FROM tareas "
            "WHERE usuario_id = ? ORDER BY id DESC", (g.usuario_id,)
        ).fetchall()
        return jsonify(tareas=[dict(fila) for fila in filas])

    @app.post("/api/tareas")
    @requiere_login
    def crear_tarea() -> Any:
        datos = request.get_json(silent=True)
        if not isinstance(datos, dict) or not isinstance(datos.get("titulo"), str) or not datos["titulo"].strip():
            return jsonify(error="El campo 'titulo' es obligatorio"), 400
        descripcion = datos.get("descripcion", "")
        if not isinstance(descripcion, str):
            return jsonify(error="'descripcion' debe ser texto"), 400
        db = conectar_db()
        cursor = db.execute(
            "INSERT INTO tareas (usuario_id, titulo, descripcion) VALUES (?, ?, ?)",
            (g.usuario_id, datos["titulo"].strip(), descripcion),
        )
        db.commit()
        tarea = db.execute(
            "SELECT id, titulo, descripcion, completada, creada_en FROM tareas WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return jsonify(tarea=dict(tarea)), 201

    return app


app = crear_app()
# Gunicorn importa `servidor:app` y no ejecuta el bloque __main__; inicializar
# aquí garantiza que las tablas existan también en el entorno desplegado.
inicializar_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
