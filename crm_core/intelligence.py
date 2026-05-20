"""Local CRM intelligence helpers built on pandas and numpy.

The models here are intentionally offline and explainable. They use CRM data
already stored in SQLite to produce practical guidance without sending records
to an external AI service.
"""

from __future__ import annotations

import math
import re
import sqlite3
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from crm_core.matching import smart_match_score as shared_smart_match_score

try:
    import numpy as np
    import pandas as pd
    from sklearn.neural_network import MLPRegressor
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover
    np = None
    pd = None
    MLPRegressor = None
    ConvergenceWarning = None
    TfidfVectorizer = None
    cosine_similarity = None
    AI_LIBS_AVAILABLE = False
else:
    AI_LIBS_AVAILABLE = True


STOP_WORDS = {
    "and", "or", "the", "for", "with", "from", "this", "that", "have",
    "has", "need", "needs", "want", "wants", "required", "requirement",
    "available", "availability", "property", "properties", "rent", "sale",
    "flat", "house", "home", "plot", "apartment", "villa", "room", "bed",
    "beds", "bath", "baths", "sqft", "sq", "ft", "yard", "yards", "rs",
    "near", "area", "location", "client", "owner", "family", "bachelor",
}

DEAL_STAGES = ["Lead", "Contacted", "Visit Scheduled", "Negotiation", "Closed", "Deal Done"]
PRIORITY_SCORE = {"Urgent": 1.0, "High": 0.82, "Medium": 0.55, "Low": 0.3}
STAGE_SCORE = {
    "Lead": 0.25,
    "Contacted": 0.42,
    "Visit Scheduled": 0.62,
    "Negotiation": 0.82,
    "Closed": 0.9,
    "Deal Done": 1.0,
}


@dataclass
class MatchCandidate:
    source: str
    target_id: Any
    candidate_id: Any
    score: float
    name: str
    location: str
    amount: float
    reasons: list[str]


