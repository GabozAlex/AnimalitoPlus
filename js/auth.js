document.addEventListener('DOMContentLoaded', () => {
  const regForm = document.getElementById('registerForm');
  if (regForm) {
    regForm.addEventListener('submit', async e => {
      e.preventDefault();
      const nombre = document.getElementById('regNombre').value.trim();
      const correo = document.getElementById('regUsuario').value.trim();
      const pass = document.getElementById('regPass').value;
      const pass2 = document.getElementById('regPass2').value;
      const telefono = document.getElementById('regTelefono').value.trim();
      let valid = true;
      document.querySelectorAll('.error-msg').forEach(el => el.classList.remove('show'));
      document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
      if (nombre.length < 3) { showError('regNombre', 'Nombre demasiado corto'); valid = false; }
      if (correo.length < 3 || !correo.includes('@')) { showError('regUsuario', 'Correo inválido'); valid = false; }
      if (pass.length < 6) { showError('regPass', 'Mínimo 6 caracteres'); valid = false; }
      if (pass !== pass2) { showError('regPass2', 'No coinciden'); valid = false; }
      if (telefono.length < 7) { showError('regTelefono', 'Teléfono inválido'); valid = false; }
      if (!valid) return;
      const res = await apiFetch('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ nombre, apellido: '', correo, clave: pass, telefono }),
      });
      if (!res.ok) {
        const err = await res.json();
        showError('regUsuario', err.detail || 'Error al registrar');
        return;
      }
      const data = await res.json();
      setToken(data.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(data.usuario));
      Swal.fire({ icon: 'success', title: '¡Cuenta creada!', text: 'Bienvenido a AnimalitoPlus', timer: 1500, showConfirmButton: false })
        .then(() => window.location.href = data.usuario.rol === 'admin' ? 'admin.html' : 'dashboard.html');
    });
  }

  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', async e => {
      e.preventDefault();
      const correo = document.getElementById('loginUsuario').value.trim();
      const pass = document.getElementById('loginPass').value;
      document.querySelectorAll('.error-msg').forEach(el => el.classList.remove('show'));
      document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
      if (!correo || !pass) { showError('loginUsuario', 'Completa todos los campos'); return; }
      const res = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ correo, clave: pass }),
      });
      if (!res.ok) { showError('loginUsuario', 'Correo o contraseña incorrectos'); return; }
      const data = await res.json();
      setToken(data.access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(data.usuario));
      Swal.fire({ icon: 'success', title: '¡Bienvenido!', timer: 1000, showConfirmButton: false })
        .then(() => window.location.href = data.usuario.rol === 'admin' ? 'admin.html' : 'dashboard.html');
    });
  }
});

function showError(fieldId, msg) {
  const input = document.getElementById(fieldId);
  if (input) input.classList.add('is-invalid');
  const err = document.getElementById(fieldId + 'Error');
  if (err) { err.textContent = msg; err.classList.add('show'); }
}
