/* ===== REGISTRO ===== */
document.addEventListener('DOMContentLoaded', () => {
  const regForm = document.getElementById('registerForm');
  if (regForm) {
    regForm.addEventListener('submit', e => {
      e.preventDefault();

      const nombre = document.getElementById('regNombre').value.trim();
      const usuario = document.getElementById('regUsuario').value.trim();
      const pass = document.getElementById('regPass').value;
      const pass2 = document.getElementById('regPass2').value;
      const telefono = document.getElementById('regTelefono').value.trim();

      let valid = true;

      // Reset errors
      document.querySelectorAll('.error-msg').forEach(el => el.classList.remove('show'));
      document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

      if (nombre.length < 3) {
        showError('regNombre', 'Nombre demasiado corto');
        valid = false;
      }
      if (usuario.length < 3) {
        showError('regUsuario', 'Usuario debe tener al menos 3 caracteres');
        valid = false;
      }
      if (pass.length < 6) {
        showError('regPass', 'La contraseña debe tener al menos 6 caracteres');
        valid = false;
      }
      if (pass !== pass2) {
        showError('regPass2', 'Las contraseñas no coinciden');
        valid = false;
      }
      if (telefono.length < 7) {
        showError('regTelefono', 'Teléfono inválido');
        valid = false;
      }

      if (!valid) return;

      // Check if user exists
      const users = JSON.parse(localStorage.getItem('animalito_users') || '[]');
      if (users.find(u => u.usuario === usuario)) {
        showError('regUsuario', 'Este usuario ya existe');
        return;
      }

      // Create user
      const newUser = {
        nombre,
        usuario,
        password: pass,
        telefono,
        balance: 0,
        createdAt: new Date().toISOString(),
      };
      users.push(newUser);
      localStorage.setItem('animalito_users', JSON.stringify(users));

      // Auto-login
      localStorage.setItem('animalito_user', JSON.stringify({
        nombre: newUser.nombre,
        usuario: newUser.usuario,
        balance: newUser.balance,
      }));

      Swal.fire({
        icon: 'success',
        title: '¡Cuenta creada!',
        text: 'Bienvenido a AnimalitoPlus',
        timer: 1500,
        showConfirmButton: false,
      }).then(() => {
        window.location.href = 'dashboard.html';
      });
    });
  }

  /* ===== LOGIN ===== */
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', e => {
      e.preventDefault();

      const usuario = document.getElementById('loginUsuario').value.trim();
      const pass = document.getElementById('loginPass').value;

      document.querySelectorAll('.error-msg').forEach(el => el.classList.remove('show'));
      document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

      if (!usuario || !pass) {
        showError('loginUsuario', 'Completa todos los campos');
        return;
      }

      const users = JSON.parse(localStorage.getItem('animalito_users') || '[]');
      const user = users.find(u => u.usuario === usuario && u.password === pass);

      if (!user) {
        showError('loginUsuario', 'Usuario o contraseña incorrectos');
        return;
      }

      localStorage.setItem('animalito_user', JSON.stringify({
        nombre: user.nombre,
        usuario: user.usuario,
        balance: user.balance,
      }));

      Swal.fire({
        icon: 'success',
        title: '¡Bienvenido!',
        timer: 1000,
        showConfirmButton: false,
      }).then(() => {
        window.location.href = 'dashboard.html';
      });
    });
  }
});

function showError(fieldId, msg) {
  const input = document.getElementById(fieldId);
  if (input) input.classList.add('is-invalid');
  const err = document.getElementById(fieldId + 'Error');
  if (err) {
    err.textContent = msg;
    err.classList.add('show');
  }
}
