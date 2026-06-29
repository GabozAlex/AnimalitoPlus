const API_BASE = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname === '0.0.0.0')
  ? `http://${window.location.hostname}:8000`
  : 'https://animalitoplus-api.onrender.com';

const TOKEN_KEY = 'animalito_token';
const USER_KEY = 'animalito_user';

const LOTTERY_IMAGE_FOLDER = {
  lotto_activo: 'lotto_activo',
  la_granjita: 'la_granjita',
  selvaplus: 'selvaplus',
};
const LOTTERY_LOGO = {
  lotto_activo: 'img/loterias/lotto_activo.webp',
  la_granjita: 'img/loterias/la_granjita.webp',
  selvaplus: 'img/loterias/selvaplus.webp',
};
function animalImg(loteria, animalId) {
  const folder = LOTTERY_IMAGE_FOLDER[loteria] || 'lotto_activo';
  const a = ANIMALES.find(x => String(x.id) === String(animalId));
  if (!a) return '';
  return `img/animales/${folder}/${a.nombre.charAt(0) + a.nombre.slice(1).toLowerCase()}.webp`;
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function getUser() {
  const data = localStorage.getItem(USER_KEY);
  return data ? JSON.parse(data) : null;
}

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function requireAuth() {
  const token = getToken();
  if (!token) {
    window.location.href = 'login.html';
    return null;
  }
  return token;
}

function getCurrentUser() {
  const data = localStorage.getItem(USER_KEY);
  return data ? JSON.parse(data) : null;
}

function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return fetch(`${API_BASE}${path}`, { ...options, headers });
}

async function updateBalanceDisplay() {
  const navEl = document.getElementById('navBalance');
  try {
    const res = await apiFetch('/api/auth/balance');
    if (res.ok) {
      const data = await res.json();
      if (navEl) navEl.textContent = data.saldo.toFixed(2);
      if (window.Alpine && Alpine.store('app')) Alpine.store('app').balance = data.saldo;
    }
  } catch (e) { console.error('updateBalanceDisplay:', e); }
}

// ===== NOTIFICACIONES =====
let notifInterval = null;

async function cargarContadorNotis() {
  try {
    const res = await apiFetch('/api/notificaciones/no-leidas');
    if (!res.ok) return;
    const { count } = await res.json();
    document.querySelectorAll('.notif-badge').forEach(el => {
      el.textContent = count;
      el.style.display = count > 0 ? 'flex' : 'none';
    });
  } catch (e) { console.error(e); }
}

async function mostrarNotificaciones() {
  const res = await apiFetch('/api/notificaciones');
  if (!res.ok) return;
  const notis = await res.json();
  const icons = { ganada: '🎉', perdida: '😢', premio: '💰', sistema: '🔔', info: '📢' };
  Swal.fire({
    title: 'Notificaciones',
    html: notis.length === 0
      ? '<div class="text-muted py-4">No hay notificaciones</div>'
      : '<div style="max-height:400px;overflow-y:auto;text-align:left;">' +
        notis.map(n => `
          <div class="notif-item ${n.leida ? '' : 'fw-bold'}" style="padding:8px 0;border-bottom:1px solid #eee;cursor:pointer;"
               onclick="${n.leida ? '' : `marcarLeida(${n.id});this.classList.remove('fw-bold')`}">
            <div style="font-size:13px;">${icons[n.tipo] || '🔔'} ${n.titulo}</div>
            <div style="font-size:12px;color:#64748b;">${n.contenido || ''}</div>
            <small style="font-size:11px;color:#94a3b8;">${new Date(n.created_at).toLocaleString()}</small>
          </div>
        `).join('') + '</div>',
    showCancelButton: notis.some(n => !n.leida),
    cancelButtonText: 'Marcar todas leídas',
    confirmButtonText: 'Cerrar',
    confirmButtonColor: '#0ea5e9',
    didOpen: () => { cargarContadorNotis(); },
  }).then(r => {
    if (r.isDismissed && notis.some(n => !n.leida)) {
      apiFetch('/api/notificaciones/leer-todas', { method: 'PUT' }).then(() => cargarContadorNotis());
    }
  });
}

