# Propuesta: Plataforma de Lotería de Animalitos (Banca Propia)

---

## 1. Resumen de la Idea

Plataforma web donde los usuarios apuestan en línea a la lotería de los 38 animales. El dueño de la plataforma es **la banca**: recibe todas las apuestas y paga los premios. Modelo de negocio similar a las loterías tradicionales pero en formato digital propio.

**Diferenciación:** Usa modelos de ML y estadísticos (Markov, Random Forest, XGBoost) para ajustar probabilidades y ofrecer estadísticas a los jugadores, dándole una fachada de "plataforma analítica" para argumentar que es un juego de habilidad/análisis y no puro azar.

---

## 2. Estructura del Negocio

### 2.1 Stack Tecnológico

| Componente | Tecnología | Dominio actual |
|-----------|-----------|----------------|
| Frontend | React + Tailwind o Streamlit | Nuevo (pero aprendible) |
| Backend API | FastAPI (Python) | Ya sabes Python |
| Base de datos | PostgreSQL o SQLite (escalable) | Ya sabes SQLite |
| Autenticación | JWT con FastAPI | Ya tienes lógica de roles |
| Motor de sorteos | RNG + modelos ML opcionales | Ya lo tienes en PrediccionNumeros |
| Pagos | Binance Pay / PayPal / Cripto | Nuevo |
| Hosting | VPS (DigitalOcean, Hetzner) | Nuevo |

### 2.2 Funcionalidades Clave

**Para el jugador:**
- Registro y login con cédula/email
- Recarga de saldo (cripto, transferencia, efectivo vía puntos de recarga)
- Selección de animal para apostar
- Ingreso del monto a apostar
- Historial de apuestas realizadas
- Resultados en vivo (sorteos cada hora 08:00-19:00)
- Estadísticas: animales más pagados, fríos, calientes, frecuencias por hora

**Para el admin (tú):**
- Dashboard de control de bankroll
- Configuración de premios (multiplicador por animal)
- Historial completo de apuestas y pagos
- Usuarios: ver, bloquear, saldo
- Reportes: ganancias/pérdidas por día, montos jugados vs pagados
- Sistema de auditoría (como el de Sistema-Policia)
- Control de riesgo: límite de apuesta máxima por usuario, por hora, por día

### 2.3 Módulo de Pago (tu ventaja sobre loterías callejeras)

| Método | Descripción |
|--------|------------|
| **Cripto (USDT/Binance Pay)** | Automático, sin intervención manual |
| **Puntos de recarga** | Vendes saldo a revendedores que reciben efectivo |
| **Transferencia móvil** | Pagomóvil (manual, para empezar) |
| **Descuento de saldo** | El jugador tiene un monedero interno |

---

## 3. Plan Financiero

### 3.1 Capital Inicial

| Concepto | Costo (Bs) | Costo ($) |
|----------|-----------|-----------|
| Bankroll | 18.360 | 30 |
| VPS (1 mes, DigitalOcean) | 366 | 0.6 |
| Dominio (.com.ve o similar) | 0 | 0.6-1 |
| **Total inicial** | **~18.726** | **~31** |

### 3.2 Estructura de Apuestas y Pagos

| Apuesta (Bs) | Pago 30x (Bs) | Tu ganancia si pierde (Bs) |
|-------------|---------------|---------------------------|
| 1 | 30 | 1 |
| 2 | 60 | 2 |
| 5 | 150 | 5 |
| 10 | 300 | 10 |
| 15 | 450 | 15 |
| 20 | 600 | 20 |
| 25 | 750 | 25 |

### 3.3 Simulación de Escenarios

**Escenario normal (70% aciertos de la banca):**
- 100 apuestas de 10 Bs = 1.000 Bs jugados
- La banca gana en ~70 → 700 Bs ingresan
- La banca pierde en ~30 → 9.000 Bs salen (30 × 300)
- **Resultado: -8.300 Bs** (pérdida)

