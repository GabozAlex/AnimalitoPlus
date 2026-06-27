let selectedAmount = 1;
let selectedLoteria = null;
let selectedHorario = null;
const betSlip = {};

const LOTERIAS = [
  { key: 'lotto_activo', nombre: 'Lotto Activo', icono: 'fa-lion', logo: 'img/loterias/lotto_activo.webp', color: '#0ea5e9' },
  { key: 'la_granjita', nombre: 'La Granjita', icono: 'fa-egg', logo: 'img/loterias/la_granjita.webp', color: '#22c55e' },
  { key: 'selvaplus', nombre: 'Selva Plus', icono: 'fa-hippo', logo: 'img/loterias/selvaplus.webp', color: '#f59e0b' },
];

const HORARIOS = [
  '08:00', '09:00', '10:00', '11:00', '12:00',
  '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00',
];

document.addEventListener('DOMContentLoaded', () => {
  const token = requireAuth();
  if (!token) return;
  updateBalanceDisplay();
  renderAnimalGrid();
  renderBetSlip();
  renderLotterySelector();
  renderHourGrid();
  setupBetAmounts();
  document.getElementById('btnPlay')?.addEventListener('click', playBets);
});

function setupBetAmounts() {
  document.querySelectorAll('.bet-amt').forEach(el => {
    el.addEventListener('click', () => {
      document.querySelectorAll('.bet-amt').forEach(b => b.classList.remove('active'));
      el.classList.add('active');
      selectedAmount = parseFloat(el.dataset.amt);
    });
  });
}

function renderLotterySelector() {
  const container = document.getElementById('lotterySelector');
  if (!container) return;
  container.innerHTML = LOTERIAS.map(l => `
    <div class="lottery-card ${selectedLoteria === l.key ? 'active' : ''}" data-loteria="${l.key}" onclick="selectLoteria('${l.key}')">
      <img src="${l.logo}" alt="${l.nombre}" class="lottery-logo" loading="lazy">
      <div class="lottery-name">${l.nombre}</div>
    </div>
  `).join('');
}

function selectLoteria(key) {
  if (Object.keys(betSlip).length > 0) {
    Swal.fire('Ticket pendiente', 'Debes culminar el ticket actual antes de cambiar de lotería', 'warning');
    return;
  }
  selectedLoteria = key;
  selectedHorario = null;
  document.querySelectorAll('.lottery-card').forEach(el => {
    el.classList.toggle('active', el.dataset.loteria === key);
  });
  renderHourGrid();
  renderAnimalGrid();
}

function renderHourGrid() {
  const container = document.getElementById('hourGrid');
  if (!container) return;
  const now = new Date();
  const currentHour = now.getHours();
  const currentMin = now.getMinutes();
  container.innerHTML = HORARIOS.map(h => {
    const [hh, mm] = h.split(':').map(Number);
    const isPast = hh < currentHour || (hh === currentHour && mm <= currentMin);
    const isActive = selectedHorario === h;
    return `
      <div class="hour-item ${isPast ? 'disabled' : ''} ${isActive ? 'active' : ''}"
           data-horario="${h}"
           onclick="${isPast ? '' : `selectHorario('${h}')`}">
        ${h}
      </div>
    `;
  }).join('');
}

function selectHorario(h) {
  if (Object.keys(betSlip).length > 0) {
    Swal.fire('Ticket pendiente', 'Debes culminar el ticket actual antes de cambiar de horario', 'warning');
    return;
  }
  selectedHorario = h;
  document.querySelectorAll('.hour-item').forEach(el => {
    el.classList.toggle('active', el.dataset.horario === h);
  });
}

function renderAnimalGrid() {
  const grid = document.getElementById('animalGrid');
  if (!grid) return;
  const imgFolder = LOTTERY_IMAGE_FOLDER[selectedLoteria] || 'lotto_activo';
  grid.innerHTML = ANIMALES.map(a => {
    const imgName = a.nombre.charAt(0) + a.nombre.slice(1).toLowerCase();
    return `
    <div class="animal-item" data-id="${a.id}" onclick="toggleAnimal('${a.id}')">
      <img src="img/animales/${imgFolder}/${imgName}.webp" alt="${a.nombre}" class="animal-img" loading="lazy">
      <div class="animal-number">${String(a.id).padStart(2, '0')}</div>
      <div class="animal-name">${a.nombre}</div>
      <div class="bet-badge" id="badge-${a.id}"></div>
    </div>
  `}).join('');
}

function toggleAnimal(id) {
  if (betSlip[id]) { delete betSlip[id]; }
  else { betSlip[id] = { id, monto: selectedAmount }; }
  renderBetSlip();
  updateAnimalGridUI();
}

function updateAnimalGridUI() {
  document.querySelectorAll('.animal-item').forEach(el => {
    const id = el.dataset.id;
    const isSelected = !!betSlip[id];
    el.classList.toggle('selected', isSelected);
    const badge = document.getElementById(`badge-${id}`);
    if (badge && isSelected) {
      badge.textContent = betSlip[id].monto;
      badge.style.display = 'flex';
    } else if (badge) { badge.style.display = 'none'; }
  });
}