async function marcarLeida(id) {
  await apiFetch(`/api/notificaciones/${id}/leer`, { method: 'PUT' });
  cargarContadorNotis();
}

function iniciarPollNotis() {
  cargarContadorNotis();
  if (notifInterval) clearInterval(notifInterval);
  notifInterval = setInterval(async () => {
    try {
      const res = await apiFetch('/api/notificaciones/no-leidas');
      if (!res.ok) return;
      const { count } = await res.json();
      const prevCount = parseInt(localStorage.getItem('notifCount') || '0');
      document.querySelectorAll('.notif-badge').forEach(el => {
        el.textContent = count;
        el.style.display = count > 0 ? 'flex' : 'none';
      });
      if (count > 0 && prevCount === 0) {
        mostrarNotificaciones();
      }
      localStorage.setItem('notifCount', count);
    } catch (e) { console.error(e); }
  }, 30000);
}

async function renderResults(fecha, loteria) {
  const container = document.getElementById('resultsBody');
  if (!container) return;
  let params = fecha ? `?fecha=${fecha}` : '';
  if (loteria) params += (params ? '&' : '?') + `loteria=${encodeURIComponent(loteria)}`;

  container.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4">🔍 Consultando resultados...</td></tr>';

  let slowTimer = setTimeout(() => {
    container.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4">⏳ Obteniendo datos de las loterías...</td></tr>';
  }, 3000);

  const res = await apiFetch(`/api/resultados${params}`);
  clearTimeout(slowTimer);

  if (!res.ok) {
    container.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4">⚠️ Error al conectar con los sitios</td></tr>';
    return;
  }
  const data = await res.json();
  if (data.count === 0) {
    container.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4">❌ No hay resultados disponibles hoy</td></tr>';
    return;
  }
  container.innerHTML = '<tr><td colspan="3" class="text-center text-success py-2"><small>✅ Resultados actualizados</small></td></tr>' +
    data.resultados.map(r => {
      const animal = ANIMALES.find(a => String(a.id) === r.animal_id);
      const loteriaKey = r.loteria || loteria;
      const imgSrc = animal ? animalImg(loteriaKey, r.animal_id) : '';
      return `
      <tr>
        <td>${r.horario}</td>
        <td><div class="animal-cell">${imgSrc ? `<img src="${imgSrc}" alt="${animal?.nombre || ''}" loading="lazy">` : `<i class="fas ${animal ? animal.icono : 'fa-paw'} text-primary"></i>`} ${animal ? animal.nombre : r.animal_id}</div></td>
        <td class="num-cell">${r.numero}</td>
      </tr>
    `;
    }).join('');
}

