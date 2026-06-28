-- =============================================
-- ESQUEMA COMPLETO DE BASE DE DATOS (PostgreSQL)
-- =============================================

-- 1. USUARIOS
CREATE TABLE IF NOT EXISTS usuarios (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    correo VARCHAR(255) UNIQUE NOT NULL,
    clave VARCHAR(255) NOT NULL,
    saldo DECIMAL(12,2) DEFAULT 0,
    cedula VARCHAR(20),
    telefono VARCHAR(20),
    banco VARCHAR(100),
    banco_codigo VARCHAR(10),
    pago_movil_titular VARCHAR(100),
    rol VARCHAR(10) DEFAULT 'user' CHECK (rol IN ('user', 'admin')),
    bloqueado BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_usuarios_correo ON usuarios(correo);

-- 2. APUESTAS (ticket)
CREATE TABLE IF NOT EXISTS apuestas (
    id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    loteria VARCHAR(50) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    horario TIME NOT NULL,
    estado VARCHAR(20) DEFAULT 'pendiente' CHECK (estado IN ('pendiente', 'ganada', 'perdida', 'pagada')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_apuestas_usuario ON apuestas(usuario_id);
CREATE INDEX idx_apuestas_fecha ON apuestas(fecha);

-- 3. DETALLE DE APUESTA (animales dentro del ticket)
CREATE TABLE IF NOT EXISTS detalle_apuesta (
    id BIGSERIAL PRIMARY KEY,
    apuesta_id BIGINT NOT NULL REFERENCES apuestas(id) ON DELETE CASCADE,
    animal_id VARCHAR(3) NOT NULL,
    monto DECIMAL(10,2) NOT NULL
);

CREATE INDEX idx_detalle_apuesta ON detalle_apuesta(apuesta_id);

-- 4. RESULTADOS DE SORTEOS
CREATE TABLE IF NOT EXISTS resultados (
    id BIGSERIAL PRIMARY KEY,
    loteria VARCHAR(50) NOT NULL,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    horario TIME NOT NULL,
    animal_id VARCHAR(3) NOT NULL,
    numero VARCHAR(2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_resultados_fecha ON resultados(fecha);
CREATE INDEX idx_resultados_loteria ON resultados(loteria);

-- 5. TRANSACCIONES (auditoría)
CREATE TABLE IF NOT EXISTS transacciones (
    id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT REFERENCES usuarios(id) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('recarga', 'retiro', 'apuesta', 'pago_premio', 'ajuste_admin')),
    monto DECIMAL(12,2) NOT NULL,
    metodo VARCHAR(20),        -- pago_movil, cripto, manual
    referencia VARCHAR(255),
    estado VARCHAR(20) DEFAULT 'pendiente',
    descripcion TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transacciones_usuario ON transacciones(usuario_id);
CREATE INDEX idx_transacciones_fecha ON transacciones(created_at);

-- 6. CREAR ADMIN INICIAL (cambiar credenciales)
-- Contraseña: admin123 (hash bcrypt generado automáticamente)
INSERT INTO usuarios (nombre, apellido, correo, clave, rol)
SELECT 'Admin', 'Principal', 'admin@animalitoplus.com', '$2b$12$RJh.PFrXlCsXF9G2VY8HLeMCU0I03fg5hdjfYh5Ldq/vuJDLBTam6', 'admin'
WHERE NOT EXISTS (SELECT 1 FROM usuarios WHERE correo = 'admin@animalitoplus.com');

-- 7. CONFIGURACION (banco para recargas, límites, etc.)
CREATE TABLE IF NOT EXISTS config (
    clave VARCHAR(50) PRIMARY KEY,
    valor TEXT NOT NULL
);

INSERT INTO config (clave, valor)
VALUES ('casa', '{"nombre":"Gabriel Alejandro Rosas Rosas","banco":"Banco Mercantil","banco_codigo":"0105","cedula":"27650586","telefono":"4123656230"}')
ON CONFLICT (clave) DO NOTHING;

INSERT INTO config (clave, valor)
VALUES ('limites', '{"max_por_apuesta":0,"max_por_hora":0,"max_por_dia":0}')
ON CONFLICT (clave) DO NOTHING;

-- 8. AUDITORIA
CREATE TABLE IF NOT EXISTS auditoria (
    id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT REFERENCES usuarios(id) ON DELETE SET NULL,
    accion VARCHAR(50) NOT NULL,
    descripcion TEXT,
    ip VARCHAR(45),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_auditoria_usuario ON auditoria(usuario_id);
CREATE INDEX idx_auditoria_creado ON auditoria(created_at);

-- 9. MIGRACION: Float → Numeric (ejecutar si ya existen tablas con columnas Float) (ejecutar si ya existen tablas con columnas Float)
-- ALTER TABLE usuarios ALTER COLUMN saldo TYPE DECIMAL(12,2);
-- ALTER TABLE apuestas ALTER COLUMN total TYPE DECIMAL(12,2);
-- ALTER TABLE detalle_apuesta ALTER COLUMN monto TYPE DECIMAL(12,2);
-- ALTER TABLE transacciones ALTER COLUMN monto TYPE DECIMAL(12,2);

-- 11. MIGRACION: Agregar codigo_referido, referido_por, bono_referido (si no existen)
-- ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS codigo_referido VARCHAR(20) UNIQUE;
-- ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS referido_por BIGINT REFERENCES usuarios(id);
-- ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS bono_referido BOOLEAN DEFAULT FALSE;

-- 12. NOTIFICACIONES
CREATE TABLE IF NOT EXISTS notificaciones (
    id BIGSERIAL PRIMARY KEY,
    usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('ganada', 'perdida', 'premio', 'sistema', 'info')),
    titulo VARCHAR(200) NOT NULL,
    contenido TEXT,
    referencia_id INTEGER,
    leida BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notificaciones_usuario ON notificaciones(usuario_id);
CREATE INDEX idx_notificaciones_no_leidas ON notificaciones(usuario_id, leida) WHERE leida = FALSE;

-- 13. CUPOS (configuración de límites por animal + horario)
CREATE TABLE IF NOT EXISTS cupos (
    id BIGSERIAL PRIMARY KEY,
    loteria VARCHAR(50) NOT NULL,
    horario TIME NOT NULL,
    animal_id VARCHAR(3) NOT NULL,
    maximo DECIMAL(12,2) NOT NULL DEFAULT 0,
    activo BOOLEAN DEFAULT TRUE,
    UNIQUE (loteria, horario, animal_id)
);

-- 14. ACUMULADOS DE CUPOS (se resetea diariamente)
CREATE TABLE IF NOT EXISTS acumulados_cupos (
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    loteria VARCHAR(50) NOT NULL,
    horario TIME NOT NULL,
    animal_id VARCHAR(3) NOT NULL,
    acumulado DECIMAL(12,2) NOT NULL DEFAULT 0,
    PRIMARY KEY (fecha, loteria, horario, animal_id)
);

-- 15. FOLIO en apuestas
ALTER TABLE apuestas ADD COLUMN IF NOT EXISTS folio VARCHAR(20) UNIQUE;
