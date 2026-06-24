/* ===== NAVEGACIÓN ACTIVA ===== */
document.addEventListener('DOMContentLoaded', () => {
  const page = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a, .bottom-nav a').forEach(link => {
    const href = link.getAttribute('href');
    if (href === page) link.classList.add('active');
  });
});

/* ===== PROTECCIÓN RUTAS ===== */
function requireAuth() {
  const user = JSON.parse(localStorage.getItem('animalito_user'));
  if (!user) {
    window.location.href = 'login.html';
    return null;
  }
  return user;
}

/* ===== USUARIO ACTUAL ===== */
function getCurrentUser() {
  return JSON.parse(localStorage.getItem('animalito_user'));
}

/* ===== SALDO ===== */
function updateBalanceDisplay() {
  const el = document.getElementById('balanceDisplay');
  const user = getCurrentUser();
  if (el && user) {
    el.textContent = user.balance.toFixed(2);
  }
}

/* ===== ANIMALES (38) ===== */
const ANIMALES = [
  { id: 1,  nombre: 'Ratón',     icono: 'fa-rat' },
  { id: 2,  nombre: 'Gallina',   icono: 'fa-kiwi-bird' },
  { id: 3,  nombre: 'Gato',      icono: 'fa-cat' },
  { id: 4,  nombre: 'Perro',     icono: 'fa-dog' },
  { id: 5,  nombre: 'Serpiente', icono: 'fa-snake' },
  { id: 6,  nombre: 'Tigre',     icono: 'fa-paw' },
  { id: 7,  nombre: 'Dragón',    icono: 'fa-dragon' },
  { id: 8,  nombre: 'Conejo',    icono: 'fa-rabbit' },
  { id: 9,  nombre: 'Mono',      icono: 'fa-monkey' },
  { id: 10, nombre: 'Caballo',   icono: 'fa-horse' },
  { id: 11, nombre: 'Oveja',     icono: 'fa-sheep' },
  { id: 12, nombre: 'Vaca',      icono: 'fa-cow' },
  { id: 13, nombre: 'Elefante',  icono: 'fa-elephant' },
  { id: 14, nombre: 'Mariposa',  icono: 'fa-butterfly' },
  { id: 15, nombre: 'Gallo',     icono: 'fa-kiwi-bird' },
  { id: 16, nombre: 'León',      icono: 'fa-paw' },
  { id: 17, nombre: 'Pavo',      icono: 'fa-paw' },
  { id: 18, nombre: 'Búfalo',    icono: 'fa-paw' },
  { id: 19, nombre: 'Zorro',     icono: 'fa-paw' },
  { id: 20, nombre: 'Loro',      icono: 'fa-dove' },
  { id: 21, nombre: 'Cocodrilo', icono: 'fa-lizard' },
  { id: 22, nombre: 'Tortuga',   icono: 'fa-turtle' },
  { id: 23, nombre: 'Cebra',     icono: 'fa-paw' },
  { id: 24, nombre: 'Oso',       icono: 'fa-paw' },
  { id: 25, nombre: 'Águila',    icono: 'fa-feather' },
  { id: 26, nombre: 'Lobo',      icono: 'fa-paw' },
  { id: 27, nombre: 'Ballena',   icono: 'fa-fish' },
  { id: 28, nombre: 'Delfín',    icono: 'fa-fish' },
  { id: 29, nombre: 'Cangrejo',  icono: 'fa-crab' },
  { id: 30, nombre: 'Camello',   icono: 'fa-horse' },
  { id: 31, nombre: 'Murciélago',icono: 'fa-paw' },
  { id: 32, nombre: 'Rana',      icono: 'fa-frog' },
  { id: 33, nombre: 'Abeja',     icono: 'fa-bee' },
  { id: 34, nombre: 'Hormiga',   icono: 'fa-ant' },
  { id: 35, nombre: 'Pato',      icono: 'fa-duck' },
  { id: 36, nombre: 'Burro',     icono: 'fa-horse' },
  { id: 37, nombre: 'Águila 2',  icono: 'fa-feather' },
  { id: 38, nombre: 'León 2',    icono: 'fa-paw' },
];

/* ===== CERRAR SESIÓN ===== */
function logout() {
  Swal.fire({
    title: '¿Cerrar sesión?',
    icon: 'question',
    showCancelButton: true,
    confirmButtonText: 'Sí, salir',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#0ea5e9',
  }).then(res => {
    if (res.isConfirmed) {
      localStorage.removeItem('animalito_user');
      window.location.href = 'index.html';
    }
  });
}

/* ===== MODAL RECARGA / RETIRO ===== */
function showRechargeModal() {
  Swal.fire({
    title: 'Recargar saldo',
    html: `
      <div class="mb-3">
        <label class="form-label">Monto a recargar (Bs)</label>
        <input type="number" id="swal-recharge" class="form-control" min="1" step="0.5" placeholder="Ej: 50">
      </div>
    `,
    showCancelButton: true,
    confirmButtonText: 'Recargar',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#22c55e',
    preConfirm: () => {
      const val = parseFloat(document.getElementById('swal-recharge').value);
      if (!val || val <= 0) {
        Swal.showValidationMessage('Ingresa un monto válido');
        return false;
      }
      return val;
    }
  }).then(res => {
    if (res.isConfirmed) {
      const user = getCurrentUser();
      user.balance += res.value;
      localStorage.setItem('animalito_user', JSON.stringify(user));
      updateBalanceDisplay();
      Swal.fire('¡Listo!', `Se recargaron Bs ${res.value.toFixed(2)}`, 'success');
    }
  });
}

function showWithdrawModal() {
  Swal.fire({
    title: 'Retirar saldo',
    html: `
      <div class="mb-3">
        <label class="form-label">Monto a retirar (Bs)</label>
        <input type="number" id="swal-withdraw" class="form-control" min="1" step="0.5" placeholder="Ej: 20">
      </div>
    `,
    showCancelButton: true,
    confirmButtonText: 'Retirar',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#ef4444',
    preConfirm: () => {
      const val = parseFloat(document.getElementById('swal-withdraw').value);
      if (!val || val <= 0) {
        Swal.showValidationMessage('Ingresa un monto válido');
        return false;
      }
      return val;
    }
  }).then(res => {
    if (res.isConfirmed) {
      const user = getCurrentUser();
      if (res.value > user.balance) {
        Swal.fire('Saldo insuficiente', 'No tienes suficiente saldo para retirar ese monto', 'error');
        return;
      }
      user.balance -= res.value;
      localStorage.setItem('animalito_user', JSON.stringify(user));
      updateBalanceDisplay();
      Swal.fire('¡Listo!', `Solicitaste retiro de Bs ${res.value.toFixed(2)}`, 'success');
    }
  });
}