let ANIMALES = [
  { id: '0',  numero: '0',  nombre: 'DELFIN',   icono: 'fa-fish' },
  { id: '00', numero: '00', nombre: 'BALLENA',  icono: 'fa-fish' },
  { id: 1,  numero: '01', nombre: 'CARNERO',  icono: 'fa-horse-head' },
  { id: 2,  numero: '02', nombre: 'TORO',     icono: 'fa-cow' },
  { id: 3,  numero: '03', nombre: 'CIEMPIES', icono: 'fa-bug' },
  { id: 4,  numero: '04', nombre: 'ALACRAN',  icono: 'fa-bug' },
  { id: 5,  numero: '05', nombre: 'LEON',     icono: 'fa-paw' },
  { id: 6,  numero: '06', nombre: 'RANA',     icono: 'fa-dragon' },
  { id: 7,  numero: '07', nombre: 'PERICO',   icono: 'fa-dove' },
  { id: 8,  numero: '08', nombre: 'RATON',    icono: 'fa-otter' },
  { id: 9,  numero: '09', nombre: 'AGUILA',   icono: 'fa-feather' },
  { id: 10, numero: '10', nombre: 'TIGRE',    icono: 'fa-paw' },
  { id: 11, numero: '11', nombre: 'GATO',     icono: 'fa-cat' },
  { id: 12, numero: '12', nombre: 'CABALLO',  icono: 'fa-horse' },
  { id: 13, numero: '13', nombre: 'MONO',     icono: 'fa-paw' },
  { id: 14, numero: '14', nombre: 'PALOMA',   icono: 'fa-dove' },
  { id: 15, numero: '15', nombre: 'ZORRO',    icono: 'fa-paw' },
  { id: 16, numero: '16', nombre: 'OSO',      icono: 'fa-paw' },
  { id: 17, numero: '17', nombre: 'PAVO',     icono: 'fa-kiwi-bird' },
  { id: 18, numero: '18', nombre: 'BURRO',    icono: 'fa-horse' },
  { id: 19, numero: '19', nombre: 'CHIVO',    icono: 'fa-paw' },
  { id: 20, numero: '20', nombre: 'COCHINO',  icono: 'fa-piggy-bank' },
  { id: 21, numero: '21', nombre: 'GALLO',    icono: 'fa-kiwi-bird' },
  { id: 22, numero: '22', nombre: 'CAMELLO',  icono: 'fa-horse' },
  { id: 23, numero: '23', nombre: 'CEBRA',    icono: 'fa-paw' },
  { id: 24, numero: '24', nombre: 'IGUANA',   icono: 'fa-lizard' },
  { id: 25, numero: '25', nombre: 'GALLINA',  icono: 'fa-kiwi-bird' },
  { id: 26, numero: '26', nombre: 'VACA',     icono: 'fa-cow' },
  { id: 27, numero: '27', nombre: 'PERRO',    icono: 'fa-dog' },
  { id: 28, numero: '28', nombre: 'ZAMURO',   icono: 'fa-feather' },
  { id: 29, numero: '29', nombre: 'ELEFANTE', icono: 'fa-hippo' },
  { id: 30, numero: '30', nombre: 'CAIMAN',   icono: 'fa-lizard' },
  { id: 31, numero: '31', nombre: 'LAPA',     icono: 'fa-paw' },
  { id: 32, numero: '32', nombre: 'ARDILLA',  icono: 'fa-paw' },
  { id: 33, numero: '33', nombre: 'PESCADO',  icono: 'fa-fish' },
  { id: 34, numero: '34', nombre: 'VENADO',   icono: 'fa-paw' },
  { id: 35, numero: '35', nombre: 'JIRAFA',   icono: 'fa-paw' },
  { id: 36, numero: '36', nombre: 'CULEBRA',  icono: 'fa-worm' },
];

async function loadAnimalesFromAPI() {
  try {
    const url = `${API_BASE}/api/animales`;
    const res = await fetch(url);
    if (!res.ok) return;
    const data = await res.json();
    if (data && data.length > 0) {
      ANIMALES.length = 0;
      ANIMALES.push(...data);
      window.dispatchEvent(new CustomEvent('animalesLoaded'));
    }
  } catch(e) { console.warn('No se pudieron cargar animales desde API, usando hardcode'); }
}

// Cargar animales desde API al iniciar (no bloquea)
loadAnimalesFromAPI();