function renderBetSlip() {
  const container = document.getElementById('betSlipItems');
  const totalEl = document.getElementById('betTotal');
  const countEl = document.getElementById('betCount');
  const btn = document.getElementById('btnPlay');
  if (!container) return;
  const entries = Object.values(betSlip);
  if (entries.length === 0) {
    container.innerHTML = '<div class="text-muted text-center py-2" style="font-size:13px;">Selecciona un animal para apostar</div>';
    totalEl.textContent = 'Bs 0.00';
    countEl.textContent = '0';
    btn.disabled = true;
    return;
  }
  let total = 0;
  container.innerHTML = entries.map(e => {
    const animal = ANIMALES.find(a => String(a.id) === String(e.id));
    total += e.monto;
    return `
      <div class="comanda-item">
        <span>${animal.nombre} #${String(e.id).padStart(2, '0')}</span>
        <span><strong>Bs ${e.monto.toFixed(2)}</strong> <i class="fas fa-times text-danger ms-2" style="cursor:pointer;" onclick="removeBet(${e.id})"></i></span>
      </div>
    `;
  }).join('');
  totalEl.textContent = `Bs ${total.toFixed(2)}`;
  countEl.textContent = entries.length;
  btn.disabled = false;
}

function removeBet(id) {
  delete betSlip[id];
  renderBetSlip();
  updateAnimalGridUI();
}

async function playBets() {
  const token = getToken();
  if (!token) { window.location.href = 'login.html'; return; }
  const entries = Object.values(betSlip);
  if (entries.length === 0) return;

  if (!selectedLoteria) {
    Swal.fire('Selecciona una lotería', 'Elige una lotería para continuar', 'warning');
    return;
  }
  if (!selectedHorario) {
    Swal.fire('Selecciona un horario', 'Elige un horario disponible', 'warning');
    return;
  }

  const total = entries.reduce((sum, e) => sum + e.monto, 0);
  const res = await apiFetch('/api/auth/balance');
  if (res.ok) {
    const { saldo } = await res.json();
    if (total > saldo) {
      Swal.fire('Saldo insuficiente', 'Recarga para seguir jugando', 'error');
      return;
    }
  }

  const loteriaNom = LOTERIAS.find(l => l.key === selectedLoteria)?.nombre || selectedLoteria;
  const imgFolder = LOTTERY_IMAGE_FOLDER[selectedLoteria] || 'lotto_activo';
  const animalListHtml = entries.map(e => {
    const a = ANIMALES.find(x => String(x.id) === String(e.id));
    const imgName = a ? a.nombre.charAt(0) + a.nombre.slice(1).toLowerCase() : '';
    return `<div style="display:flex;align-items:center;justify-content:space-between;padding:4px 0;border-bottom:1px solid #eee;font-size:14px;">
      <span>${imgName ? `<img src="img/animales/${imgFolder}/${imgName}.webp" style="width:24px;height:24px;border-radius:50%;vertical-align:middle;margin-right:6px;">` : ''}${a ? a.nombre : e.id} #${String(e.id).padStart(2, '0')}</span>
      <strong>Bs ${e.monto.toFixed(2)}</strong>
    </div>`;
  }).join('');

  const confirm = await Swal.fire({
    title: 'Confirmar jugada',
    html: `
      <div style="text-align:left;font-size:14px;">
        <p><strong>Lotería:</strong> ${loteriaNom}</p>
        <p><strong>Horario:</strong> ${selectedHorario}</p>
        <hr style="margin:8px 0;">
        ${animalListHtml}
        <hr style="margin:8px 0;">
        <div style="display:flex;justify-content:space-between;font-size:16px;">
          <strong>Total</strong>
          <strong style="color:var(--primary);">Bs ${total.toFixed(2)}</strong>
        </div>
      </div>
    `,
    showCancelButton: true,
    confirmButtonText: '<i class="fas fa-check me-1"></i> Confirmar',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#f59e0b',
  });
  if (!confirm.isConfirmed) return;

  Swal.fire({ title: 'Procesando...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });

  const r = await apiFetch('/api/apuestas', {
    method: 'POST',
    body: JSON.stringify({
      loteria: selectedLoteria,
      horario: selectedHorario,
      animales: entries.map(e => ({ animal_id: String(e.id), monto: e.monto })),
    }),
  });

  Swal.close();

  if (!r.ok) {
    const err = await r.json();
    Swal.fire('Error', err.detail || 'No se pudo realizar la apuesta', 'error');
    return;
  }

  Object.keys(betSlip).forEach(k => delete betSlip[k]);
  renderBetSlip();
  updateAnimalGridUI();
  await updateBalanceDisplay();

  Swal.fire({ icon: 'success', title: '¡Jugada registrada!', text: `Total: Bs ${total.toFixed(2)}`, timer: 2000, showConfirmButton: false });
}
