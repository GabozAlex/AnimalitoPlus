/* ===== INICIALIZACIÓN ===== */
let selectedAmount = 1;
const betSlip = {};

document.addEventListener('DOMContentLoaded', () => {
  const user = requireAuth();
  if (!user) return;

  updateBalanceDisplay();
  renderAnimalGrid();
  renderBetSlip();
  renderLastPlays();
  startTimer();
  setupBetAmounts();

  // Botón jugar
  document.getElementById('btnPlay')?.addEventListener('click', playBets);
});

/* ===== SELECCIÓN DE MONTOS ===== */
function setupBetAmounts() {
  document.querySelectorAll('.bet-amt').forEach(el => {
    el.addEventListener('click', () => {
      document.querySelectorAll('.bet-amt').forEach(b => b.classList.remove('active'));
      el.classList.add('active');
      selectedAmount = parseFloat(el.dataset.amt);
    });
  });
}

/* ===== GRID DE ANIMALES ===== */
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

/* ===== TOGGLE ANIMAL EN APUESTA ===== */
function toggleAnimal(id) {
  if (betSlip[id]) {
    delete betSlip[id];
  } else {
    betSlip[id] = { id, monto: selectedAmount };
  }
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
    } else if (badge) {
      badge.style.display = 'none';
    }
  });
}

/* ===== COMANDA ===== */
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

/* ===== JUGAR ===== */
function playBets() {
  const user = getCurrentUser();
  if (!user) return;

  const entries = Object.values(betSlip);
  if (entries.length === 0) return;

  const total = entries.reduce((sum, e) => sum + e.monto, 0);
  if (total > user.balance) {
    Swal.fire('Saldo insuficiente', 'Recarga para seguir jugando', 'error');
    return;
  }

  Swal.fire({
    title: 'Confirmar jugada',
    html: `
      <p style="font-size:14px;">
        Vas a apostar <strong>Bs ${total.toFixed(2)}</strong> en <strong>${entries.length} animal(es)</strong>.
      </p>
    `,
    icon: 'question',
    showCancelButton: true,
    confirmButtonText: '¡Jugar!',
    cancelButtonText: 'Cancelar',
    confirmButtonColor: '#f59e0b',
  }).then(res => {
    if (!res.isConfirmed) return;

    // Descontar saldo
    user.balance -= total;
    localStorage.setItem('animalito_user', JSON.stringify(user));
    updateBalanceDisplay();

    // Guardar jugada
    const play = {
      id: Date.now(),
      fecha: new Date().toISOString(),
      usuario: user.usuario,
      total,
      animales: entries.map(e => ({
        id: e.id,
        nombre: ANIMALES.find(a => a.id === e.id).nombre,
        monto: e.monto,
      })),
    };
    const plays = JSON.parse(localStorage.getItem('animalito_plays') || '[]');
    plays.unshift(play);
    localStorage.setItem('animalito_plays', JSON.stringify(plays));

    // Limpiar apuestas
    Object.keys(betSlip).forEach(k => delete betSlip[k]);
    renderBetSlip();
    updateAnimalGridUI();
    renderLastPlays();

    Swal.fire({
      icon: 'success',
      title: '¡Jugada registrada!',
      text: `Total apostado: Bs ${total.toFixed(2)}`,
      timer: 2000,
      showConfirmButton: false,
    });
  });
}

/* ===== ÚLTIMAS JUGADAS ===== */
function renderLastPlays() {
  const container = document.getElementById('lastPlays');
  if (!container) return;

  const user = getCurrentUser();
  if (!user) return;

  const plays = JSON.parse(localStorage.getItem('animalito_plays') || '[]')
    .filter(p => p.usuario === user.usuario)
    .slice(0, 5);

  if (plays.length === 0) {
    container.innerHTML = '<div class="text-muted text-center py-3" style="font-size:13px;">Aún no has realizado jugadas</div>';
    return;
  }

  container.innerHTML = plays.map(p => {
    const time = new Date(p.fecha).toLocaleTimeString('es-BO', { hour: '2-digit', minute: '2-digit' });
    const animales = p.animales.map(a => a.nombre).join(', ');
    return `
      <div class="play-item">
        <div>
          <div style="font-weight:600;font-size:12px;">${time}</div>
          <div style="font-size:12px;color:var(--text-muted);">${animales}</div>
        </div>
        <div class="play-result">Bs ${p.total.toFixed(2)}</div>
      </div>
    `;
  }).join('');
}

/* ===== TEMPORIZADOR ===== */
let timerInterval = null;

function startTimer() {
  const el = document.getElementById('timerValue');
  if (!el) return;

  // Próximo sorteo: cada 5 minutos desde la hora actual redondeada
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

/* ===== RESULTADOS ===== */
function generateMockResults(fecha) {
  const results = JSON.parse(localStorage.getItem('animalito_results') || '[]');
  const key = fecha || new Date().toISOString().split('T')[0];

  let dayResults = results.filter(r => r.fecha.startsWith(key));
  if (dayResults.length === 0 && !fecha) {
    // Generar resultados de ejemplo para hoy
    const hours = ['09:00', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00', '17:00', '18:00', '19:00', '20:00', '21:00'];
    dayResults = hours.map(h => {
      const animal = ANIMALES[Math.floor(Math.random() * ANIMALES.length)];
      return {
        hora: h,
        animalId: animal.id,
        animalNombre: animal.nombre,
        animalIcono: animal.icono,
        numero: String(Math.floor(Math.random() * 100)).padStart(2, '0'),
        fecha: `${key}T${h}:00`,
      };
    });
  }
  return dayResults;
}

function renderResults(fecha) {
  const container = document.getElementById('resultsBody');
  if (!container) return;

  const results = generateMockResults(fecha);
  if (results.length === 0) {
    container.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-4">No hay resultados para esta fecha</td></tr>';
    return;
  }

  container.innerHTML = results.map(r => `
    <tr>
      <td>${r.hora}</td>
      <td><div class="animal-cell"><i class="fas ${r.animalIcono} text-primary"></i> ${r.animalNombre}</div></td>
      <td class="num-cell">${r.numero}</td>
    </tr>
  `).join('');
}