const BANCOS = [
  { codigo: '0001', nombre: 'Banco Central de Venezuela (BCV)' },
  { codigo: '0102', nombre: 'Banco de Venezuela' },
  { codigo: '0104', nombre: 'Banco Venezolano de Crédito' },
  { codigo: '0105', nombre: 'Banco Mercantil' },
  { codigo: '0108', nombre: 'Banco Provincial' },
  { codigo: '0114', nombre: 'Bancaribe' },
  { codigo: '0115', nombre: 'Banco Exterior' },
  { codigo: '0116', nombre: 'Banco Occidental de Descuento (BOD)' },
  { codigo: '0128', nombre: 'Banco Caroní' },
  { codigo: '0134', nombre: 'Banesco' },
  { codigo: '0137', nombre: 'Banco Sofitasa' },
  { codigo: '0138', nombre: 'Banco Plaza' },
  { codigo: '0146', nombre: 'Bangente' },
  { codigo: '0149', nombre: 'Banco del Pueblo Soberano' },
  { codigo: '0151', nombre: 'BFC Banco Fondo Común' },
  { codigo: '0156', nombre: '100% Banco' },
  { codigo: '0157', nombre: 'Del Sur Banco Universal' },
  { codigo: '0163', nombre: 'Banco del Tesoro' },
  { codigo: '0166', nombre: 'Banco Agrícola de Venezuela' },
  { codigo: '0168', nombre: 'Bancrecer' },
  { codigo: '0169', nombre: 'Mi Banco' },
  { codigo: '0171', nombre: 'Banco Activo' },
  { codigo: '0172', nombre: 'Bancamiga' },
  { codigo: '0173', nombre: 'Banco Internacional de Desarrollo' },
  { codigo: '0174', nombre: 'Banplus' },
  { codigo: '0175', nombre: 'Banco Bicentenario' },
  { codigo: '0177', nombre: 'Banco de la Fuerza Armada Nacional Bolivariana (BANFANB)' },
  { codigo: '0190', nombre: 'Citibank' },
  { codigo: '0191', nombre: 'Banco Nacional de Crédito' },
  { codigo: '0601', nombre: 'Instituto Municipal de Crédito Popular' },
];

const CASA = {
  nombre: 'Gabriel Alejandro Rosas Rosas',
  banco: 'Banco Mercantil',
  banco_codigo: '0105',
  cedula: '27650586',
  telefono: '4123656230',
};

const MOVIL_PREFIXES = ['412', '414', '416', '424', '426'];

function normalizePhone(raw) {
  const digits = raw.replace(/\D/g, '');
  if (digits.startsWith('58') && digits.length > 10) return digits.slice(2);
  if (digits.startsWith('0') && digits.length > 10) return digits.slice(1);
  return digits;
}

function validarTelefonoVE(raw) {
  const num = normalizePhone(raw);
  if (num.length !== 10) return { valido: false, msg: 'Debe tener 10 dígitos (ej: 04121234567)' };
  const prefix = num.slice(0, 3);
  if (MOVIL_PREFIXES.includes(prefix)) return { valido: true, msg: '', num };
  if (prefix.startsWith('2')) return { valido: true, msg: '', num };
  return { valido: false, msg: 'Prefijo telefónico inválido para Venezuela' };
}

function validarCorreo(email) {
  return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email);
}

function formatPhone(num) {
  if (!num || num.length < 10) return num || '';
  return '0' + num.slice(0, 3) + '-' + num.slice(3);
}

function normalizeCedula(raw) {
  let s = raw.replace(/[\s.-]+/g, '').toUpperCase();
  if (/^[VE]\d+$/.test(s)) return s;
  if (/^\d+$/.test(s)) return 'V' + s;
  return raw.trim();
}

function validarCedulaVE(raw) {
  const s = normalizeCedula(raw);
  if (/^[VE]\d{1,8}$/.test(s)) return { valido: true, msg: '', cedula: s };
  return { valido: false, msg: 'Formato: V-12345678 (V o E, hasta 8 dígitos)' };
}

function formatCedula(ced) {
  if (!ced) return '';
  const letra = ced.charAt(0);
  const nums = ced.slice(1).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return letra + '-' + nums;
}

async function logout() {
  Swal.fire({
    title: '¿Cerrar sesión?',
    icon: 'question',
    showCancelButton: true,
    confirmButtonText: 'Sí, salir',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#0ea5e9',
  }).then(res => {
    if (res.isConfirmed) {
      clearAuth();
      window.location.href = 'index.html';
    }
  });
}

