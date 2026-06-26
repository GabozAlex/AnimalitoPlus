let selectedAmount = 1;
const betSlip = {};

document.addEventListener('DOMContentLoaded', () => {
  const token = requireAuth();
  if (!token) return;
  loadUserInfo();
  updateBalanceDisplay();
  renderAnimalGrid();
  renderBetSlip();
  renderLastPlays();
  startTimer();
  setupBetAmounts();
  document.getElementById('btnPlay')?.addEventListener('click', playBets);
});

async function loadUserInfo() {
  const nameEl = document.getElementById('userName');
  if (nameEl) {
    const user = getCurrentUser();
    if (user) nameEl.textContent = `${user.nombre} ${user.apellido}`.trim() || user.correo;
  }
  const adminLink = document.getElementById('adminLink');
  if (adminLink) {
    const user = getCurrentUser();
    if (user && user.rol === 'admin') adminLink.classList.remove('d-none');
  }
}

function setupBetAmounts() {
  document.querySelectorAll('.bet-amt').forEach(el => {
    el.addEventListener('click', () => {
      document.querySelectorAll('.bet-amt').forEach(b => b.classList.remove('active'));
      el.classList.add('active');
      selectedAmount = parseFloat(el.dataset.amt);
    });
  });
}

function renderAnimalGrid() {
  const grid = document.getElementById('animalGrid');
  if (!grid) return;
  grid.innerHTML = ANIMALES.map(a => `
    <div class="animal-item" data-id="${a.id}" onclick="toggleAnimal(${a.id})">
      <i class="fas ${a.icono} animal-icon"></i>
      <div class="animal-number">${String(a.id).padStart(2, '0')}</div>
      <div class="animal-name">${a.nombre}</div>
      <div class="bet-badge" id="badge-${a.id}"></div>
    </div>
  `).join('');
}

function toggleAnimal(id) {
  if (betSlip[id]) { delete betSlip[id]; }
  else { betSlip[id] = { id, monto: selectedAmount }; }
  renderBetSlip();
  updateAnimalGridUI();
}

function updateAnimalGridUI() {
  document.querySelectorAll('.animal-item').forEach(el => {
    const id = parseInt(el.dataset.id);
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
    const animal = ANIMALES.find(a => a.id === e.id);
    total += e.monto;
    return `
      <div class="comanda-item">
        <span><i class="fas ${animal.icono} me-1"></i> ${animal.nombre} #${String(e.id).padStart(2, '0')}</span>
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

  const total = entries.reduce((sum, e) => sum + e.monto, 0);
  const res = await apiFetch('/api/auth/balance');
  if (res.ok) {
    const { saldo } = await res.json();
    if (total > saldo) {
      Swal.fire('Saldo insuficiente', 'Recarga para seguir jugando', 'error');
      return;
    }
  }

  const { value: loteria } = await Swal.fire({
    title: 'Seleccionar lotería',
    input: 'select',
    inputOptions: {
      'lotto_activo': 'Lotto Activo',
      'la_granjita': 'La Granjita',
      'selvaplus': 'SelvaPlus',
    },
    inputPlaceholder: 'Elige una lotería',
    showCancelButton: true,
    confirmButtonText: 'Continuar',
    confirmButtonColor: '#f59e0b',
    inputValidator: v => { if (!v) return 'Selecciona una lotería'; },
  });
  if (!loteria) return;

  const { value: horario } = await Swal.fire({
    title: 'Seleccionar horario',
    input: 'select',
    inputOptions: {
      '09:00': '09:00', '10:00': '10:00', '11:00': '11:00',
      '12:00': '12:00', '13:00': '13:00', '14:00': '14:00',
      '15:00': '15:00', '16:00': '16:00', '17:00': '17:00',
      '18:00': '18:00', '19:00': '19:00',
    },
    inputPlaceholder: 'Elige horario',
    showCancelButton: true,
    confirmButtonText: 'Jugar',
    confirmButtonColor: '#f59e0b',
    inputValidator: v => { if (!v) return 'Selecciona un horario'; },
  });
  if (!horario) return;

  Swal.fire({ title: 'Procesando...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });

  const r = await apiFetch('/api/apuestas', {
    method: 'POST',
    body: JSON.stringify({
      loteria,
      horario,
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
  renderLastPlays();

  Swal.fire({ icon: 'success', title: '¡Jugada registrada!', text: `Total: Bs ${total.toFixed(2)}`, timer: 2000, showConfirmButton: false });
}

async function renderLastPlays() {
  const container = document.getElementById('lastPlays');
  if (!container) return;
  const token = getToken();
  if (!token) return;

  const res = await apiFetch('/api/apuestas?limit=5');
  if (!res.ok) { container.innerHTML = '<div class="text-muted text-center py-3" style="font-size:13px;">Error al cargar jugadas</div>'; return; }
  const apuestas = await res.json();

  if (apuestas.length === 0) {
    container.innerHTML = '<div class="text-muted text-center py-3" style="font-size:13px;">Aún no has realizado jugadas</div>';
    return;
  }

  container.innerHTML = apuestas.map(p => {
    const time = new Date(p.created_at).toLocaleTimeString('es-BO', { hour: '2-digit', minute: '2-digit' });
    const animales = (p.detalles || []).map(d => {
      const a = ANIMALES.find(an => String(an.id) === d.animal_id);
      return a ? a.nombre : d.animal_id;
    }).join(', ');
    const estadoClass = p.estado === 'ganada' ? 'play-win' : p.estado === 'perdida' ? 'play-lose' : '';
    return `
      <div class="play-item ${estadoClass}">
        <div>
          <div style="font-weight:600;font-size:12px;">${time} · ${p.loteria}</div>
          <div style="font-size:12px;color:var(--text-muted);">${animales}</div>
        </div>
        <div class="play-result">Bs ${p.total.toFixed(2)}</div>
      </div>
    `;
  }).join('');
}

let timerInterval = null;

function startTimer() {
  const el = document.getElementById('timerValue');
  if (!el) return;
  function updateTimer() {
    const now = new Date();
    const minutes = now.getMinutes();
    const nextMinute = Math.ceil((minutes + 1) / 5) * 5;
    const next = new Date(now);
    next.setMinutes(nextMinute, 0, 0);
    const diff = next - now;
    if (diff <= 0) return;
    const m = Math.floor(diff / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    el.innerHTML = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')} <span>min</span>`;
    el.classList.toggle('warning', m === 0 && s <= 30);
  }
  updateTimer();
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(updateTimer, 1000);
}

async function renderResults(fecha) {
  const container = document.getElementById('resultsBody');
  if (!container) return;
  const params = fecha ? `?fecha=${fecha}` : '';
  const res = await apiFetch(`/api/resultados${params}`);
  if (!res.ok) { container.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4">Error al cargar resultados</td></tr>'; return; }
  const results = await res.json();
  if (results.length === 0) {
    container.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4">No hay resultados para esta fecha</td></tr>';
    return;
  }
  container.innerHTML = results.map(r => {
    const animal = ANIMALES.find(a => String(a.id) === r.animal_id);
    return `
      <tr>
        <td>${r.horario}</td>
        <td><div class="animal-cell"><i class="fas ${animal ? animal.icono : 'fa-paw'} text-primary"></i> ${animal ? animal.nombre : r.animal_id}</div></td>
        <td class="num-cell">${r.numero}</td>
      </tr>
    `;
  }).join('');
}