**Escenario normal ajustado (probabilidad real 1/38 ≈ 2.6%):**
- 100 apuestas de 10 Bs = 1.000 Bs jugados
- La banca gana en ~97.4 → 974 Bs
- La banca pierde en ~2.6 → 780 Bs (2.6 × 300)
- **Resultado: +194 Bs** (ganancia)

Con el multiplicador 30x y 1/38 de probabilidad, el margen de la banca es:
```
(38 × 1) - (1 × 30) = 8 unidades de ganancia cada 38 sorteos
Margen ≈ 21%
```

### 3.4 Punto de Equilibrio

Con $30 de bankroll (18.360 Bs) y apuestas máximas de 25 Bs:
- Peor racha posible: ~24 aciertos seguidos de apuesta máxima
- Probabilidad de eso: (1/38)^24 ≈ 0 (esencialmente imposible)
- **El margen estadístico te protege siempre que tengas suficiente volumen de apuestas**

---

## 4. Esquema de Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| **Legal** (operar sin licencia) | Alta | Crítico | Hostear fuera de Vzla/RD, usar cripto, no tener oficina física, términos legales que lo definan como "juego de habilidad" |
| **Fraude de usuarios** (apuestas falsas, doble reclamo) | Media | Alto | Auditoría de todas las transacciones, límites por IP/usuario, registro de cada apuesta con timestamp |
| **Ataque DDoS/hackeo** | Baja | Crítico | VPS con firewall, Cloudflare, backups diarios |
| **Bankrun** (muchos aciertos seguidos) | Muy baja | Alto | Límite de apuesta diario por usuario, tope de pago por hora |
| **Competencia** (otras loterías online) | Media | Medio | Diferenciar con estadísticas/ML, mejor UX, atención al cliente |

---

## 5. Roadmap

### Fase 1 — MVP (2-3 semanas)
- Backend FastAPI con CRUD de usuarios, apuestas, saldo
- Base de datos SQLite/PostgreSQL
- Login con roles (admin, usuario)
- Módulo de apuestas: seleccionar animal, monto, guardar
- Sorteo manual (tú mismo ingresas el resultado)
- Dashboard admin: historial de apuestas, saldo, ganancias/pérdidas
- Sin pagos reales todavía (prueba interna)

### Fase 2 — Pagos (2 semanas)
- Integrar Binance Pay / USDT
- Monedero interno (el usuario recarga y juega con saldo)
- Retiro de ganancias
- Límites de apuesta por usuario/hora/día

### Fase 3 — Automatización (1-2 semanas)
- Sorteos automáticos cada hora (08:00-19:00)
- Resultados desde scraping de loterías reales (tus scrapers actuales)
- Notificaciones de resultados al usuario
- Historial público de sorteos

### Fase 4 — Crecimiento (continuo)
- Estadísticas avanzadas para el jugador (usando tus modelos ML)
- Programa de referidos
- App móvil (PWA primero)
- Revendedores (compran saldo al por mayor para vender en efectivo)

---

## 6. Ventajas Competitivas

| Frente a loterías callejeras | Frente a otras plataformas online |
|------------------------------|-----------------------------------|
| Sin necesidad de cobrador físico | Estadísticas ML para el jugador |
| Sin límite de ubicación | Interfaz moderna |
| Pago automático (sin reclamar) | Control de bankroll en tiempo real |
| Historial completo para el jugador | Dashboard con métricas de rendimiento |

---

## 7. Próximo Paso Concreto

1. Construir el MVP con FastAPI + SQLite (sin pagos reales)
2. Probar interna y externamente con amigos (apuestas falsas o con saldo de prueba)
3. Validar: ¿los usuarios entienden la plataforma? ¿el margen se comporta como esperas?
4. Agregar pagos con cripto
5. Abrir al público con un grupo piloto controlado
6. Recién después de semanas de validación, escalar

---

**Nota:** Este documento es una propuesta técnica y de negocio. El aspecto legal debe consultarse con un abogado especializado antes de lanzar al público.