async function showRechargeModal() {
  const token = getToken();
  if (!token) return;

  const res = await apiFetch('/api/pagos/config/casa');
  const casa = res.ok ? await res.json() : CASA;

  const hoy = new Date().toISOString().split('T')[0];

  Swal.fire({
    title: 'Recargar saldo',
    html: `
      <div style="text-align:left;font-size:13px;background:#f0fdf4;padding:10px;border-radius:8px;margin-bottom:12px;border:1px solid #bbf7d0;">
        <div class="mb-1 fw-bold text-success"><i class="fas fa-university me-1"></i> Depósito a:</div>
        <div class="mb-1"><strong>Banco:</strong> ${casa.banco} (${casa.banco_codigo})</div>
        <div class="mb-1"><strong>Titular:</strong> ${casa.nombre}</div>
        <div class="mb-1"><strong>Cédula:</strong> ${casa.cedula}</div>
        <div class="mb-1"><strong>Teléfono:</strong> ${formatPhone(casa.telefono)}</div>
      </div>
      <div class="alert alert-info py-1 px-2 mb-2" style="font-size:12px;border-radius:6px;">
        <i class="fas fa-clock me-1"></i> Si el pago es de otro banco, la recarga puede tardar unos minutos. No te preocupes.
      </div>
      <div class="mb-2">
        <label class="form-label">Monto a recargar (Bs) <span class="text-danger">*</span></label>
        <input type="number" id="swal-monto" class="form-control" min="1" step="0.5" placeholder="Ej: 50">
        <div class="quick-amounts" style="display:flex;gap:4px;flex-wrap:wrap;margin-top:6px;">
          <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.getElementById('swal-monto').value=10">Bs 10</button>
          <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.getElementById('swal-monto').value=20">Bs 20</button>
          <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.getElementById('swal-monto').value=50">Bs 50</button>
          <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.getElementById('swal-monto').value=100">Bs 100</button>
          <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.getElementById('swal-monto').value=200">Bs 200</button>
          <button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.getElementById('swal-monto').value=500">Bs 500</button>
        </div>
      </div>
      <div class="mb-2">
        <label class="form-label">Número de referencia <span class="text-danger">*</span></label>
        <input type="text" id="swal-ref" class="form-control" placeholder="Ej: 123456 (4, 6 o 12 dígitos)">
      </div>
      <div class="mb-2">
        <label class="form-label">Tipo de pago <span class="text-danger">*</span></label>
        <select id="swal-tipo" class="form-select">
          <option value="MOVIL_PAY">Pago Móvil</option>
          <option value="TRANSFER">Transferencia</option>
        </select>
      </div>
      <div class="mb-2">
        <label class="form-label">Fecha del pago</label>
        <input type="date" id="swal-fecha" class="form-control" value="${hoy}">
      </div>
    `,
    showCancelButton: true,
    confirmButtonText: 'Solicitar recarga',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#22c55e',
    preConfirm: () => {
      const monto = parseFloat(document.getElementById('swal-monto').value);
      if (!monto || monto <= 0) { Swal.showValidationMessage('Ingresa un monto válido'); return false; }
      if (monto < 10) { Swal.showValidationMessage('El monto mínimo es Bs 10'); return false; }
      if (monto > 10000) { Swal.showValidationMessage('El monto máximo es Bs 10.000'); return false; }
      const ref = document.getElementById('swal-ref').value.trim();
      if (!ref) { Swal.showValidationMessage('Ingresa el número de referencia'); return false; }
      if (!/^\d{4}$|^\d{6}$|^\d{12}$/.test(ref)) {
        Swal.showValidationMessage('La referencia debe tener 4, 6 o 12 dígitos numéricos'); return false;
      }
      const tipo = document.getElementById('swal-tipo').value;
      const fecha = document.getElementById('swal-fecha').value;
      return { monto, referencia: ref, movement_type: tipo, fecha };
    }
  }).then(async res => {
    if (!res.isConfirmed) return;
    const r = await apiFetch('/api/pagos/recarga', {
      method: 'POST',
      body: JSON.stringify({
        monto: res.value.monto,
        metodo: 'pago_movil',
        referencia: res.value.referencia,
        movement_type: res.value.movement_type,
        fecha: res.value.fecha,
      }),
    });
    if (r.ok) {
      Swal.fire('¡Solicitud enviada!', 'Tu recarga está pendiente de verificación', 'success');
    } else {
      Swal.fire('Error', 'No se pudo procesar la recarga', 'error');
    }
  });
}

