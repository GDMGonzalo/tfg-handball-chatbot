from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.schema import ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

db = SQLAlchemy()

# ---------------------------
# Tabla de usuarios
# ---------------------------
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    
    # Relaciones
    temporadas = relationship('Temporada', back_populates='user', cascade="all, delete-orphan")
    equipos = relationship('Equipo', back_populates='user', cascade="all, delete-orphan")

# ---------------------------
# Tabla de temporadas
# ---------------------------
# En la clase Temporada, necesitamos modificar la relación con Partido
class Temporada(db.Model):
    __tablename__ = 'temporada'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    
    # Relaciones
    user = relationship('User', back_populates='temporadas')
    ligas = relationship('Liga', back_populates='temporada', cascade="all, delete-orphan")
    
    # Propiedad para acceder a los partidos a través de las ligas
    @property
    def partidos(self):
        from sqlalchemy.orm import Session
        session = Session.object_session(self)
        if session:
            from sqlalchemy import select
            stmt = select(Partido).join(Liga).filter(Liga.temporada_id == self.id)
            return session.execute(stmt).scalars().all()
        return []
# ----------------及ひ
# Tabla de categorías
# ---------------------------
class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    
    # Relaciones
    ligas = relationship('Liga', back_populates='categoria')

# ---------------------------
# Tabla de ligas
# ---------------------------
class Liga(db.Model):
    __tablename__ = 'liga'
    id = db.Column(db.Integer, primary_key=True)
    temporada_id = db.Column(db.Integer, db.ForeignKey('temporada.id'), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    
    # Relaciones
    temporada = relationship('Temporada', back_populates='ligas')
    categoria = relationship('Categoria', back_populates='ligas')
    equipo_ligas = relationship('EquipoLiga', back_populates='liga', cascade="all, delete-orphan")
    partidos = relationship('Partido', back_populates='liga', cascade="all, delete-orphan")

# ---------------------------
# Tabla de equipos
# ---------------------------
class Equipo(db.Model):
    __tablename__ = 'equipos'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)  # SIN unique=True global
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    tipo = db.Column(db.Enum('masculino', 'femenino', 'mixto', name='tipo_enum'), default='mixto', nullable=False)
    
    # Relaciones
    user = relationship('User', back_populates='equipos')
    jugadores = relationship('Jugador', back_populates='equipo', cascade="all, delete-orphan")
    equipo_ligas = relationship('EquipoLiga', back_populates='equipo', cascade="all, delete-orphan")
    partidos_local = relationship('Partido', foreign_keys='Partido.equipo_local_id', back_populates='equipo_local')
    partidos_visitante = relationship('Partido', foreign_keys='Partido.equipo_visitante_id', back_populates='equipo_visitante')
    eventos = relationship('Evento', back_populates='equipo')
    
    
    __table_args__ = (UniqueConstraint('user_id', 'nombre', name='uq_equipo_usuario_nombre'),)

