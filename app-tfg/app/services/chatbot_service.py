import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from services.chatbot_parser import ChatbotParser
from services.chatbot_queries import ChatbotQueries
from services.chatbot_slm import ChatbotSLM


class ChatbotService:

    PLAYER_ONLY_METRICS = {
        "assists",
        "recoveries",
        "losses",
        "fouls_committed",
        "fouls_received",
        "minutes_played",
        "shot_stats",
        "shot_accuracy",
        "seven_m_accuracy",
        "shot_zone_distribution",
    }

    TEAM_ONLY_METRICS = {
        "wins",
        "draws",
        "losses",
        "matches",
        "goals_for",
        "goals_against",
        "goal_difference",
        "goals_for_avg",
        "goals_against_avg",
        "goal_difference_avg",
        "attack_composite",
        "defense_composite",
        "solidity_composite",
        "team_shot_stats",
        "team_zone_distribution",
    }

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.queries = ChatbotQueries(user_id)
        self.team_names = self.queries.get_all_team_names()
        self.player_names = self.queries.get_all_player_names()
        self.parser = ChatbotParser(self.team_names, self.player_names)
        self.slm = ChatbotSLM()
        self.slm_status = self.slm.status()
        self.slm_operational = self.slm.is_operational()


    @staticmethod
    def _q(text: str) -> str:
        return ChatbotParser._normalize(text)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    @staticmethod
    def _contains_any(text: str, phrases: list[str]) -> bool:
        return any(p in text for p in phrases)

    def _contains_word_any(self, q: str, words: list[str]) -> bool:
        return any(re.search(rf"\b{re.escape(self._q(w))}\b", q) for w in words)

    def _fuzzy_contains_any(self, text: str, phrases: list[str], threshold: float = 0.84) -> bool:
        q = self._q(text)
        q_tokens = self._tokenize(q)

        for phrase in phrases:
            p = self._q(phrase)
            if p in q:
                return True
            p_tokens = self._tokenize(p)
            if not p_tokens:
                continue
            for qt in q_tokens:
                if len(qt) < 4:
                    continue
                for pt in p_tokens:
                    if len(pt) < 4:
                        continue
                    if SequenceMatcher(None, qt, pt).ratio() >= threshold:
                        return True
            if SequenceMatcher(None, q, p).ratio() >= threshold:
                return True
        return False

    @staticmethod
    def _format_number(value: Any) -> str:
        try:
            num = float(value)
            if num.is_integer():
                return str(int(num))
            return f"{num:.2f}".rstrip("0").rstrip(".")
        except Exception:
            return str(value)

    @staticmethod
    def _plural_es(n: float, singular: str, plural: Optional[str] = None) -> str:
        try:
            num = float(n)
        except Exception:
            num = 0.0
        if int(num) == 1 and num == 1.0:
            return singular
        return plural or (singular + "s")

    @staticmethod
    def _join_names(names: list[str]) -> str:
        names = [n for n in names if n]
        if not names:
            return ""
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} y {names[1]}"
        return ", ".join(names[:-1]) + f" y {names[-1]}"

    def _refresh_entities(self) -> None:
        self.team_names = self.queries.get_all_team_names()
        self.player_names = self.queries.get_all_player_names()
        self.parser.team_names = self.team_names
        self.parser.player_names = self.player_names

    def _sanitize_entity_names(self, names: Optional[list[str]], valid_names: Optional[list[str]] = None) -> list[str]:
        if not names:
            return []
        valid_set = set(valid_names) if valid_names else None
        cleaned: list[str] = []
        for item in names:
            if item is None:
                continue
            name = str(item).strip()
            if not name or name.lower() in {"none", "null", "nan"}:
                continue
            if valid_set is not None and name not in valid_set:
                continue
            if name not in cleaned:
                cleaned.append(name)
        return cleaned

    def _merge_unique_names(self, *groups: Optional[list[str]]) -> list[str]:
        out: list[str] = []
        for group in groups:
            for name in group or []:
                if name and name not in out:
                    out.append(name)
        return out


    def _extract_team_names_from_question(self, question: str) -> list[str]:
        return self.parser.extract_team_names(question)

    def _extract_player_names_from_question(self, question: str) -> list[str]:
        team_tokens = set()
        for team in self.team_names:
            team_tokens.update(self._tokenize(self._q(team)))

        strong_team_context = self._has_strong_team_context(question)
        q = self._q(question)
        q_tokens = [t for t in self._tokenize(q) if not t.isdigit()]
        q_token_set = set(q_tokens)
        found = []

        def _filter_player_tokens(tokens: list[str]) -> list[str]:
            return [
                t for t in tokens
                if not t.isdigit()
                and not (strong_team_context and t in team_tokens)
            ]


        for player in self.player_names:
            clean = re.sub(r"\s*\(#?\d+\)", "", player).strip()
            clean_q = self._q(clean)


            if clean_q and clean_q in q:
                found.append(player)
                continue

            ptokens = _filter_player_tokens(self._tokenize(clean_q))

            if len(q_tokens) >= 2 and len(ptokens) >= 2:
                first_ok = any(
                    SequenceMatcher(None, qt, ptokens[0]).ratio() >= 0.85
                    for qt in q_tokens
                )
                last_ok = any(
                    SequenceMatcher(None, qt, ptokens[-1]).ratio() >= 0.80
                    for qt in q_tokens
                )

                if first_ok and last_ok:
                    found.append(player)
                    continue


        if found:
            unique = []
            for item in found:
                if item not in unique:
                    unique.append(item)
            return unique


        for player in self.player_names:
            if player in found:
                continue
            pn = self._q(player)
            if pn and pn in q:
                found.append(player)


        for player in self.player_names:
            if player in found:
                continue
            ptokens = _filter_player_tokens(self._tokenize(self._q(player)))
            if ptokens and set(ptokens) & q_token_set:
                found.append(player)


        for player in self.player_names:
            if player in found:
                continue
            ptokens = _filter_player_tokens(self._tokenize(self._q(player)))
            if not ptokens:
                continue

            matched = False
            for qtok in q_tokens:
                if len(qtok) < 4:
                    continue
                for ptok in ptokens:
                    if len(ptok) < 4:
                        continue
                    if SequenceMatcher(None, qtok, ptok).ratio() >= 0.80:
                        found.append(player)
                        matched = True
                        break
                if matched:
                    break


        if not found:
            def _clean_player_name(name: str) -> str:
                return re.sub(r'\s*\(\#?\d+\)\s*$', '', name).strip()

            clean_map = {}
            for player in self.player_names:
                clean = _clean_player_name(player)
                if clean:
                    clean_map[clean] = player

            for clean, original in clean_map.items():
                clean_norm = self._q(clean)
                if clean_norm and clean_norm in q:
                    found.append(original)

            for clean, original in clean_map.items():
                if original in found:
                    continue
                ctokens = _filter_player_tokens(self._tokenize(self._q(clean)))
                if ctokens and set(ctokens) & q_token_set:
                    found.append(original)

            for clean, original in clean_map.items():
                if original in found:
                    continue
                ctokens = _filter_player_tokens(self._tokenize(self._q(clean)))
                if not ctokens:
                    continue

                matched = False
                for qtok in q_tokens:
                    if len(qtok) < 4:
                        continue
                    for ctok in ctokens:
                        if len(ctok) < 4:
                            continue
                        if SequenceMatcher(None, qtok, ctok).ratio() >= 0.80:
                            found.append(original)
                            matched = True
                            break
                    if matched:
                        break


        if not found:
            dorsal_match = re.search(r"(?:#|dorsal\s+|numero\s+|número\s+|jugador\s+n[ºo]?\s*)(\d+)", q)
            if dorsal_match:
                dorsal = dorsal_match.group(1)
                for player in self.player_names:
                    if re.search(rf"\(#?{re.escape(dorsal)}\)", player):
                        found.append(player)

        unique = []
        for item in found:
            if item not in unique:
                unique.append(item)

        return unique

    def _extract_exact_player_names_from_question(self, question: str) -> list[str]:
        q = self._q(question)
        found = []

        for player in self.player_names:
            clean = re.sub(r"\s*\(#?\d+\)", "", player).strip()
            clean_q = self._q(clean)

            if clean_q and clean_q in q:
                found.append(player)

        unique = []
        for item in found:
            if item not in unique:
                unique.append(item)

        return unique


    def _get_explicit_context(self, question: str) -> Optional[str]:
        q = self._q(question)
        if self._fuzzy_contains_any(q, ["local", "casa"], threshold=0.80):
            return "home"
        if self._fuzzy_contains_any(q, ["visitante", "fuera"], threshold=0.80):
            return "away"
        return None

    def _get_explicit_result(self, question: str) -> Optional[str]:
        q = self._q(question)
        if self._fuzzy_contains_any(q, ["victoria", "victorias", "ganado", "gano", "ganó", "gana", "ganar"], threshold=0.80):
            return "win"
        if self._fuzzy_contains_any(q, ["derrota", "derrotas", "perdido", "perdio", "perdió", "pierde", "perder"], threshold=0.80):
            return "loss"
        if self._fuzzy_contains_any(q, ["empate", "empates", "empatado", "empato", "empató", "empata", "empatar"], threshold=0.80):
            return "draw"
        return None

    def _is_global_team_metric_question(self, question: str) -> bool:
        q = self._q(question)

        return any(k in q for k in [
            "balance de goles",
            "mejor balance",
            "peor balance",
            "diferencia de goles",
            "mejor diferencia",
            "peor diferencia",
            "gol average",
            "goal difference",
            "quien tiene mejor balance",
            "quién tiene mejor balance",
            "quien tiene peor balance",
            "quién tiene peor balance",
        ])

    def _is_direct_team_count_question(self, question: str) -> bool:
        q = self._q(question)
        metric = self._classify_team_direct_metric(q)
        team_names = self._extract_team_names_from_question(question)

        if metric not in {"wins", "draws", "losses", "matches"}:
            return False

        if not team_names:
            return False


        ranking_or_compare_terms = [
            "quien", "quién", "que equipo", "qué equipo",
            "top", "ranking", "clasificacion", "clasificación",
            "compara", "comparar", "vs", "contra",
            "mejor", "peor", "más", "mas", "menos",
            "gana más", "gana mas", "pierde menos", "pierde más", "pierde mas"
        ]

        if any(k in q for k in ranking_or_compare_terms):
            return False

        return True


    def _answer_direct_team_count_question(self, question: str) -> str:
        q = self._q(question)
        metric = self._classify_team_direct_metric(q)
        context = self._get_explicit_context(question)

        team_names = self._sanitize_entity_names(
            self._extract_team_names_from_question(question),
            self.team_names,
        )

        label_map = {
            "wins": "Victorias",
            "draws": "Empates",
            "losses": "Derrotas",
            "matches": "Partidos",
        }

        label = label_map.get(metric, self._team_metric_title(metric).capitalize())
        lines = [f"{label}:"]

        for team in team_names:
            snap = self.queries.get_team_snapshot(team)

            if context == "home":
                value = snap[metric]["home"]
                suffix = " como local"
            elif context == "away":
                value = snap[metric]["away"]
                suffix = " como visitante"
            else:
                value = snap[metric]["total"]
                suffix = ""

            unit = self._team_metric_title(metric)
            lines.append(f"- {team}: {self._format_number(value)} {unit}{suffix}")

        return "\n".join(lines)

    def _is_direct_team_ranking_question(self, question: str) -> bool:
        q = self._q(question)
        if self._extract_player_names_from_question(question):
            return False
        metric = self._classify_team_direct_metric(q)

        if metric not in {"wins", "draws", "losses", "matches"}:
            return False


        if self._extract_team_names_from_question(question):
            return False

        ranking_terms = [
            "que equipo", "qué equipo", "quien", "quién",
            "top", "ranking", "clasificacion", "clasificación",
            "mas", "más", "menos", "mayor", "menor",
            "ha ganado", "ganado", "gana",
            "ha perdido", "perdido", "pierde",
            "ha empatado", "empatado", "empata",
            "ha jugado", "jugado", "juega",
            "partidos ganados", "partidos perdidos", "partidos jugados",
        ]
        return any(k in q for k in ranking_terms)

    def _answer_direct_team_ranking_question(self, question: str) -> str:
        q = self._q(question)
        metric = self._classify_team_direct_metric(q)
        top_k = self._extract_top_k(question)

        asks_less = any(k in q for k in [
            "menos", "menor",
            "ha ganado menos", "ganado menos", "gana menos",
            "ha perdido menos", "perdido menos", "pierde menos",
            "ha empatado menos", "empatado menos", "empata menos",
            "ha jugado menos", "jugado menos", "juega menos",
            "menos victorias", "menos derrotas", "menos empates", "menos partidos",
        ])

        descending = not asks_less
        ranking = self._rank_teams(metric, descending=descending)
        ranking = self._include_ties_at_cutoff(ranking, top_k)

        title = f"Top {top_k} en {self._team_metric_title(metric)}"
        if len(ranking) > top_k:
            title += " (incluyendo empates)"
        title += ":"

        lines = [title]
        for idx, row in enumerate(ranking, start=1):
            team = row.get("team_name") or row.get("name") or "Equipo"
            value = row.get("score")
            lines.append(f"{idx}. {team}: {self._format_number(value)}")

        return "\n".join(lines)

    def _is_team_summary_question(self, question: str) -> bool:
        q = self._q(question)
        team_names = self._extract_team_names_from_question(question)
        if not team_names:
            return False
        return any(k in q for k in [
            "situacion", "situación", "resumen", "estado", "como va", "cómo va",
            "que tal", "qué tal", "rendimiento general", "situacion general",
        ])

    def _answer_team_summary_question(self, question: str) -> str:
        team_names = self._sanitize_entity_names(
            self._extract_team_names_from_question(question),
            self.team_names,
        )
        data_bundle = {
            "mode": "team_summary",
            "teams": [self.queries.get_team_snapshot(t) for t in team_names],
        }
        plan = {
            "domain": "team",
            "intent": "summary",
            "entity_names": team_names,
            "metric": None,
            "template_id": "summary",
            "top_k": 1,
        }
        if self.slm_operational:
            slm_answer = self._slm_redact(question, plan, data_bundle)
            if slm_answer:
                return slm_answer
        return self._format_team_summary(data_bundle)

    def _is_goals_avg_by_result_question(self, question: str) -> bool:
        q = self._q(question)
        team_names = self._extract_team_names_from_question(question)
        if not team_names:
            return False
        has_goals = any(k in q for k in [
            "goles", "gol", "marca", "marcan", "mete", "meten", "anota", "anotan",
        ])
        has_average = any(k in q for k in [
            "media", "promedio", "promedia", "de media", "por partido",
        ])
        has_result = self._get_explicit_result(question) is not None
        return has_goals and has_average and has_result

    def _infer_goals_avg_focus(self, question: str) -> str:
        q = self._q(question)
        against_terms = [
            "recibe", "reciben", "recibido", "encaja", "encajan", "encajado",
            "goles en contra", "en contra", "contra por partido"
        ]
        for_terms = [
            "marca", "marcan", "marcado", "mete", "meten", "metido",
            "anota", "anotan", "anotado", "goles a favor", "a favor"
        ]
        asks_against = any(k in q for k in against_terms)
        asks_for = any(k in q for k in for_terms)
        if asks_against and not asks_for:
            return "against"
        if asks_for and not asks_against:
            return "for"
        return "both"

    def _answer_goals_avg_by_result_question(self, question: str) -> str:
        team_names = self._sanitize_entity_names(
            self._extract_team_names_from_question(question),
            self.team_names,
        )
        result = self._get_explicit_result(question)
        context = self._get_explicit_context(question)
        if not team_names or not result:
            return "No he podido identificar el equipo o el resultado solicitado."
        data_bundle = self._build_goals_avg_by_result_bundle(team_names, [result], context)
        data_bundle["goal_focus"] = self._infer_goals_avg_focus(question)
        plan = {
            "domain": "team",
            "intent": "goals_avg",
            "entity_names": team_names,
            "metric": "goals_for_avg",
            "context": context,
            "result_filter": result,
            "template_id": "goals_avg_by_result",
            "top_k": 1,
        }
        if self.slm_operational:
            slm_answer = self._slm_redact(question, plan, data_bundle)
            if slm_answer:
                return slm_answer
        return self._format_goals_avg_by_result(data_bundle)

    def _is_explicit_mixed_question(self, question: str) -> bool:
        q = self._q(question)
        player_names = self._extract_player_names_from_question(question)
        team_names = self._extract_team_names_from_question(question)
        if not player_names or not team_names:
            return False

        mixed_terms = [
            "compara", "comparar", "comparame", "compárame", "vs", "frente a",
            "rendimiento general", "situacion", "situación", "resumen", "balance",
        ]
        return any(k in q for k in mixed_terms)

    def _is_direct_team_zone_question(self, question: str) -> bool:
        q = self._q(question)
        if not self._extract_team_names_from_question(question):
            return False
        if not self._extract_shot_zone(question):
            return False
        zone_terms = [
            "desde", "zona", "zonas", "6m", "6-9m", "7m",
            "contraataque", "contrataque", "extremo",
            "porcentaje", "acierto", "efectividad",
            "tiro", "tiros", "lanzamiento", "lanzamientos", "como tira",
        ]
        return any(k in q for k in zone_terms)

    def _extract_shot_zone(self, question: str) -> Optional[str]:
        q = self._q(question)

        alias_map = {
            "6m": [
                "6m", "6 metros", "seis metros"
            ],
            "6-9m": [
                "6-9m", "6 9m", "6 a 9m", "6 a 9 metros",
                "entre 6 y 9", "entre 6 y 9 metros",
                "9m", "9 metros", "nueve metros"
            ],
            "7m": [
                "7m", "7 metros", "siete metros"
            ],
            "Contraataque": [
                "contraataque", "contra ataque", "contrataque", "contrataques"
            ],
            "Extremo derecho": [
                "extremo derecho", "derecho"
            ],
            "Extremo izquierdo": [
                "extremo izquierdo", "izquierdo"
            ],
        }


        for canonical, aliases in alias_map.items():
            for alias in aliases:
                if self._q(alias) in q:
                    return canonical


        try:
            zones = self.queries.get_available_shot_zones()
        except Exception:
            zones = []

        for zone in zones:
            zn = self._q(zone)
            if zn and zn in q:
                return zone


        q_tokens = self._tokenize(q)
        best_zone = None
        best_score = 0.0

        for zone in zones:
            zn = self._q(zone)
            zone_tokens = self._tokenize(zn)

            for qt in q_tokens:
                if len(qt) < 4:
                    continue
                for zt in zone_tokens:
                    if len(zt) < 4:
                        continue
                    score = SequenceMatcher(None, qt, zt).ratio()
                    if score > best_score:
                        best_score = score
                        best_zone = zone

        if best_score >= 0.80:
            return best_zone

        return None

    def _extract_top_k(self, question: str) -> int:
        q = self._q(question)
        m = re.search(r"\btop\s+(\d+)\b", q)
        if m:
            return max(1, min(int(m.group(1)), 20))
        for m in re.finditer(r"\b(\d+)\b", q):
            suffix = q[m.end():].lstrip()
            if suffix.startswith("m") or suffix.startswith("metros"):
                continue
            n = int(m.group(1))
            if 1 <= n <= 20:
                return n
        return 1

    def _has_player_signal(self, q: str) -> bool:

        if any(k in q for k in [
            "jugador", "jugadores", "jugadora", "plantilla", "portero"
        ]):
            return True


        position_words = ["pivote", "extremo", "central", "lateral"]
        shot_context = any(k in q for k in [
            "zona", "zonas", "tiro", "tiros", "lanza", "lanzamiento",
            "desde", "porcentaje", "acierto"
        ])

        if not shot_context and any(k in q for k in position_words):
            return True

        return False

    def _has_team_signal(self, q: str) -> bool:
        return any(k in q for k in [
            "equipo", "equipos", "club", "seleccion", "selección"
        ])

    def _infer_focus(self, question: str) -> str:
        q = self._q(question)
        attack = any(k in q for k in [
            "ataque", "marca", "marcan", "marcado", "marcados", "mete",
            "anota", "anotado", "anotados", "goles a favor", "goles anotados",
            "goles marcados", "goles totales", "más goles", "mas goles", "atacante"
        ])
        defense = any(k in q for k in [
            "defensa", "defiende", "encaja", "encajado", "encajados",
            "recibe", "recibido", "recibidos", "recupera", "roba", "robos",
            "goles en contra", "goles recibidos", "goles encajados", "menos goles"
        ])
        if attack and defense:
            return "attack_defense"
        if attack:
            return "attack"
        if defense:
            return "defense"
        return "generic"

    def _classify_player_direct_metric(self, q: str) -> Optional[str]:


        if self._extract_shot_zone(q) and any(k in q for k in [
            "desde", "zona", "zonas", "6m", "6-9m", "7m",
            "contraataque", "contrataque", "extremo",
            "porcentaje", "acierto", "efectividad", "tiro", "tiros",
            "lanzamiento", "lanzamientos", "como tira"
        ]):
            return "shot_zone_distribution"

        if self._contains_any(q, ["goles de campo", "tiros de campo"]):
            return "goals_field"
        if self._contains_any(q, ["goles de 7 metros", "goles de 7m"]):
            return "goals_7m"
        patterns = [
            ("minutes_played", ["minutos jugados", "minutos", "tiempo jugado", "segundos jugados", "tiempo en pista"]),
            ("shot_zone_distribution", ["zona de tiro", "zonas de tiro", "distribucion de tiro", "distribuci", "desde 6m", "desde 6 metros", "desde 7m", "desde 7 metros", "extremo izquierdo", "extremo derecho", "lateral izquierdo", "lateral derecho", "pivote", "contraataque", "porteria vacia"]),
            ("seven_m_accuracy", ["porcentaje de 7 metros", "acierto de 7 metros", "efectividad de 7 metros", "porcentaje 7m", "acierto 7m", "efectividad 7m"]),
            ("shot_accuracy", ["porcentaje de tiro", "acierto de tiro", "efectividad de tiro", "porcentaje de lanzamiento", "acierto de lanzamiento", "efectividad de lanzamiento"]),
            ("shot_stats", ["tiros totales", "lanzamientos", "lanzamiento", "tiros", "tiro"]),
            ("goals_field", ["goles de campo", "tiros de campo"]),
            ("goals_7m", ["goles de 7 metros", "goles de 7m", "7 metros", "7m"]),
            ("assists", ["asistencia", "asistencias", "asiste", "pases de gol",
                         "asistente", "maximo asistente", "máximo asistente"]),
            ("goals_total", [
                "goles", "gol", "goleador", "maximo goleador", "máximo goleador",
                "anotador", "maximo anotador", "máximo anotador"
            ]),
            ("recoveries", ["recuperación", "recuperaciones", "recupera", "robos", "robo"]),
            ("losses", ["pérdida", "pérdidas", "pierde balón", "pierde balon"]),
            ("fouls_committed", ["faltas cometidas", "comete falta"]),
            ("fouls_received", ["faltas recibidas"]),
        ]
        for metric, aliases in patterns:
            if self._contains_any(q, aliases):
                return metric

        if self._contains_word_any(q, ["partido", "partidos", "jugado", "jugados", "juega"]):
            return "matches"

        return None

    def _classify_team_direct_metric(self, q: str) -> Optional[str]:
        if self._contains_any(q, [
            "zona de tiro", "zonas de tiro", "distribucion de tiro", "distribución de tiro",
            "desde que zona", "de que zona",
            "zona tira", "zona lanza", "tira mas desde", "lanza mas desde",
            "por donde tira",
            "desde 6m", "desde 6 metros", "desde 7m", "desde 7 metros",
            "desde 6-9m", "desde 9 metros",
            "extremo izquierdo", "extremo derecho", "lateral izquierdo", "lateral derecho",
            "pivote", "contraataque", "porteria vacia",
            "desde extremo", "desde el extremo", "tira desde", "lanza desde",
        ]):
            return "team_zone_distribution"
        if self._contains_any(q, ["tiros totales", "lanzamientos", "lanzamiento", "tiros", "tiro", "porcentaje de tiro", "acierto de tiro", "efectividad de tiro"]):
            return "team_shot_stats"
        if self._contains_any(q, ["victoria", "victorias", "vicotria", "vicotrias", "vitoria", "vitorias", "ganado", "ganados", "gana", "ganar"]):
            return "wins"
        if self._contains_any(q, ["empate", "empates", "empatado", "empata", "empatar"]):
            return "draws"
        if self._contains_any(q, ["derrota", "derrotas", "perdido", "pierde", "perder"]):
            return "losses"
        if self._contains_word_any(q, ["partido", "partidos", "jugado", "jugados", "juega"]):
            return "matches"

        if self._contains_any(q, [
            "goles a favor", "goles anotados", "goles marcados",
            "mas goles anotados", "más goles anotados",
            "menos goles anotados", "mas goles marcados", "más goles marcados",
            "menos goles marcados", "marca más", "marca mas", "marca menos",
            "mete más", "mete mas", "mete menos", "anota más", "anota mas",
            "anota menos", "anotados", "marcados"
        ]):
            if self._contains_any(q, ["por partido", "promedio", "media"]):
                return "goals_for_avg"
            if self._contains_any(q, ["total", "totales", "en total"]):
                return "goals_for"
            return "goals_for_avg"

        if self._contains_any(q, [
            "goles en contra", "goles recibidos", "goles encajados",
            "mas goles recibidos", "más goles recibidos", "menos goles recibidos",
            "mas goles encajados", "más goles encajados", "menos goles encajados",
            "encaja menos", "encaja más", "encaja mas", "recibe menos",
            "recibe más", "recibe mas", "recibidos", "encajados"
        ]):
            if self._contains_any(q, ["por partido", "promedio", "media"]):
                return "goals_against_avg"
            if self._contains_any(q, ["total", "totales", "en total"]):
                return "goals_against"
            return "goals_against_avg"

        if self._contains_any(q, ["diferencia de goles", "balance", "gol average", "goal difference"]):
            if self._contains_any(q, ["por partido", "promedio", "media"]):
                return "goal_difference_avg"
            if self._contains_any(q, ["total", "totales", "en total"]):
                return "goal_difference"
            return "goal_difference_avg"

        if self._contains_any(q, ["más sólido", "mas solido", "sólido", "solido", "va mejor", "mejor equipo", "mejor rendimiento"]):
            return "solidity_composite"

        return None

    def _asks_average(self, question: str) -> bool:
        q = self._q(question)
        return any(k in q for k in [
            "promedia",
            "promedio",
            "media",
            "de media",
            "por partido"
        ])

    def _is_team_comparison_signal(self, q: str) -> bool:
        return self._fuzzy_contains_any(q, [
            "compara", "comparar", "vs", "contra",
            "quién", "quien", "mejor", "peor", "más", "mas", "menos",
            "encaja", "recibe", "mete", "marca", "anota",
            "goles", "victorias", "derrotas", "empates", "balance",
            "como local", "como visitante", "local", "visitante", "casa", "fuera",
        ], threshold=0.80)

    def _has_strong_team_context(self, question: str) -> bool:
        q = self._q(question)

        generic_team_context = any(k in q for k in [
            "equipo", "equipos", "club", "plantilla",
            "distribucion de tiro", "distribución de tiro",
            "zonas de tiro", "zona de tiro",
            "compara", "comparar", "contra", "frente a",
            "desde", "tira", "lanza"
        ])

        if generic_team_context:
            return True

        for team in self.team_names:
            tq = self._q(team)
            if f"del {tq}" in q or f"de {tq}" in q:
                return True

        return False

    def _is_player_ranking_inside_team_question(self, question: str) -> bool:
        q = self._q(question)
        has_team = bool(self._extract_team_names_from_question(question))
        player_ranking_terms = [
            "maximo goleador", "máximo goleador", "goleador",
            "maximo asistente", "máximo asistente", "asistente",
            "jugador con mas", "jugador con más",
            "quien tiene mas", "quién tiene más",
            "quien lleva mas", "quién lleva más",
            "mejor tirador", "mejor lanzador",
            "mas faltas", "más faltas",
            "mas recuperaciones", "más recuperaciones",
            "mas perdidas", "más pérdidas",
        ]
        return has_team and any(term in q for term in player_ranking_terms)

    def _is_available_zones_question(self, question: str) -> bool:
        q = self._q(question)
        return any(k in q for k in [
            "cuales son las zonas de tiro",
            "cuáles son las zonas de tiro",
            "que zonas de tiro hay",
            "qué zonas de tiro hay",
            "zonas disponibles",
            "zonas de lanzamiento",
            "tipos de zona",
            "zonas que existen",
            "zonas registradas"
        ])

    def _resolve_zone_metric(self, question: str) -> str:
        q = self._q(question)


        if any(k in q for k in [
            "acierto", "efectividad", "precision", "precisión",
            "porcentaje de acierto", "% de acierto",
            "mejor acierto", "mayor acierto",
            "mejor efectividad", "mayor efectividad"
        ]):
            return "accuracy_pct"

        if any(k in q for k in [
            "porcentaje de tiro", "porcentaje de tiros",
            "porcentaje de lanzamiento", "porcentaje de lanzamientos",
            "que porcentaje", "qué porcentaje",
            "uso", "utiliza", "usa", "frecuencia",
            "proporcion", "proporción", "peso", "volumen"
        ]):
            return "usage_pct"

        if "porcentaje" in q:
            return "usage_pct"

        if any(k in q for k in [
            "goles", "marca", "anota", "convierte"
        ]):
            return "goals"
        if any(k in q for k in [
            "paradas", "parado", "detenido"
        ]):
            return "saves"
        return "shots"

    def _resolve_team_compare_metric(self, question: str, plan: Optional[Dict[str, Any]] = None, prefer_direct: bool = True) -> Tuple[str, str]:
        q = self._q(question)
        total_mode = any(x in q for x in ["total", "totales", "en total"])

        if any(k in q for k in [
            "encaja mas goles", "encaja más goles", "recibe mas goles", "recibe más goles",
            "mas goles recibidos", "más goles recibidos", "mas goles encajados", "más goles encajados",
            "goles en contra", "defiende peor", "peor defensa"
        ]):
            return ("goals_against" if total_mode else "goals_against_avg", "worst")
        if any(k in q for k in [
            "encaja menos goles", "recibe menos goles", "menos goles en contra",
            "menos goles encajados", "menos goles recibidos", "defiende mejor", "mejor defensa"
        ]):
            return ("goals_against" if total_mode else "goals_against_avg", "best")

        if any(k in q for k in [
            "mete mas goles", "mete más goles", "anota mas goles", "anota más goles",
            "marca mas goles", "marca más goles", "mas goles a favor", "más goles a favor",
            "mas goles anotados", "más goles anotados", "mas goles marcados", "más goles marcados",
            "quién mete más goles", "quien mete mas goles", "mejor ataque"
        ]):
            return ("goals_for" if total_mode else "goals_for_avg", "best")
        if any(k in q for k in [
            "mete menos goles", "anota menos goles", "marca menos goles",
            "menos goles a favor", "menos goles anotados", "menos goles marcados", "peor ataque"
        ]):
            return ("goals_for" if total_mode else "goals_for_avg", "worst")

        if any(k in q for k in ["peor balance", "peor diferencia", "peor balance de goles", "peor diferencia de goles"]):
            return ("goal_difference" if total_mode else "goal_difference_avg", "worst")
        if any(k in q for k in ["mejor balance", "mejor diferencia", "balance de goles", "diferencia de goles"]):
            return ("goal_difference" if total_mode else "goal_difference_avg", "best")

        if any(k in q for k in ["pierde menos", "menos derrotas"]):
            return ("losses", "best")
        if any(k in q for k in ["pierde más", "más derrotas", "mas derrotas"]):
            return ("losses", "worst")
        if any(k in q for k in ["gana más", "gana mas", "más victorias", "mas victorias"]):
            return ("wins", "best")
        if any(k in q for k in ["gana menos", "menos victorias"]):
            return ("wins", "worst")

        if any(k in q for k in ["como local", "como visitante", "local", "visitante", "casa", "fuera"]):
            return ("goals_for_avg", "best")

        if prefer_direct:
            return ("goals_for_avg", "best")

        metric, _, _ = self._infer_team_ranking_spec(question, plan, prefer_direct=prefer_direct)
        return (metric, "best")

    def classify_domain(self, question: str) -> str:
        q = self._q(question)
        player_names = self._extract_player_names_from_question(question)
        team_names = self._extract_team_names_from_question(question)

        exact_player_names = self._extract_exact_player_names_from_question(question)

        if self._is_global_team_metric_question(question) and not exact_player_names:
            return "team"

        if exact_player_names:
            explicit_team_question = any(k in q for k in [
                "equipo", "equipos", "club", "plantilla",
                "distribucion de tiro", "distribución de tiro",
                "zona de tiro", "zonas de tiro",
                "compara", "comparar", "contra", "frente a"
            ])

            if not explicit_team_question:
                return "player"

        player_kw = self._has_player_signal(q)
        team_kw = self._has_team_signal(q)
        player_metric = self._classify_player_direct_metric(q)
        team_metric = self._classify_team_direct_metric(q)


        if self._is_player_ranking_inside_team_question(question):
            return "player"

        if self._has_strong_team_context(question) and team_names:
            return "team"

        if player_names and team_names:
            return "mixed"


        if team_kw and not player_names:
            return "team"

        if player_names and not team_kw:
            return "player"
        if team_names and not player_kw:
            return "team"

        if player_kw and not team_kw:
            return "player"
        if team_kw and not player_kw:
            return "team"

        if player_metric in self.PLAYER_ONLY_METRICS:
            return "player"
        if team_metric in self.TEAM_ONLY_METRICS:
            return "team"

        if any(k in q for k in ["defiende", "defensa", "encaja", "recibe", "mete", "marca", "anota", "goles", "victorias", "derrotas", "empates", "balance", "ranking", "mejor", "peor", "más", "mas", "menos", "quién", "quien", "top"]):
            return "team"

        return "unknown"


    def _fallback_plan(self, question: str, domain: str) -> Dict[str, Any]:
        q = self._q(question)
        top_k = self._extract_top_k(question)
        context = self._get_explicit_context(question)
        result = self._get_explicit_result(question)
        player_names = self._extract_player_names_from_question(question)
        team_names = self._extract_team_names_from_question(question)
        focus = self._infer_focus(question)

        plan: Dict[str, Any] = {
            "domain": domain,
            "intent": "unknown",
            "entity_names": [],
            "metric": None,
            "context": context,
            "result_filter": result,
            "ranking_order": None,
            "ranking_polarity": None,
            "comparison": False,
            "detail_level": "normal",
            "template_id": "unknown",
            "top_k": top_k,
            "confidence": 0.35,
            "focus": focus,
        }

        worst_hint = any(k in q for k in ["peor", "menos", "encaja menos", "recibe menos", "goles en contra",
                                           "derrotas", "pierde más", "pierde mas", "mas derrotas"])
        best_hint = any(k in q for k in ["mejor", "más", "mas", "mete más", "mete mas", "marca más", "marca mas",
                                         "goles a favor", "victorias", "gana más", "gana mas"])

        multi_metrics = []
        if "victorias" in q or "wins" in q:
            multi_metrics.append("wins")
        if "empates" in q or "draws" in q:
            multi_metrics.append("draws")
        if "derrotas" in q or "losses" in q:
            multi_metrics.append("losses")
        if len(multi_metrics) >= 2:
            plan["multi_metrics"] = multi_metrics

        if domain == "player":
            metric = self._classify_player_direct_metric(q) or ("goals_total" if "goles" in q or "gol" in q else "goals_total")
            if len(player_names) >= 2 and any(k in q for k in ["compara", "comparar", "vs", "contra"]):
                plan.update({
                    "intent": "player_compare",
                    "entity_names": player_names,
                    "metric": metric,
                    "comparison": True,
                    "template_id": "two_player_compare",
                })
                return plan
            if len(player_names) == 1:
                plan["entity_names"] = player_names
                plan["metric"] = metric
                plan["intent"] = "player_metric" if metric in self.PLAYER_ONLY_METRICS or top_k == 1 else "player_ranking"
                plan["template_id"] = "player_metrics" if plan["intent"] == "player_metric" else "ranking"
                return plan
            plan["metric"] = metric
            plan["intent"] = "player_ranking"
            plan["template_id"] = "ranking"
            return plan

        if domain == "team":
            metric = self._classify_team_direct_metric(q)
            if len(team_names) >= 2 and self._is_team_comparison_signal(q):
                plan.update({
                    "intent": "best_team",
                    "entity_names": team_names,
                    "metric": metric,
                    "comparison": True,
                    "template_id": "two_team_compare",
                })
                return plan
            if team_names:
                plan["entity_names"] = team_names
                plan["metric"] = metric
                if metric in self.TEAM_ONLY_METRICS:
                    plan["intent"] = metric if metric not in {"goal_difference_avg"} else "best_team"
                else:
                    plan["intent"] = "best_team"
                plan["template_id"] = "team_metrics" if metric in self.TEAM_ONLY_METRICS else "ranking"
            metric_for_polarity = metric or self._classify_team_direct_metric(q)

            if metric_for_polarity in {"goals_against", "goals_against_avg"}:
                if any(k in q for k in [
                    "encaja mas", "recibe mas", "mas goles recibidos", "mas goles encajados",
                    "más goles recibidos", "más goles encajados", "peor defensa"
                ]):
                    plan["ranking_polarity"] = "worst"
                elif any(k in q for k in [
                    "encaja menos", "recibe menos", "menos goles en contra",
                    "menos goles recibidos", "menos goles encajados", "mejor defensa"
                ]):
                    plan["ranking_polarity"] = "best"

            elif metric_for_polarity == "losses":
                if any(k in q for k in ["mas derrotas", "más derrotas", "pierde mas", "pierde más"]):
                    plan["ranking_polarity"] = "worst"
                elif any(k in q for k in ["menos derrotas", "pierde menos"]):
                    plan["ranking_polarity"] = "best"

            elif metric_for_polarity in {"goal_difference", "goal_difference_avg"}:
                if any(k in q for k in ["peor balance", "peor diferencia"]):
                    plan["ranking_polarity"] = "worst"
                elif any(k in q for k in ["mejor balance", "mejor diferencia", "balance de goles"]):
                    plan["ranking_polarity"] = "best"

            elif any(k in q for k in ["peor", "menos", "peor ataque"]):
                plan["ranking_polarity"] = "worst"

            elif any(k in q for k in ["mejor", "mas", "más", "gana mas", "gana más", "victorias", "mejor ataque"]):
                plan["ranking_polarity"] = "best"
            plan["metric"] = metric
            plan["intent"] = "best_team"
            plan["template_id"] = "ranking"

            return plan

        plan["intent"] = "mixed_compare" if any(k in q for k in ["compara", "comparar", "vs", "contra"]) else "mixed_ranking"
        plan["comparison"] = True
        plan["template_id"] = "mixed"
        return plan

    def _resolve_question(self, question: str) -> Dict[str, Any]:
        self._refresh_entities()
        domain = self.classify_domain(question)
        plan = self._fallback_plan(question, domain)

        if self.slm_operational and hasattr(self.slm, "interpret_question"):
            try:
                slm_plan = self.slm.interpret_question(question, self.team_names, self.player_names, domain)
            except Exception:
                slm_plan = None

            if isinstance(slm_plan, dict):
                merged = dict(plan)


                for key in [
                    "domain", "entity_names", "context", "result_filter",
                    "comparison", "detail_level", "template_id", "confidence",
                ]:
                    if key in slm_plan and slm_plan[key] not in (None, "", [], "unknown"):
                        merged[key] = slm_plan[key]

                if merged.get("domain") not in {"player", "team", "mixed"}:
                    merged["domain"] = plan.get("domain", "unknown")


                if plan.get("domain") in {"player", "team", "mixed"}:
                    merged["domain"] = plan["domain"]

                merged["entity_names"] = self._sanitize_entity_names(
                    merged.get("entity_names", []),
                    self.team_names + self.player_names,
                )
                if not merged["entity_names"]:
                    merged["entity_names"] = self._sanitize_entity_names(
                        plan.get("entity_names", []),
                        self.team_names + self.player_names,
                    )


                merged["metric"] = plan.get("metric")
                merged["intent"] = plan.get("intent")
                merged["ranking_order"] = plan.get("ranking_order")
                merged["ranking_polarity"] = plan.get("ranking_polarity")
                merged["top_k"] = plan.get("top_k", 1)
                return merged

        plan["entity_names"] = self._sanitize_entity_names(
            plan.get("entity_names", []),
            self.team_names + self.player_names,
        )
        return plan

    def _player_metric_title(self, metric: str) -> str:
        return {
            "goals_total": "goles",
            "goals_field": "goles de campo",
            "goals_7m": "goles de 7 metros",
            "assists": "asistencias",
            "recoveries": "recuperaciones",
            "losses": "pérdidas",
            "fouls_committed": "faltas cometidas",
            "fouls_received": "faltas recibidas",
            "matches": "partidos",
            "shot_accuracy": "porcentaje de tiro",
            "shots_total": "tiros",
        }.get(metric, metric)

    def _player_prefers_higher(self, metric: str) -> bool:
        return metric not in {"losses"}

    def _rank_players(self, metric: str, descending: bool = True,
                      player_names: Optional[list[str]] = None,
                      team_names: Optional[list[str]] = None,
                      context: Optional[str] = None,
                      min_matches: int = 1) -> list[dict]:
        ranking = self.queries.get_ranked_players(
            metric=metric,
            player_names=player_names,
            team_names=team_names,
            descending=descending,
            min_matches=min_matches,
            context=context,
        )
        return ranking.get("ranking", [])

    def _build_player_data_bundle(self, plan: Dict[str, Any], question: str) -> Dict[str, Any]:
        q = self._q(question)
        direct_metric = self._classify_player_direct_metric(q)
        explicit_zone = self._extract_shot_zone(question)


        if explicit_zone and any(k in q for k in [
            "desde", "zona", "6m", "6-9m", "7m",
            "contraataque", "contrataque", "extremo",
            "porcentaje", "acierto", "efectividad", "como tira",
            "tiro", "tiros", "lanzamiento", "lanzamientos"
        ]):
            direct_metric = "shot_zone_distribution"
        if direct_metric in {"shot_stats", "shot_accuracy", "seven_m_accuracy", "shot_zone_distribution", "minutes_played"}:
            metric = direct_metric
        else:
            metric = plan.get("metric") or direct_metric or "goals_total"
        context = plan.get("context") or self._get_explicit_context(question)

        explicit_names = self._sanitize_entity_names(
            self._extract_player_names_from_question(question),
            self.player_names,
        )
        explicit_team_names = self._sanitize_entity_names(
            self._extract_team_names_from_question(question),
            self.team_names,
        )
        ranking_like = any(k in q for k in [
            "top", "ranking", "clasificacion", "clasificaci",
            "mejor porcentaje", "mayor porcentaje", "jugador con mejor porcentaje",
            "que jugador", "quien", "qui",
        ])
        plan_names = self._sanitize_entity_names(
            [] if ranking_like and not explicit_names else plan.get("entity_names"),
            self.player_names,
        )
        names = self._merge_unique_names(explicit_names, plan_names)

        compare_requested = any(k in q for k in ["compara", "comparar", "vs", "contra"])
        new_stats_metrics = {"minutes_played", "shot_stats", "shot_accuracy", "seven_m_accuracy", "shot_zone_distribution"}

        if metric == "shot_zone_distribution" and not names and ranking_like:
            zone = explicit_zone or self._extract_shot_zone(question)
            zone_metric = self._resolve_zone_metric(question)
            if zone:
                top_k = self._extract_top_k(question)
                ranking = self.queries.compare_players_by_zone(
                    player_names=None,
                    zone=zone,
                    metric=zone_metric,
                    descending=True,
                    min_shots=3 if zone_metric == "accuracy_pct" else 1,
                )
                ranking = self._include_ties_at_cutoff(ranking, top_k)
                return {
                    "mode": "player_zone_ranking",
                    "metric": zone_metric,
                    "zone": zone,
                    "ranking": ranking,
                    "top_k": top_k,
                    "context": context,
                }

        if metric in new_stats_metrics and names and not compare_requested:
            player_name = names[0]
            if metric == "minutes_played":
                return {
                    "mode": "player_minutes",
                    "metric": metric,
                    "context": context,
                    "average": self._asks_average(question),
                    "player": self.queries.get_player_minutes(player_name, context=context),
                }
            if metric == "shot_zone_distribution":
                zone = explicit_zone or self._extract_shot_zone(question)
                zone_metric = self._resolve_zone_metric(question)
                return {
                    "mode": "player_zone_distribution",
                    "metric": metric,
                    "zone_metric": zone_metric,
                    "context": context,
                    "zone": zone,
                    "zones": self.queries.get_player_zone_distribution(player_name, zone=zone, context=context),
                    "player_name": player_name,
                }
            return {
                "mode": "player_shot_stats",
                "metric": metric,
                "context": context,
                "player": self.queries.get_player_shot_stats(player_name, context=context),
            }
        if compare_requested and len(names) >= 2:
            ranking = self._rank_players(
                metric,
                descending=self._player_prefers_higher(metric),
                player_names=names,
                context=context,
            )
            top_k = max(self._extract_top_k(question), len(names))
            return {
                "mode": "player_compare",
                "metric": metric,
                "metric_label": self._player_metric_title(metric),
                "context": context,
                "top_k": top_k,
                "ranking": ranking,
                "compare_names": names,
            }

        if len(explicit_names) == 1 and not compare_requested:
            snap = self.queries.get_player_snapshot(explicit_names[0], context=context)
            return {
                "mode": "player_metric",
                "metric": metric,
                "context": context,
                "player": snap,
            }

        if plan.get("intent") == "player_summary" and names:
            snap = self.queries.get_player_snapshot(names[0], context=context)
            return {
                "mode": "player_summary",
                "metric": metric,
                "context": context,
                "player": snap,
            }

        ranking_names = explicit_names if explicit_names else None
        top_k = self._extract_top_k(question)
        if metric == "shot_accuracy" and not ranking_names and top_k == 1:
            top_k = 3

        ranking = self._rank_players(
            metric,
            descending=self._player_prefers_higher(metric),
            player_names=ranking_names,
            team_names=explicit_team_names if explicit_team_names else None,
            context=context,
        )
        ranking = self._include_ties_at_cutoff(ranking, top_k)
        leaders = [r for r in ranking if ranking and r["score"] == ranking[0]["score"]] if ranking else []
        return {
            "mode": "player_ranking",
            "metric": metric,
            "metric_label": self._player_metric_title(metric),
            "context": context,
            "top_k": top_k,
            "ranking": ranking,
            "leaders": leaders,
            "team_filter": explicit_team_names,
        }

    def _team_metric_title(self, metric: str) -> str:
        return {
            "wins": "victorias",
            "draws": "empates",
            "losses": "derrotas",
            "matches": "partidos",
            "goals_for": "goles a favor",
            "goals_against": "goles en contra",
            "goal_difference": "balance de goles",
            "goals_for_avg": "goles a favor por partido",
            "goals_against_avg": "goles en contra por partido",
            "goal_difference_avg": "balance de goles por partido",
            "attack_composite": "ataque compuesto",
            "defense_composite": "defensa compuesta",
            "solidity_composite": "solidez",
            "team_shot_stats": "porcentaje de tiro",
            "shot_accuracy": "porcentaje de tiro",
            "team_zone_distribution": "zonas de tiro",
        }.get(metric, metric)

    def _zone_metric_label(self, metric: str) -> str:
        return {
            "shots": "tiros",
            "goals": "goles",
            "misses": "fallos",
            "saves": "paradas",
            "blocks": "bloqueos",
            "usage_pct": "porcentaje de uso",
            "accuracy_pct": "porcentaje de acierto",
        }.get(metric, metric)

    def _rank_teams(self, metric: str, descending: bool = True,
                    team_names: Optional[list[str]] = None,
                    context: Optional[str] = None,
                    min_matches: int = 1) -> list[dict]:
        if metric == "team_shot_stats":
            return self.queries.get_ranked_team_shot_accuracy(team_names=team_names, descending=descending)
        ranking = self.queries.get_ranked_teams(
            metric=metric,
            team_names=team_names,
            descending=descending,
            min_matches=min_matches,
            context=context,
        )
        return ranking.get("ranking", [])

    def _team_value(self, snap: dict, metric: str, context: str | None = None) -> float:
        if metric in {"wins", "draws", "losses", "matches"}:
            if context == "home":
                return float(snap.get(metric, {}).get("home", 0))
            if context == "away":
                return float(snap.get(metric, {}).get("away", 0))
            return float(snap.get(metric, {}).get("total", 0))

        goals = snap.get("goals", {})
        bucket = goals.get("home" if context == "home" else "away" if context == "away" else "overall", {})

        if metric == "goals_for":
            return float(bucket.get("gf", 0))
        if metric == "goals_against":
            return float(bucket.get("gc", 0))
        if metric == "goals_for_avg":
            return float(bucket.get("avg_for", 0))
        if metric == "goals_against_avg":
            return float(bucket.get("avg_against", 0))
        if metric == "goal_difference":
            return float(bucket.get("gf", 0)) - float(bucket.get("gc", 0))
        if metric == "goal_difference_avg":
            matches = max(bucket.get("matches", 0), 1)
            return (float(bucket.get("gf", 0)) - float(bucket.get("gc", 0))) / matches
        return 0.0

    def _metric_prefers_higher(self, metric: str, polarity: Optional[str] = None) -> bool:
        lower_is_better = metric in {"losses", "goals_against", "goals_against_avg"}
        default_desc = not lower_is_better
        if polarity == "worst":
            return not default_desc
        return default_desc

    def _attack_specs(self) -> list[Tuple[str, bool, str]]:
        return [
            ("goals_for_avg", True, "goles a favor por partido"),
            ("goal_difference_avg", True, "balance por partido"),
        ]

    def _defense_specs(self) -> list[Tuple[str, bool, str]]:
        return [
            ("goals_against_avg", False, "goles encajados por partido"),
            ("losses", False, "derrotas"),
            ("goal_difference_avg", True, "balance por partido"),
        ]

    def _solidity_specs(self) -> list[Tuple[str, bool, str]]:
        return self._attack_specs() + self._defense_specs()

    def _aggregate_team_ranking(self, team_names: Optional[list[str]],
                                specs: list[Tuple[str, bool, str]],
                                context: Optional[str] = None,
                                top_k: int = 3) -> dict:
        candidates = team_names or self.queries.get_teams_with_matches(min_matches=1) or self.team_names
        candidates = [t for t in candidates if t]
        rows = []
        for team in candidates:
            total_score = 0
            details = []
            for metric, descending, label in specs:
                ranking = self._rank_teams(metric, descending=descending, team_names=candidates, context=context)
                if not ranking:
                    continue
                pos = next((i + 1 for i, row in enumerate(ranking) if row["team_name"] == team), len(ranking) + 1)
                total_score += pos
                details.append({"metric": metric, "position": pos, "label": label})
            rows.append({"team_name": team, "score": total_score, "details": details})
        rows.sort(key=lambda x: (x["score"], x["team_name"].lower()))
        leaders = [r for r in rows if rows and r["score"] == rows[0]["score"]] if rows else []
        return {"ranking": rows, "leaders": leaders, "top_k": top_k, "specs": specs}

    def _infer_team_ranking_spec(self, question: str, plan: Optional[Dict[str, Any]] = None,
                                  prefer_direct: bool = False) -> Tuple[str, str, str]:
        q = self._q(question)
        total_mode = any(x in q for x in ["total", "totales", "en total"])

        if any(k in q for k in [
            "encaja mas goles", "encaja más goles", "recibe mas goles", "recibe más goles",
            "mas goles recibidos", "más goles recibidos", "mas goles encajados", "más goles encajados"
        ]):
            return ("goals_against" if total_mode else "goals_against_avg", "desc", "worst")
        if any(k in q for k in [
            "encaja menos goles", "recibe menos goles", "menos goles en contra",
            "menos goles encajados", "menos goles recibidos"
        ]):
            return ("goals_against" if total_mode else "goals_against_avg", "asc", "best")

        if any(k in q for k in [
            "mete mas goles", "mete más goles", "anota mas goles", "anota más goles",
            "marca mas goles", "marca más goles", "mas goles a favor", "más goles a favor",
            "mas goles anotados", "más goles anotados", "mas goles marcados", "más goles marcados",
            "quien mete mas goles", "quién mete más goles"
        ]):
            return ("goals_for" if total_mode else "goals_for_avg", "desc", "best")
        if any(k in q for k in [
            "mete menos goles", "anota menos goles", "marca menos goles",
            "menos goles a favor", "menos goles anotados", "menos goles marcados"
        ]):
            return ("goals_for" if total_mode else "goals_for_avg", "asc", "worst")

        if any(k in q for k in ["goles a favor", "a favor de goles", "goles anotados", "goles marcados"]):
            return ("goals_for" if total_mode else "goals_for_avg", "desc", "best")
        if any(k in q for k in ["goles en contra", "en contra de goles", "goles recibidos", "goles encajados"]):
            return ("goals_against" if total_mode else "goals_against_avg", "asc", "best")

        if any(k in q for k in ["peor balance", "peor diferencia", "peor balance de goles", "peor diferencia de goles"]):
            return ("goal_difference" if total_mode else "goal_difference_avg", "asc", "worst")
        if any(k in q for k in ["mejor balance", "mejor diferencia", "balance de goles", "diferencia de goles"]):
            return ("goal_difference" if total_mode else "goal_difference_avg", "desc", "best")

        if any(k in q for k in ["pierde menos", "menos derrotas"]):
            return ("losses", "asc", "best")
        if any(k in q for k in ["pierde más", "más derrotas", "mas derrotas"]):
            return ("losses", "desc", "worst")
        if any(k in q for k in ["gana más", "gana mas", "más victorias", "mas victorias"]):
            return ("wins", "desc", "best")
        if any(k in q for k in ["gana menos", "menos victorias"]):
            return ("wins", "asc", "worst")

        if prefer_direct:
            return ("goals_for_avg", "desc", "best")

        if any(k in q for k in ["mejor defensa", "defiende mejor", "defensa más sólida"]):
            return ("defense_composite", "asc", "best")
        if any(k in q for k in ["peor defensa", "defiende peor"]):
            return ("defense_composite", "desc", "worst")
        if any(k in q for k in ["mejor ataque", "mejor atacante"]):
            return ("attack_composite", "desc", "best")
        if any(k in q for k in ["peor ataque"]):
            return ("attack_composite", "asc", "worst")
        if any(k in q for k in ["peor equipo", "equipo más débil"]):
            return ("solidity_composite", "asc", "worst")
        if any(k in q for k in ["más sólido", "mas solido", "sólido", "solido", "va mejor", "mejor equipo", "mejor rendimiento", "top", "ranking"]):
            return ("solidity_composite", "desc", "best")

        return ("goals_for_avg", "desc", "best")

    def _build_two_team_compare_bundle(self, team_a: str, team_b: str, metric: str,
                                       context: Optional[str], result: Optional[str], polarity: Optional[str] = None) -> Dict[str, Any]:
        return {
            "mode": "two_team_compare",
            "metric": metric,
            "ranking_polarity": polarity,
            "context": context,
            "result": result,
            "team_a": team_a,
            "team_b": team_b,
        }

    def _build_goals_avg_by_result_bundle(self, team_names: list[str], result_filters: list[str], context: Optional[str]) -> Dict[str, Any]:
        teams_data = []
        for team in team_names:
            team_res = {"team_name": team, "results": {}}
            for r in result_filters:
                if context:
                    gf, gc, matches = self.queries.get_team_goals_stats(team, context=context, result=r)
                    team_res["results"][r] = {
                        "gf": gf, "gc": gc, "matches": matches,
                        "avg_for": round(gf / matches, 2) if matches else 0.0,
                        "avg_against": round(gc / matches, 2) if matches else 0.0,
                    }
                else:
                    bd = self.queries.get_team_goals_breakdown(team, result=r)
                    overall = dict(bd["overall"])
                    matches = overall.get("matches", 0) or 0
                    gf = overall.get("gf", 0) or 0
                    gc = overall.get("gc", 0) or 0
                    overall["avg_for"] = round(gf / matches, 2) if matches else 0.0
                    overall["avg_against"] = round(gc / matches, 2) if matches else 0.0
                    team_res["results"][r] = overall
            teams_data.append(team_res)
        return {"mode": "goals_avg_by_result", "context": context, "teams": teams_data, "results": result_filters}

    def _build_multi_metric_bundle(self, team_names: list[str], metrics: list[str], context: Optional[str], result: Optional[str]) -> Dict[str, Any]:
        teams_data = []
        for team in team_names:
            snap = self.queries.get_team_snapshot(team)
            data = {"team_name": team, "metrics": {}}
            for m in metrics:
                data["metrics"][m] = self._team_value(snap, m, context=context)
            teams_data.append(data)
        return {"mode": "team_metrics", "metrics_requested": metrics, "teams": teams_data, "context": context, "result": result}

    def _build_defense_multi_bundle(self, context: Optional[str], polarity: str) -> Dict[str, Any]:
        desc = polarity == "worst"
        total = self.queries.get_ranked_teams(metric="goals_against", descending=desc, context=context)
        avg = self.queries.get_ranked_teams(metric="goals_against_avg", descending=desc, context=context)
        losses = self.queries.get_ranked_teams(metric="losses", descending=desc, context=context)
        return {
            "mode": "defense_multi",
            "polarity": polarity,
            "context": context,
            "leaders_total_goals_against": total.get("leaders", []) if total.get("ranking") else [],
            "leaders_avg_goals_against": avg.get("leaders", []) if avg.get("ranking") else [],
            "leaders_losses": losses.get("leaders", []) if losses.get("ranking") else [],
        }

    def _build_combo_attack_defense_bundle(self, context: Optional[str], team_names: Optional[list[str]]) -> Dict[str, Any]:
        attack = self.queries.get_ranked_teams(metric="goals_for_avg", descending=True, context=context, team_names=team_names)
        defense = self.queries.get_ranked_teams(metric="goals_against_avg", descending=False, context=context, team_names=team_names)
        return {
            "mode": "combo_attack_defense",
            "context": context,
            "attack_leaders": attack.get("leaders", []) if attack.get("ranking") else [],
            "defense_leaders": defense.get("leaders", []) if defense.get("ranking") else [],
        }

    def _build_mixed_data_bundle(self, question: str, plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        q = self._q(question)
        top_k = int((plan or {}).get("top_k") or self._extract_top_k(question))
        context = (plan or {}).get("context") or self._get_explicit_context(question)
        result = (plan or {}).get("result_filter") or self._get_explicit_result(question)

        raw_entities = list((plan or {}).get("entity_names") or [])
        player_names = [n for n in raw_entities if n in self.player_names]
        team_names = [n for n in raw_entities if n in self.team_names]

        if not player_names:
            player_names = self._extract_player_names_from_question(question)
        if not team_names:
            team_names = self._extract_team_names_from_question(question)

        player_names = self._sanitize_entity_names(player_names, self.player_names)
        team_names = self._sanitize_entity_names(team_names, self.team_names)

        if not player_names:
            player_names = [r["player_name"] for r in self._rank_players("goals_total", descending=True)[:3]]
        if not team_names:
            if self._infer_focus(question) == "defense":
                team_names = [r["team_name"] for r in self._rank_teams("goals_against_avg", descending=False)[:3]]
            else:
                team_names = [r["team_name"] for r in self._rank_teams("goals_for_avg", descending=True)[:3]]

        return {
            "mode": "mixed",
            "context": context,
            "result": result,
            "top_k": top_k,
            "focus": self._infer_focus(question),
            "player_names": player_names,
            "team_names": team_names,
            "players": [self.queries.get_player_snapshot(p, context=context) for p in player_names],
            "teams": [self.queries.get_team_snapshot(t) for t in team_names],
        }

    def _build_data_bundle(self, plan: Dict[str, Any], question: str) -> Dict[str, Any]:
        domain = plan.get("domain", "unknown")
        intent = plan.get("intent", "unknown")
        q = self._q(question)
        context = plan.get("context") or self._get_explicit_context(question)
        result = plan.get("result_filter") or self._get_explicit_result(question)
        top_k = int(plan.get("top_k") or self._extract_top_k(question))
        entity_names = self._sanitize_entity_names(plan.get("entity_names") or [], self.team_names + self.player_names)

        if domain == "player":
            return self._build_player_data_bundle({**plan, "entity_names": self._sanitize_entity_names(entity_names, self.player_names)}, question)

        if domain == "mixed":
            return self._build_mixed_data_bundle(question, {**plan, "entity_names": entity_names})

        explicit_team_names = self._sanitize_entity_names(
            self._extract_team_names_from_question(question),
            self.team_names,
        )
        ranking_like = any(k in q for k in [
            "top", "ranking", "clasificacion", "clasificaci",
            "mejor porcentaje", "mayor porcentaje", "equipos con mejor porcentaje",
            "que equipo", "quien", "qui",
        ])
        if ranking_like and not explicit_team_names:
            team_names = []
        else:
            team_names = explicit_team_names or self._sanitize_entity_names(entity_names, self.team_names)
        direct_metric = self._classify_team_direct_metric(q)


        if direct_metric in {"wins", "draws", "losses", "matches"} and team_names:
            teams = []
            for team in team_names:
                snap = self.queries.get_team_snapshot(team)
                teams.append({
                    "team_name": team,
                    "value": snap[direct_metric]["total"],
                    "home": snap[direct_metric]["home"],
                    "away": snap[direct_metric]["away"],
                })

            return {
                "mode": "team_metric",
                "metric": direct_metric,
                "metric_label": self._team_metric_title(direct_metric),
                "context": context,
                "teams": teams,
            }

        if direct_metric in {"team_shot_stats", "team_zone_distribution"}:
            metric = direct_metric
        else:
            metric = plan.get("metric") or direct_metric


        zone = self._extract_shot_zone(question)
        zone_question = metric == "team_zone_distribution" or zone is not None

        ranking_question = any(k in q for k in [
            "quien", "quién", "que equipo", "qué equipo",
            "top", "ranking", "clasificacion", "clasificación",
            "más", "mas", "menos", "mejor", "peor",
            "encaja", "recibe", "mete", "marca", "anota",
            "gana", "pierde", "victorias", "derrotas",
            "balance", "diferencia"
        ])

        if ranking_question and not team_names and not zone_question:
            inferred_metric, inferred_order, inferred_polarity = self._infer_team_ranking_spec(
                question,
                plan,
                prefer_direct=False,
            )
            metric = inferred_metric
            plan["ranking_order"] = inferred_order
            plan["ranking_polarity"] = inferred_polarity


        if zone_question and len(explicit_team_names) >= 2:
            zone_metric = self._resolve_zone_metric(question)
            ranking = self.queries.compare_teams_by_zone(
                team_names=explicit_team_names,
                zone=zone,
                metric=zone_metric,
                descending=True,
            )
            return {
                "mode": "team_zone_compare",
                "metric": zone_metric,
                "zone": zone,
                "teams": explicit_team_names,
                "ranking": ranking,
                "top_k": len(explicit_team_names),
            }


        if zone_question and zone and not explicit_team_names:
            zone_metric = self._resolve_zone_metric(question)
            ranking = self.queries.compare_teams_by_zone(
                team_names=None,
                zone=zone,
                metric=zone_metric,
                descending=True,
            )

            count_metric_map = {
                "shots": "shots",
                "goals": "goals",
                "misses": "misses",
                "saves": "saves",
                "blocks": "blocks",
            }

            ranking_by_avg = zone_metric in count_metric_map

            if ranking_by_avg:
                stat_key = count_metric_map[zone_metric]
                enriched = []

                for row in ranking:
                    team_name = row.get("team_name") or row.get("equipo")
                    if not team_name:
                        continue

                    snap = self.queries.get_team_snapshot(team_name)
                    matches = snap.get("matches", {}).get("total", 0) or 0
                    total_value = float(row.get(stat_key, 0) or 0)
                    avg_value = round(total_value / matches, 4) if matches else 0.0

                    row = dict(row)
                    row["matches"] = matches
                    row["score_avg"] = avg_value
                    row["score"] = avg_value
                    enriched.append(row)

                enriched.sort(key=lambda x: (-float(x.get("score_avg", 0) or 0), str(x.get("team_name") or x.get("equipo") or "").lower()))
                ranking = self._include_ties_at_cutoff(enriched, top_k)
            else:
                ranking = self._include_ties_at_cutoff(ranking, top_k)

            return {
                "mode": "team_zone_ranking",
                "metric": zone_metric,
                "zone": zone,
                "ranking": ranking,
                "top_k": top_k,
                "ranking_by_avg": ranking_by_avg,
            }


            if metric == "team_shot_stats" and not team_names:
                ranking = self.queries.get_ranked_team_shot_accuracy(top_k=top_k, descending=True)
                return {
                    "mode": "team_shot_ranking",
                    "metric": metric,
                    "metric_label": "porcentaje de tiro",
                    "ranking": ranking,
                    "leaders": [ranking[0]] if ranking else [],
                    "top_k": top_k,
                    "context": context,
                    "result_filter": result,
                }

        if metric in {"team_shot_stats", "team_zone_distribution"} and team_names:
            if metric == "team_zone_distribution":
                zone = self._extract_shot_zone(question)
                zone_metric = self._resolve_zone_metric(question)
                return {
                    "mode": "team_zone_distribution",
                    "metric": metric,
                    "zone_metric": zone_metric,
                    "context": context,
                    "result_filter": result,
                    "zone": zone,
                    "top_zone": any(k in q for k in [
                        "desde que zona", "de que zona", "zona tira", "zona lanza",
                        "por donde tira", "tira mas desde", "lanza mas desde",
                    ]),
                    "team_name": team_names[0],
                    "zones": self.queries.get_team_zone_distribution(team_names[0], zone=zone, context=context, result=result),
                }
            return {
                "mode": "team_shot_stats",
                "metric": metric,
                "context": context,
                "result_filter": result,
                "team": self.queries.get_team_shot_stats(team_names[0], context=context, result=result),
            }

        if not metric or metric == "best_team" or metric not in self.TEAM_ONLY_METRICS:
            prefer_direct = (len(team_names) == 2 and self._is_team_comparison_signal(q))
            metric, order, polarity = self._infer_team_ranking_spec(question, plan, prefer_direct=prefer_direct)
            plan["ranking_order"] = order
            plan["ranking_polarity"] = polarity

        if plan.get("multi_metrics") and team_names:
            return self._build_multi_metric_bundle(team_names, plan["multi_metrics"], context, result)

        if intent == "summary" and team_names:
            return {"mode": "team_summary", "teams": [self.queries.get_team_snapshot(t) for t in team_names]}

        if intent in {"wins", "draws", "losses", "matches"} and team_names:
            teams = []
            for team in team_names:
                snap = self.queries.get_team_snapshot(team)
                teams.append({
                    "team_name": team,
                    "value": snap[intent]["total"],
                    "home": snap[intent]["home"],
                    "away": snap[intent]["away"],
                })
            return {"mode": "team_metric", "metric": intent, "metric_label": self._team_metric_title(intent), "context": context, "teams": teams}

        if len(team_names) == 2 and self._is_team_comparison_signal(q):
            compare_metric, compare_polarity = self._resolve_team_compare_metric(question, plan, prefer_direct=True)
            return self._build_two_team_compare_bundle(team_names[0], team_names[1], compare_metric, context, result, polarity=compare_polarity)

        if intent == "goals_avg" and team_names and result:
            bundle = self._build_goals_avg_by_result_bundle(team_names, [result], context)
            bundle["goal_focus"] = self._infer_goals_avg_focus(question)
            return bundle

        broad_defense_question = (
            self._infer_focus(question) == "defense"
            and not team_names
            and any(k in q for k in [
                "mejor defensa",
                "peor defensa",
                "defiende mejor",
                "defiende peor",
            ])
        )

        if broad_defense_question:
            polarity = "worst" if any(k in q for k in ["peor", "defiende peor"]) else "best"
            return self._build_defense_multi_bundle(context, polarity)

        if metric == "attack_composite":
            agg = self._aggregate_team_ranking(team_names or None, self._attack_specs(), context=context, top_k=top_k)
            ranking = agg.get("ranking", [])
            polarity = plan.get("ranking_polarity")
            if polarity == "worst":
                ranking = list(reversed(ranking))
                metric_label = "peor ataque"
            else:
                metric_label = "mejor ataque"
            return {"mode": "team_ranking", "ranking_kind": "attack", "metric": metric, "metric_label": metric_label, "ranking": ranking, "leaders": [ranking[0]] if ranking else [], "top_k": top_k, "context": context, "ranking_polarity": polarity}
        if metric == "defense_composite":
            agg = self._aggregate_team_ranking(team_names or None, self._defense_specs(), context=context, top_k=top_k)
            ranking = agg.get("ranking", [])
            polarity = plan.get("ranking_polarity")
            if polarity == "worst":
                ranking = list(reversed(ranking))
                metric_label = "peor defensa"
            else:
                metric_label = "mejor defensa"
            return {"mode": "team_ranking", "ranking_kind": "defense", "metric": metric, "metric_label": metric_label, "ranking": ranking, "leaders": [ranking[0]] if ranking else [], "top_k": top_k, "context": context, "ranking_polarity": polarity}
        if metric == "solidity_composite":
            agg = self._aggregate_team_ranking(team_names or None, self._solidity_specs(), context=context, top_k=top_k)
            ranking = agg.get("ranking", [])
            polarity = plan.get("ranking_polarity")
            if polarity == "worst":
                ranking = list(reversed(ranking))
                metric_label = "peor equipo"
            else:
                metric_label = "equipo más sólido"
            return {"mode": "team_ranking", "ranking_kind": "solidity", "metric": metric, "metric_label": metric_label, "ranking": ranking, "leaders": [ranking[0]] if ranking else [], "top_k": top_k, "context": context, "ranking_polarity": polarity}

        descending = self._metric_prefers_higher(metric, plan.get("ranking_polarity"))
        if plan.get("ranking_order") == "asc":
            descending = False
        elif plan.get("ranking_order") == "desc":
            descending = True

        ranking = self._rank_teams(metric, descending=descending, team_names=team_names or None, context=context)
        if not ranking and not team_names:
            ranking = self._rank_teams(metric, descending=descending, team_names=self.team_names or None, context=context)
        if top_k:
            ranking = self._include_ties_at_cutoff(ranking, top_k)
        leaders = [r for r in ranking if ranking and r["score"] == ranking[0]["score"]] if ranking else []
        return {
            "mode": "team_ranking",
            "ranking_kind": "direct",
            "metric": metric,
            "metric_label": self._team_metric_title(metric),
            "ranking": ranking,
            "leaders": leaders,
            "top_k": top_k,
            "context": context,
            "result_filter": result,
        }


    def _format_player_minutes(self, data: Dict[str, Any]) -> str:
        player = data.get("player")
        if not player:
            return "Todavía no hay una vista con minutos jugados para ese jugador."

        if data.get("average"):
            return (
                f"{player['player_name']} promedia "
                f"{self._format_number(player.get('avg_minutes', 0))} minutos por partido "
                f"({self._format_number(player.get('avg_seconds', 0))} segundos)."
            )

        return (
            f"{player['player_name']} ha jugado {self._format_number(player['minutes'])} minutos "
            f"({self._format_number(player['seconds'])} segundos)."
        )

    def _format_player_shot_stats(self, data: Dict[str, Any]) -> str:
        player = data.get("player")
        if not player:
            return "Todavía no hay una vista con estadísticas ampliadas de lanzamiento para ese jugador."
        metric = data.get("metric")
        shots = player["shots"]
        seven = player["seven_m"]
        if metric == "shot_accuracy":
            return (
                f"{player['player_name']} tiene un {self._format_number(shots['accuracy'])}% de acierto "
                f"en tiros ({shots['scored']}/{shots['total']})."
            )
        if metric == "seven_m_accuracy":
            return (
                f"{player['player_name']} tiene un {self._format_number(seven['accuracy'])}% de acierto "
                f"en 7 metros ({seven['scored']}/{seven['total']})."
            )
        return (
            f"{player['player_name']}: {shots['total']} tiros, {shots['scored']} goles, "
            f"{shots['missed']} fallos y {shots['saved']} parados "
            f"({self._format_number(shots['accuracy'])}% de acierto). "
            f"En 7 m: {seven['scored']}/{seven['total']} "
            f"({self._format_number(seven['accuracy'])}%)."
        )

    def _format_zone_distribution(
        self,
        rows: Optional[list[dict]],
        entity_name: str,
        zone: Optional[str] = None,
        top_zone: bool = False,
        zone_metric: Optional[str] = None,
    ) -> str:
        if not rows:
            if zone:
                return f"No hay datos de tiros de {entity_name} desde {zone}."
            return "Todavía no hay una vista de zonas de tiro disponible para esa consulta."

        zone_metric = zone_metric or "summary"

        if top_zone and rows:
            row = rows[0]
            return (
                f"La zona desde la que más tira {entity_name} es {row['zone']}: "
                f"{row['shots']} tiros, {row['goals']} goles, "
                f"{self._format_number(row['usage_pct'])}% de uso y "
                f"{self._format_number(row['accuracy_pct'])}% de acierto."
            )

        if zone and len(rows) == 1:
            row = rows[0]
            shots = int(row.get("shots", 0) or 0)
            goals = int(row.get("goals", 0) or 0)
            usage = self._format_number(row.get("usage_pct", 0))
            accuracy = self._format_number(row.get("accuracy_pct", 0))

            if zone_metric == "usage_pct":
                return (
                    f"El {usage}% de los tiros de {entity_name} se realizan desde {row['zone']}. "
                    f"En esa zona registra {shots} tiros, {goals} goles y un {accuracy}% de acierto."
                )

            if zone_metric == "accuracy_pct":
                return (
                    f"{entity_name} tiene un {accuracy}% de acierto desde {row['zone']} "
                    f"({goals}/{shots} goles/tiros). Esta zona supone el {usage}% de sus tiros."
                )

            if zone_metric == "goals":
                return (
                    f"{entity_name} ha marcado {goals} goles desde {row['zone']} "
                    f"en {shots} tiros ({accuracy}% de acierto)."
                )

            return (
                f"{entity_name} desde {row['zone']}: {shots} tiros, {goals} goles, "
                f"{row.get('misses', 0)} fallos y {row.get('saves', 0)} paradas "
                f"({accuracy}% de acierto y {usage}% de uso)."
            )

        lines = [f"Distribución de tiro de {entity_name} por zonas:"]
        for row in rows[:6]:
            lines.append(
                f"- {row['zone']}: {row['shots']} tiros, {row['goals']} goles, "
                f"{self._format_number(row['usage_pct'])}% de uso, "
                f"{self._format_number(row['accuracy_pct'])}% de acierto"
            )
        return "\n".join(lines)

    def _format_player_ranking(self, data: Dict[str, Any]) -> str:
        ranking = data.get("ranking", [])
        metric_label = data.get("metric_label") or self._player_metric_title(data.get("metric", "goals_total"))
        top_k = data.get("top_k") or len(ranking)
        team_filter = data.get("team_filter") or []
        team_suffix = f" del {self._join_names(team_filter)}" if team_filter else ""

        if not ranking:
            return f"No hay información disponible para generar el top {top_k} de jugadores con más {metric_label}{team_suffix}."

        if data.get("metric") == "shot_accuracy":
            lines = [f"Top {min(top_k, len(ranking))} en porcentaje de tiro entre jugadores con al menos 3 lanzamientos{team_suffix}:"]
        else:
            lines = [f"Top {min(top_k, len(ranking))} en {metric_label}{team_suffix}:"]
        for idx, row in enumerate(ranking[:top_k], start=1):
            suffix = "%" if data.get("metric") == "shot_accuracy" else f" {metric_label}"
            lines.append(f"{idx}. {row['player_name']}: {self._format_number(row['score'])}{suffix}")
        return "\n".join(lines)

    def _player_metric_value(self, snap: dict, metric: str) -> float:
        if metric == "matches":
            return float(snap.get("matches", 0) or 0)
        if metric == "goals_total":
            return float(snap.get("goals", {}).get("total", 0))
        if metric == "goals_field":
            return float(snap.get("goals", {}).get("field", 0))
        if metric == "goals_7m":
            return float(snap.get("goals", {}).get("seven_m", 0))
        return float(snap.get(metric, {}).get("total", snap.get(metric, 0)))

    def _format_player_metric(self, data: Dict[str, Any]) -> str:
        player = data.get("player")
        if not player:
            return "No he podido identificar el jugador en tu pregunta."
        metric = data.get("metric", "goals_total")
        if metric == "goals_total":
            return f"{player['player_name']} ha conseguido {self._format_number(player['goals']['total'])} goles."
        if metric == "goals_field":
            return f"{player['player_name']} ha conseguido {self._format_number(player['goals']['field'])} goles de campo."
        if metric == "goals_7m":
            return f"{player['player_name']} ha conseguido {self._format_number(player['goals']['seven_m'])} goles de 7 metros."
        if metric == "assists":
            return f"{player['player_name']} ha dado {self._format_number(player['assists']['total'])} asistencias."
        if metric == "recoveries":
            return f"{player['player_name']} ha conseguido {self._format_number(player['recoveries']['total'])} recuperaciones."
        if metric == "losses":
            return f"{player['player_name']} ha cometido {self._format_number(player['losses']['total'])} pérdidas."
        if metric == "fouls_committed":
            return f"{player['player_name']} ha cometido {self._format_number(player['fouls_committed']['total'])} faltas."
        if metric == "fouls_received":
            return f"{player['player_name']} ha recibido {self._format_number(player['fouls_received']['total'])} faltas."
        if metric == "matches":
            n = player.get("matches", 0)
            partido_word = self._plural_es(n, "partido", "partidos")
            return f"{player['player_name']} ha jugado {self._format_number(n)} {partido_word}."

    def _format_player_compare(self, data: Dict[str, Any]) -> str:
        ranking = data.get("ranking", [])
        metric = data.get("metric") or "goals_total"
        metric_label = self._player_metric_title(metric)
        if len(ranking) < 2:
            return "No he podido identificar jugadores suficientes para comparar."
        if len(ranking) == 2:
            first = ranking[0]
            second = ranking[1]
            if abs(float(first["score"]) - float(second["score"])) < 1e-9:
                return f"{first['player_name']} y {second['player_name']} empatan en {metric_label} ({self._format_number(first['score'])})."
            return f"{first['player_name']} está por encima de {second['player_name']} en {metric_label} ({self._format_number(first['score'])} frente a {self._format_number(second['score'])})."
        top_k = data.get("top_k") or len(ranking)
        lines = [f"Top {min(top_k, len(ranking))} en {metric_label} entre los jugadores indicados:"]
        for idx, row in enumerate(ranking[:top_k], start=1):
            lines.append(f"{idx}. {row['player_name']}: {self._format_number(row['score'])} {metric_label}")
        return "\n".join(lines)

    def _format_player_summary(self, data: Dict[str, Any]) -> str:
        player = data.get("player")
        if not player:
            return "No he podido identificar el jugador en tu pregunta."
        return (
            f"{player['player_name']}: {self._format_number(player['goals']['total'])} goles, "
            f"{self._format_number(player['assists']['total'])} asistencias, "
            f"{self._format_number(player['recoveries']['total'])} recuperaciones, "
            f"{self._format_number(player['losses']['total'])} pérdidas y "
            f"{self._format_number(player['matches'])} partidos."
        )


    def _format_team_shot_stats(self, data: Dict[str, Any]) -> str:
        team = data.get("team")
        if not team:
            return "Todavía no hay una vista con estadísticas ampliadas de lanzamiento para ese equipo."
        shots = team["shots"]
        seven = team["seven_m"]
        keeper = team["goalkeeper"]
        return (
            f"{team['team_name']}: {shots['total']} tiros, {shots['scored']} goles, "
            f"{shots['missed']} fallos y {shots['saved']} parados "
            f"({self._format_number(shots['accuracy'])}% de acierto). "
            f"En 7 m: {seven['scored']}/{seven['total']} "
            f"({self._format_number(seven['accuracy'])}%). "
            f"Portería: {keeper['saves']} paradas, {keeper['seven_m_saves']} de 7 m "
            f"({self._format_number(keeper['save_pct'])}% de paradas)."
        )

    def _format_team_shot_ranking(self, data: Dict[str, Any]) -> str:
        ranking = data.get("ranking") or []
        top_k = data.get("top_k") or len(ranking)
        if not ranking:
            return "Todavía no hay datos suficientes para generar el ranking de porcentaje de tiro."
        lines = [f"Top {min(top_k, len(ranking))} equipos con mejor porcentaje de tiro entre equipos con al menos 5 lanzamientos:"]
        for idx, row in enumerate(ranking[:top_k], start=1):
            stats = row["stats"]
            shots = stats["shots"]
            lines.append(
                f"{idx}. {row['team_name']}: {self._format_number(row['score'])}% "
                f"({shots['scored']}/{shots['total']} tiros)"
            )
        return "\n".join(lines)

    def _format_player_zone_ranking(self, data: Dict[str, Any]) -> str:
        ranking = data.get("ranking") or []
        zone = data.get("zone") or "esa zona"
        metric = data.get("metric") or "accuracy_pct"
        top_k = data.get("top_k") or len(ranking)
        label = self._zone_metric_label(metric)

        if not ranking:
            if metric == "accuracy_pct":
                return f"Todavía no hay jugadores con al menos 3 tiros registrados desde {zone} para generar un ranking de acierto."
            return f"Todavía no hay datos suficientes para generar el ranking de jugadores desde {zone}."

        extra_ties = len(ranking) > top_k

        if top_k == 1 and not extra_ties:
            row = ranking[0]
            if metric == "accuracy_pct":
                return (
                    f"El jugador con mejor acierto desde {zone} es {row['player_name']}: "
                    f"{self._format_number(row['accuracy_pct'])}% "
                    f"({self._format_number(row['goals'])}/{self._format_number(row['shots'])} goles/tiros; "
                    f"{self._format_number(row['usage_pct'])}% de uso)."
                )
            if metric == "usage_pct":
                return (
                    f"El jugador que más utiliza la zona {zone} es {row['player_name']}: "
                    f"{self._format_number(row['usage_pct'])}% de sus tiros "
                    f"({self._format_number(row['shots'])} tiros y {self._format_number(row['accuracy_pct'])}% de acierto)."
                )
            return (
                f"El jugador con más {label} desde {zone} es {row['player_name']}: "
                f"{self._format_number(row.get('score', 0))}."
            )

        if metric == "accuracy_pct":
            if extra_ties:
                title = f"Jugadores empatados con el mejor porcentaje de acierto desde {zone} (mínimo 3 tiros):"
            else:
                title = f"Top {min(top_k, len(ranking))} jugadores con mejor porcentaje de acierto desde {zone} (mínimo 3 tiros):"
        elif metric == "usage_pct":
            if extra_ties:
                title = f"Jugadores que más utilizan la zona {zone} (incluyendo empates):"
            else:
                title = f"Top {min(top_k, len(ranking))} jugadores por porcentaje de uso desde {zone}:"
        else:
            title = f"Top {min(top_k, len(ranking))} jugadores en {label} desde {zone}"
            if extra_ties:
                title += " (incluyendo empates)"
            title += ":"

        lines = [title]
        for idx, row in enumerate(ranking, start=1):
            lines.append(
                f"{idx}. {row['player_name']}: "
                f"{self._format_number(row['usage_pct'])}% de uso, "
                f"{self._format_number(row['accuracy_pct'])}% de acierto "
                f"({self._format_number(row['goals'])}/{self._format_number(row['shots'])} goles/tiros)"
            )
        return "\n".join(lines)

    def _format_team_zone_ranking(self, data: Dict[str, Any]) -> str:
        ranking = data.get("ranking") or []
        zone = data.get("zone") or "esa zona"
        metric = data.get("metric") or "shots"
        top_k = data.get("top_k") or len(ranking)

        if not ranking:
            return "Todavía no hay datos suficientes para generar el ranking por zona de tiro."

        def _extract_zone_stats(row: dict) -> dict:
            z = row.get("zone")
            if isinstance(z, dict):
                return {
                    "zone": z.get("zone") or zone,
                    "shots": z.get("shots", 0),
                    "goals": z.get("goals", 0),
                    "misses": z.get("misses", 0),
                    "saves": z.get("saves", 0),
                    "blocks": z.get("blocks", 0),
                    "usage_pct": z.get("usage_pct", 0),
                    "accuracy_pct": z.get("accuracy_pct", 0),
                }
            return {
                "zone": z or zone,
                "shots": row.get("shots", 0),
                "goals": row.get("goals", 0),
                "misses": row.get("misses", 0),
                "saves": row.get("saves", 0),
                "blocks": row.get("blocks", 0),
                "usage_pct": row.get("usage_pct", 0),
                "accuracy_pct": row.get("accuracy_pct", 0),
            }

        def _team_name(row: dict) -> str:
            return row.get("team_name") or row.get("equipo") or "Equipo"

        def _metric_label(metric_name: str) -> str:
            return {
                "shots": "tiros",
                "goals": "goles",
                "misses": "fallos",
                "saves": "paradas",
                "blocks": "bloqueos",
                "usage_pct": "porcentaje de uso",
                "accuracy_pct": "porcentaje de acierto",
            }.get(metric_name, metric_name)

        label = _metric_label(metric)
        extra_ties = len(ranking) > top_k


        if top_k == 1 and not extra_ties:
            row = ranking[0]
            z = _extract_zone_stats(row)
            team = _team_name(row)
            matches = row.get("matches", 0)
            partido_word = self._plural_es(matches, "partido", "partidos")

            if data.get("ranking_by_avg") and "score_avg" in row:
                return (
                    f"El equipo con más {label} por partido desde {zone} es {team}: "
                    f"{self._format_number(row['score_avg'])} por partido "
                    f"({self._format_number(z['shots'])} tiros, "
                    f"{self._format_number(z['goals'])} goles en "
                    f"{self._format_number(matches)} {partido_word}; "
                    f"{self._format_number(z['usage_pct'])}% de uso y "
                    f"{self._format_number(z['accuracy_pct'])}% de acierto)."
                )

            return (
                f"El equipo con más {label} desde {zone} es {team}: "
                f"{self._format_number(z['shots'])} tiros, "
                f"{self._format_number(z['goals'])} goles, "
                f"{self._format_number(z['usage_pct'])}% de uso y "
                f"{self._format_number(z['accuracy_pct'])}% de acierto."
            )

        title = f"Top {top_k} equipos en {label} desde {zone}"
        if data.get("ranking_by_avg"):
            title = f"Top {top_k} equipos en {label} por partido desde {zone}"
        if extra_ties:
            title += " (incluyendo empates)"
        title += ":"

        lines = [title]

        for idx, row in enumerate(ranking, start=1):
            z = _extract_zone_stats(row)

            if data.get("ranking_by_avg") and "score_avg" in row:
                matches = row.get("matches", 0)
                partido_word = self._plural_es(matches, "partido", "partidos")
                lines.append(
                    f"{idx}. {_team_name(row)}: "
                    f"{self._format_number(row['score_avg'])} por partido "
                    f"({self._format_number(z['shots'])} tiros, "
                    f"{self._format_number(z['goals'])} goles en "
                    f"{self._format_number(matches)} {partido_word}; "
                    f"{self._format_number(z['usage_pct'])}% de uso y "
                    f"{self._format_number(z['accuracy_pct'])}% de acierto)"
                )
            else:
                lines.append(
                    f"{idx}. {_team_name(row)}: "
                    f"{self._format_number(z['shots'])} tiros, "
                    f"{self._format_number(z['goals'])} goles, "
                    f"{self._format_number(z['usage_pct'])}% de uso, "
                    f"{self._format_number(z['accuracy_pct'])}% de acierto"
                )

        return "\n".join(lines)

    def _format_available_zones(self, zones: list[str]) -> str:
        if not zones:
            return "No hay zonas de tiro registradas actualmente."

        lines = ["Las zonas de tiro registradas actualmente son:"]
        for zone in zones:
            lines.append(f"- {zone}")
        return "\n".join(lines)

    def _format_team_zone_compare(self, data: Dict[str, Any]) -> str:
        ranking = data.get("ranking", [])
        zone = data.get("zone") or "esa zona"
        metric = data.get("metric") or "shots"
        label = self._zone_metric_label(metric)
        if not ranking:
            return f"No hay datos suficientes para comparar equipos desde {zone}."
        lines = [f"Comparativa de equipos en {label} desde {zone}:"]
        for idx, row in enumerate(ranking, start=1):
            lines.append(
                f"{idx}. {row['team_name']}: "
                f"{row['shots']} tiros, {row['goals']} goles, "
                f"{row['usage_pct']}% de uso y {row['accuracy_pct']}% de acierto"
            )
        return "\n".join(lines)

    def _format_team_metric(self, data: Dict[str, Any]) -> str:
        metric = data.get("metric")
        metric_label = data.get("metric_label") or self._team_metric_title(metric)
        teams = data.get("teams", [])
        if not teams:
            return "No he podido identificar el equipo en tu pregunta."
        if len(teams) == 1 and metric in {"wins", "draws", "losses", "matches"}:
            row = teams[0]
            return f"{metric_label.capitalize()}:\n- {row['team_name']}: {self._format_number(row['value'])}"
        if len(teams) == 1 and metric in {"goals_for", "goals_against", "goal_difference", "goals_for_avg", "goals_against_avg", "goal_difference_avg"}:
            row = teams[0]
            if metric == "goals_for":
                return f"{row['team_name']} ha marcado {self._format_number(row['goals_for'])} goles a favor."
            if metric == "goals_against":
                return f"{row['team_name']} ha encajado {self._format_number(row['goals_against'])} goles."
            if metric == "goal_difference":
                return f"{row['team_name']} tiene un balance de goles de {self._format_number(row['goal_difference'])}."
            if metric == "goals_for_avg":
                return f"{row['team_name']} promedia {self._format_number(row['goals_for_avg'])} goles a favor por partido."
            if metric == "goals_against_avg":
                return f"{row['team_name']} promedia {self._format_number(row['goals_against_avg'])} goles en contra por partido."
            if metric == "goal_difference_avg":
                return f"{row['team_name']} promedia un balance de goles de {self._format_number(row['goal_difference_avg'])} por partido."
        lines = [f"{metric_label.capitalize()}:"]
        for row in teams:
            if metric in {"wins", "draws", "losses", "matches"}:
                lines.append(f"- {row['team_name']}: {self._format_number(row['value'])}")
            elif metric == "goals_for":
                lines.append(f"- {row['team_name']}: {self._format_number(row['goals_for'])} goles a favor")
            elif metric == "goals_against":
                lines.append(f"- {row['team_name']}: {self._format_number(row['goals_against'])} goles en contra")
            elif metric == "goal_difference":
                lines.append(f"- {row['team_name']}: {self._format_number(row['goal_difference'])} de balance")
            elif metric == "goals_for_avg":
                lines.append(f"- {row['team_name']}: {self._format_number(row['goals_for_avg'])} goles a favor por partido")
            elif metric == "goals_against_avg":
                lines.append(f"- {row['team_name']}: {self._format_number(row['goals_against_avg'])} goles en contra por partido")
            elif metric == "goal_difference_avg":
                lines.append(f"- {row['team_name']}: {self._format_number(row['goal_difference_avg'])} de balance por partido")
            else:
                lines.append(f"- {row['team_name']}: {self._format_number(row.get('value', 0))}")
        return "\n".join(lines)

    def _format_team_ranking(self, data: Dict[str, Any]) -> str:
        ranking = data.get("ranking", [])
        metric = data.get("metric")
        metric_label = data.get("metric_label") or self._team_metric_title(metric)
        top_k = data.get("top_k") or len(ranking)
        ranking_kind = data.get("ranking_kind")
        if not ranking:
            if metric_label:
                return f"No se encontraron equipos para mostrar el ranking de {metric_label}."
            return "No hay datos suficientes para mostrar el ranking."
        display_ranking = self._include_ties_at_cutoff(ranking, top_k)

        extra_ties = len(display_ranking) > top_k
        title = f"Top {top_k} en {metric_label}"
        if extra_ties:
            title += " (incluyendo empates)"
        title += ":"

        if ranking_kind in {"attack", "defense", "solidity"}:
            lines = [title]
            for idx, row in enumerate(display_ranking, start=1):
                details = ", ".join([f"{d['label']}: {d['position']}" for d in row.get("details", [])])
                lines.append(
                    f"{idx}. {row['team_name']}: {self._format_number(row['score'])} puntos ({details})"
                )
            return "\n".join(lines)

        lines = [title]
        for idx, row in enumerate(display_ranking, start=1):
            lines.append(f"{idx}. {row['team_name']}: {self._format_number(row['score'])}")
        return "\n".join(lines)

    def _format_team_compare(self, team_a: str, team_b: str, metric: str,
                             context: Optional[str] = None, result: Optional[str] = None, polarity: Optional[str] = None) -> str:
        snap_a = self.queries.get_team_snapshot(team_a)
        snap_b = self.queries.get_team_snapshot(team_b)
        val_a = self._team_value(snap_a, metric, context=context)
        val_b = self._team_value(snap_b, metric, context=context)
        label = self._team_metric_title(metric)
        if abs(float(val_a) - float(val_b)) < 1e-9:
            return f"{team_a} y {team_b} empatan en {label} ({self._format_number(val_a)})."
        prefers_higher = self._metric_prefers_higher(metric, polarity)
        if (prefers_higher and val_a > val_b) or ((not prefers_higher) and val_a < val_b):
            winner, loser, wv, lv = team_a, team_b, val_a, val_b
        else:
            winner, loser, wv, lv = team_b, team_a, val_b, val_a
        suffix = ""
        if context == "home":
            suffix = " como local"
        elif context == "away":
            suffix = " como visitante"
        return f"{winner} está por encima de {loser} en {label}{suffix} ({self._format_number(wv)} frente a {self._format_number(lv)})."

    def _summary_text(self, snap: dict) -> str:
        if not snap:
            return "No se pudieron generar datos."
        wins = snap.get("wins", {}).get("total", 0)
        draws = snap.get("draws", {}).get("total", 0)
        losses = snap.get("losses", {}).get("total", 0)
        matches = snap.get("matches", {}).get("total", 0)
        goals = snap.get("goals", {}).get("overall", {})
        gf = goals.get("gf", 0)
        gc = goals.get("gc", 0)
        home = snap.get("goals", {}).get("home", {})
        away = snap.get("goals", {}).get("away", {})
        diff = snap.get("goal_difference", gf - gc)
        return (
            f"{snap.get('team_name', 'Equipo')}: {self._format_number(wins)} victorias, "
            f"{self._format_number(draws)} empates y {self._format_number(losses)} derrotas en {self._format_number(matches)} partidos. "
            f"Ha marcado {self._format_number(gf)} goles y ha recibido {self._format_number(gc)}. "
            f"En casa ha marcado {self._format_number(home.get('gf', 0))} y recibido {self._format_number(home.get('gc', 0))}. "
            f"Fuera de casa ha marcado {self._format_number(away.get('gf', 0))} y recibido {self._format_number(away.get('gc', 0))}. "
            f"Su diferencial de goles es de {self._format_number(diff)}."
        )

    def _format_team_summary(self, data: Dict[str, Any]) -> str:
        teams = data.get("teams") or []
        if not teams:
            return "No he podido identificar el equipo en tu pregunta."
        if len(teams) == 1:
            return self._summary_text(teams[0])
        parts = [self._summary_text(team) for team in teams]
        return "\n\n".join(parts)

    def _include_ties_at_cutoff(self, ranking: list[dict], top_k: int) -> list[dict]:
        if not ranking:
            return []

        if not top_k or top_k >= len(ranking):
            return ranking

        selected = ranking[:top_k]
        cutoff_score = float(selected[-1].get("score", 0))

        for row in ranking[top_k:]:
            if abs(float(row.get("score", 0)) - cutoff_score) < 1e-9:
                selected.append(row)
            else:
                break

        return selected

    def _format_goals_avg_by_result(self, data: Dict[str, Any]) -> str:
        teams = data.get("teams", [])
        result_filters = data.get("results", [])
        context = data.get("context")
        goal_focus = data.get("goal_focus", "both")
        if not teams:
            return "No he podido identificar los equipos."
        if not result_filters:
            return "No he podido identificar los resultados a comparar."
        result_labels = {"win": "Victorias", "loss": "Derrotas", "draw": "Empates"}
        sections = []
        for result in result_filters:
            lines = [f"{result_labels[result]}:"]
            for team in teams:
                result_data = team["results"].get(result)
                if not result_data or result_data.get("matches", 0) == 0:
                    lines.append(f"- {team['team_name']} no registra datos suficientes.")
                    continue

                avg_for = self._format_number(result_data.get("avg_for", 0))
                avg_against = self._format_number(result_data.get("avg_against", 0))
                ctx_label = ""
                if context:
                    ctx_label = " como local" if context == "home" else " como visitante"
                result_label = result_labels[result].lower()

                if goal_focus == "for":
                    lines.append(
                        f"- {team['team_name']} promedia {avg_for} goles a favor{ctx_label} en {result_label}."
                    )
                elif goal_focus == "against":
                    lines.append(
                        f"- {team['team_name']} promedia {avg_against} goles en contra{ctx_label} en {result_label}."
                    )
                else:
                    lines.append(
                        f"- {team['team_name']} promedia {avg_for} goles a favor y "
                        f"{avg_against} en contra{ctx_label} en {result_label}."
                    )
            sections.append("\n".join(lines))
        return "\n\n".join(sections)

    def _format_multi_metric(self, data: Dict[str, Any]) -> str:
        teams = data.get("teams", [])
        metrics = data.get("metrics_requested", [])
        if not teams:
            return "No he podido identificar los equipos."
        if not metrics:
            return "No he podido identificar qué métricas quieres comparar."
        blocks = []
        for metric in metrics:
            title = self._team_metric_title(metric).capitalize()
            lines = [f"{title}:"]
            for row in teams:
                value = row["metrics"].get(metric, 0)
                if metric == "goals_for":
                    lines.append(f"- {row['team_name']}: {self._format_number(value)} goles a favor")
                elif metric == "goals_against":
                    lines.append(f"- {row['team_name']}: {self._format_number(value)} goles en contra")
                elif metric == "goal_difference":
                    lines.append(f"- {row['team_name']}: {self._format_number(value)} de balance")
                elif metric == "goals_for_avg":
                    lines.append(f"- {row['team_name']}: {self._format_number(value)} goles a favor por partido")
                elif metric == "goals_against_avg":
                    lines.append(f"- {row['team_name']}: {self._format_number(value)} goles en contra por partido")
                elif metric == "goal_difference_avg":
                    lines.append(f"- {row['team_name']}: {self._format_number(value)} de balance por partido")
                else:
                    lines.append(f"- {row['team_name']}: {self._format_number(value)}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def _format_defense_multi(self, data: Dict[str, Any]) -> str:
        polarity = data.get("polarity", "best")
        context = data.get("context")
        title = "Peor defensa" if polarity == "worst" else "Mejor defensa"
        total = data.get("leaders_total_goals_against") or []
        avg = data.get("leaders_avg_goals_against") or []
        losses = data.get("leaders_losses") or []
        lines = [f"{title}:"]
        if total:
            names = self._join_names([t["team_name"] for t in total])
            lines.append(f"- Goles encajados totales: {names} ({self._format_number(total[0]['score'])})")
        if avg:
            names = self._join_names([t["team_name"] for t in avg])
            lines.append(f"- Goles encajados por partido: {names} ({self._format_number(avg[0]['score'])})")
        if losses:
            names = self._join_names([t["team_name"] for t in losses])
            lines.append(f"- Derrotas: {names} ({self._format_number(losses[0]['score'])})")
        if context == "home":
            lines.append("- Contexto considerado: local.")
        elif context == "away":
            lines.append("- Contexto considerado: visitante.")
        return "\n".join(lines)

    def _format_combo_attack_defense(self, data: Dict[str, Any]) -> str:
        attack = data.get("attack_leaders") or []
        defense = data.get("defense_leaders") or []
        lines = []
        if attack:
            names = self._join_names([t["team_name"] for t in attack])
            lines.append(f"Mejor ataque: {names} ({self._format_number(attack[0]['score'])}).")
        if defense:
            names = self._join_names([t["team_name"] for t in defense])
            lines.append(f"Mejor defensa: {names} ({self._format_number(defense[0]['score'])}).")
        if not lines:
            return "No hay datos suficientes para comparar ataque y defensa."
        return "\n".join(lines)

    def _format_mixed(self, data: Dict[str, Any]) -> str:
        parts = []
        players = data.get("players") or []
        teams = data.get("teams") or []
        player_names = data.get("player_names", [])
        team_names = data.get("team_names", [])

        if players:
            lines = ["Jugadores:"]
            for snap in players:
                name = snap.get("player_name", "Jugador")
                lines.append(
                    f"- {name}: {self._format_number(snap.get('goals_total', 0))} goles, "
                    f"{self._format_number(snap.get('assists', 0))} asistencias, "
                    f"{self._format_number(snap.get('recoveries', 0))} recuperaciones y "
                    f"{self._format_number(snap.get('matches', 0))} partidos."
                )
            parts.append("\n".join(lines))
        elif player_names:
            player_ranking = self._rank_players("goals_total", descending=True, player_names=player_names)
            if player_ranking:
                lines = ["Jugadores:"]
                for idx, row in enumerate(player_ranking[:3], start=1):
                    lines.append(f"{idx}. {row['player_name']}: {self._format_number(row['score'])} goles")
                parts.append("\n".join(lines))

        if teams:
            lines = ["Equipos:"]
            for snap in teams:
                name = snap.get("team_name", "Equipo")
                wins = snap.get("wins", {}).get("total", 0)
                draws = snap.get("draws", {}).get("total", 0)
                losses = snap.get("losses", {}).get("total", 0)
                matches = snap.get("matches", {}).get("total", 0)
                goals = snap.get("goals", {}).get("overall", {})
                diff = snap.get("goal_difference", goals.get("gf", 0) - goals.get("gc", 0))
                lines.append(
                    f"- {name}: {self._format_number(wins)} victorias, "
                    f"{self._format_number(draws)} empates y {self._format_number(losses)} derrotas "
                    f"en {self._format_number(matches)} partidos; "
                    f"{self._format_number(goals.get('gf', 0))} goles a favor, "
                    f"{self._format_number(goals.get('gc', 0))} en contra y "
                    f"{self._format_number(diff)} de balance."
                )
            parts.append("\n".join(lines))
        elif team_names:
            team_ranking = self._rank_teams("goals_for_avg", descending=True, team_names=team_names)
            if team_ranking:
                lines = ["Equipos:"]
                for idx, row in enumerate(team_ranking[:3], start=1):
                    lines.append(f"{idx}. {row['team_name']}: {self._format_number(row['score'])} goles a favor por partido")
                parts.append("\n".join(lines))

        if not parts:
            return "No he podido generar una respuesta mixta."
        return "\n\n".join(parts)

    def _build_facts_for_redaction(self, question: str, plan: Dict[str, Any], data: Dict[str, Any]) -> str:
        mode = data.get("mode")
        lines = [f"Modo: {mode}"]

        if mode == "team_summary":
            for snap in data.get("teams") or []:
                lines.append(self._summary_text(snap))
            return "\n".join(lines)

        if mode == "goals_avg_by_result":
            lines.append(self._format_goals_avg_by_result(data))
            return "\n".join(lines)

        if mode == "two_team_compare":
            q = self._q(question)
            specific_terms = [
                "goles", "encaja", "recibe", "marca", "mete", "anota",
                "victorias", "derrotas", "empates", "partidos",
                "balance", "diferencia", "acierto", "tiros", "zona",
            ]
            if not any(k in q for k in specific_terms):
                lines.append("Comparativa general de equipos:")
                for team in [data.get("team_a"), data.get("team_b")]:
                    if team:
                        lines.append(self._summary_text(self.queries.get_team_snapshot(team)))
                return "\n".join(lines)

            lines.append(self._format_team_compare(
                data["team_a"], data["team_b"], data["metric"],
                context=data.get("context"),
                result=data.get("result"),
                polarity=data.get("ranking_polarity"),
            ))
            return "\n".join(lines)

        if mode == "defense_multi":
            lines.append(self._format_defense_multi(data))
            return "\n".join(lines)

        if mode == "combo_attack_defense":
            lines.append(self._format_combo_attack_defense(data))
            return "\n".join(lines)

        if mode == "mixed":
            lines.append(self._format_mixed(data))
            return "\n".join(lines)


        try:
            if mode == "team_metric":
                lines.append(self._format_team_metric(data))
            elif mode == "team_ranking":
                lines.append(self._format_team_ranking(data))
            elif mode == "player_metric":
                lines.append(self._format_player_metric(data))
            elif mode == "player_ranking":
                lines.append(self._format_player_ranking(data))
            else:
                lines.append(str(data))
        except Exception:
            lines.append(str(data))
        return "\n".join(lines)

    def _extract_numeric_literals(self, text: str) -> set[str]:
        if not text:
            return set()
        raw = re.findall(r"(?<![A-Za-zÁÉÍÓÚáéíóúÑñ#])-?\d+(?:[\.,]\d+)?%?", str(text))
        out = set()
        for item in raw:
            clean = item.replace(",", ".")
            if clean.endswith("%"):
                num = clean[:-1]
                suffix = "%"
            else:
                num = clean
                suffix = ""
            try:
                value = float(num)
                if value.is_integer():
                    clean = str(int(value)) + suffix
                else:
                    clean = f"{value:.2f}".rstrip("0").rstrip(".") + suffix
            except Exception:
                pass
            out.add(clean)
        return out

    def _slm_answer_respects_facts(self, facts: str, answer: str) -> bool:
        if not facts or not answer:
            return False
        fact_nums = self._extract_numeric_literals(facts)
        answer_nums = self._extract_numeric_literals(answer)
        extra_nums = answer_nums - fact_nums
        if extra_nums:
            return False
        return True

    def _slm_redact(self, question: str, plan: Dict[str, Any], data_bundle: Dict[str, Any]) -> Optional[str]:
        if not self.slm_operational:
            return None
        if not hasattr(self.slm, "generate_answer"):
            return None
        try:
            safe_bundle = dict(data_bundle or {})
            facts = self._build_facts_for_redaction(question, plan, data_bundle or {})
            safe_bundle["FACTS_OBLIGATORIOS"] = facts
            answer = self.slm.generate_answer(question, plan, safe_bundle)
            if answer and self._slm_answer_respects_facts(facts, answer):
                return answer
            return None
        except Exception as e:
            return None


    def _handle_player_question(self, question: str) -> Optional[str]:
        try:


            q = self._q(question)
            explicit_zone = self._extract_shot_zone(question)
            if explicit_zone and any(k in q for k in [
                "desde", "zona", "6m", "6-9m", "7m",
                "contraataque", "contrataque", "extremo",
                "porcentaje", "acierto", "efectividad", "como tira",
                "tiro", "tiros", "lanzamiento", "lanzamientos"
            ]):
                zone_metric = self._resolve_zone_metric(question)
                context = self._get_explicit_context(question)


                exact_players = self._sanitize_entity_names(
                    self._extract_exact_player_names_from_question(question),
                    self.player_names,
                )

                ranking_like = any(k in q for k in [
                    "que jugador", "qué jugador", "quien", "quién",
                    "top", "ranking", "clasificacion", "clasificación",
                    "mejor", "mayor", "mas", "más", "menos"
                ])

                if exact_players:
                    player_name = exact_players[0]
                    rows = self.queries.get_player_zone_distribution(
                        player_name,
                        zone=explicit_zone,
                        context=context,
                    )
                    return self._format_zone_distribution(
                        rows,
                        player_name,
                        explicit_zone,
                        zone_metric=zone_metric,
                    )

                if ranking_like or self._has_player_signal(q):
                    top_k = self._extract_top_k(question)
                    descending = zone_metric not in {"misses", "saves"}
                    ranking = self.queries.compare_players_by_zone(
                        player_names=None,
                        zone=explicit_zone,
                        metric=zone_metric,
                        descending=descending,
                        min_shots=3 if zone_metric == "accuracy_pct" else 1,
                    )
                    ranking = self._include_ties_at_cutoff(ranking, top_k)
                    return self._format_player_zone_ranking({
                        "mode": "player_zone_ranking",
                        "metric": zone_metric,
                        "zone": explicit_zone,
                        "ranking": ranking,
                        "top_k": top_k,
                        "context": context,
                    })

            plan = self._resolve_question(question)
            if plan.get("domain") not in {"player", "mixed"} and not self._extract_player_names_from_question(question):
                return None
            data_bundle = self._build_player_data_bundle(plan, question)
            mode = data_bundle.get("mode")
            if mode == "player_minutes":
                return self._format_player_minutes(data_bundle)
            if mode == "player_shot_stats":
                return self._format_player_shot_stats(data_bundle)
            if mode == "player_zone_distribution":
                return self._format_zone_distribution(
                    data_bundle.get("zones"),
                    data_bundle.get("player_name") or "el jugador",
                    data_bundle.get("zone"),
                    zone_metric=data_bundle.get("zone_metric"),
                )
            if mode == "player_zone_ranking":
                return self._format_player_zone_ranking(data_bundle)
            if mode == "player_ranking":
                return self._format_player_ranking(data_bundle)
            if mode == "player_metric":
                return self._format_player_metric(data_bundle)
            if mode == "player_compare":
                return self._format_player_compare(data_bundle)
            if mode == "player_summary":
                return self._format_player_summary(data_bundle)
            return None
        except Exception as e:
            return "Error al procesar la pregunta de jugador."

    def _handle_team_question(self, question: str) -> Optional[str]:
        try:
            plan = self._resolve_question(question)
            if plan.get("domain") not in {"team", "mixed", "unknown"} and not self._extract_team_names_from_question(question):
                return None
            data_bundle = self._build_data_bundle(plan, question)
            mode = data_bundle.get("mode")


            if self.slm_operational and mode in {
                "team_summary",
                "goals_avg_by_result",
                "two_team_compare",
                "defense_multi",
                "combo_attack_defense",
            }:
                slm_answer = self._slm_redact(question, plan, data_bundle)
                if slm_answer:
                    return slm_answer
            if mode == "team_ranking":
                return self._format_team_ranking(data_bundle)
            if mode == "team_shot_stats":
                return self._format_team_shot_stats(data_bundle)
            if mode == "team_shot_ranking":
                return self._format_team_shot_ranking(data_bundle)
            if mode == "team_zone_distribution":
                return self._format_zone_distribution(
                    data_bundle.get("zones"),
                    data_bundle.get("team_name") or "el equipo",
                    data_bundle.get("zone"),
                    data_bundle.get("top_zone", False),
                    data_bundle.get("zone_metric"),
                )
            if mode == "team_zone_compare":
                return self._format_team_zone_compare(data_bundle)
            if mode == "team_zone_ranking":
                return self._format_team_zone_ranking(data_bundle)
            if mode == "team_metric":
                return self._format_team_metric(data_bundle)
            if mode == "team_summary":
                return self._format_team_summary(data_bundle)
            if mode in {"team_metrics", "multi_metric"}:
                return self._format_multi_metric(data_bundle)
            if mode == "goals_avg_by_result":
                return self._format_goals_avg_by_result(data_bundle)
            if mode == "two_team_compare":
                return self._format_team_compare(
                    data_bundle["team_a"],
                    data_bundle["team_b"],
                    data_bundle["metric"],
                    context=data_bundle.get("context"),
                    result=data_bundle.get("result"),
                    polarity=data_bundle.get("ranking_polarity"),
                )
            if mode == "defense_multi":
                return self._format_defense_multi(data_bundle)
            if mode == "combo_attack_defense":
                return self._format_combo_attack_defense(data_bundle)
            return None
        except Exception as e:
            return "Error al procesar la pregunta de equipo."

    def _handle_mixed_question(self, question: str) -> str:
        try:
            plan = self._resolve_question(question)
            data_bundle = self._build_mixed_data_bundle(question, plan)
            if self.slm_operational:
                slm_answer = self._slm_redact(question, plan, data_bundle)
                if slm_answer:
                    return slm_answer
            return self._format_mixed(data_bundle)
        except Exception as e:
            return "Error al procesar la pregunta mixta."


    def process_question(self, question: str) -> str:
        try:
            self._refresh_entities()


            if self._is_available_zones_question(question):
                zones = self.queries.get_available_shot_zones()
                return self._format_available_zones(zones)


            if self._is_direct_team_zone_question(question):
                answer = self._handle_team_question(question)
                if answer and "Error" not in answer and "No he podido" not in answer:
                    return answer


            if self._is_explicit_mixed_question(question):
                return self._handle_mixed_question(question)


            if self._is_goals_avg_by_result_question(question):
                return self._answer_goals_avg_by_result_question(question)


            if self._is_team_summary_question(question):
                return self._answer_team_summary_question(question)


            if self._is_direct_team_count_question(question):
                return self._answer_direct_team_count_question(question)


            if self._is_direct_team_ranking_question(question):
                return self._answer_direct_team_ranking_question(question)

            domain = self.classify_domain(question)


            if domain == "player":
                answer = self._handle_player_question(question)
                if answer and "Error" not in answer:
                    return answer
                return "No he podido procesar tu consulta sobre jugadores."

            if domain == "team":
                answer = self._handle_team_question(question)
                if answer and "Error" not in answer:
                    return answer
                return "No he podido procesar tu consulta sobre equipos."

            if domain == "mixed":
                return self._handle_mixed_question(question)

            q = self._q(question)
            if self._has_team_signal(q) or self._classify_team_direct_metric(q) or any(k in q for k in ["quien", "quién", "mejor", "peor", "top", "ranking", "defiende", "ataque", "goles", "victorias", "derrotas", "empates", "balance"]):
                answer = self._handle_team_question(question)
                if answer and "Error" not in answer and "No he podido" not in answer:
                    return answer

            if self._has_player_signal(q) or self._classify_player_direct_metric(q):
                answer = self._handle_player_question(question)
                if answer and "Error" not in answer and "No he podido" not in answer:
                    return answer

            if self._extract_player_names_from_question(question) and self._extract_team_names_from_question(question):
                return self._handle_mixed_question(question)

            return (
                "No he podido determinar si tu pregunta se refiere a jugadores o equipos. "
                "Por favor, especifica si buscas información de un jugador o de un equipo."
            )

        except Exception as e:
            return "Lo siento, ha ocurrido un error interno al procesar tu pregunta. Por favor, inténtalo de nuevo."
