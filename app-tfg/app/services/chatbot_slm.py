import json
import os
import re
import urllib.request
from typing import Any, Dict, List, Optional


class ChatbotSLM:

    VALID_DOMAINS = {"player", "team", "mixed", "unknown"}
    VALID_INTENTS = {

        "wins", "draws", "losses", "matches", "goals_avg", "summary", "best_team",

        "player_ranking", "player_metric", "player_summary", "player_compare",
        "player_minutes", "player_shot_distribution", "player_shot_accuracy",

        "mixed_ranking", "mixed_compare",
    }
    VALID_CONTEXTS = {"home", "away"}
    VALID_RESULTS = {"win", "loss", "draw"}
    VALID_RANKING_METRICS = {

        "wins", "draws", "losses", "matches",
        "goals_for", "goals_against", "goal_difference",
        "goals_for_avg", "goals_against_avg", "goal_difference_avg",
        "attack_composite", "defense_composite", "solidity_composite",

        "goals_total", "goals_field", "goals_7m", "assists",
        "recoveries", "losses", "fouls_committed", "fouls_received",
        "minutes_played", "shot_stats", "shot_accuracy", "seven_m_accuracy",
        "shot_zone_distribution", "team_shot_stats", "team_zone_distribution",
    }
    VALID_RANKING_ORDERS = {"asc", "desc"}
    VALID_RANKING_POLARITIES = {"best", "worst"}
    VALID_DETAIL_LEVELS = {"brief", "normal", "detailed"}
    VALID_TEMPLATE_IDS = {
        "ranking", "summary", "team_metrics", "player_metrics",
        "two_team_compare", "two_player_compare", "multi_metric",
        "goals_avg_by_result", "combo_attack_defense", "defense_multi", "mixed", "unknown",
    }

    def __init__(self):
        self.base_url = os.getenv("SLM_BASE_URL", "").rstrip("/")
        self.api_key = os.getenv("SLM_API_KEY", "")
        self.model = os.getenv("SLM_MODEL", "")
        self.timeout = int(os.getenv("SLM_TIMEOUT", "20"))
        self._last_ping_ok = None
        self._last_ping_error = None

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.model)

    def status(self) -> Dict[str, Any]:
        return {
            "configured": self.enabled,
            "base_url": self.base_url,
            "model": self.model,
            "last_ping_ok": self._last_ping_ok,
            "last_ping_error": self._last_ping_error,
        }

    def ping(self, force: bool = False) -> bool:
        if not self.enabled:
            self._last_ping_ok = False
            self._last_ping_error = "SLM no configurado"
            return False

        if self._last_ping_ok is not None and not force:
            return self._last_ping_ok

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Responde solo con OK."},
                {"role": "user", "content": "ping"},
            ],
            "temperature": 0.0,
            "max_tokens": 4,
        }

        data = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                parsed = json.loads(raw)
                ok = bool(parsed)
                self._last_ping_ok = ok
                self._last_ping_error = None
                return ok
        except Exception as exc:
            self._last_ping_ok = False
            self._last_ping_error = str(exc)
            return False

    def is_operational(self) -> bool:
        return self.enabled and self.ping()

    def _post_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 300,
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        data = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None
        text = text.strip()
        try:
            return json.loads(text)
        except Exception:
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None

    def _validate_and_clean(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        domain = raw.get("domain", "unknown")
        if domain not in self.VALID_DOMAINS:
            domain = "unknown"

        intent = raw.get("intent")
        if intent not in self.VALID_INTENTS:
            intent = "unknown"

        context = raw.get("context")
        if context not in self.VALID_CONTEXTS:
            context = None

        result = raw.get("result")
        if result not in self.VALID_RESULTS:
            result = None

        ranking_metric = raw.get("metric") or raw.get("ranking_metric")
        if ranking_metric not in self.VALID_RANKING_METRICS:
            ranking_metric = None

        ranking_order = raw.get("ranking_order")
        if ranking_order not in self.VALID_RANKING_ORDERS:
            ranking_order = None

        ranking_polarity = raw.get("ranking_polarity")
        if ranking_polarity not in self.VALID_RANKING_POLARITIES:
            ranking_polarity = None

        detail_level = raw.get("detail_level", "normal")
        if detail_level not in self.VALID_DETAIL_LEVELS:
            detail_level = "normal"

        template_id = raw.get("template_id", "unknown")
        if template_id not in self.VALID_TEMPLATE_IDS:
            template_id = "unknown"

        try:
            confidence = float(raw.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = 0.0

        entity_names_out: List[str] = []
        raw_entities = raw.get("entity_names") or raw.get("team_names") or raw.get("player_names")
        if isinstance(raw_entities, list):
            for item in raw_entities:
                if item and str(item).strip().lower() not in {"null", "none", ""}:
                    name = str(item).strip()
                    if name not in entity_names_out:
                        entity_names_out.append(name)

        top_k = raw.get("top_k", 1)
        try:
            top_k = int(top_k)
        except (TypeError, ValueError):
            top_k = 1
        top_k = max(1, min(top_k, 20))

        comparison = bool(raw.get("comparison")) or len(entity_names_out) > 1

        return {
            "domain": domain,
            "intent": intent,
            "entity_names": entity_names_out,
            "metric": ranking_metric,
            "context": context,
            "result_filter": result,
            "ranking_order": ranking_order,
            "ranking_polarity": ranking_polarity,
            "comparison": comparison,
            "detail_level": detail_level,
            "template_id": template_id,
            "confidence": confidence,
            "top_k": top_k,
        }

    def interpret_question(
        self,
        question: str,
        team_names: List[str],
        player_names: Optional[List[str]] = None,
        domain: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None

        player_names = player_names or []
        teams_preview = ", ".join(team_names[:80]) if team_names else "sin equipos cargados"
        players_preview = ", ".join(player_names[:80]) if player_names else "sin jugadores cargados"
        domain = domain or "unknown"

        system_prompt = (
            "Eres el orquestador semántico de un chatbot estadístico de balonmano. "
            "Devuelve SOLO JSON válido. Sin texto adicional, sin markdown. "
            "Tu único trabajo es clasificar la intención y extraer entidades. "
            "No generes respuestas ni estadísticas."
        )

        user_prompt = f"""Pregunta:
{question}

Dominio preclasificado:
{domain}

Equipos disponibles:
{teams_preview}

Jugadores disponibles:
{players_preview}

Devuelve exactamente este JSON:
{{
  "domain": "player|team|mixed|unknown",
  "intent": "wins|draws|losses|matches|goals_avg|summary|best_team|player_ranking|player_metric|player_summary|player_compare|player_minutes|player_shot_distribution|player_shot_accuracy|mixed_ranking|mixed_compare",
  "entity_names": ["nombres exactos"],
  "metric": "wins|draws|losses|matches|goals_for|goals_against|goal_difference|goals_for_avg|goals_against_avg|goal_difference_avg|attack_composite|defense_composite|solidity_composite|goals_total|goals_field|goals_7m|assists|recoveries|fouls_committed|fouls_received|minutes_played|shot_stats|shot_accuracy|seven_m_accuracy|shot_zone_distribution|team_shot_stats|team_zone_distribution|null",
  "context": "home|away|null",
  "result": "win|loss|draw|null",
  "ranking_order": "asc|desc|null",
  "ranking_polarity": "best|worst|null",
  "comparison": false,
  "detail_level": "brief|normal|detailed",
  "template_id": "ranking|summary|team_metrics|player_metrics|two_team_compare|two_player_compare|multi_metric|goals_avg_by_result|combo_attack_defense|defense_multi|mixed|unknown",
  "top_k": 1,
  "confidence": 0.0
}}

Reglas:
- Si domain="player", usa intents de jugador.
- Si domain="team", usa intents de equipo.
- Si domain="mixed", divide la respuesta en jugador/equipo y usa intents mixtos.
- Si la pregunta dice "top N", llena top_k con N.
- Si la pregunta habla de ataque/defensa, elige la métrica más coherente.
- No inventes nombres ni métricas.
"""

        response = self._post_chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=350,
        )

        if not response:
            return None

        try:
            content = response["choices"][0]["message"]["content"]
        except Exception:
            return None

        raw = self._extract_json(content)
        if not raw:
            return None
        return self._validate_and_clean(raw)

    def generate_answer(
        self,
        question: str,
        plan: Dict[str, Any],
        data_bundle: Dict[str, Any],
    ) -> Optional[str]:
        if not self.enabled:
            return None

        facts = ""
        if isinstance(data_bundle, dict):
            facts = str(data_bundle.get("FACTS_OBLIGATORIOS") or "").strip()

        if not facts:


            return None

        system_prompt = """Eres el redactor final de un chatbot de análisis estadístico de balonmano.

Tu tarea es responder al usuario en español natural usando EXCLUSIVAMENTE la ficha factual recibida.

REGLAS OBLIGATORIAS:
- La ficha factual es la única fuente de verdad.
- Debes conservar todos los nombres y números importantes que aparezcan en la ficha.
- No inventes nombres, valores, partidos, porcentajes, rankings ni conclusiones no presentes.
- No escribas ningún número que no aparezca literalmente en la ficha factual.
- No cambies la métrica: si la ficha habla de victorias, responde sobre victorias; si habla de acierto, responde sobre acierto.
- No recalcules nada y no sustituyas promedios por totales.
- Si la ficha dice "promedia X goles", la respuesta debe mantener ese promedio X.
- Si la ficha contiene varios equipos o jugadores, no omitas entidades relevantes.
- Si hay empate, menciónalo de forma natural.
- No menciones JSON, SQL, backend, ficha factual, plan, métricas internas ni campos técnicos.

ESTILO:
- Respuesta breve, clara y natural.
- Puedes redactar con más fluidez que una plantilla, pero sin alterar el significado.
- Evita frases genéricas si la ficha contiene valores concretos.
"""

        user_prompt = f"""Pregunta original:
{question}

Ficha factual obligatoria:
{facts}

Redacta la respuesta final para el usuario usando solo esa ficha factual. Si no puedes mejorar la redacción sin alterar datos, reescribe la ficha de forma muy cercana.
"""

        response = self._post_chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=550,
        )

        if not response:
            return None

        try:
            content = response["choices"][0]["message"]["content"].strip()
            return content or None
        except Exception:
            return None
