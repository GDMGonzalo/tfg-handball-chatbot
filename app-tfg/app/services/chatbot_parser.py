import re
import unicodedata
from difflib import get_close_matches, SequenceMatcher


class ChatbotParser:
    def __init__(self, team_names=None, player_names=None):
        self.team_names = team_names or []
        self.player_names = player_names or []

    @staticmethod
    def _normalize(text: str) -> str:
        text = unicodedata.normalize("NFKD", str(text))
        text = "".join(c for c in text if not unicodedata.combining(c))
        text = text.lower().strip()
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", text.lower())

    def _fuzzy_contains_any(self, text: str, phrases: list[str], threshold: float = 0.84) -> bool:
        if not text:
            return False

        q = self._normalize(text)
        q_tokens = self._tokenize(q)

        for phrase in phrases:
            p = self._normalize(phrase)
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

    def _best_team_matches(self, question_normalized: str) -> list[str]:
        if not self.team_names:
            return []

        q_tokens = self._tokenize(question_normalized)
        q_token_set = set(q_tokens)
        found = []

        for team in self.team_names:
            team_norm = self._normalize(team)
            if team_norm and team_norm in question_normalized:
                found.append(team)

        for team in self.team_names:
            if team in found:
                continue
            team_tokens = self._tokenize(self._normalize(team))
            if not team_tokens:
                continue
            if len(set(team_tokens) & q_token_set) > 0:
                found.append(team)

        normalized_team_tokens = {team: self._tokenize(self._normalize(team)) for team in self.team_names}
        for team in self.team_names:
            if team in found:
                continue

            team_tokens = normalized_team_tokens.get(team, [])
            if not team_tokens:
                continue

            matched = False
            for qtok in q_tokens:
                if len(qtok) < 4:
                    continue
                for ttok in team_tokens:
                    if len(ttok) < 4:
                        continue
                    if SequenceMatcher(None, qtok, ttok).ratio() >= 0.80:
                        found.append(team)
                        matched = True
                        break
                if matched:
                    break

        if not found:
            matches = get_close_matches(
                question_normalized,
                [self._normalize(t) for t in self.team_names],
                n=3,
                cutoff=0.72,
            )
            for m in matches:
                for team in self.team_names:
                    if self._normalize(team) == m and team not in found:
                        found.append(team)

        unique = []
        for team in found:
            if team not in unique:
                unique.append(team)
        return unique

    def _best_player_matches(self, question_normalized: str) -> list[str]:
        if not self.player_names:
            return []

        q_tokens = self._tokenize(question_normalized)
        q_token_set = set(t for t in q_tokens if not t.isdigit())
        found = []


        for player in self.player_names:
            player_norm = self._normalize(player)
            if player_norm and player_norm in question_normalized:
                found.append(player)


        for player in self.player_names:
            if player in found:
                continue
            player_tokens = [t for t in self._tokenize(self._normalize(player)) if not t.isdigit()]
            if player_tokens and set(player_tokens) & q_token_set:
                found.append(player)


        for player in self.player_names:
            if player in found:
                continue
            player_tokens = [t for t in self._tokenize(self._normalize(player)) if not t.isdigit()]
            if not player_tokens:
                continue

            matched = False
            for qtok in q_tokens:
                if len(qtok) < 4:
                    continue
                for ptok in player_tokens:
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
                return re.sub(r"\s*\(\#?\d+\)\s*$", "", str(name)).strip()

            clean_map = {}
            for player in self.player_names:
                clean = _clean_player_name(player)
                if clean:
                    clean_map[clean] = player

            for clean, original in clean_map.items():
                clean_norm = self._normalize(clean)
                if clean_norm and clean_norm in question_normalized:
                    found.append(original)

            for clean, original in clean_map.items():
                if original in found:
                    continue
                ctokens = [t for t in self._tokenize(self._normalize(clean)) if not t.isdigit()]
                if ctokens and set(ctokens) & q_token_set:
                    found.append(original)

            for clean, original in clean_map.items():
                if original in found:
                    continue
                ctokens = [t for t in self._tokenize(self._normalize(clean)) if not t.isdigit()]
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

        unique = []
        for item in found:
            if item not in unique:
                unique.append(item)
        return unique

    def extract_team_names(self, question: str) -> list[str]:
        return self._best_team_matches(self._normalize(question))

    def extract_player_names(self, question: str) -> list[str]:
        return self._best_player_matches(self._normalize(question))

    def parse(self, question: str):
        q = self._normalize(question)
        team_names = self._best_team_matches(q)
        team = team_names[0] if team_names else None

        context = None
        if self._fuzzy_contains_any(q, ["local", "casa"], threshold=0.80):
            context = "home"
        elif self._fuzzy_contains_any(q, ["visitante", "fuera"], threshold=0.80):
            context = "away"

        result = None
        if self._fuzzy_contains_any(q, ["victoria", "victorias", "ganado", "gano", "ganó", "gana", "ganar", "vicotria", "vicotrias"], threshold=0.80):
            result = "win"
        elif self._fuzzy_contains_any(q, ["derrota", "derrotas", "perdido", "perdio", "perdió", "pierde", "perder"], threshold=0.80):
            result = "loss"
        elif self._fuzzy_contains_any(q, ["empate", "empates", "empatado", "empato", "empató", "empata", "empatar"], threshold=0.80):
            result = "draw"

        if any(
            k in q
            for k in [
                "promedio de goles",
                "media de goles",
                "goles de media",
                "goles de promedio",
                "cuantos goles de media",
                "cuántos goles de media",
                "promedia goles",
                "goles promedio",
                "promedio goleador",
                "cuantos goles mete de media",
                "cuántos goles mete de media",
            ]
        ):
            return "goals_avg", team, context, result

        if self._fuzzy_contains_any(
            q,
            [
                "quien es el mejor",
                "quién es el mejor",
                "mejor equipo",
                "mejor rendimiento",
                "quien gana mas",
                "quién gana más",
                "gana más",
                "gana mas",
                "mejor defensa",
                "defiende mejor",
                "recibe menos goles",
                "encaja menos goles",
                "menos goles en contra",
                "goles en contra",
                "quien recibe menos goles",
                "quién recibe menos goles",
                "quien encaja menos goles",
                "quién encaja menos goles",
                "quien mete más goles",
                "quien mete mas goles",
                "que equipo tiene mas goles",
                "qué equipo tiene mas goles",
                "que equipo tiene más goles",
                "qué equipo tiene más goles",
                "más sólido",
                "mas solido",
                "sólido",
                "solido",
                "va mejor",
                "top",
            ],
            threshold=0.82,
        ):
            return "best_team", team, context, result

        if self._fuzzy_contains_any(q, ["victorias", "ganado", "gano", "ganó", "gana", "ganar"], threshold=0.80):
            return "wins", team, context, None
        if self._fuzzy_contains_any(q, ["empates", "empatado", "empato", "empató", "empata", "empatar"], threshold=0.80):
            return "draws", team, context, None
        if self._fuzzy_contains_any(q, ["derrotas", "perdido", "perdio", "perdió", "pierde", "perder"], threshold=0.80):
            return "losses", team, context, None
        if self._fuzzy_contains_any(q, ["partidos", "jugado", "jugó", "ha jugado"], threshold=0.80):
            return "matches", team, context, None

        return None, team, context, result
