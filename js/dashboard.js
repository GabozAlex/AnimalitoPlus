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
  cargarAvisos();
  iniciarPollNotis();
  document.getElementById('btnPlay')?.addEventListener('click', playBets);
});

// Re-render animal grid when animales are loaded from API
window.addEventListener('animalesLoaded', () => {
  renderAnimalGrid();
  renderBetSlip();
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
  const isRed = n => [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(n);
  const imgName = a => a.nombre.charAt(0) + a.nombre.slice(1).toLowerCase();
  const animalById = id => ANIMALES.find(a => String(a.id) === String(id));

  // Roulette zero cells (left column)
  const zero00 = animalById('00');
  const zero0 = animalById('0');
  let html = `
    <div class="animal-item roulette-cell zero" data-id="00" onclick="toggleAnimal('00')" style="grid-column:1;grid-row:1/3;">
      <div class="roulette-num">00</div>
      <img src="img/animales/${imgFolder}/${imgName(zero00)}.webp" alt="BALLENA" class="roulette-img">
      <div class="roulette-name">${zero00.nombre}</div>
    </div>
    <div class="animal-item roulette-cell zero" data-id="0" onclick="toggleAnimal('0')" style="grid-column:1;grid-row:3;">
      <div class="roulette-num">0</div>
      <img src="img/animales/${imgFolder}/${imgName(zero0)}.webp" alt="DELFIN" class="roulette-img">
      <div class="roulette-name">${zero0.nombre}</div>
    </div>
  `;

  // 3 rows × 12 columns
  const rows = [
    [3,6,9,12,15,18,21,24,27,30,33,36],
    [2,5,8,11,14,17,20,23,26,29,32,35],
    [1,4,7,10,13,16,19,22,25,28,31,34],
  ];

  rows.forEach((row, rIdx) => {
    row.forEach((num, cIdx) => {
      const a = animalById(num);
      html += `
        <div class="animal-item roulette-cell ${isRed(num) ? 'red' : 'black'}" data-id="${num}" onclick="toggleAnimal('${num}')" style="grid-column:${cIdx + 2};grid-row:${rIdx + 1};">
          <div class="roulette-num">${num}</div>
          <img src="img/animales/${imgFolder}/${imgName(a)}.webp" alt="${a.nombre}" class="roulette-img">
          <div class="roulette-name">${a.nombre}</div>
        </div>
      `;
    });
  });

  grid.innerHTML = html;
}

function toggleAnimal(id) {
  if (!selectedLoteria) {
    Swal.fire('Selecciona una lotería', 'Elige una lotería primero', 'warning');
    return;
  }
  if (!selectedHorario) {
    Swal.fire('Selecciona un horario', 'Elige un horario disponible primero', 'warning');
    return;
  }
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
    const monto = isSelected ? betSlip[id].monto : null;
    let chip = el.querySelector('.chip-overlay');
    if (isSelected && monto) {
      if (!chip) {
        chip = document.createElement('div');
        chip.className = 'chip-overlay';
        el.appendChild(chip);
      }
      chip.innerHTML = `<div class="chip chip-${monto}"><span>${monto}</span></div>`;
      chip.style.display = 'flex';
    } else if (chip) {
      chip.style.display = 'none';
    }
  });
}

function renderBetSlip() {
  const container = document.getElementById('betSlipItems');
  const totalEl = document.getElementById('betTotal');
  const countEl = document.getElementById('betCount');
  const btn = document.getElementById('btnPlay');
  const clearBtn = document.getElementById('clearBtnContainer');
  if (!container) return;
  const entries = Object.values(betSlip);
  if (entries.length === 0) {
    container.innerHTML = '<div class="text-muted text-center py-2" style="font-size:13px;">Elige lotería → horario → monto → toca el animal</div>';
    totalEl.textContent = 'Bs 0.00';
    countEl.textContent = '0';
    btn.disabled = true;
    if (clearBtn) clearBtn.style.display = 'none';
    return;
  }
  let total = 0;
  const loteriaNom = LOTERIAS.find(l => l.key === selectedLoteria)?.nombre || selectedLoteria;
  container.innerHTML = `
    <div class="comanda-info">
      <span><i class="fas fa-dice-d6 me-1"></i> ${loteriaNom}</span>
      <span><i class="fas fa-clock me-1"></i> ${selectedHorario}</span>
    </div>
    <div class="comanda-hint">El monto se asigna al tocar el animal. Para cambiarlo, elimínalo y tócalo de nuevo.</div>
    ${entries.map(e => {
      const animal = ANIMALES.find(a => String(a.id) === String(e.id));
      total += e.monto;
      return `
        <div class="comanda-item">
          <span>${animal?.nombre || e.id} #${e.id}</span>
          <span><strong>Bs ${e.monto.toFixed(2)}</strong> <i class="fas fa-times text-danger ms-2" style="cursor:pointer;" onclick="removeBet('${e.id}')"></i></span>
        </div>
      `;
    }).join('')}
  `;
  totalEl.textContent = `Bs ${total.toFixed(2)}`;
  countEl.textContent = entries.length;
  btn.disabled = false;
  if (clearBtn) clearBtn.style.display = 'block';
}