class IntelligenceService:
    def __init__(self, db_path: Path | str, *, currency_symbol: str = "Rs.", company_name: str = "Real Estate CRM"):
        self.db_path = Path(db_path)
        self.currency_symbol = currency_symbol
        self.company_name = company_name

    def generate_report(self) -> str:
        if not AI_LIBS_AVAILABLE:
            return (
                "AI libraries are not installed.\n\n"
                "Install pandas and numpy, then rebuild/run the app:\n"
                "    python -m pip install pandas numpy\n"
            )

        frames = self._load_frames()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        sections = [
            "=" * 84,
            "LOCAL AI INTELLIGENCE REPORT",
            f"Company: {self.company_name}",
            f"Generated: {now}",
            "=" * 84,
            "",
            "Models used: pandas profiling, numpy regression, local NLP token scoring,",
            "MLP-style lead scoring, z-score anomaly detection, and trend forecasting.",
            "All analysis is offline on the local SQLite database.",
            "",
        ]
        sections.extend(self._executive_summary(frames))
        sections.extend(self._lead_scoring_section(frames))
        sections.extend(self._price_guidance_section(frames))
        sections.extend(self._matching_section(frames))
        sections.extend(self._nlp_section(frames))
        sections.extend(self._duplicate_section(frames))
        sections.extend(self._financial_forecast_section(frames))
        sections.extend(self._anomaly_section(frames))
        sections.extend(self._recommendations_section(frames))
        return "\n".join(sections).rstrip() + "\n"

    def match_report(self, table: str, row_id: int) -> str:
        if not AI_LIBS_AVAILABLE:
            return "AI matching requires pandas and numpy."
        frames = self._load_frames()
        table = table.lower()
        if table not in frames or frames[table].empty:
            return "No source table data found."
        source = frames[table]
        target_rows = source[source["id"].astype(str) == str(row_id)]
        if target_rows.empty:
            return f"No record found for {table} #{row_id}."
        target = target_rows.iloc[0].to_dict()
        counterpart = self._counterpart_table(table)
        if not counterpart or counterpart not in frames or frames[counterpart].empty:
            return "No matching counterpart data found."

        candidates = []
        for candidate in frames[counterpart].to_dict("records"):
            score, reasons = self._match_score(target, candidate, table, counterpart)
            if score > 0:
                candidates.append(
                    MatchCandidate(
                        source=counterpart,
                        target_id=row_id,
                        candidate_id=candidate.get("id"),
                        score=score,
                        name=str(candidate.get("client_name") or candidate.get("owner_name") or "-"),
                        location=str(candidate.get("location") or "-"),
                        amount=self._amount_for_row(candidate, counterpart),
                        reasons=reasons,
                    )
                )
        candidates.sort(key=lambda item: item.score, reverse=True)

        lines = [
            f"AI smart matches for {table} #{row_id}",
            "=" * 84,
            "Scoring uses location similarity, property text overlap, size hints, and budget fit.",
            "",
        ]
        if not candidates:
            lines.append("No close matches found.")
            return "\n".join(lines)
        for item in candidates[:12]:
            reasons = ", ".join(item.reasons[:3]) or "general similarity"
            lines.append(
                f"{item.score:5.1f}%  #{item.candidate_id:<5} {item.name[:24]:<24} "
                f"{item.location[:20]:<20} {self._money(item.amount):>13}  {reasons}"
            )
        return "\n".join(lines)

    def _load_frames(self) -> dict[str, Any]:
        tables = [
            "rent_requirements", "rent_availability", "sale_requirements", "sale_availability",
            "clients", "properties", "income_transactions", "expense_transactions", "employees",
        ]
        frames: dict[str, Any] = {}
        with sqlite3.connect(self.db_path) as conn:
            for table in tables:
                try:
                    frames[table] = pd.read_sql_query(f"SELECT * FROM {table}", conn)
                except Exception:
                    frames[table] = pd.DataFrame()
        return frames

    def _executive_summary(self, frames: dict[str, Any]) -> list[str]:
        rent_req = len(frames["rent_requirements"])
        rent_av = len(frames["rent_availability"])
        sale_req = len(frames["sale_requirements"])
        sale_av = len(frames["sale_availability"])
        income = self._sum_amount(frames["income_transactions"], "amount")
        expenses = self._sum_amount(frames["expense_transactions"], "amount")
        profit = income - expenses
        return [
            "EXECUTIVE SUMMARY",
            "-" * 84,
            f"Rent demand/supply: {rent_req} requirements vs {rent_av} available records",
            f"Sale demand/supply: {sale_req} requirements vs {sale_av} available records",
            f"Financial position: income {self._money(income)}, expenses {self._money(expenses)}, net {self._money(profit)}",
            "",
        ]

    def _lead_scoring_section(self, frames: dict[str, Any]) -> list[str]:
        rows = []
        mlp_model = self._train_mlp_model(frames)
        
        for table in ("rent_requirements", "rent_availability", "sale_requirements", "sale_availability"):
            for row in frames[table].to_dict("records"):
                score, reasons = self._lead_score(row, table, frames, mlp_model)
                rows.append((score, table, row, reasons))
        rows.sort(key=lambda item: item[0], reverse=True)
        lines = [
            "MLP-STYLE LEAD SCORING",
            "-" * 84,
            "Highest action priority records. Score blends completeness, recency, stage, priority,",
            "approval state, deal value, and available match pressure.",
            "",
        ]
        if not rows:
            lines.extend(["No deal records available.", ""])
            return lines
        for score, table, row, reasons in rows[:12]:
            name = row.get("client_name") or row.get("owner_name") or "-"
            stage = row.get("workflow_stage") or "Lead"
            priority = row.get("priority") or "Medium"
            amount = self._amount_for_row(row, table)
            lines.append(
                f"{score:5.1f}%  {self._short_source(table):<9} #{row.get('id'):<5} "
                f"{str(name)[:23]:<23} {stage[:16]:<16} {priority[:7]:<7} "
                f"{self._money(amount):>13}  {', '.join(reasons[:3])}"
            )
        lines.append("")
        return lines

    def _price_guidance_section(self, frames: dict[str, Any]) -> list[str]:
        lines = ["REGRESSION PRICE GUIDANCE", "-" * 84]
        for kind, req_table, av_table, amount_col, label in (
            ("rent", "rent_requirements", "rent_availability", "monthly_rent", "Rent"),
            ("sale", "sale_requirements", "sale_availability", "demand", "Sale"),
        ):
            model = self._fit_price_model(frames[av_table], amount_col)
            lines.append(f"{label} model: {model['summary']}")
            if model["ready"] and not frames[req_table].empty:
                predictions = []
                for row in frames[req_table].to_dict("records"):
                    predicted = self._predict_price(model, row)
                    current = self._amount_for_row(row, req_table)
                    gap = current - predicted if current else 0
                    predictions.append((abs(gap), gap, predicted, current, row))
                predictions.sort(key=lambda item: item[0], reverse=True)
                for _abs_gap, gap, predicted, current, row in predictions[:5]:
                    name = row.get("client_name") or "-"
                    location = row.get("location") or "-"
                    budget_note = "budget above model" if gap > 0 else "budget below model"
                    if not current:
                        budget_note = "missing budget"
                    lines.append(
                        f"  {self._short_source(req_table):<9} #{row.get('id'):<5} {str(name)[:22]:<22} "
                        f"{str(location)[:18]:<18} model {self._money(predicted):>12} "
                        f"current {self._money(current):>12}  {budget_note}"
                    )
            lines.append("")
        return lines

    def _matching_section(self, frames: dict[str, Any]) -> list[str]:
        lines = ["DEMAND / SUPPLY MATCHING", "-" * 84]
        pairs = [
            ("rent_requirements", "rent_availability"),
            ("rent_availability", "rent_requirements"),
            ("sale_requirements", "sale_availability"),
            ("sale_availability", "sale_requirements"),
        ]
        matches = []
        for left, right in pairs:
            for row in frames[left].to_dict("records")[:80]:
                best = None
                for candidate in frames[right].to_dict("records")[:160]:
                    score, reasons = self._match_score(row, candidate, left, right)
                    if best is None or score > best[0]:
                        best = (score, candidate, reasons)
                if best and best[0] >= 45:
                    matches.append((best[0], left, row, right, best[1], best[2]))
        matches.sort(key=lambda item: item[0], reverse=True)
        if not matches:
            lines.extend(["No strong demand/supply matches yet.", ""])
            return lines
        for score, left, row, right, candidate, reasons in matches[:12]:
            left_name = row.get("client_name") or row.get("owner_name") or "-"
            right_name = candidate.get("client_name") or candidate.get("owner_name") or "-"
            lines.append(
                f"{score:5.1f}%  {self._short_source(left)} #{row.get('id')} {str(left_name)[:18]:<18} -> "
                f"{self._short_source(right)} #{candidate.get('id')} {str(right_name)[:18]:<18} "
                f"{', '.join(reasons[:3])}"
            )
        lines.append("")
        return lines

    def _nlp_section(self, frames: dict[str, Any]) -> list[str]:
        lines = ["NLP KEYWORDS AND MARKET LANGUAGE", "-" * 84]
        for label, tables in (
            ("Rent market", ("rent_requirements", "rent_availability")),
            ("Sale market", ("sale_requirements", "sale_availability")),
            ("Properties", ("properties",)),
        ):
            counter = Counter()
            for table in tables:
                for row in frames[table].to_dict("records"):
                    counter.update(self._tokens(self._row_text(row)))
            keywords = ", ".join(f"{word} ({count})" for word, count in counter.most_common(14))
            lines.append(f"{label}: {keywords or 'not enough text data'}")
        lines.append("")
        return lines

    def _duplicate_section(self, frames: dict[str, Any]) -> list[str]:
        lines = ["DUPLICATE / DATA CLEANUP RISKS", "-" * 84]
        contact_map: dict[str, list[str]] = defaultdict(list)
        for table in ("clients", "rent_requirements", "rent_availability", "sale_requirements", "sale_availability"):
            for row in frames[table].to_dict("records"):
                contact = self._normalize_contact(row.get("phone") or row.get("contact") or row.get("contact_phone"))
                if contact:
                    name = row.get("client_name") or row.get("owner_name") or row.get("full_name") or "-"
                    contact_map[contact].append(f"{self._short_source(table)} #{row.get('id')} {name}")
        duplicates = [(contact, refs) for contact, refs in contact_map.items() if len(refs) > 1]
        duplicates.sort(key=lambda item: len(item[1]), reverse=True)
        if not duplicates:
            lines.extend(["No duplicate phone/contact clusters found.", ""])
            return lines
        for contact, refs in duplicates[:10]:
            lines.append(f"{contact}: " + " | ".join(refs[:5]))
        lines.append("")
        return lines

    def _financial_forecast_section(self, frames: dict[str, Any]) -> list[str]:
        lines = ["FINANCIAL TREND FORECAST", "-" * 84]
        income_forecast = self._monthly_forecast(frames["income_transactions"], "transaction_date", "amount")
        expense_forecast = self._monthly_forecast(frames["expense_transactions"], "transaction_date", "amount")
        lines.append(f"Next-month income estimate:  {income_forecast}")
        lines.append(f"Next-month expense estimate: {expense_forecast}")
        lines.append("")
        return lines

    def _anomaly_section(self, frames: dict[str, Any]) -> list[str]:
        lines = ["PRICE OUTLIERS", "-" * 84]
        found = False
        for table, amount_col in (("rent_availability", "monthly_rent"), ("sale_availability", "demand")):
            df = frames[table]
            if df.empty or amount_col not in df:
                continue
            amounts = self._numeric(df[amount_col])
            valid = df[amounts > 0].copy()
            amounts = amounts[amounts > 0]
            if len(amounts) < 4 or amounts.std() == 0:
                continue
            z = (amounts - amounts.mean()) / amounts.std()
            for idx in z[abs(z) >= 1.5].index[:10]:
                row = valid.loc[idx].to_dict()
                direction = "high" if z.loc[idx] > 0 else "low"
                found = True
                lines.append(
                    f"{self._short_source(table):<9} #{row.get('id'):<5} {direction:<4} outlier "
                    f"{self._money(row.get(amount_col)):<14} {str(row.get('location') or '-')[:24]}"
                )
        if not found:
            lines.append("No strong price outliers detected yet.")
        lines.append("")
        return lines

    def _recommendations_section(self, frames: dict[str, Any]) -> list[str]:
        lines = ["RECOMMENDED ACTIONS", "-" * 84]
        actions = 0
        rent_gap = len(frames["rent_requirements"]) - len(frames["rent_availability"])
        sale_gap = len(frames["sale_requirements"]) - len(frames["sale_availability"])
        if rent_gap > 0:
            lines.append(f"Rent side has {rent_gap} more requirements than availability. Add owner inventory in top NLP locations.")
            actions += 1
        if sale_gap > 0:
            lines.append(f"Sale side has {sale_gap} more requirements than availability. Prioritize seller listings.")
            actions += 1
        incomplete = 0
        for table in ("rent_requirements", "rent_availability", "sale_requirements", "sale_availability"):
            for row in frames[table].to_dict("records"):
                if self._completeness(row, table) < 0.55:
                    incomplete += 1
        if incomplete:
            lines.append(f"{incomplete} deal records are low-completeness. Fill contact, location, type, amount, and notes before matching.")
            actions += 1
        if not actions:
            lines.append("Keep adding clean amounts, sizes, locations, and outcomes. Regression quality improves as records grow.")
        lines.append("")
        return lines

    def _lead_score(self, row: dict[str, Any], table: str, frames: dict[str, Any], model: Any = None) -> tuple[float, list[str]]:
        completeness = self._completeness(row, table)
        recency = self._recency_score(row)
        priority = PRIORITY_SCORE.get(str(row.get("priority") or "Medium"), 0.55)
        stage = STAGE_SCORE.get(str(row.get("workflow_stage") or "Lead"), 0.25)
        amount = self._amount_for_row(row, table)
        amount_score = min(1.0, math.log10(max(amount, 1)) / 7.5) if amount else 0.15
        approval = 1.0 if str(row.get("approval_status") or "").lower() == "approved" else 0.58
        match_pressure = self._match_pressure(row, table, frames)
        features = np.array([completeness, recency, priority, stage, amount_score, approval, match_pressure], dtype=float)
        
        if model is not None:
            score = max(0.0, min(100.0, float(model.predict([features])[0]) * 100))
        else:
            score = self._mlp_score(features)
            
        reasons = []
        if priority >= 0.8:
            reasons.append("high priority")
        if stage >= 0.75:
            reasons.append("late-stage deal")
        if match_pressure >= 0.65:
            reasons.append("good match supply")
        if completeness < 0.55:
            reasons.append("needs data cleanup")
        if recency > 0.75:
            reasons.append("recent activity")
        if not reasons:
            reasons.append("steady follow-up")
        return score, reasons

    def _train_mlp_model(self, frames: dict[str, Any]) -> Any:
        if MLPRegressor is None:
            return None
        X = []
        y = []
        for table in ("rent_requirements", "rent_availability", "sale_requirements", "sale_availability"):
            for row in frames[table].to_dict("records"):
                X.append([
                    self._completeness(row, table),
                    self._recency_score(row),
                    PRIORITY_SCORE.get(str(row.get("priority") or "Medium"), 0.55),
                    STAGE_SCORE.get(str(row.get("workflow_stage") or "Lead"), 0.25),
                    min(1.0, math.log10(max(self._amount_for_row(row, table), 1)) / 7.5) if self._amount_for_row(row, table) else 0.15,
                    1.0 if str(row.get("approval_status") or "").lower() == "approved" else 0.58,
                    self._match_pressure(row, table, frames)
                ])
                # Target is probability
                y.append(float(row.get("deal_probability") or STAGE_PROBABILITY.get(str(row.get("workflow_stage") or "Lead"), 10.0)) / 100.0)
        if len(X) < 12 or len({round(value, 3) for value in y}) < 2:
            return None
        model = MLPRegressor(
            hidden_layer_sizes=(8,),
            solver="lbfgs",
            alpha=0.01,
            max_iter=1000,
            random_state=42,
        )
        try:
            with warnings.catch_warnings():
                if ConvergenceWarning is not None:
                    warnings.simplefilter("ignore", ConvergenceWarning)
                model.fit(X, y)
        except Exception:
            return None
        return model

    def _mlp_score(self, features: Any) -> float:
        weights_1 = np.array([
            [1.2, -0.5, 0.8, 0.4],
            [0.7, 0.9, -0.2, 0.4],
            [1.1, 0.2, 0.7, -0.4],
            [0.3, 1.1, 0.6, 0.5],
            [0.6, -0.1, 1.0, 0.8],
            [0.8, 0.5, -0.2, 0.9],
            [1.0, 0.7, 0.6, -0.2],
        ])
        bias_1 = np.array([-0.45, -0.25, -0.35, -0.4])
        hidden = 1 / (1 + np.exp(-(features @ weights_1 + bias_1)))
        weights_2 = np.array([1.05, 0.95, 1.15, 0.85])
        raw = hidden @ weights_2 - 1.85
        return float((1 / (1 + np.exp(-raw))) * 100)

    def _fit_price_model(self, df: Any, amount_col: str) -> dict[str, Any]:
        if df.empty or amount_col not in df:
            return {"ready": False, "summary": "no data available", "median": 0.0}
        work = df.copy()
        y = self._numeric(work[amount_col])
        work = work[y > 0].copy()
        y = y[y > 0]
        median = float(y.median()) if len(y) else 0.0
        if len(work) < 3:
            return {"ready": False, "summary": f"needs at least 3 priced records; median {self._money(median)}", "median": median}
        x = self._feature_matrix(work)
        if len(work) <= x.shape[1]:
            return {"ready": False, "summary": f"not enough rows for regression; median {self._money(median)}", "median": median}
        lam = 0.25
        xtx = x.T @ x + lam * np.eye(x.shape[1])
        beta = np.linalg.pinv(xtx) @ x.T @ y.to_numpy(dtype=float)
        pred = x @ beta
        ss_res = float(np.sum((y.to_numpy(dtype=float) - pred) ** 2))
        ss_tot = float(np.sum((y.to_numpy(dtype=float) - y.mean()) ** 2))
        r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
        return {
            "ready": True,
            "summary": f"ridge regression on {len(work)} records, R2 {r2:.2f}, median {self._money(median)}",
            "beta": beta,
            "median": median,
            "columns": x.shape[1],
        }

    def _predict_price(self, model: dict[str, Any], row: dict[str, Any]) -> float:
        if not model.get("ready"):
            return float(model.get("median") or 0)
        x = self._feature_matrix(pd.DataFrame([row]))
        beta = model["beta"]
        if x.shape[1] != len(beta):
            return float(model.get("median") or 0)
        predicted = np.asarray(x @ beta, dtype=float).ravel()[0]
        return max(0.0, float(predicted))

    def _feature_matrix(self, df: Any) -> Any:
        sq_ft = self._numeric(df.get("sq_ft", pd.Series([0] * len(df))))
        if sq_ft.max() == 0 and "measurement" in df:
            sq_ft = df["measurement"].map(self._extract_number).astype(float)
        beds = df.get("size_beds", pd.Series([0] * len(df))).map(self._extract_number).astype(float)
        if beds.max() == 0 and "size" in df:
            beds = df["size"].map(self._extract_number).astype(float)
        floor = df.get("floor_no", pd.Series([0] * len(df))).map(self._extract_number).astype(float)
        if floor.max() == 0 and "floor" in df:
            floor = df["floor"].map(self._extract_number).astype(float)
        loc_len = df.get("location", pd.Series([""] * len(df))).fillna("").astype(str).str.len().astype(float)
        type_len = self._type_series(df).fillna("").astype(str).str.len().astype(float)
        return np.column_stack([
            np.ones(len(df)),
            self._scale(sq_ft),
            self._scale(beds),
            self._scale(floor),
            self._scale(loc_len),
            self._scale(type_len),
        ])

    def _match_pressure(self, row: dict[str, Any], table: str, frames: dict[str, Any]) -> float:
        counterpart = self._counterpart_table(table)
        if not counterpart or frames[counterpart].empty:
            return 0.0
        scores = [self._match_score(row, candidate, table, counterpart)[0] for candidate in frames[counterpart].to_dict("records")[:180]]
        return min(1.0, (max(scores) if scores else 0) / 100)

    def _match_score(self, left: dict[str, Any], right: dict[str, Any], left_table: str, right_table: str) -> tuple[float, list[str]]:
        shared_score, shared_reasons = shared_smart_match_score(left, right, left_table, right_table)
        if shared_score or shared_reasons:
            return shared_score, shared_reasons
        score = 0.0
        reasons: list[str] = []
        left_location = str(left.get("location") or "").strip().lower()
        right_location = str(right.get("location") or "").strip().lower()
        if left_location and right_location:
            if left_location == right_location:
                score += 32
                reasons.append("same location")
            elif left_location in right_location or right_location in left_location:
                score += 22
                reasons.append("near location text")
        if TfidfVectorizer is not None and cosine_similarity is not None:
            text_l = self._row_text(left)
            text_r = self._row_text(right)
            if text_l.strip() and text_r.strip():
                try:
                    vec = TfidfVectorizer(stop_words=list(STOP_WORDS)).fit_transform([text_l, text_r])
                    sim = float(cosine_similarity(vec[0:1], vec[1:2])[0][0])
                    if sim > 0.1:
                        score += min(28.0, sim * 40)
                        reasons.append(f"NLP semantic match ({sim*100:.0f}%)")
                except ValueError:
                    pass
        else:
            left_tokens = set(self._tokens(self._row_text(left)))
            right_tokens = set(self._tokens(self._row_text(right)))
            overlap = len(left_tokens & right_tokens)
            if overlap:
                score += min(28, overlap * 7)
                reasons.append(f"{overlap} text match(es)")
        left_amount = self._amount_for_row(left, left_table)
        right_amount = self._amount_for_row(right, right_table)
        if left_amount and right_amount:
            ratio = min(left_amount, right_amount) / max(left_amount, right_amount)
            score += ratio * 28
            if ratio >= 0.8:
                reasons.append("budget fit")
        left_size = self._extract_number(left.get("size") or left.get("property_type") or "")
        right_size = self._extract_number(right.get("size") or right.get("property_type") or "")
        if left_size and right_size:
            diff = abs(left_size - right_size)
            size_score = max(0, 12 - diff * 4)
            score += size_score
            if size_score >= 8:
                reasons.append("size fit")
        return min(100.0, score), reasons

    def _monthly_forecast(self, df: Any, date_col: str, amount_col: str) -> str:
        if df.empty or date_col not in df or amount_col not in df:
            return "not enough data"
        work = df.copy()
        work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
        work[amount_col] = self._numeric(work[amount_col])
        work = work.dropna(subset=[date_col])
        work = work[work[amount_col] > 0]
        if work.empty:
            return "not enough data"
        monthly = work.groupby(work[date_col].dt.to_period("M"))[amount_col].sum().sort_index()
        if len(monthly) == 1:
            return f"{self._money(monthly.iloc[-1])} based on latest month only"
        x = np.arange(len(monthly), dtype=float)
        y = monthly.to_numpy(dtype=float)
        beta = np.polyfit(x, y, 1)
        forecast = max(0.0, float(beta[0] * len(monthly) + beta[1]))
        direction = "rising" if beta[0] > 0 else "falling" if beta[0] < 0 else "flat"
        return f"{self._money(forecast)} ({direction} trend from {len(monthly)} month(s))"

    def _completeness(self, row: dict[str, Any], table: str) -> float:
        keys = ["location", "contact", "workflow_stage", "priority", "approval_status"]
        if table.endswith("requirements"):
            keys.extend(["client_name", "property_requires"])
            keys.append("budget" if table.startswith(("rent", "sale")) else "budget_max")
        else:
            keys.extend(["owner_name", "property_availability"])
            keys.append("monthly_rent" if table.startswith("rent") else "demand")
        filled = sum(1 for key in keys if row.get(key) not in (None, "", 0))
        return filled / len(keys)

    def _recency_score(self, row: dict[str, Any]) -> float:
        raw = row.get("date") or row.get("created_at") or row.get("date_created") or row.get("date_posted")
        if not raw:
            return 0.35
        try:
            dt = pd.to_datetime(raw, errors="coerce")
            if pd.isna(dt):
                return 0.35
            days = max(0, (pd.Timestamp.now() - dt).days)
            return float(max(0.1, min(1.0, 1 - days / 90)))
        except Exception:
            return 0.35

    def _amount_for_row(self, row: dict[str, Any], table: str) -> float:
        keys = {
            "rent_requirements": ["budget", "budget_max", "budget_min"],
            "rent_availability": ["monthly_rent"],
            "sale_requirements": ["budget", "budget_max", "budget_min"],
            "sale_availability": ["demand", "asking_price"],
            "properties": ["monthly_rent", "sale_price"],
        }.get(table, ["amount"])
        for key in keys:
            value = self._to_float(row.get(key))
            if value:
                return value
        return 0.0

    def _counterpart_table(self, table: str) -> str | None:
        return {
            "rent_requirements": "rent_availability",
            "rent_availability": "rent_requirements",
            "sale_requirements": "sale_availability",
            "sale_availability": "sale_requirements",
        }.get(table)

    def _row_text(self, row: dict[str, Any]) -> str:
        keys = [
            "location", "property_type", "property_requires", "property_availability",
            "size", "measurement", "facilities", "description", "notes", "remarks",
            "bachelor_family", "option1", "option2", "title", "area",
        ]
        return " ".join(self._clean_text_value(row.get(key)) for key in keys)

    def _tokens(self, text: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9]{2,}", str(text).lower())
        return [token for token in tokens if token not in STOP_WORDS]

    def _clean_text_value(self, value: Any) -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, float) and not math.isfinite(value):
            return ""
        text = str(value).strip()
        return "" if text.lower() in {"nan", "none", "null"} else text

    def _type_series(self, df: Any) -> Any:
        for key in ("property_type", "property_requires", "property_availability", "title"):
            if key in df:
                return df[key]
        return pd.Series([""] * len(df))

    def _numeric(self, series: Any) -> Any:
        return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.replace("Rs.", "", regex=False), errors="coerce").fillna(0)

    def _sum_amount(self, df: Any, column: str) -> float:
        if df.empty or column not in df:
            return 0.0
        return float(self._numeric(df[column]).sum())

    def _scale(self, series: Any) -> Any:
        values = pd.to_numeric(series, errors="coerce").fillna(0).to_numpy(dtype=float)
        max_value = np.max(np.abs(values)) if len(values) else 0
        if max_value == 0:
            return values
        return values / max_value

    def _extract_number(self, value: Any) -> float:
        match = re.search(r"\d+(?:\.\d+)?", str(value or "").replace(",", ""))
        return float(match.group(0)) if match else 0.0

    def _to_float(self, value: Any) -> float:
        try:
            if value in (None, ""):
                return 0.0
            number = float(str(value).replace(",", "").replace("Rs.", "").strip())
            return number if math.isfinite(number) else 0.0
        except Exception:
            return 0.0

    def _normalize_contact(self, value: Any) -> str:
        digits = re.sub(r"\D+", "", str(value or ""))
        return digits[-10:] if len(digits) >= 7 else ""

    def _money(self, value: Any) -> str:
        return f"{self.currency_symbol}{self._to_float(value):,.0f}"

    def _short_source(self, table: str) -> str:
        return {
            "rent_requirements": "Rent Req",
            "rent_availability": "Rent Av",
            "sale_requirements": "Sale Req",
            "sale_availability": "Sale Av",
            "income_transactions": "Income",
            "expense_transactions": "Expense",
        }.get(table, table[:9])
