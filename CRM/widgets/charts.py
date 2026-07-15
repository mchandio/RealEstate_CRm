"""Dashboard chart widgets."""
from __future__ import annotations
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget
from typing import Any

class DashboardBarChart(QWidget):
    def __init__(self, rows: list[dict[str, Any]]):
        super().__init__()
        self.rows = rows[:6] or [{"location": "No Data", "rent_requirements": 0, "rent_availability": 0}]
        self.setMinimumHeight(190)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(18, 8, -18, -28)
        left = rect.left()
        right = rect.right()
        top = rect.top() + 4
        bottom = rect.bottom() - 22
        grid_pen = QPen(QColor("#b9cce2"))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for index in range(4):
            y = top + ((bottom - top) / 3) * index
            painter.drawLine(QPointF(left, y), QPointF(right, y))
        max_value = max(
            1,
            *[
                max(safe_float(row.get("rent_requirements")), safe_float(row.get("rent_availability")))
                for row in self.rows
            ],
        )
        group_width = max(70, int((right - left) / max(len(self.rows), 1)))
        bar_width = 18
        for index, row in enumerate(self.rows):
            center = left + group_width * index + group_width / 2
            req_height = ((bottom - top) * safe_float(row.get("rent_requirements"))) / max_value
            av_height = ((bottom - top) * safe_float(row.get("rent_availability"))) / max_value
            req_rect = QRectF(center - bar_width - 3, bottom - req_height, bar_width, req_height)
            av_rect = QRectF(center + 3, bottom - av_height, bar_width, av_height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor("#1976d2")))
            painter.drawRoundedRect(req_rect, 3, 3)
            painter.setBrush(QBrush(QColor("#21964b")))
            painter.drawRoundedRect(av_rect, 3, 3)
            painter.setPen(QPen(QColor("#163f79")))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            label_rect = QRectF(center - group_width / 2 + 3, bottom + 8, group_width - 6, 20)
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, str(row.get("location") or "Area"))


class DashboardDonut(QWidget):
    def __init__(self, total: int, segments: list[dict[str, Any]]):
        super().__init__()
        self.total = total
        self.segments = segments[:3]
        self.setMinimumSize(210, 210)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 24
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        if not self.segments or sum(safe_float(row.get("percent")) for row in self.segments) <= 0:
            painter.setBrush(QBrush(QColor("#cbd5e1")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(rect)
        else:
            start = 90 * 16
            for row in self.segments:
                span = int(-safe_float(row.get("percent")) * 3.6 * 16)
                painter.setBrush(QBrush(QColor(str(row.get("color") or "#1976d2"))))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPie(rect, start, span)
                start += span
        inner = rect.adjusted(side * 0.24, side * 0.24, -side * 0.24, -side * 0.24)
        painter.setBrush(QBrush(QColor("#eef7ff")))
        painter.setPen(QPen(QColor("#d6e6f7"), 1))
        painter.drawEllipse(inner)
        painter.setPen(QPen(QColor("#17345c")))
        painter.setFont(QFont("Segoe UI", 24, QFont.Weight.Black))
        painter.drawText(inner, Qt.AlignmentFlag.AlignCenter, f"{self.total:,}")


class DashboardLineChart(QWidget):
    SERIES = (
        ("response_time", QColor("#1976d2")),
        ("approvals_cleared", QColor("#ef7d00")),
        ("conversion", QColor("#3b9629")),
    )

    def __init__(self, rows: list[dict[str, Any]]):
        super().__init__()
        self.rows = rows[:3] or [
            {"period": "30 Days", "response_time": 35, "approvals_cleared": 20, "conversion": 12},
            {"period": "90 Days", "response_time": 65, "approvals_cleared": 60, "conversion": 35},
            {"period": "180 Days", "response_time": 72, "approvals_cleared": 82, "conversion": 50},
        ]
        self.setMinimumHeight(210)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(22, 10, -22, -38)
        top = rect.top() + 8
        bottom = rect.bottom() - 4
        left = rect.left()
        right = rect.right()
        painter.setPen(QPen(QColor("#b9cce2"), 1))
        for index in range(4):
            y = top + ((bottom - top) / 3) * index
            painter.drawLine(QPointF(left, y), QPointF(right, y))
        x_positions = [
            left + ((right - left) / max(len(self.rows) - 1, 1)) * index
            for index in range(len(self.rows))
        ]
        for key, color in self.SERIES:
            pen = QPen(color, 4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            points = []
            for index, row in enumerate(self.rows):
                value = max(0, min(100, safe_float(row.get(key))))
                y = bottom - ((bottom - top) * value / 100)
                points.append(QPointF(x_positions[index], y))
            for start, end in zip(points, points[1:]):
                painter.drawLine(start, end)
            painter.setBrush(QBrush(color))
            for point in points:
                painter.drawEllipse(point, 6, 6)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QPen(QColor("#173f75")))
        for index, row in enumerate(self.rows):
            label = str(row.get("period") or "")
            painter.drawText(QRectF(x_positions[index] - 45, bottom + 12, 90, 24), Qt.AlignmentFlag.AlignCenter, label)



# ─── CRM module imports ───
from CRM.utils import safe_float