function clearBetSlip() {
  Object.keys(betSlip).forEach(k => delete betSlip[k]);
  renderBetSlip();
  updateAnimalGridUI();
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
      <span>${imgName ? `<img src="img/animales/${imgFolder}/${imgName}.webp" style="width:24px;height:24px;border-radius:50%;vertical-align:middle;margin-right:6px;">` : ''}${a ? a.nombre : e.id} #${e.id}</span>
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

  const data = await r.json();
  const confirmResult = await Swal.fire({
    icon: 'success',
    title: '✅ ¡Jugada registrada!',
    html: `
      <div style="text-align:left;font-size:14px;margin:0 auto;display:inline-block;">
        <p style="margin:4px 0;"><strong>Folio:</strong> ${data.folio || 'N/A'}</p>
        <p style="margin:4px 0;"><strong>Total:</strong> <span style="color:var(--primary);">Bs ${total.toFixed(2)}</span></p>
      </div>
    `,
    confirmButtonText: '<i class="fas fa-print"></i> Ver Ticket',
    showCancelButton: true,
    cancelButtonText: 'Cerrar',
    confirmButtonColor: '#f59e0b',
  });
  if (confirmResult.isConfirmed) verTicketModal(data.id);
}

async function cargarAvisos() {
  try {
    const r = await apiFetch('/api/avisos');
    if (!r.ok) return;
    const avisos = await r.json();
    const bar = document.getElementById('avisosBar');
    if (!bar) return;
    if (avisos.length === 0) { bar.style.display = 'none'; return; }
    bar.style.display = 'flex';
    const loterias = { lotto_activo: 'Lotto Activo', la_granjita: 'La Granjita', selvaplus: 'Selva Plus' };
    bar.innerHTML = avisos.map(a => {
      const esInsta = a.fuente === 'instagram';
      const badge = esInsta ? '<i class="fab fa-instagram"></i> Instagram' : '<i class="fas fa-bullhorn"></i> Aviso';
      const extra = a.url_instagram ? `<a href="${a.url_instagram}" target="_blank" rel="noopener">Ver en Instagram</a>` : '';
      const lote = a.loteria ? loterias[a.loteria] || a.loteria : '';
      return `<div class="aviso-card ${esInsta ? 'aviso-instagram' : ''}">
        <div class="aviso-icon">${esInsta ? '<i class="fab fa-instagram"></i>' : '<i class="fas fa-exclamation-triangle"></i>'}</div>
        <div class="aviso-body">
          <div class="aviso-titulo">${a.titulo}${lote ? ' — ' + lote : ''}</div>
          <div class="aviso-texto">${a.contenido}</div>
          <div class="aviso-meta">${badge} · ${new Date(a.created_at).toLocaleDateString()} ${extra ? '· ' + extra : ''}</div>
        </div>
      </div>`;
    }).join('');
  } catch(e) { console.error(e); }
}

async function verTicketModal(apuestaId) {
  try {
    const res = await apiFetch('/api/apuestas/' + apuestaId + '/ticket');
    if (!res.ok) throw new Error('Error');
    const html = await res.text();
    Swal.fire({
      icon: 'success',
      title: '¡Jugada registrada!',
      html: `<div style="max-height:60vh;overflow:auto;text-align:left;">${html}</div>`,
      showCancelButton: true,
      confirmButtonText: '<i class="fas fa-print"></i> Imprimir',
      cancelButtonText: 'Cerrar',
      width: '500px',
      customClass: { confirmButton: 'btn btn-primary', cancelButton: 'btn btn-secondary' },
      buttonsStyling: false,
      didOpen: () => {
        const btn = Swal.getConfirmButton();
        btn.onclick = () => { window.print(); };
      },
    });
  } catch (e) {
    Swal.fire({ icon: 'success', title: '¡Jugada registrada!', timer: 2000, showConfirmButton: false });
  }
}
