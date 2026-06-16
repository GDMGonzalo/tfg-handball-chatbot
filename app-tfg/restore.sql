-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 04-09-2025 a las 21:24:57
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `mikel`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `categorias`
--

CREATE DATABASE IF NOT EXISTS `mikel` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `mikel`;

CREATE TABLE `categorias` (
  `id` int(11) NOT NULL,
  `nombre` varchar(50) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `categorias`
--

INSERT INTO `categorias` (`id`, `nombre`, `descripcion`, `created_at`) VALUES
(1, 'Benjamines', 'Categoría para niños y niñas de hasta 10 años.', '2025-09-04 19:24:35'),
(2, 'Alevines', 'Categoría para niños y niñas de 11 y 12 años.', '2025-09-04 19:24:35'),
(3, 'Infantiles', 'Categoría para jugadores de 13 y 14 años.', '2025-09-04 19:24:35'),
(4, 'Cadetes', 'Categoría para jugadores de 15 y 16 años.', '2025-09-04 19:24:35'),
(5, 'Juveniles', 'Categoría para jugadores de 17 y 18 años.', '2025-09-04 19:24:35'),
(6, 'Senior', 'Categoría para mayores de 18 años.', '2025-09-04 19:24:35');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `categorias_evento`
--

CREATE TABLE `categorias_evento` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `categorias_evento`
--

INSERT INTO `categorias_evento` (`id`, `nombre`) VALUES
(7, '7 Metros'),
(11, 'Asistencias'),
(10, 'Defensa'),
(2, 'Falta'),
(5, 'Global'),
(8, 'Paradas'),
(9, 'Perdidas'),
(3, 'Sanción'),
(4, 'Sustitución'),
(6, 'Táctica'),
(1, 'Tiro');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `convocados`
--

CREATE TABLE `convocados` (
  `id` int(11) NOT NULL,
  `partido_id` int(11) NOT NULL,
  `jugador_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `descargas`
--

CREATE TABLE `descargas` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `tarea_id` int(11) NOT NULL,
  `fecha_creacion` datetime DEFAULT current_timestamp(),
  `fecha_completada` datetime DEFAULT NULL,
  `estado` int(11) DEFAULT 0,
  `progreso` float DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `equipos`
--

CREATE TABLE `equipos` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `tipo` enum('masculino','femenino','mixto') NOT NULL DEFAULT 'mixto',
  `user_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `equipo_liga`
--

CREATE TABLE `equipo_liga` (
  `id` int(11) NOT NULL,
  `equipo_id` int(11) NOT NULL,
  `liga_id` int(11) NOT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `eventos`
--

CREATE TABLE `eventos` (
  `id` int(11) NOT NULL,
  `video_id` int(11) NOT NULL,
  `tiempo_seg` int(11) NOT NULL,
  `tipo_evento_id` int(11) DEFAULT NULL,
  `partido_id` int(11) NOT NULL,
  `equipo_id` int(11) DEFAULT NULL,
  `jugador_id` int(11) DEFAULT NULL,
  `descripcion` text DEFAULT NULL,
  `evento_personalizado_id` int(11) DEFAULT NULL,
  `zona_tiro` varchar(20) DEFAULT NULL,
  `resultado_tiro` varchar(20) DEFAULT NULL
) ;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `eventos_seleccionados_video`
--

CREATE TABLE `eventos_seleccionados_video` (
  `id` int(11) NOT NULL,
  `video_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `tipo_evento_id` int(11) DEFAULT NULL,
  `evento_personalizado_id` int(11) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `evento_personalizado`
--

CREATE TABLE `evento_personalizado` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `categoria_evento_id` int(11) NOT NULL,
  `es_equipo` tinyint(1) DEFAULT 0,
  `es_global` tinyint(1) DEFAULT 0,
  `es_jugador` tinyint(1) DEFAULT 1,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `estadistica_tipo` enum('gol','falta','perdida','recuperacion') DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `jugadores`
--

CREATE TABLE `jugadores` (
  `id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `apellido` varchar(100) NOT NULL,
  `dorsal` int(11) DEFAULT NULL,
  `rol` enum('jugador','entrenador') NOT NULL DEFAULT 'jugador',
  `equipo_id` int(11) NOT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `es_capitan` tinyint(1) DEFAULT 0,
  `posicion_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `jugadores_en_pista`
--

CREATE TABLE `jugadores_en_pista` (
  `id` int(11) NOT NULL,
  `partido_id` int(11) NOT NULL,
  `jugador_id` int(11) NOT NULL,
  `equipo_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `jugadores_tracking`
--

CREATE TABLE `jugadores_tracking` (
  `tarea_id` int(11) NOT NULL,
  `jugador_id` int(11) NOT NULL,
  `id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `liga`
--

CREATE TABLE `liga` (
  `id` int(11) NOT NULL,
  `temporada_id` int(11) NOT NULL,
  `categoria_id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `partidos`
--

CREATE TABLE `partidos` (
  `id` int(11) NOT NULL,
  `liga_id` int(11) NOT NULL,
  `fecha_hora` datetime NOT NULL,
  `equipo_local_id` int(11) DEFAULT NULL,
  `equipo_visitante_id` int(11) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `goles_local` int(11) DEFAULT NULL,
  `goles_visitante` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `posiciones`
--

CREATE TABLE `posiciones` (
  `id` int(11) NOT NULL,
  `nombre` varchar(50) NOT NULL,
  `color` varchar(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `posiciones`
--

INSERT INTO `posiciones` (`id`, `nombre`, `color`) VALUES
(1, 'portero', '#1E90FF'),
(2, 'lateral', '#FF8C00'),
(3, 'central', '#FFD700'),
(4, 'pivote', '#DC143C'),
(5, 'extremo', '#32CD32');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tareas`
--

CREATE TABLE `tareas` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `video_id` int(11) NOT NULL,
  `fecha_creacion` datetime DEFAULT current_timestamp(),
  `fecha_completada` datetime DEFAULT NULL,
  `estado` int(11) DEFAULT NULL,
  `progreso` float DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `temporada`
--

CREATE TABLE `temporada` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `nombre` varchar(100) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tipo_evento`
--

CREATE TABLE `tipo_evento` (
  `id` int(11) NOT NULL,
  `nombre` varchar(50) NOT NULL,
  `es_equipo` tinyint(1) NOT NULL DEFAULT 0,
  `es_global` tinyint(1) NOT NULL DEFAULT 0,
  `es_jugador` tinyint(1) NOT NULL DEFAULT 0,
  `categoria_evento_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `tipo_evento`
--

INSERT INTO `tipo_evento` (`id`, `nombre`, `es_equipo`, `es_global`, `es_jugador`, `categoria_evento_id`) VALUES
(4, 'Falta cometida', 0, 0, 1, 2),
(5, 'Exclusión 2 minutos', 0, 0, 1, 3),
(6, 'Entra en pista', 0, 0, 1, 4),
(7, 'Sale de pista', 0, 0, 1, 4),
(8, 'Inicio primer tiempo', 0, 1, 0, 5),
(9, 'Fin primer tiempo', 0, 1, 0, 5),
(10, 'Tiempo muerto', 1, 0, 0, 6),
(11, 'Fin sanción 2 minutos', 0, 0, 1, 3),
(12, 'Falta Recibida', 0, 0, 1, 2),
(13, 'Gol 7 metros', 0, 0, 1, 7),
(14, 'Tiro fallido 7 metros', 0, 0, 1, 7),
(15, 'Tiro parado 7 metros', 0, 0, 1, 7),
(16, 'Comete 7 metros', 0, 0, 1, 2),
(17, 'Inicio segunda parte', 0, 1, 0, 5),
(18, 'Fin segunda parte', 0, 1, 0, 5),
(19, 'Inicio prórroga', 0, 1, 0, 5),
(20, 'Fin prórroga', 0, 1, 0, 5),
(23, 'Final del partido', 0, 1, 0, 5),
(28, 'Parada', 0, 0, 1, 8),
(29, 'Parada 7 metros', 0, 0, 1, 8),
(30, 'Pérdida', 0, 0, 1, 9),
(31, 'Recuperación', 0, 0, 1, 10),
(32, 'Asistencia de gol', 0, 0, 0, 11),
(33, 'Tarjeta Roja', 0, 0, 1, 3),
(34, 'Tarjeta Amarilla', 0, 0, 1, 3),
(35, 'Porteria Vacia (7 J.)', 1, 0, 0, 6),
(36, 'Porteria Vacia (6 J.)', 1, 0, 0, 6),
(37, 'Tiro', 0, 0, 1, 1),
(38, 'Tiro bloqueado', 0, 0, 1, 10),
(39, 'Sustitucion ilegal', 0, 0, 1, 3),
(40, 'Asistencia para Fly', 0, 0, 1, 11);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `created_at` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `users`
--

INSERT INTO `users` (`id`, `username`, `password`, `created_at`) VALUES
(1, 'demo', 'sha256$demo$5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', '2025-09-04 19:24:35');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `videos`
--

CREATE TABLE `videos` (
  `id` int(11) NOT NULL,
  `partido_id` int(11) NOT NULL,
  `filename` varchar(255) NOT NULL,
  `uploaded_at` datetime DEFAULT current_timestamp(),
  `duracion_segundos` int(11) NOT NULL,
  `fps` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura Stand-in para la vista `vista_convocados`
-- (Véase abajo para la vista actual)
--
CREATE TABLE `vista_convocados` (
`jugador_id` int(11)
,`jugador_nombre` varchar(100)
,`jugador_apellido` varchar(100)
,`jugador_dorsal` int(11)
,`jugador_rol` enum('jugador','entrenador')
,`partido_id` int(11)
,`equipo_id` int(11)
,`equipo_nombre` varchar(100)
,`tipo_equipo` varchar(9)
);

-- --------------------------------------------------------

--
-- Estructura Stand-in para la vista `v_estadisticas_jugador_partido`
-- (Véase abajo para la vista actual)
--
CREATE TABLE `v_estadisticas_jugador_partido` (
`partido_id` int(11)
,`fecha_partido` datetime
,`equipo_local` varchar(100)
,`equipo_visitante` varchar(100)
,`jugador_id` int(11)
,`jugador` varchar(216)
,`equipo_jugador` varchar(100)
,`tiros_campo` varbinary(47)
,`tiros_7m` varbinary(47)
,`perdidas` decimal(22,0)
,`recuperaciones` decimal(22,0)
,`faltas_cometidas` decimal(22,0)
,`faltas_recibidas` decimal(22,0)
,`asistencias` decimal(22,0)
);

-- --------------------------------------------------------

--
-- Estructura para la vista `vista_convocados`
--
DROP TABLE IF EXISTS `vista_convocados`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vista_convocados`  AS SELECT `j`.`id` AS `jugador_id`, `j`.`nombre` AS `jugador_nombre`, `j`.`apellido` AS `jugador_apellido`, `j`.`dorsal` AS `jugador_dorsal`, `j`.`rol` AS `jugador_rol`, `c`.`partido_id` AS `partido_id`, `j`.`equipo_id` AS `equipo_id`, `e`.`nombre` AS `equipo_nombre`, CASE WHEN `p`.`equipo_local_id` = `j`.`equipo_id` THEN 'local' WHEN `p`.`equipo_visitante_id` = `j`.`equipo_id` THEN 'visitante' ELSE 'otro' END AS `tipo_equipo` FROM (((`convocados` `c` join `jugadores` `j` on(`c`.`jugador_id` = `j`.`id`)) join `partidos` `p` on(`c`.`partido_id` = `p`.`id`)) join `equipos` `e` on(`j`.`equipo_id` = `e`.`id`)) ;

-- --------------------------------------------------------

--
-- Estructura para la vista `v_estadisticas_jugador_partido`
--
DROP TABLE IF EXISTS `v_estadisticas_jugador_partido`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `v_estadisticas_jugador_partido`  AS SELECT `p`.`id` AS `partido_id`, `p`.`fecha_hora` AS `fecha_partido`, `e_local`.`nombre` AS `equipo_local`, `e_visitante`.`nombre` AS `equipo_visitante`, `j`.`id` AS `jugador_id`, concat(`j`.`nombre`,' ',`j`.`apellido`,convert(ifnull(concat(' (#',`j`.`dorsal`,')'),'') using utf8mb4)) AS `jugador`, `eq`.`nombre` AS `equipo_jugador`, concat(sum(case when `te`.`id` = 37 and `ev`.`resultado_tiro` = 'gol' then 1 else 0 end),'/',sum(case when `te`.`id` = 37 then 1 else 0 end)) AS `tiros_campo`, concat(sum(case when `te`.`id` = 13 then 1 else 0 end),'/',sum(case when `te`.`id` = 13 then 1 else 0 end)) AS `tiros_7m`, sum(case when `te`.`id` = 30 then 1 else 0 end) AS `perdidas`, sum(case when `te`.`id` = 31 then 1 else 0 end) AS `recuperaciones`, sum(case when `te`.`id` = 4 then 1 else 0 end) AS `faltas_cometidas`, sum(case when `te`.`id` = 5 then 1 else 0 end) AS `faltas_recibidas`, sum(case when `te`.`id` = 32 then 1 else 0 end) AS `asistencias` FROM ((((((`eventos` `ev` join `tipo_evento` `te` on(`ev`.`tipo_evento_id` = `te`.`id`)) join `partidos` `p` on(`ev`.`partido_id` = `p`.`id`)) join `equipos` `e_local` on(`p`.`equipo_local_id` = `e_local`.`id`)) join `equipos` `e_visitante` on(`p`.`equipo_visitante_id` = `e_visitante`.`id`)) join `jugadores` `j` on(`ev`.`jugador_id` = `j`.`id`)) join `equipos` `eq` on(`j`.`equipo_id` = `eq`.`id`)) WHERE `ev`.`jugador_id` is not null GROUP BY `p`.`id`, `j`.`id` ORDER BY `p`.`fecha_hora` DESC, `eq`.`nombre` ASC, concat(`j`.`nombre`,' ',`j`.`apellido`,convert(ifnull(concat(' (#',`j`.`dorsal`,')'),'') using utf8mb4)) ASC, sum(case when `te`.`id` = 32 then 1 else 0 end) ASC ;

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `categorias`
--
ALTER TABLE `categorias`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `nombre` (`nombre`);

--
-- Indices de la tabla `categorias_evento`
--
ALTER TABLE `categorias_evento`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `nombre` (`nombre`);

--
-- Indices de la tabla `convocados`
--
ALTER TABLE `convocados`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uniq_partido_jugador` (`partido_id`,`jugador_id`),
  ADD KEY `idx_jugador_id` (`jugador_id`);

--
-- Indices de la tabla `descargas`
--
ALTER TABLE `descargas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_descargas_user` (`user_id`),
  ADD KEY `fk_descargas_tarea` (`tarea_id`);

--
-- Indices de la tabla `equipos`
--
ALTER TABLE `equipos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_equipos_user_id` (`user_id`);

--
-- Indices de la tabla `equipo_liga`
--
ALTER TABLE `equipo_liga`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_equipo_liga` (`equipo_id`,`liga_id`),
  ADD KEY `equipo_liga_ibfk_liga` (`liga_id`);

--
-- Indices de la tabla `eventos`
--
ALTER TABLE `eventos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_video_id` (`video_id`),
  ADD KEY `idx_tipo_evento_id` (`tipo_evento_id`),
  ADD KEY `idx_partido_id` (`partido_id`),
  ADD KEY `idx_equipo_id` (`equipo_id`),
  ADD KEY `idx_jugador_id` (`jugador_id`),
  ADD KEY `fk_eventos_evento_personalizado` (`evento_personalizado_id`);

--
-- Indices de la tabla `eventos_seleccionados_video`
--
ALTER TABLE `eventos_seleccionados_video`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_video_evento_usuario` (`video_id`,`user_id`,`tipo_evento_id`,`evento_personalizado_id`),
  ADD KEY `fk_esv_user` (`user_id`),
  ADD KEY `fk_esv_tipo_evento` (`tipo_evento_id`),
  ADD KEY `fk_esv_evento_personalizado` (`evento_personalizado_id`);

--
-- Indices de la tabla `evento_personalizado`
--
ALTER TABLE `evento_personalizado`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_evento_personalizado_usuario` (`user_id`,`nombre`),
  ADD KEY `categoria_evento_id` (`categoria_evento_id`);

--
-- Indices de la tabla `jugadores`
--
ALTER TABLE `jugadores`
  ADD PRIMARY KEY (`id`),
  ADD KEY `equipo_id` (`equipo_id`),
  ADD KEY `fk_posicion` (`posicion_id`);

--
-- Indices de la tabla `jugadores_en_pista`
--
ALTER TABLE `jugadores_en_pista`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_jugador_pista_entrada` (`partido_id`,`jugador_id`),
  ADD KEY `jugador_id` (`jugador_id`),
  ADD KEY `equipo_id` (`equipo_id`);

--
-- Indices de la tabla `jugadores_tracking`
--
ALTER TABLE `jugadores_tracking`
  ADD PRIMARY KEY (`tarea_id`,`jugador_id`,`id`),
  ADD KEY `fk_jugador` (`jugador_id`);

--
-- Indices de la tabla `liga`
--
ALTER TABLE `liga`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_temporada_liga_nombre` (`temporada_id`,`nombre`),
  ADD KEY `liga_ibfk_categoria` (`categoria_id`);

--
-- Indices de la tabla `partidos`
--
ALTER TABLE `partidos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_equipo_local_id` (`equipo_local_id`),
  ADD KEY `idx_equipo_visitante_id` (`equipo_visitante_id`),
  ADD KEY `partidos_ibfk_liga` (`liga_id`);

--
-- Indices de la tabla `posiciones`
--
ALTER TABLE `posiciones`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `nombre` (`nombre`);

--
-- Indices de la tabla `tareas`
--
ALTER TABLE `tareas`
  ADD PRIMARY KEY (`id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `video_id` (`video_id`);

--
-- Indices de la tabla `temporada`
--
ALTER TABLE `temporada`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_user_proyecto_nombre` (`user_id`,`nombre`);

--
-- Indices de la tabla `tipo_evento`
--
ALTER TABLE `tipo_evento`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_nombre` (`nombre`),
  ADD KEY `fk_categoria_evento` (`categoria_evento_id`);

--
-- Indices de la tabla `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- Indices de la tabla `videos`
--
ALTER TABLE `videos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_partido_id` (`partido_id`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `categorias`
--
ALTER TABLE `categorias`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT de la tabla `categorias_evento`
--
ALTER TABLE `categorias_evento`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT de la tabla `convocados`
--
ALTER TABLE `convocados`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de la tabla `descargas`
--
ALTER TABLE `descargas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=17;

--
-- AUTO_INCREMENT de la tabla `equipos`
--
ALTER TABLE `equipos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de la tabla `equipo_liga`
--
ALTER TABLE `equipo_liga`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `eventos`
--
ALTER TABLE `eventos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `eventos_seleccionados_video`
--
ALTER TABLE `eventos_seleccionados_video`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `evento_personalizado`
--
ALTER TABLE `evento_personalizado`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `jugadores`
--
ALTER TABLE `jugadores`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de la tabla `jugadores_en_pista`
--
ALTER TABLE `jugadores_en_pista`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de la tabla `liga`
--
ALTER TABLE `liga`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de la tabla `partidos`
--
ALTER TABLE `partidos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- AUTO_INCREMENT de la tabla `posiciones`
--
ALTER TABLE `posiciones`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT de la tabla `tareas`
--
ALTER TABLE `tareas`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=58;

--
-- AUTO_INCREMENT de la tabla `temporada`
--
ALTER TABLE `temporada`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `tipo_evento`
--
ALTER TABLE `tipo_evento`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=41;

--
-- AUTO_INCREMENT de la tabla `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de la tabla `videos`
--
ALTER TABLE `videos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `convocados`
--
ALTER TABLE `convocados`
  ADD CONSTRAINT `convocados_ibfk_1` FOREIGN KEY (`partido_id`) REFERENCES `partidos` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `convocados_ibfk_2` FOREIGN KEY (`jugador_id`) REFERENCES `jugadores` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `descargas`
--
ALTER TABLE `descargas`
  ADD CONSTRAINT `fk_descargas_tarea` FOREIGN KEY (`tarea_id`) REFERENCES `tareas` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_descargas_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `equipos`
--
ALTER TABLE `equipos`
  ADD CONSTRAINT `fk_equipos_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `equipo_liga`
--
ALTER TABLE `equipo_liga`
  ADD CONSTRAINT `equipo_liga_ibfk_equipo` FOREIGN KEY (`equipo_id`) REFERENCES `equipos` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `equipo_liga_ibfk_liga` FOREIGN KEY (`liga_id`) REFERENCES `liga` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `eventos`
--
ALTER TABLE `eventos`
  ADD CONSTRAINT `eventos_ibfk_equipo` FOREIGN KEY (`equipo_id`) REFERENCES `equipos` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `eventos_ibfk_jugador` FOREIGN KEY (`jugador_id`) REFERENCES `jugadores` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `eventos_ibfk_partido` FOREIGN KEY (`partido_id`) REFERENCES `partidos` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `eventos_ibfk_tipo_evento` FOREIGN KEY (`tipo_evento_id`) REFERENCES `tipo_evento` (`id`),
  ADD CONSTRAINT `eventos_ibfk_video` FOREIGN KEY (`video_id`) REFERENCES `videos` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_eventos_evento_personalizado` FOREIGN KEY (`evento_personalizado_id`) REFERENCES `evento_personalizado` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `eventos_seleccionados_video`
--
ALTER TABLE `eventos_seleccionados_video`
  ADD CONSTRAINT `fk_esv_evento_personalizado` FOREIGN KEY (`evento_personalizado_id`) REFERENCES `evento_personalizado` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_esv_tipo_evento` FOREIGN KEY (`tipo_evento_id`) REFERENCES `tipo_evento` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_esv_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_esv_video` FOREIGN KEY (`video_id`) REFERENCES `videos` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `evento_personalizado`
--
ALTER TABLE `evento_personalizado`
  ADD CONSTRAINT `evento_personalizado_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `evento_personalizado_ibfk_2` FOREIGN KEY (`categoria_evento_id`) REFERENCES `categorias_evento` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `jugadores`
--
ALTER TABLE `jugadores`
  ADD CONSTRAINT `fk_posicion` FOREIGN KEY (`posicion_id`) REFERENCES `posiciones` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `jugadores_ibfk_1` FOREIGN KEY (`equipo_id`) REFERENCES `equipos` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `jugadores_en_pista`
--
ALTER TABLE `jugadores_en_pista`
  ADD CONSTRAINT `jugadores_en_pista_ibfk_1` FOREIGN KEY (`partido_id`) REFERENCES `partidos` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `jugadores_en_pista_ibfk_2` FOREIGN KEY (`jugador_id`) REFERENCES `jugadores` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `jugadores_en_pista_ibfk_3` FOREIGN KEY (`equipo_id`) REFERENCES `equipos` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `jugadores_tracking`
--
ALTER TABLE `jugadores_tracking`
  ADD CONSTRAINT `fk_jugador` FOREIGN KEY (`jugador_id`) REFERENCES `jugadores` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_tarea` FOREIGN KEY (`tarea_id`) REFERENCES `tareas` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `liga`
--
ALTER TABLE `liga`
  ADD CONSTRAINT `liga_ibfk_categoria` FOREIGN KEY (`categoria_id`) REFERENCES `categorias` (`id`),
  ADD CONSTRAINT `liga_ibfk_temporada` FOREIGN KEY (`temporada_id`) REFERENCES `temporada` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `partidos`
--
ALTER TABLE `partidos`
  ADD CONSTRAINT `partidos_ibfk_2` FOREIGN KEY (`equipo_local_id`) REFERENCES `equipos` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `partidos_ibfk_3` FOREIGN KEY (`equipo_visitante_id`) REFERENCES `equipos` (`id`) ON DELETE SET NULL,
  ADD CONSTRAINT `partidos_ibfk_liga` FOREIGN KEY (`liga_id`) REFERENCES `liga` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `tareas`
--
ALTER TABLE `tareas`
  ADD CONSTRAINT `tareas_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `tareas_ibfk_2` FOREIGN KEY (`video_id`) REFERENCES `videos` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `temporada`
--
ALTER TABLE `temporada`
  ADD CONSTRAINT `temporada_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `tipo_evento`
--
ALTER TABLE `tipo_evento`
  ADD CONSTRAINT `fk_categoria_evento` FOREIGN KEY (`categoria_evento_id`) REFERENCES `categorias_evento` (`id`) ON DELETE SET NULL;

--
-- Filtros para la tabla `videos`
--
ALTER TABLE `videos`
  ADD CONSTRAINT `videos_ibfk_1` FOREIGN KEY (`partido_id`) REFERENCES `partidos` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