async function showWithdrawModal() {
  const token = getToken();
  if (!token) return;
  let saldoActual = 0;
  try {
    const r = await apiFetch('/api/auth/balance');
    if (r.ok) {
      const b = await r.json();
      saldoActual = b.saldo || 0;
    }
  } catch(e) {}
  Swal.fire({
    title: 'Retirar saldo',
    html: `
      <div class="mb-2 text-center">
        <small class="text-muted">Saldo disponible</small><br>
        <strong style="font-size:1.4rem;color:var(--gold);">Bs ${saldoActual.toFixed(2)}</strong>
      </div>
      <div class="mb-3">
        <label class="form-label">Monto a retirar (Bs)</label>
        <input type="number" id="swal-withdraw" class="form-control" min="1" max="${saldoActual}" step="0.5" placeholder="Ej: 20">
        <div class="quick-amounts" style="display:flex;gap:4px;flex-wrap:wrap;margin-top:6px;">
          <button type="button" class="btn btn-sm btn-outline-danger" onclick="document.getElementById('swal-withdraw').value=Math.min(10, ${saldoActual})">Bs 10</button>
          <button type="button" class="btn btn-sm btn-outline-danger" onclick="document.getElementById('swal-withdraw').value=Math.min(20, ${saldoActual})">Bs 20</button>
          <button type="button" class="btn btn-sm btn-outline-danger" onclick="document.getElementById('swal-withdraw').value=Math.min(50, ${saldoActual})">Bs 50</button>
          <button type="button" class="btn btn-sm btn-outline-danger" onclick="document.getElementById('swal-withdraw').value=Math.min(100, ${saldoActual})">Bs 100</button>
          <button type="button" class="btn btn-sm btn-outline-danger" onclick="document.getElementById('swal-withdraw').value=Math.min(200, ${saldoActual})">Bs 200</button>
        </div>
      </div>
    `,
    showCancelButton: true,
    confirmButtonText: 'Retirar',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#ef4444',
    preConfirm: () => {
      const val = parseFloat(document.getElementById('swal-withdraw').value);
      if (!val || val <= 0) { Swal.showValidationMessage('Ingresa un monto válido'); return false; }
      if (val < 10) { Swal.showValidationMessage('El monto mínimo es Bs 10'); return false; }
      if (val > 10000) { Swal.showValidationMessage('El monto máximo por transacción es Bs 10.000'); return false; }
      if (val > saldoActual) { Swal.showValidationMessage(`El monto no puede exceder tu saldo de Bs ${saldoActual.toFixed(2)}`); return false; }
      return val;
    }
  }).then(async res => {
    if (!res.isConfirmed) return;
    const r = await apiFetch('/api/pagos/retiro', {
      method: 'POST',
      body: JSON.stringify({ monto: res.value }),
    });
    if (r.ok) {
      await updateBalanceDisplay();
      Swal.fire('¡Listo!', `Solicitud de retiro de Bs ${res.value.toFixed(2)} registrada`, 'success');
      // recargar historial si estamos en perfil
      if (typeof cargarRetiros === 'function') cargarRetiros();
    } else {
      let msg = 'Error al procesar la solicitud';
      try { const err = await r.json(); msg = err.detail || msg; } catch(e) {}
      Swal.fire('Error', msg, 'error');
    }
  });
}

window.addEventListener('unhandledrejection', e => { console.warn('[unhandled]', e.reason); });

document.addEventListener('DOMContentLoaded', () => {
  const page = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a, .bottom-nav a').forEach(link => {
    const href = link.getAttribute('href');
    if (href === page) link.classList.add('active');
  });
  // Register service worker for PWA
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js').catch(() => {});
  }
});
