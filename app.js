(() => {
  const apiBase = (window.API_BASE_URL || "").trim().replace(/\/$/, "");
  const tokenKey = "pfo2_token";
  const userKey = "pfo2_usuario";
  const accessPanel = document.querySelector("#acceso");
  const taskPanel = document.querySelector("#area-tareas");
  const message = document.querySelector("#mensaje");
  const taskList = document.querySelector("#lista-tareas");
  const status = document.querySelector("#estado-api");

  if (!apiBase) {
    status.textContent = "Falta configurar la URL de la API en api-config.js. Publica primero el backend y copia aquí su URL.";
  }

  function showMessage(text, isError = false) {
    message.textContent = text;
    message.classList.toggle("error", isError);
  }

  async function api(path, options = {}, authenticated = false) {
    if (!apiBase) throw new Error("Configura la URL de la API en api-config.js.");
    const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
    if (authenticated) {
      const token = localStorage.getItem(tokenKey);
      if (!token) throw new Error("Inicia sesión para continuar.");
      headers.Authorization = `Bearer ${token}`;
    }
    let response;
    try {
      response = await fetch(`${apiBase}${path}`, { ...options, headers });
    } catch (_error) {
      throw new Error("No se pudo conectar con la API. Verifica que esté desplegada y configurada.");
    }
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `Error HTTP ${response.status}`);
    return result;
  }

  function formData(form) {
    return Object.fromEntries(new FormData(form).entries());
  }

  function showLoggedOut() {
    localStorage.removeItem(tokenKey);
    localStorage.removeItem(userKey);
    accessPanel.hidden = false;
    taskPanel.hidden = true;
    taskList.replaceChildren();
  }

  async function loadTasks() {
    const result = await api("/api/tareas", {}, true);
    taskList.replaceChildren();
    if (!result.tareas.length) {
      const empty = document.createElement("li");
      empty.textContent = "Todavía no tienes tareas.";
      taskList.append(empty);
      return;
    }
    for (const task of result.tareas) {
      const item = document.createElement("li");
      const title = document.createElement("strong");
      title.textContent = task.titulo;
      item.append(title);
      if (task.descripcion) {
        const description = document.createElement("p");
        description.textContent = task.descripcion;
        item.append(description);
      }
      taskList.append(item);
    }
  }

  async function startSession(credentials) {
    const result = await api("/login", { method: "POST", body: JSON.stringify(credentials) });
    localStorage.setItem(tokenKey, result.token);
    localStorage.setItem(userKey, result.usuario);
    document.querySelector("#nombre-usuario").textContent = result.usuario;
    accessPanel.hidden = true;
    taskPanel.hidden = false;
    await loadTasks();
  }

  document.querySelector("#form-registro").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const datos = formData(event.currentTarget);
      await api("/registro", { method: "POST", body: JSON.stringify(datos) });
      await startSession(datos);
      showMessage("Cuenta creada e inicio de sesión correcto.");
    } catch (error) { showMessage(error.message, true); }
  });

  document.querySelector("#form-login").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await startSession(formData(event.currentTarget));
      showMessage("Sesión iniciada.");
    } catch (error) { showMessage(error.message, true); }
  });

  document.querySelector("#form-tarea").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api("/api/tareas", { method: "POST", body: JSON.stringify(formData(event.currentTarget)) }, true);
      event.currentTarget.reset();
      await loadTasks();
      showMessage("Tarea agregada.");
    } catch (error) { showMessage(error.message, true); }
  });

  document.querySelector("#boton-salir").addEventListener("click", () => {
    showLoggedOut();
    showMessage("Sesión cerrada en este navegador.");
  });

  const savedToken = localStorage.getItem(tokenKey);
  const savedUser = localStorage.getItem(userKey);
  if (savedToken && savedUser) {
    document.querySelector("#nombre-usuario").textContent = savedUser;
    accessPanel.hidden = true;
    taskPanel.hidden = false;
    loadTasks().catch((error) => { showLoggedOut(); showMessage(error.message, true); });
  }
})();
