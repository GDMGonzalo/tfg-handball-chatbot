from sqlalchemy import text
from models import db


class ChatbotQueries:
    def __init__(self, user_id: int):
        self.user_id = user_id


    def _relation_exists(self, relation_name: str) -> bool:
        stmt = text("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = :relation_name
        """)
        try:
            row = db.session.execute(stmt, {"relation_name": relation_name}).fetchone()
            return bool(row and row[0])
        except Exception:
            return False

    def _columns(self, relation_name: str) -> set[str]:
        stmt = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = :relation_name
        """)
        try:
            rows = db.session.execute(stmt, {"relation_name": relation_name}).fetchall()
            return {str(row[0]) for row in rows}
        except Exception:
            return set()

    @staticmethod
    def _pct(numerator: float, denominator: float) -> float:
        return round((numerator / denominator) * 100, 2) if denominator else 0.0

    @staticmethod
    def _num(row, key: str, default: float = 0.0) -> float:
        if row is None:
            return default
        try:
            value = row._mapping.get(key, default)
        except Exception:
            value = default
        return float(value or 0)

    @staticmethod
    def _int_or_float(value: float):
        return int(value) if float(value).is_integer() else value


    def get_all_team_names(self):
        stmt = text("""
            SELECT nombre
            FROM equipos
            WHERE user_id = :user_id
            ORDER BY nombre ASC
        """)
        rows = db.session.execute(stmt, {"user_id": self.user_id}).fetchall()
        return [row[0] for row in rows]

    def get_teams_with_matches(self, min_matches: int = 1) -> list:
        stmt = text("""
            WITH team_matches AS (
                SELECT e.nombre, COUNT(p.id) AS matches
                FROM equipos e
                LEFT JOIN partidos p ON (p.equipo_local_id = e.id OR p.equipo_visitante_id = e.id)
                WHERE e.user_id = :user_id
                GROUP BY e.id
            )
            SELECT nombre FROM team_matches WHERE matches >= :min_matches
            ORDER BY nombre
        """)
        rows = db.session.execute(stmt, {"user_id": self.user_id, "min_matches": min_matches}).fetchall()
        return [row[0] for row in rows]


    def get_all_player_names(self):
        stmt = text("""
            SELECT DISTINCT v.jugador
            FROM v_estadisticas_jugador_partido v
            JOIN jugadores j ON v.jugador_id = j.id
            JOIN equipos e ON j.equipo_id = e.id
            WHERE e.user_id = :user_id
            ORDER BY v.jugador ASC
        """)
        rows = db.session.execute(stmt, {"user_id": self.user_id}).fetchall()
        return [row[0] for row in rows]

    def get_players_with_stats(self, min_matches: int = 1) -> list:
        stmt = text("""
            SELECT v.jugador
            FROM v_estadisticas_jugador_partido v
            JOIN jugadores j ON v.jugador_id = j.id
            JOIN equipos e ON j.equipo_id = e.id
            WHERE e.user_id = :user_id
            GROUP BY v.jugador_id, v.jugador
            HAVING COUNT(DISTINCT v.partido_id) >= :min_matches
            ORDER BY v.jugador ASC
        """)
        rows = db.session.execute(
            stmt,
            {"user_id": self.user_id, "min_matches": min_matches}
        ).fetchall()
        return [row[0] for row in rows]


    def get_player_snapshot(self, player_name: str, context: str | None = None):
        filters = [
            "e.user_id = :user_id",
            "v.jugador = :player_name",
        ]
        params = {
            "user_id": self.user_id,
            "player_name": player_name,
        }

        if context == "home":
            filters.append("v.equipo_jugador = v.equipo_local")
        elif context == "away":
            filters.append("v.equipo_jugador = v.equipo_visitante")

        where_clause = " AND ".join(filters)

        stmt = text(f"""
            SELECT
                v.jugador_id AS player_id,
                v.jugador AS player_name,
                MAX(v.equipo_jugador) AS team_name,
                COUNT(DISTINCT v.partido_id) AS matches,
                COALESCE(SUM(COALESCE(v.tiros_campo, 0)), 0) AS goals_field,
                COALESCE(SUM(COALESCE(v.tiros_7m, 0)), 0) AS goals_7m,
                COALESCE(SUM(COALESCE(v.perdidas, 0)), 0) AS losses,
                COALESCE(SUM(COALESCE(v.recuperaciones, 0)), 0) AS recoveries,
                COALESCE(SUM(COALESCE(v.faltas_cometidas, 0)), 0) AS fouls_committed,
                COALESCE(SUM(COALESCE(v.faltas_recibidas, 0)), 0) AS fouls_received,
                COALESCE(SUM(COALESCE(v.asistencias, 0)), 0) AS assists,
                COALESCE(SUM(CASE WHEN v.equipo_jugador = v.equipo_local THEN 1 ELSE 0 END), 0) AS home_matches,
                COALESCE(SUM(CASE WHEN v.equipo_jugador = v.equipo_visitante THEN 1 ELSE 0 END), 0) AS away_matches
            FROM v_estadisticas_jugador_partido v
            JOIN jugadores j ON v.jugador_id = j.id
            JOIN equipos e ON j.equipo_id = e.id
            WHERE {where_clause}
        """)

        row = db.session.execute(stmt, params).fetchone()

        if not row:
            return {
                "player_id": None,
                "player_name": player_name,
                "team_name": None,
                "matches": 0,
                "home_matches": 0,
                "away_matches": 0,
                "goals": {"field": 0, "seven_m": 0, "total": 0, "avg_total": 0.0, "avg_field": 0.0, "avg_seven_m": 0.0},
                "assists": {"total": 0, "avg": 0.0},
                "recoveries": {"total": 0, "avg": 0.0},
                "losses": {"total": 0, "avg": 0.0},
                "fouls_committed": {"total": 0, "avg": 0.0},
                "fouls_received": {"total": 0, "avg": 0.0},
            }

        matches = int(row[3] or 0)
        goals_field = int(row[4] or 0)
        goals_7m = int(row[5] or 0)
        goals_total = goals_field + goals_7m

        def _avg(value: int) -> float:
            return round(value / matches, 2) if matches else 0.0

        return {
            "player_id": int(row[0]) if row[0] is not None else None,
            "player_name": row[1],
            "team_name": row[2],
            "matches": matches,
            "home_matches": int(row[11] or 0),
            "away_matches": int(row[12] or 0),
            "goals": {
                "field": goals_field,
                "seven_m": goals_7m,
                "total": goals_total,
                "avg_total": _avg(goals_total),
                "avg_field": _avg(goals_field),
                "avg_seven_m": _avg(goals_7m),
            },
            "assists": {"total": int(row[10] or 0), "avg": _avg(int(row[10] or 0))},
            "recoveries": {"total": int(row[7] or 0), "avg": _avg(int(row[7] or 0))},
            "losses": {"total": int(row[6] or 0), "avg": _avg(int(row[6] or 0))},
            "fouls_committed": {"total": int(row[8] or 0), "avg": _avg(int(row[8] or 0))},
            "fouls_received": {"total": int(row[9] or 0), "avg": _avg(int(row[9] or 0))},
        }


    def get_ranked_players(self, metric="goals_total", player_names=None, team_names=None, descending=True, min_matches=1, context=None):
        if player_names:
            all_names = self.get_all_player_names()
            candidate_names = [p for p in player_names if p in all_names]
        elif team_names:
            params = {"user_id": self.user_id}
            placeholders = []
            for i, team in enumerate(team_names):
                key = f"team_{i}"
                params[key] = team
                placeholders.append(f":{key}")
            stmt = text(f"""
                SELECT v.jugador
                FROM v_estadisticas_jugador_partido v
                JOIN jugadores j ON v.jugador_id = j.id
                JOIN equipos e ON j.equipo_id = e.id
                WHERE e.user_id = :user_id
                  AND v.equipo_jugador IN ({", ".join(placeholders)})
                GROUP BY v.jugador_id, v.jugador
                HAVING COUNT(DISTINCT v.partido_id) >= :min_matches
                ORDER BY v.jugador ASC
            """)
            params["min_matches"] = min_matches
            rows = db.session.execute(stmt, params).fetchall()
            candidate_names = [row[0] for row in rows]
        else:
            candidate_names = self.get_players_with_stats(min_matches=min_matches)

        items = []
        excluded = []

        for player_name in candidate_names:
            snap = self.get_player_snapshot(player_name, context=context)
            matches = snap["matches"]

            if matches < min_matches:
                excluded.append(player_name)
                continue

            if metric in {"shot_accuracy", "shots_total"}:
                shot_stats = self.get_player_shot_stats(player_name, context=context)
                if not shot_stats:
                    excluded.append(player_name)
                    continue
                if metric == "shot_accuracy" and shot_stats["shots"]["total"] < 3:
                    excluded.append(player_name)
                    continue
                score = shot_stats["shots"]["accuracy"] if metric == "shot_accuracy" else shot_stats["shots"]["total"]
                snap = {**snap, "shot_stats": shot_stats}
            elif metric == "goals_total":
                score = snap["goals"]["total"]
            elif metric == "goals_field":
                score = snap["goals"]["field"]
            elif metric == "goals_7m":
                score = snap["goals"]["seven_m"]
            elif metric == "assists":
                score = snap["assists"]["total"]
            elif metric == "recoveries":
                score = snap["recoveries"]["total"]
            elif metric == "losses":
                score = snap["losses"]["total"]
            elif metric == "fouls_committed":
                score = snap["fouls_committed"]["total"]
            elif metric == "fouls_received":
                score = snap["fouls_received"]["total"]
            elif metric == "matches":
                score = snap["matches"]
            elif metric == "goals_total_avg":
                score = snap["goals"]["avg_total"]
            elif metric == "assists_avg":
                score = snap["assists"]["avg"]
            elif metric == "recoveries_avg":
                score = snap["recoveries"]["avg"]
            else:
                score = snap["goals"]["total"]

            items.append({
                "player_name": player_name,
                "score": float(score),
                "snapshot": snap,
            })

        items.sort(key=lambda x: x["player_name"].lower())
        items.sort(key=lambda x: x["score"], reverse=descending)

        top_score = items[0]["score"] if items else None
        leaders = [item for item in items if items and item["score"] == top_score] if items else []

        return {
            "ranking": items,
            "leaders": leaders,
            "excluded": excluded,
        }


    def get_player_minutes(self, player_name: str, context: str | None = None):
        relation = "v_estadisticas_jugador_total"
        if not self._relation_exists(relation):
            relation = "v_estadisticas_jugador_partido"

        cols = self._columns(relation)
        seconds_col = "segundos_jugados" if "segundos_jugados" in cols else None
        minutes_col = "minutos_jugados" if "minutos_jugados" in cols else None
        if not seconds_col and not minutes_col:
            return None

        filters = ["e.user_id = :user_id", "v.jugador = :player_name"]
        params = {"user_id": self.user_id, "player_name": player_name}
        if relation == "v_estadisticas_jugador_partido":
            if context == "home":
                filters.append("v.equipo_jugador = v.equipo_local")
            elif context == "away":
                filters.append("v.equipo_jugador = v.equipo_visitante")

        seconds_expr = f"SUM(COALESCE(v.{seconds_col}, 0))" if seconds_col else f"SUM(COALESCE(v.{minutes_col}, 0)) * 60"
        minutes_expr = f"SUM(COALESCE(v.{minutes_col}, 0))" if minutes_col else f"SUM(COALESCE(v.{seconds_col}, 0)) / 60"

        if "partidos" in cols:
            matches_expr = "MAX(COALESCE(v.partidos, 0))"
        elif "partido_id" in cols:
            matches_expr = "COUNT(DISTINCT v.partido_id)"
        else:
            matches_expr = "0"

        stmt = text(f"""
            SELECT
                v.jugador AS player_name,
                MAX(v.equipo_jugador) AS team_name,
                COALESCE({seconds_expr}, 0) AS seconds_played,
                COALESCE({minutes_expr}, 0) AS minutes_played,
                COALESCE({matches_expr}, 0) AS matches
            FROM {relation} v
            JOIN jugadores j ON v.jugador_id = j.id
            JOIN equipos e ON j.equipo_id = e.id
            WHERE {" AND ".join(filters)}
            GROUP BY v.jugador
        """)
        row = db.session.execute(stmt, params).fetchone()
        if not row:
            return None
        matches = int(self._num(row, "matches"))

        return {
            "player_name": row._mapping["player_name"],
            "team_name": row._mapping["team_name"],
            "seconds": int(self._num(row, "seconds_played")),
            "minutes": round(self._num(row, "minutes_played"), 2),
            "matches": matches,
            "avg_seconds": round(self._num(row, "seconds_played") / matches, 2) if matches else 0,
            "avg_minutes": round(self._num(row, "minutes_played") / matches, 2) if matches else 0,
        }

    def get_player_shot_stats(self, player_name: str, context: str | None = None):
        relation = "v_estadisticas_jugador_total"
        if not self._relation_exists(relation):
            relation = "v_estadisticas_jugador_partido"

        cols = self._columns(relation)
        wanted = {
            "tiros_totales", "tiros_convertidos", "tiros_fallados", "tiros_parados",
            "porcentaje_tiros", "tiros_7m_totales", "tiros_7m_convertidos",
            "tiros_7m_fallados", "tiros_7m_parados", "porcentaje_7m",
            "goles_por_minuto", "asistencias_por_minuto", "recuperaciones_por_minuto",
        }
        if not (wanted & cols):
            return None

        def expr(*names: str) -> str:
            for col in names:
                if col in cols:
                    return f"SUM(COALESCE(v.{col}, 0))"
            return "0"

        filters = ["e.user_id = :user_id", "v.jugador = :player_name"]
        params = {"user_id": self.user_id, "player_name": player_name}
        if relation == "v_estadisticas_jugador_partido":
            if context == "home":
                filters.append("v.equipo_jugador = v.equipo_local")
            elif context == "away":
                filters.append("v.equipo_jugador = v.equipo_visitante")

        stmt = text(f"""
            SELECT
                v.jugador AS player_name,
                MAX(v.equipo_jugador) AS team_name,
                {expr("tiros_totales")} AS shots_total,
                {expr("tiros_convertidos")} AS shots_scored,
                {expr("tiros_fallados")} AS shots_missed,
                {expr("tiros_parados")} AS shots_saved,
                {expr("tiros_7m_totales")} AS seven_total,
                {expr("tiros_7m_convertidos")} AS seven_scored,
                {expr("tiros_7m_fallados")} AS seven_missed,
                {expr("tiros_7m_parados")} AS seven_saved,
                {expr("goles_por_minuto")} AS goals_per_minute,
                {expr("asistencias_por_minuto")} AS assists_per_minute,
                {expr("recuperaciones_por_minuto")} AS recoveries_per_minute
            FROM {relation} v
            JOIN jugadores j ON v.jugador_id = j.id
            JOIN equipos e ON j.equipo_id = e.id
            WHERE {" AND ".join(filters)}
            GROUP BY v.jugador
        """)
        row = db.session.execute(stmt, params).fetchone()
        if not row:
            return None

        shots_total = self._num(row, "shots_total")
        shots_scored = self._num(row, "shots_scored")
        seven_total = self._num(row, "seven_total")
        seven_scored = self._num(row, "seven_scored")

        return {
            "player_name": row._mapping["player_name"],
            "team_name": row._mapping["team_name"],
            "shots": {
                "total": int(shots_total),
                "scored": int(shots_scored),
                "missed": int(self._num(row, "shots_missed")),
                "saved": int(self._num(row, "shots_saved")),
                "accuracy": self._pct(shots_scored, shots_total),
            },
            "seven_m": {
                "total": int(seven_total),
                "scored": int(seven_scored),
                "missed": int(self._num(row, "seven_missed")),
                "saved": int(self._num(row, "seven_saved")),
                "accuracy": self._pct(seven_scored, seven_total),
            },
            "per_minute": {
                "goals": round(self._num(row, "goals_per_minute"), 4),
                "assists": round(self._num(row, "assists_per_minute"), 4),
                "recoveries": round(self._num(row, "recoveries_per_minute"), 4),
            },
        }

    def get_player_zone_distribution(self, player_name: str, zone: str | None = None, context: str | None = None):
        relation = "v_jugador_shot_zones"
        if not self._relation_exists(relation):
            return None

        cols = self._columns(relation)
        zone_col = "zona_tiro" if "zona_tiro" in cols else "zona" if "zona" in cols else None
        if not zone_col:
            return None
        team_expr = "z.equipo_jugador" if "equipo_jugador" in cols else "z.equipo" if "equipo" in cols else "e.nombre"

        def col(*names: str) -> str:
            for name in names:
                if name in cols:
                    return f"z.{name}"
            return "0"

        filters = ["e.user_id = :user_id", "z.jugador = :player_name"]
        params = {"user_id": self.user_id, "player_name": player_name}
        if zone:
            filters.append(f"LOWER(z.{zone_col}) = LOWER(:zone)")
            params["zone"] = zone

        stmt = text(f"""
            SELECT
                z.jugador AS player_name,
                MAX({team_expr}) AS team_name,
                z.{zone_col} AS zone,
                COALESCE(SUM({col("tiros", "tiros_totales")}), 0) AS shots,
                COALESCE(SUM({col("goles", "tiros_convertidos")}), 0) AS goals,
                COALESCE(SUM({col("fallos", "tiros_fallados")}), 0) AS misses,
                COALESCE(SUM({col("paradas", "tiros_parados")}), 0) AS saves,
                COALESCE(AVG({col("usage_pct", "porcentaje_uso")}), 0) AS usage_pct,
                COALESCE(AVG({col("accuracy_pct", "porcentaje_acierto")}), 0) AS accuracy_pct
            FROM {relation} z
            JOIN jugadores j ON z.jugador_id = j.id
            JOIN equipos e ON j.equipo_id = e.id
            WHERE {" AND ".join(filters)}
            GROUP BY z.jugador, z.{zone_col}
            ORDER BY shots DESC, zone ASC
        """)
        rows = db.session.execute(stmt, params).fetchall()
        if not rows:
            return None
        return [
            {
                "player_name": row._mapping["player_name"],
                "team_name": row._mapping["team_name"],
                "zone": row._mapping["zone"],
                "shots": int(self._num(row, "shots")),
                "goals": int(self._num(row, "goals")),
                "misses": int(self._num(row, "misses")),
                "saves": int(self._num(row, "saves")),
                "usage_pct": round(self._num(row, "usage_pct"), 2),
                "accuracy_pct": round(self._num(row, "accuracy_pct"), 2),
            }
            for row in rows
        ]

    def compare_players_by_zone(
        self,
        player_names: list[str] | None,
        zone: str,
        metric: str = "accuracy_pct",
        descending: bool = True,
        min_shots: int = 1,
    ):
        candidates = player_names or self.get_players_with_stats(min_matches=1)
        metric_map = {
            "shots": "shots",
            "goals": "goals",
            "misses": "misses",
            "saves": "saves",
            "usage_pct": "usage_pct",
            "accuracy_pct": "accuracy_pct",
        }
        score_key = metric_map.get(metric, "accuracy_pct")

        rows = []
        for player_name in candidates:
            zones = self.get_player_zone_distribution(player_name, zone=zone)
            if not zones:
                continue
            row = dict(zones[0])
            if int(row.get("shots", 0) or 0) < min_shots:
                continue
            row["score"] = float(row.get(score_key, 0) or 0)
            rows.append(row)

        rows.sort(key=lambda row: str(row.get("player_name", "")).lower())
        rows.sort(key=lambda row: row.get("score", 0), reverse=descending)
        return rows


    def get_team_wins(self, team_name, home=False, away=False):
        if home:
            condition = "e_local.nombre = :team_name AND p.goles_local > p.goles_visitante"
        elif away:
            condition = "e_visit.nombre = :team_name AND p.goles_visitante > p.goles_local"
        else:
            condition = """
                (e_local.nombre = :team_name AND p.goles_local > p.goles_visitante)
                OR
                (e_visit.nombre = :team_name AND p.goles_visitante > p.goles_local)
            """

        stmt = text(f"""
            SELECT COUNT(*)
            FROM partidos p
            JOIN equipos e_local ON p.equipo_local_id = e_local.id
            JOIN equipos e_visit ON p.equipo_visitante_id = e_visit.id
            WHERE ({condition})
              AND (e_local.user_id = :user_id OR e_visit.user_id = :user_id)
        """)

        row = db.session.execute(stmt, {
            "user_id": self.user_id,
            "team_name": team_name
        }).fetchone()

        return int(row[0] or 0)

    def get_team_wins_breakdown(self, team_name):
        total = self.get_team_wins(team_name)
        home = self.get_team_wins(team_name, home=True)
        away = self.get_team_wins(team_name, away=True)
        return total, home, away


    def get_team_draws(self, team_name, home=False, away=False):
        if home:
            condition = "e_local.nombre = :team_name"
        elif away:
            condition = "e_visit.nombre = :team_name"
        else:
            condition = "(e_local.nombre = :team_name OR e_visit.nombre = :team_name)"

        stmt = text(f"""
            SELECT COUNT(*)
            FROM partidos p
            JOIN equipos e_local ON p.equipo_local_id = e_local.id
            JOIN equipos e_visit ON p.equipo_visitante_id = e_visit.id
            WHERE p.goles_local = p.goles_visitante
              AND ({condition})
              AND (e_local.user_id = :user_id OR e_visit.user_id = :user_id)
        """)

        row = db.session.execute(stmt, {
            "user_id": self.user_id,
            "team_name": team_name
        }).fetchone()

        return int(row[0] or 0)

    def get_team_draws_breakdown(self, team_name):
        total = self.get_team_draws(team_name)
        home = self.get_team_draws(team_name, home=True)
        away = self.get_team_draws(team_name, away=True)
        return total, home, away


    def get_team_losses(self, team_name, home=False, away=False):
        if home:
            condition = "e_local.nombre = :team_name AND p.goles_local < p.goles_visitante"
        elif away:
            condition = "e_visit.nombre = :team_name AND p.goles_visitante < p.goles_local"
        else:
            condition = """
                (e_local.nombre = :team_name AND p.goles_local < p.goles_visitante)
                OR
                (e_visit.nombre = :team_name AND p.goles_visitante < p.goles_local)
            """

        stmt = text(f"""
            SELECT COUNT(*)
            FROM partidos p
            JOIN equipos e_local ON p.equipo_local_id = e_local.id
            JOIN equipos e_visit ON p.equipo_visitante_id = e_visit.id
            WHERE ({condition})
              AND (e_local.user_id = :user_id OR e_visit.user_id = :user_id)
        """)

        row = db.session.execute(stmt, {
            "user_id": self.user_id,
            "team_name": team_name
        }).fetchone()

        return int(row[0] or 0)

    def get_team_losses_breakdown(self, team_name):
        total = self.get_team_losses(team_name)
        home = self.get_team_losses(team_name, home=True)
        away = self.get_team_losses(team_name, away=True)
        return total, home, away


    def get_team_matches(self, team_name, home=False, away=False):
        if home:
            condition = "e_local.nombre = :team_name"
        elif away:
            condition = "e_visit.nombre = :team_name"
        else:
            condition = "(e_local.nombre = :team_name OR e_visit.nombre = :team_name)"

        stmt = text(f"""
            SELECT COUNT(*)
            FROM partidos p
            JOIN equipos e_local ON p.equipo_local_id = e_local.id
            JOIN equipos e_visit ON p.equipo_visitante_id = e_visit.id
            WHERE ({condition})
              AND (e_local.user_id = :user_id OR e_visit.user_id = :user_id)
        """)

        row = db.session.execute(stmt, {
            "user_id": self.user_id,
            "team_name": team_name
        }).fetchone()

        return int(row[0] or 0)

    def get_team_matches_breakdown(self, team_name):
        total = self.get_team_matches(team_name)
        home = self.get_team_matches(team_name, home=True)
        away = self.get_team_matches(team_name, away=True)
        return total, home, away


    def get_team_goals_stats(self, team_name, context=None, result=None):
        filters = []
        params = {"user_id": self.user_id, "team_name": team_name}

        if context == "home":
            filters.append("e_local.nombre = :team_name")
            gf = "p.goles_local"
            gc = "p.goles_visitante"

        elif context == "away":
            filters.append("e_visit.nombre = :team_name")
            gf = "p.goles_visitante"
            gc = "p.goles_local"

        else:
            gf = """
                CASE
                    WHEN e_local.nombre = :team_name THEN p.goles_local
                    ELSE p.goles_visitante
                END
            """
            gc = """
                CASE
                    WHEN e_local.nombre = :team_name THEN p.goles_visitante
                    ELSE p.goles_local
                END
            """
            filters.append("(e_local.nombre = :team_name OR e_visit.nombre = :team_name)")

        if result == "win":
            filters.append("""
                (
                    (e_local.nombre = :team_name AND p.goles_local > p.goles_visitante)
                    OR
                    (e_visit.nombre = :team_name AND p.goles_visitante > p.goles_local)
                )
            """)

        elif result == "loss":
            filters.append("""
                (
                    (e_local.nombre = :team_name AND p.goles_local < p.goles_visitante)
                    OR
                    (e_visit.nombre = :team_name AND p.goles_visitante < p.goles_local)
                )
            """)

        elif result == "draw":
            filters.append("p.goles_local = p.goles_visitante")

        where_clause = " AND ".join(filters)

        stmt = text(f"""
            SELECT
                COALESCE(SUM({gf}), 0) AS goles_favor,
                COALESCE(SUM({gc}), 0) AS goles_contra,
                COUNT(*) AS partidos
            FROM partidos p
            JOIN equipos e_local ON p.equipo_local_id = e_local.id
            JOIN equipos e_visit ON p.equipo_visitante_id = e_visit.id
            WHERE {where_clause}
        """)

        row = db.session.execute(stmt, params).fetchone()

        if not row or row[2] == 0:
            return 0, 0, 0

        return int(row[0]), int(row[1]), int(row[2])

    def get_team_goals_breakdown(self, team_name, result=None):
        overall = self.get_team_goals_stats(team_name, context=None, result=result)
        home = self.get_team_goals_stats(team_name, context="home", result=result)
        away = self.get_team_goals_stats(team_name, context="away", result=result)

        return {
            "overall": {
                "gf": overall[0],
                "gc": overall[1],
                "matches": overall[2],
            },
            "home": {
                "gf": home[0],
                "gc": home[1],
                "matches": home[2],
            },
            "away": {
                "gf": away[0],
                "gc": away[1],
                "matches": away[2],
            },
        }


    def get_team_snapshot(self, team_name):
        wins_total, wins_home, wins_away = self.get_team_wins_breakdown(team_name)
        draws_total, draws_home, draws_away = self.get_team_draws_breakdown(team_name)
        losses_total, losses_home, losses_away = self.get_team_losses_breakdown(team_name)
        matches_total, matches_home, matches_away = self.get_team_matches_breakdown(team_name)

        goals_overall = self.get_team_goals_stats(team_name, context=None, result=None)
        goals_home = self.get_team_goals_stats(team_name, context="home", result=None)
        goals_away = self.get_team_goals_stats(team_name, context="away", result=None)

        def _avg(gf, gc, matches):
            if not matches:
                return 0.0, 0.0
            return round(gf / matches, 2), round(gc / matches, 2)

        overall_avg_for, overall_avg_against = _avg(*goals_overall)
        home_avg_for, home_avg_against = _avg(*goals_home)
        away_avg_for, away_avg_against = _avg(*goals_away)

        return {
            "team_name": team_name,
            "wins": {"total": wins_total, "home": wins_home, "away": wins_away},
            "draws": {"total": draws_total, "home": draws_home, "away": draws_away},
            "losses": {"total": losses_total, "home": losses_home, "away": losses_away},
            "matches": {"total": matches_total, "home": matches_home, "away": matches_away},
            "goals": {
                "overall": {
                    "gf": goals_overall[0],
                    "gc": goals_overall[1],
                    "matches": goals_overall[2],
                    "avg_for": overall_avg_for,
                    "avg_against": overall_avg_against,
                },
                "home": {
                    "gf": goals_home[0],
                    "gc": goals_home[1],
                    "matches": goals_home[2],
                    "avg_for": home_avg_for,
                    "avg_against": home_avg_against,
                },
                "away": {
                    "gf": goals_away[0],
                    "gc": goals_away[1],
                    "matches": goals_away[2],
                    "avg_for": away_avg_for,
                    "avg_against": away_avg_against,
                },
            },
            "goal_difference": goals_overall[0] - goals_overall[1],
        }

    def get_all_team_snapshots(self):
        return [self.get_team_snapshot(team_name) for team_name in self.get_all_team_names()]

    def get_ranked_teams(self, metric="wins", team_names=None, descending=True, min_matches=1, context=None, result=None):
        if team_names is None:
            candidate_names = self.get_teams_with_matches(min_matches=min_matches)
        else:
            candidate_names = [t for t in team_names if t in self.get_all_team_names()]

        valid_names = []
        excluded_names = []

        for team in candidate_names:
            if context == "home":
                relevant_matches = self.get_team_matches(team, home=True)
            elif context == "away":
                relevant_matches = self.get_team_matches(team, away=True)
            else:
                relevant_matches = self.get_team_matches(team)

            if relevant_matches >= min_matches:
                valid_names.append(team)
            else:
                excluded_names.append(team)

        home_flag = context == "home"
        away_flag = context == "away"

        def _count_metric(team, metric_name):
            if metric_name == "wins":
                return self.get_team_wins(team, home=home_flag, away=away_flag)
            if metric_name == "draws":
                return self.get_team_draws(team, home=home_flag, away=away_flag)
            if metric_name == "losses":
                return self.get_team_losses(team, home=home_flag, away=away_flag)
            if metric_name == "matches":
                return self.get_team_matches(team, home=home_flag, away=away_flag)
            return 0

        def _goal_stats(team):
            return self.get_team_goals_stats(team, context=context, result=result)

        def _score(team):
            if metric in {"wins", "draws", "losses", "matches"}:
                return float(_count_metric(team, metric))

            gf, gc, matches = _goal_stats(team)
            if matches == 0:
                return None

            if metric == "goals_for":
                return float(gf)
            if metric == "goals_against":
                return float(gc)
            if metric == "goal_difference":
                return float(gf - gc)
            if metric == "goals_for_avg":
                return round(gf / matches, 4)
            if metric == "goals_against_avg":
                return round(gc / matches, 4)
            if metric == "goal_difference_avg":
                return round((gf - gc) / matches, 4)

            if metric == "composite_strength_avg":
                wins = self.get_team_wins(team, home=home_flag, away=away_flag)
                draws = self.get_team_draws(team, home=home_flag, away=away_flag)
                losses = self.get_team_losses(team, home=home_flag, away=away_flag)
                matches_count = self.get_team_matches(team, home=home_flag, away=away_flag)
                if matches_count == 0:
                    return None

                gf2, gc2, _ = _goal_stats(team)
                goal_diff_avg = (gf2 - gc2) / matches_count
                win_rate = wins / matches_count
                draw_rate = draws / matches_count
                loss_rate = losses / matches_count

                return round((win_rate * 3) + (draw_rate * 1) - (loss_rate * 2) + goal_diff_avg, 4)

            return float(self.get_team_wins(team, home=home_flag, away=away_flag))

        items = []
        for name in valid_names:
            score = _score(name)
            if score is None:
                excluded_names.append(name)
                continue

            items.append({
                "team_name": name,
                "score": score,
                "snapshot": self.get_team_snapshot(name),
            })

        items.sort(key=lambda x: x["team_name"].lower())
        items.sort(key=lambda x: x["score"], reverse=descending)

        top_score = items[0]["score"] if items else None
        leaders = [item for item in items if items and item["score"] == top_score] if items else []

        return {
            "ranking": items,
            "leaders": leaders,
            "excluded": excluded_names,
        }

    def get_team_player_aggregates(self, team_name: str) -> dict:
        matches = self.get_team_matches(team_name)
        if not matches:
            return {"assists_per_match": 0, "recoveries_per_match": 0, "losses_per_match": 0, "fouls_committed_per_match": 0, "fouls_received_per_match": 0}

        stmt = text("""
            SELECT
                COALESCE(SUM(COALESCE(v.asistencias, 0)), 0) AS total_assists,
                COALESCE(SUM(COALESCE(v.recuperaciones, 0)), 0) AS total_recoveries,
                COALESCE(SUM(COALESCE(v.perdidas, 0)), 0) AS total_losses,
                COALESCE(SUM(COALESCE(v.faltas_cometidas, 0)), 0) AS total_fouls_committed,
                COALESCE(SUM(COALESCE(v.faltas_recibidas, 0)), 0) AS total_fouls_received
            FROM v_estadisticas_jugador_partido v
            JOIN jugadores j ON v.jugador_id = j.id
            JOIN equipos e ON j.equipo_id = e.id
            WHERE e.nombre = :team_name AND e.user_id = :user_id
        """)
        row = db.session.execute(stmt, {"team_name": team_name, "user_id": self.user_id}).fetchone()
        if not row:
            return {"assists_per_match": 0, "recoveries_per_match": 0, "losses_per_match": 0, "fouls_committed_per_match": 0, "fouls_received_per_match": 0}

        return {
            "assists_per_match": round(row[0] / matches, 2) if matches else 0,
            "recoveries_per_match": round(row[1] / matches, 2) if matches else 0,
            "losses_per_match": round(row[2] / matches, 2) if matches else 0,
            "fouls_committed_per_match": round(row[3] / matches, 2) if matches else 0,
            "fouls_received_per_match": round(row[4] / matches, 2) if matches else 0,
        }


    def get_team_shot_stats(self, team_name: str, context: str | None = None, result: str | None = None):
        relation = "v_equipo_estadisticas_total"
        if not self._relation_exists(relation):
            relation = "v_equipo_estadisticas_partido"
        if not self._relation_exists(relation):
            return None

        cols = self._columns(relation)
        wanted = {
            "tiros_totales", "tiros_convertidos", "tiros_fallados", "tiros_parados",
            "porcentaje_tiros", "tiros_7m_totales", "tiros_7m_convertidos",
            "tiros_7m_fallados", "tiros_7m_parados", "porcentaje_7m",
            "paradas", "paradas_7m", "goles_favor", "goles_contra",
        }
        if not (wanted & cols):
            return None

        team_col = "equipo" if "equipo" in cols else "equipo_nombre" if "equipo_nombre" in cols else "team_name" if "team_name" in cols else None
        if not team_col:
            return None

        def expr(*names: str) -> str:
            for col in names:
                if col in cols:
                    return f"SUM(COALESCE(v.{col}, 0))"
            return "0"

        filters = [f"v.{team_col} = :team_name"]
        params = {"team_name": team_name}
        if "user_id" in cols:
            filters.append("v.user_id = :user_id")
            params["user_id"] = self.user_id

        if context == "home" and "condicion" in cols:
            filters.append("v.condicion = 'home'")
        elif context == "away" and "condicion" in cols:
            filters.append("v.condicion = 'away'")

        if result and "resultado" in cols:
            filters.append("v.resultado = :result")
            params["result"] = result

        stmt = text(f"""
            SELECT
                v.{team_col} AS team_name,
                {expr("goles_favor")} AS goals_for,
                {expr("goles_contra")} AS goals_against,
                {expr("tiros_totales", "tiros")} AS shots_total,
                {expr("tiros_convertidos", "goles")} AS shots_scored,
                {expr("tiros_fallados", "fallos")} AS shots_missed,
                {expr("tiros_parados")} AS shots_saved,
                {expr("tiros_7m_totales")} AS seven_total,
                {expr("tiros_7m_convertidos", "goles_7m")} AS seven_scored,
                {expr("tiros_7m_fallados", "fallos_7m")} AS seven_missed,
                {expr("tiros_7m_parados", "paradas_7m_tiros")} AS seven_saved,
                {expr("paradas")} AS saves,
                {expr("paradas_7m")} AS seven_saves
            FROM {relation} v
            WHERE {" AND ".join(filters)}
            GROUP BY v.{team_col}
        """)
        row = db.session.execute(stmt, params).fetchone()
        if not row:
            return None

        shots_total = self._num(row, "shots_total")
        shots_scored = self._num(row, "shots_scored")
        seven_total = self._num(row, "seven_total")
        seven_scored = self._num(row, "seven_scored")
        seven_missed = self._num(row, "seven_missed")
        seven_saved = self._num(row, "seven_saved")
        saves = self._num(row, "saves")
        goals_against = self._num(row, "goals_against")

        if not seven_total:
            seven_zone = self.get_team_zone_distribution(team_name, zone="7m", context=context, result=result)
            if seven_zone:
                seven_total = float(seven_zone[0]["shots"])
                seven_scored = float(seven_zone[0]["goals"])
                seven_missed = float(seven_zone[0]["misses"])
                seven_saved = float(seven_zone[0]["saves"])

        return {
            "team_name": row._mapping["team_name"],
            "goals_for": int(self._num(row, "goals_for")),
            "goals_against": int(goals_against),
            "shots": {
                "total": int(shots_total),
                "scored": int(shots_scored),
                "missed": int(self._num(row, "shots_missed")),
                "saved": int(self._num(row, "shots_saved")),
                "accuracy": self._pct(shots_scored, shots_total),
            },
            "seven_m": {
                "total": int(seven_total),
                "scored": int(seven_scored),
                "missed": int(seven_missed),
                "saved": int(seven_saved),
                "accuracy": self._pct(seven_scored, seven_total),
            },
            "goalkeeper": {
                "saves": int(saves),
                "seven_m_saves": int(self._num(row, "seven_saves")),
                "save_pct": self._pct(saves, saves + goals_against),
            },
        }

    def get_team_zone_distribution(self, team_name: str, zone: str | None = None, context: str | None = None, result: str | None = None):
        relation = "v_equipo_shot_zones"
        if not self._relation_exists(relation):
            return None

        cols = self._columns(relation)
        team_col = "equipo" if "equipo" in cols else "equipo_nombre" if "equipo_nombre" in cols else "team_name" if "team_name" in cols else None
        zone_col = "zona_tiro" if "zona_tiro" in cols else "zona" if "zona" in cols else None
        if not team_col or not zone_col:
            return None

        def col(*names: str) -> str:
            for name in names:
                if name in cols:
                    return f"z.{name}"
            return "0"

        filters = [f"z.{team_col} = :team_name"]
        params = {"team_name": team_name}
        if "user_id" in cols:
            filters.append("z.user_id = :user_id")
            params["user_id"] = self.user_id
        if zone:
            filters.append(f"LOWER(z.{zone_col}) = LOWER(:zone)")
            params["zone"] = zone
        if context == "home" and "condicion" in cols:
            filters.append("z.condicion = 'home'")
        elif context == "away" and "condicion" in cols:
            filters.append("z.condicion = 'away'")
        if result and "resultado" in cols:
            filters.append("z.resultado = :result")
            params["result"] = result

        stmt = text(f"""
            SELECT
                z.{team_col} AS team_name,
                z.{zone_col} AS zone,
                COALESCE(SUM({col("tiros", "tiros_totales")}), 0) AS shots,
                COALESCE(SUM({col("goles", "tiros_convertidos")}), 0) AS goals,
                COALESCE(SUM({col("fallos", "tiros_fallados")}), 0) AS misses,
                COALESCE(SUM({col("paradas", "tiros_parados")}), 0) AS saves,
                COALESCE(AVG({col("usage_pct", "porcentaje_uso")}), 0) AS usage_pct,
                COALESCE(AVG({col("accuracy_pct", "porcentaje_acierto")}), 0) AS accuracy_pct
            FROM {relation} z
            WHERE {" AND ".join(filters)}
            GROUP BY z.{team_col}, z.{zone_col}
            ORDER BY shots DESC, zone ASC
        """)
        rows = db.session.execute(stmt, params).fetchall()
        if not rows:
            return None
        return [
            {
                "team_name": row._mapping["team_name"],
                "zone": row._mapping["zone"],
                "shots": int(self._num(row, "shots")),
                "goals": int(self._num(row, "goals")),
                "misses": int(self._num(row, "misses")),
                "saves": int(self._num(row, "saves")),
                "usage_pct": round(self._num(row, "usage_pct"), 2),
                "accuracy_pct": round(self._num(row, "accuracy_pct"), 2),
            }
            for row in rows
        ]

    def get_ranked_team_shot_accuracy(self, team_names: list[str] | None = None, top_k: int | None = None, descending: bool = True):
        candidates = team_names or self.get_teams_with_matches(min_matches=1)
        rows = []
        for team_name in candidates:
            stats = self.get_team_shot_stats(team_name)
            if not stats:
                continue
            if stats["shots"]["total"] < 5:
                continue
            rows.append({
                "team_name": team_name,
                "score": stats["shots"]["accuracy"],
                "stats": stats,
            })
        rows.sort(key=lambda row: row["team_name"].lower())
        rows.sort(key=lambda row: row["score"], reverse=descending)
        return rows[:top_k] if top_k else rows

    def get_ranked_team_zone_distribution(self, zone: str, metric: str = "shots", team_names: list[str] | None = None, top_k: int | None = None, descending: bool = True):
        candidates = team_names or self.get_teams_with_matches(min_matches=1)
        rows = []
        for team_name in candidates:
            zones = self.get_team_zone_distribution(team_name, zone=zone)
            if not zones:
                continue
            zone_row = zones[0]
            score = zone_row.get(metric, zone_row.get("shots", 0))
            rows.append({
                "team_name": team_name,
                "score": float(score or 0),
                "zone": zone_row,
            })
        rows.sort(key=lambda row: row["team_name"].lower())
        rows.sort(key=lambda row: row["score"], reverse=descending)
        return rows[:top_k] if top_k else rows

    def get_available_shot_zones(self):
        relation = "v_equipo_shot_zones"
        if not self._relation_exists(relation):
            relation = "v_jugador_shot_zones"
            if not self._relation_exists(relation):
                return []

        cols = self._columns(relation)
        zone_col = "zona" if "zona" in cols else "zona_tiro" if "zona_tiro" in cols else None
        if not zone_col:
            return []

        if relation == "v_equipo_shot_zones":
            stmt = text(f"""
                SELECT DISTINCT z.{zone_col} AS zone
                FROM {relation} z
                JOIN equipos e ON e.id = z.equipo_id
                WHERE e.user_id = :user_id
                AND z.{zone_col} IS NOT NULL
            ORDER BY z.{zone_col}
            """)
        else:
            stmt = text(f"""
                SELECT DISTINCT z.{zone_col} AS zone
                FROM {relation} z
                JOIN jugadores j ON j.id = z.jugador_id
                JOIN equipos e ON e.id = j.equipo_id
                WHERE e.user_id = :user_id
                AND z.{zone_col} IS NOT NULL
                ORDER BY z.{zone_col}
            """)

        rows = db.session.execute(stmt, {"user_id": self.user_id}).fetchall()
        return [row._mapping["zone"] for row in rows if row._mapping["zone"]]


    def compare_teams_by_zone(
        self,
        team_names: list[str] | None,
        zone: str,
        metric: str = "shots",
        descending: bool = True,
    ):

        relation = "v_equipo_shot_zones"
        if not self._relation_exists(relation):
            return []

        cols = self._columns(relation)

        zone_col = "zona" if "zona" in cols else "zona_tiro" if "zona_tiro" in cols else None
        if not zone_col:
            return []

        required_base = {"equipo_id", "equipo", zone_col}
        if not required_base.issubset(cols):
            return []

        metric_map = {
            "shots": "tiros",
            "goals": "goles",
            "misses": "fallos",
            "saves": "paradas",
            "blocks": "bloqueados",
            "usage_pct": "usage_pct",
            "accuracy_pct": "accuracy_pct",
        }

        metric_col = metric_map.get(metric, "tiros")
        if metric_col not in cols:
            metric_col = "tiros"

        def col(name: str) -> str:
            return f"z.{name}" if name in cols else "0"

        filters = [
            "e.user_id = :user_id",
            f"LOWER(z.{zone_col}) = LOWER(:zone)",
        ]

        params = {
            "user_id": self.user_id,
            "zone": zone,
        }

        clean_team_names = []
        for name in team_names or []:
            if name and name not in clean_team_names:
                clean_team_names.append(name)

        if clean_team_names:
            placeholders = []
            for i, name in enumerate(clean_team_names):
                key = f"team_{i}"
                params[key] = name
                placeholders.append(f":{key}")
            filters.append(f"z.equipo IN ({', '.join(placeholders)})")


        if metric_col in {"usage_pct", "accuracy_pct"}:
            score_expr = f"AVG({col(metric_col)})"
        else:
            score_expr = f"SUM({col(metric_col)})"

        stmt = text(f"""
            SELECT
                z.equipo AS team_name,
                z.{zone_col} AS zone,
                COALESCE(SUM({col("tiros")}), 0) AS shots,
                COALESCE(SUM({col("goles")}), 0) AS goals,
                COALESCE(SUM({col("fallos")}), 0) AS misses,
                COALESCE(SUM({col("paradas")}), 0) AS saves,
                COALESCE(SUM({col("bloqueados")}), 0) AS blocks,
                COALESCE(AVG({col("usage_pct")}), 0) AS usage_pct,
                COALESCE(AVG({col("accuracy_pct")}), 0) AS accuracy_pct,
                COALESCE({score_expr}, 0) AS score
            FROM {relation} z
            JOIN equipos e ON e.id = z.equipo_id
            WHERE {" AND ".join(filters)}
            GROUP BY z.equipo, z.{zone_col}
            ORDER BY score {"DESC" if descending else "ASC"}, z.equipo ASC
        """)

        rows = db.session.execute(stmt, params).fetchall()

        return [
            {
                "team_name": row._mapping["team_name"],
                "zone": row._mapping["zone"],
                "shots": int(self._num(row, "shots")),
                "goals": int(self._num(row, "goals")),
                "misses": int(self._num(row, "misses")),
                "saves": int(self._num(row, "saves")),
                "blocks": int(self._num(row, "blocks")),
                "usage_pct": round(self._num(row, "usage_pct"), 2),
                "accuracy_pct": round(self._num(row, "accuracy_pct"), 2),
                "score": round(self._num(row, "score"), 2),
            }
            for row in rows
        ]


    def get_league_goal_extremes(self):
        try:
            teams = self.get_all_team_names()
            if not teams:
                return {}
            return {
                "max_goals_team": teams[0],
                "min_goals_team": teams[-1],
            }
        except Exception:
            return {}
