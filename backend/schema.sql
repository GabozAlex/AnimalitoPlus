-- =============================================
-- ESQUEMA COMPLETO PARA SUPABASE (PostgreSQL)
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
    tipo VARCHAR(20) NOT NULL,  -- recarga, retiro, apuesta, pago_premio, ajuste_admin
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

-- 7. ROW LEVEL SECURITY (opcional, para seguridad)
ALTER TABLE usuarios ENABLE ROW LEVEL SECURITY;
ALTER TABLE apuestas ENABLE ROW LEVEL SECURITY;
ALTER TABLE detalle_apuesta ENABLE ROW LEVEL SECURITY;
ALTER TABLE transacciones ENABLE ROW LEVEL SECURITY;

-- Política: usuario solo ve sus propios datos
CREATE POLICY usuarios_self ON usuarios
    FOR ALL USING (id = (SELECT id FROM usuarios WHERE correo = current_user));

CREATE POLICY apuestas_self ON apuestas
    FOR ALL USING (usuario_id = (SELECT id FROM usuarios WHERE correo = current_user));

CREATE POLICY transacciones_self ON transacciones
    FOR ALL USING (usuario_id = (SELECT id FROM usuarios WHERE correo = current_user));
