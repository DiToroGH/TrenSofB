/**
 * Sistema de autenticación y gestión de sesiones
 */

class AuthManager {
  constructor() {
    this.token = localStorage.getItem('access_token');
    this.userType = localStorage.getItem('user_type');
    this.username = localStorage.getItem('username');
    /** Evita listeners duplicados al alternar login / pantalla principal. */
    this._logoutWired = false;
    this._loginFormWired = false;
    this.init();
  }

  init() {
    if (this.token) {
      this.showMainScreen();
    } else {
      this.showLoginScreen();
    }
  }

  showLoginScreen() {
    document.body.classList.remove('tren-modo-admin', 'tren-modo-user');
    document.getElementById('login-screen').style.display = 'flex';
    document.getElementById('main-screen').style.display = 'none';
    const msgEl = document.getElementById('msg');
    if (msgEl) {
      msgEl.textContent = '';
      msgEl.className = 'msg';
    }
    this.setupLoginForm();
  }

  showMainScreen() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('main-screen').style.display = 'block';
    this._aplicarClaseModoUsuario();
    this.setupMainScreen();
    this.updateUI();
  }

  _aplicarClaseModoUsuario() {
    document.body.classList.remove('tren-modo-admin', 'tren-modo-user');
    if (this.userType === 'admin') {
      document.body.classList.add('tren-modo-admin');
    } else {
      document.body.classList.add('tren-modo-user');
    }
  }

  setupLoginForm() {
    if (this._loginFormWired) return;
    this._loginFormWired = true;
    const form = document.getElementById('login-form');
    form.addEventListener('submit', (e) => this.handleLogin(e));
  }

  async handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('login-error');

    try {
      errorDiv.style.display = 'none';
      
      const response = await fetch('/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          password,
        }),
      });

      if (!response.ok) {
        throw new Error(window.trenI18n.t('invalidCreds'));
      }

      const data = await response.json();
      
      // Guardar token y datos de usuario
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user_type', data.user_type);
      localStorage.setItem('username', data.username);
      
      this.token = data.access_token;
      this.userType = data.user_type;
      this.username = data.username;
      
      this.showMainScreen();
      const msgEl = document.getElementById('msg');
      if (msgEl) {
        msgEl.textContent = '';
        msgEl.className = 'msg';
      }
      if (typeof window.__trenRecargarEstado === 'function') {
        void window.__trenRecargarEstado();
      }
      if (typeof window.__trenRefreshLineas === 'function') {
        void window.__trenRefreshLineas(false);
      }
    } catch (error) {
      errorDiv.textContent = error.message;
      errorDiv.style.display = 'block';
    }
  }

  setupMainScreen() {
    this.refreshUserDisplay();
    
    if (!this._logoutWired) {
      this._logoutWired = true;
      document.getElementById('btn-logout').addEventListener('click', () => {
        this.logout();
      });
    }

    // Mostrar/ocultar botones según el tipo de usuario
    const genBtn = document.getElementById('btn-generar');
    const cerrarBtn = document.getElementById('btn-cerrar');
    const gestionBtn = document.getElementById('btn-gestion');
    const regPasadoBtn = document.getElementById('btn-registro-pasado');
    const cardDisp = document.getElementById('card-disponibilidad');
    const gridHoy = document.getElementById('grid-hoy-asignaciones');
    const mensajeTa = document.getElementById('mensaje-turno');
    const mensajeHint = document.getElementById('mensaje-turno-hint');
    const btnGuardarMsg = document.getElementById('btn-guardar-mensaje');
    const btnRegenMsg = document.getElementById('btn-regenerar-mensaje');
    const selSegundoAcomp = document.getElementById('sel-segundo-acomp');
    if (this.userType === 'admin') {
      genBtn.style.display = 'block';
      cerrarBtn.style.display = 'block';
      gestionBtn.style.display = 'block';
      const lineasBtn = document.getElementById('btn-gestion-lineas');
      if (lineasBtn) lineasBtn.style.display = 'inline-block';
      if (regPasadoBtn) regPasadoBtn.style.display = 'block';
      if (cardDisp) cardDisp.style.display = 'none';
      if (gridHoy) gridHoy.classList.add('grid-2--solo-asignaciones');
      if (mensajeTa) mensajeTa.readOnly = false;
      if (mensajeHint) mensajeHint.style.display = '';
      if (btnGuardarMsg) btnGuardarMsg.style.display = '';
      if (btnRegenMsg) btnRegenMsg.style.display = '';
      if (selSegundoAcomp) selSegundoAcomp.disabled = false;
    } else {
      genBtn.style.display = 'none';
      cerrarBtn.style.display = 'none';
      gestionBtn.style.display = 'none';
      const lineasBtn = document.getElementById('btn-gestion-lineas');
      if (lineasBtn) lineasBtn.style.display = 'none';
      if (regPasadoBtn) regPasadoBtn.style.display = 'none';
      if (cardDisp) cardDisp.style.display = 'none';
      if (gridHoy) gridHoy.classList.add('grid-2--solo-asignaciones');
      if (mensajeTa) mensajeTa.readOnly = true;
      if (mensajeHint) mensajeHint.style.display = 'none';
      if (btnGuardarMsg) btnGuardarMsg.style.display = 'none';
      if (btnRegenMsg) btnRegenMsg.style.display = 'none';
      if (selSegundoAcomp) selSegundoAcomp.disabled = true;
    }
  }

  updateUI() {
    // Actualizar cualquier elemento que dependa del tipo de usuario
  }

  refreshUserDisplay() {
    if (!this.token) return;
    const role =
      this.userType === "admin"
        ? window.trenI18n.t("roleAdmin")
        : window.trenI18n.t("roleUser");
    const el = document.getElementById("user-display");
    if (el) {
      el.textContent = window.trenI18n.t("userDisplay", {
        username: this.username,
        role: role,
      });
    }
  }

  async logout() {
    try {
      await fetch('/logout', { method: 'POST' });
    } catch (error) {
      console.error('Error en logout:', error);
    }
    
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_type');
    localStorage.removeItem('username');
    
    this.token = null;
    this.userType = null;
    this.username = null;
    
    this.showLoginScreen();
  }

  getAuthHeader() {
    if (!this.token) {
      throw new Error('No hay sesión activa');
    }
    return {
      'Authorization': `Bearer ${this.token}`,
    };
  }

  isAdmin() {
    return this.userType === 'admin';
  }

  isAuthenticated() {
    return !!this.token;
  }
}

// Instancia global de AuthManager
const auth = new AuthManager();

window.addEventListener('tren-lang-change', () => {
  if (auth && auth.isAuthenticated()) {
    auth.refreshUserDisplay();
  }
});