# ---------------------------
# Tabla intermedia: equipo_liga
# ---------------------------
class EquipoLiga(db.Model):
    __tablename__ = 'equipo_liga'
    id = db.Column(db.Integer, primary_key=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=False)
    liga_id = db.Column(db.Integer, db.ForeignKey('liga.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    
    # Relaciones
    equipo = relationship('Equipo', back_populates='equipo_ligas')
    liga = relationship('Liga', back_populates='equipo_ligas')
    
    __table_args__ = (UniqueConstraint('equipo_id', 'liga_id', name='uq_equipo_liga'),)

# ---------------------------
# Tabla de partidos
# ---------------------------
# En la clase Partido, necesitamos agregar la relación con Temporada a través de Liga
class Partido(db.Model):
    __tablename__ = 'partidos'
    id = db.Column(db.Integer, primary_key=True)
    liga_id = db.Column(db.Integer, db.ForeignKey('liga.id'), nullable=True)
    fecha_hora = db.Column(db.DateTime, nullable=False)
    equipo_local_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=True)
    equipo_visitante_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    goles_local = db.Column(db.Integer, nullable=True)
    goles_visitante = db.Column(db.Integer, nullable=True)
    
    # Relaciones
    liga = relationship('Liga', back_populates='partidos')
    equipo_local = relationship('Equipo', foreign_keys=[equipo_local_id], back_populates='partidos_local')
    equipo_visitante = relationship('Equipo', foreign_keys=[equipo_visitante_id], back_populates='partidos_visitante')
    convocados = relationship('Convocado', back_populates='partido', cascade="all, delete-orphan")
    videos = relationship('Video', back_populates='partido', cascade="all, delete-orphan")
    
    # Propiedad para acceder a la temporada a través de la liga
    @property
    def temporada(self):
        return self.liga.temporada if self.liga else None
        
    # Propiedad para obtener el resultado formateado
    @property
    def resultado(self):
        # Calcular goles basado en eventos (incluyendo tiros con resultado gol)
        equipo_local_id = self.equipo_local_id
        equipo_visitante_id = self.equipo_visitante_id
        
        # Obtener todos los eventos de gol del partido
        eventos_gol = Evento.query.filter(
            Evento.partido_id == self.id,
            db.or_(
                Evento.tipo_evento_id.in_([1, 13]),  # Goles tradicionales
                db.and_(
                    Evento.tipo_evento_id == 37,  # Eventos de tiro
                    Evento.resultado_tiro == 'gol'  # Con resultado gol
                )
            )
        ).all()
        
        # Contar goles por equipo
        goles_local = sum(1 for e in eventos_gol if e.equipo_id == equipo_local_id)
        goles_visitante = sum(1 for e in eventos_gol if e.equipo_id == equipo_visitante_id)
        
        return f"{goles_local}-{goles_visitante}"
# ---------------------------
# Tabla de videos
# ---------------------------
# En la clase Video, necesitamos modificar la propiedad temporada
class Video(db.Model):
    __tablename__ = 'videos'
    id = db.Column(db.Integer, primary_key=True)
    partido_id = db.Column(db.Integer, db.ForeignKey('partidos.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    duracion_segundos = db.Column(db.Integer, nullable=True)
    fps = db.Column(db.Integer, nullable=True)

    # Relaciones
    partido = relationship('Partido', back_populates='videos')
    eventos = relationship('Evento', back_populates='video', cascade="all, delete-orphan")
    
    # Propiedad para acceder a la temporada a través del partido y la liga
    @property
    def temporada(self):
        return self.partido.liga.temporada if self.partido and self.partido.liga else None
# ---------------------------
# Tabla de posiciones
# ---------------------------
class Posicion(db.Model):
    __tablename__ = 'posiciones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(20), nullable=True)
    
    # Relaciones
    jugadores = relationship('Jugador', back_populates='posicion')

# ---------------------------
# Tabla de jugadores
# ---------------------------
class Jugador(db.Model):
    __tablename__ = 'jugadores'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    dorsal = db.Column(db.Integer, nullable=True)
    rol = db.Column(db.Enum('jugador', 'entrenador', name='rol_enum'), default='jugador', nullable=False)
    es_capitan = db.Column(db.Boolean, default=False)
    posicion_id = db.Column(db.Integer, db.ForeignKey('posiciones.id'), nullable=True)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    
    # Relaciones
    posicion = relationship('Posicion', back_populates='jugadores')
    equipo = relationship('Equipo', back_populates='jugadores')
    eventos = relationship('Evento', back_populates='jugador')

# ---------------------------
# Tabla de convocados
# ---------------------------
class Convocado(db.Model):
    __tablename__ = 'convocados'
    id = db.Column(db.Integer, primary_key=True)
    partido_id = db.Column(db.Integer, db.ForeignKey('partidos.id'), nullable=False)
    jugador_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'), nullable=False)
    
    # Relaciones
    partido = relationship('Partido', back_populates='convocados')
    jugador = relationship('Jugador')

# ---------------------------
# Tabla de categorías de eventos
# ---------------------------
class CategoriaEvento(db.Model):
    __tablename__ = 'categorias_evento'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    
    # Relaciones
    tipos_evento = relationship('TipoEvento', back_populates='categoria_evento')


# ---------------------------
# Tabla de tipo de eventos
# ---------------------------
class TipoEvento(db.Model):
    __tablename__ = 'tipo_evento'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    es_equipo = db.Column(db.Boolean, nullable=False, default=False)
    es_global = db.Column(db.Boolean, nullable=False, default=False)
    es_jugador = db.Column(db.Boolean, nullable=False, default=False)
    categoria_evento_id = db.Column(db.Integer, db.ForeignKey('categorias_evento.id'), nullable=True)
    
    # Relaciones
    eventos = relationship('Evento', back_populates='tipo_evento')
    categoria_evento = relationship('CategoriaEvento', back_populates='tipos_evento')


# ---------------------------
# Tabla de eventos
# ---------------------------
class Evento(db.Model):
    __tablename__ = 'eventos'
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id'), nullable=False)
    tiempo_seg = db.Column(db.Integer, nullable=False)
    tipo_evento_id = db.Column(db.Integer, db.ForeignKey('tipo_evento.id'), nullable=True)
    evento_personalizado_id = db.Column(db.Integer, db.ForeignKey('evento_personalizado.id'), nullable=True)
    partido_id = db.Column(db.Integer, db.ForeignKey('partidos.id'), nullable=False)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=True)
    jugador_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'), nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    
    # Campos específicos para eventos de tiro
    zona_tiro = db.Column(db.String(20), nullable=True)
    resultado_tiro = db.Column(db.String(20), nullable=True)
    
    # Relaciones
    video = relationship('Video', back_populates='eventos')
    tipo_evento = relationship('TipoEvento', back_populates='eventos')
    evento_personalizado = relationship('EventoPersonalizado')
    partido = relationship('Partido')
    equipo = relationship('Equipo', back_populates='eventos')
    jugador = relationship('Jugador', back_populates='eventos')
    
    # Constraint para asegurar que solo uno de los dos tipos de evento esté presente
    __table_args__ = (
        db.CheckConstraint(
            "(tipo_evento_id IS NOT NULL AND evento_personalizado_id IS NULL) OR "
            "(tipo_evento_id IS NULL AND evento_personalizado_id IS NOT NULL)",
            name='ck_un_solo_tipo_evento'
        ),
    )

# ---------------------------
# Tabla de jugadores en pista
# ---------------------------
class JugadorEnPista(db.Model):
    __tablename__ = 'jugadores_en_pista'
    id = db.Column(db.Integer, primary_key=True)
    partido_id = db.Column(db.Integer, db.ForeignKey('partidos.id'), nullable=False)
    jugador_id = db.Column(db.Integer, db.ForeignKey('jugadores.id'), nullable=False)
    equipo_id = db.Column(db.Integer, db.ForeignKey('equipos.id'), nullable=False)
    
    # Relaciones
    partido = relationship('Partido', backref='jugadores_pista')
    jugador = relationship('Jugador')
    equipo = relationship('Equipo')
    
    __table_args__ = (
        UniqueConstraint('partido_id', 'jugador_id', name='uq_jugador_pista'),
    )

# ---------------------------
# Tabla de eventos personalizados por usuario
# ---------------------------
class EventoPersonalizado(db.Model):
    __tablename__ = 'evento_personalizado'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    categoria_evento_id = db.Column(db.Integer, db.ForeignKey('categorias_evento.id', ondelete="CASCADE"), nullable=False)

    es_equipo = db.Column(db.Boolean, default=False)
    es_global = db.Column(db.Boolean, default=False)
    es_jugador = db.Column(db.Boolean, default=True)
    # Nuevo campo para estadísticas en tiempo real
    estadistica_tipo = db.Column(db.Enum('gol', 'falta', 'perdida', 'recuperacion', name='estadistica_tipo_enum'), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    user = relationship('User')
    categoria_evento = relationship('CategoriaEvento')

    __table_args__ = (
        UniqueConstraint('user_id', 'nombre', name='uq_evento_personalizado_usuario'),
    )

    def asignar_tipo_por_categoria(self):
        nombre_categoria = (self.categoria_evento.nombre or "").lower()
        if nombre_categoria == "táctica":
            self.es_equipo = True
            self.es_global = False
            self.es_jugador = False
        elif nombre_categoria == "global":
            self.es_equipo = False
            self.es_global = True
            self.es_jugador = False
        else:
            self.es_equipo = False
            self.es_global = False
            self.es_jugador = True


# ---------------------------
# Tabla de eventos seleccionados por vídeo (por usuario)
# ---------------------------
class EventosSeleccionadosVideo(db.Model):
    __tablename__ = 'eventos_seleccionados_video'
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id', ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    tipo_evento_id = db.Column(db.Integer, db.ForeignKey('tipo_evento.id', ondelete="CASCADE"), nullable=True)
    evento_personalizado_id = db.Column(db.Integer, db.ForeignKey('evento_personalizado.id', ondelete="CASCADE"), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp())

    video = relationship('Video')
    user = relationship('User')
    tipo_evento = relationship('TipoEvento')
    evento_personalizado = relationship('EventoPersonalizado')

    __table_args__ = (
        UniqueConstraint('video_id', 'user_id', 'tipo_evento_id', 'evento_personalizado_id',
                         name='uq_eventos_seleccionados_video'),
        db.CheckConstraint(
            "(tipo_evento_id IS NOT NULL AND evento_personalizado_id IS NULL) OR "
            "(tipo_evento_id IS NULL AND evento_personalizado_id IS NOT NULL)",
            name='ck_un_solo_tipo_evento'
        ),
    )

# ---------------------------
# Tabla de tareas de análisis automático
# ---------------------------

class Tarea(db.Model):
    __tablename__ = 'tareas'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey('videos.id', ondelete="CASCADE"), nullable=False)
    fecha_creacion = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    fecha_completada = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.Integer, default=False)
    progreso = db.Column(db.Float, default=0.0)

    user = relationship('User')

    
# ---------------------------
# Tabla de descargas de análisis automático
# ---------------------------

from sqlalchemy import UniqueConstraint

class Descarga(db.Model):
    __tablename__ = 'descargas'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    tarea_id = db.Column(db.Integer, db.ForeignKey('tareas.id', ondelete="CASCADE"), nullable=False)
    fecha_creacion = db.Column(db.DateTime, server_default=db.func.current_timestamp())
    fecha_completada = db.Column(db.DateTime, nullable=True)
    estado = db.Column(db.Integer, default=False)
    progreso = db.Column(db.Float, default=0.0)

    user = relationship('User')

    __table_args__ = (UniqueConstraint('tarea_id', name='_unique_tarea'),)

# ---------------------------
# Tabla de jugadores en un tracking
# ---------------------------

class JugadorTracking(db.Model):
    __tablename__ = 'jugadores_tracking'
    tarea_id = db.Column(db.Integer, db.ForeignKey('tareas.id', ondelete="CASCADE"), primary_key=True)
    jugador_id = db.Column(db.Integer, db.ForeignKey('jugadores.id', ondelete="CASCADE"), primary_key=True)
    id = db.Column(db.Integer, primary_key=True)

