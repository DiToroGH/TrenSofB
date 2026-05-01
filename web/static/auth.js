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
    document.getElementById('login-screen').style.display = 'flex';
    document.getElementById('main-screen').style.display = 'none';
    this.setupLoginForm();
  }

  showMainScreen() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('main-screen').style.display = 'block';
    this.setupMainScreen();
    this.updateUI();
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
        throw new Error('Credenciales inválidas');
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
    } catch (error) {
      errorDiv.textContent = error.message;
      errorDiv.style.display = 'block';
    }
  }

  setupMainScreen() {
    // Mostrar información del usuario
    const userType = this.userType === 'admin' ? 'Administrador' : 'Usuario';
    document.getElementById('user-display').textContent = 
      `${this.username} (${userType})`;
    
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
    
    if (this.userType === 'admin') {
      genBtn.style.display = 'block';
      cerrarBtn.style.display = 'block';
      gestionBtn.style.display = 'block';
    } else {
      genBtn.style.display = 'none';
      cerrarBtn.style.display = 'none';
      gestionBtn.style.display = 'none';
    }
  }

  updateUI() {
    // Actualizar cualquier elemento que dependa del tipo de usuario
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
