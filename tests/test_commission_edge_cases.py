"""Edge case tests for commission split percentage validation and calculation logic.

Covers:
- Split percentage boundary values (0%, 100%, >100%, negative)
- Split amount calculation from percentage
- Total split percentage across multiple splits
- Commission rate validation
- Total commission calculation
- Edge cases for commission status transitions
- Edge cases for database operations
"""
from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import sqlite3


@pytest.fixture
def commission_db():
    """Create a temporary SQLite database with commission tables."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Create commissions table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS commissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_id INTEGER NOT NULL,
            deal_type TEXT NOT NULL,
            deal_table TEXT NOT NULL,
            deal_amount REAL DEFAULT 0,
            commission_rate REAL DEFAULT 5.0,
            total_commission REAL DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            approved_by TEXT,
            approved_at TEXT,
            paid_at TEXT,
            payment_method TEXT,
            notes TEXT,
            created_by TEXT,
            created_at TEXT,
            last_edited_by TEXT,
            last_edited_at TEXT
        )
    """)

    # Create commission_splits table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS commission_splits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            commission_id INTEGER NOT NULL,
            agent_id INTEGER,
            agent_name TEXT NOT NULL,
            split_percentage REAL DEFAULT 100.0,
            split_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            paid_at TEXT,
            payment_method TEXT,
            notes TEXT,
            created_at TEXT,
            FOREIGN KEY (commission_id) REFERENCES commissions(id)
        )
    """)

    conn.commit()
    yield db_path, conn
    conn.close()
    Path(db_path).unlink(missing_ok=True)


def create_commission(conn, deal_amount, commission_rate, status="Pending"):
    """Helper to create a commission record."""
    total = deal_amount * (commission_rate / 100)
    cursor = conn.execute("""
        INSERT INTO commissions (deal_id, deal_type, deal_table, deal_amount, commission_rate, total_commission, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (1, "sale_availability", "sale_availability", deal_amount, commission_rate, total, status, datetime.now().isoformat()))
    conn.commit()
    return cursor.lastrowid


def create_split(conn, commission_id, agent_name, split_percentage, split_amount=0):
    """Helper to create a commission split record."""
    cursor = conn.execute("""
        INSERT INTO commission_splits (commission_id, agent_name, split_percentage, split_amount, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (commission_id, agent_name, split_percentage, split_amount, datetime.now().isoformat()))
    conn.commit()
    return cursor.lastrowid


# ===========================================================================
# Split Percentage Boundary Values
# ===========================================================================

class TestSplitPercentageBoundaries:
    """Test split percentage boundary values."""

    def test_split_percentage_zero(self, commission_db):
        """Split percentage of 0% should result in 0 split amount."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)  # Total = 5000
        split_id = create_split(conn, comm_id, "Agent Zero", 0.0, 0.0)

        split = conn.execute("SELECT * FROM commission_splits WHERE id=?", (split_id,)).fetchone()
        assert split["split_percentage"] == 0.0
        assert split["split_amount"] == 0.0

    def test_split_percentage_exactly_100(self, commission_db):
        """Split percentage of exactly 100% should equal total commission."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)  # Total = 5000
        split_id = create_split(conn, comm_id, "Agent Full", 100.0, 5000.0)

        split = conn.execute("SELECT * FROM commission_splits WHERE id=?", (split_id,)).fetchone()
        assert split["split_percentage"] == 100.0
        assert split["split_amount"] == 5000.0

    def test_split_percentage_over_100(self, commission_db):
        """Split percentage > 100% is allowed in database but should be validated in app."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)
        split_id = create_split(conn, comm_id, "Agent Over", 150.0, 7500.0)

        split = conn.execute("SELECT * FROM commission_splits WHERE id=?", (split_id,)).fetchone()
        assert split["split_percentage"] == 150.0

    def test_split_percentage_negative(self, commission_db):
        """Negative split percentage is allowed in database but should be validated in app."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)
        split_id = create_split(conn, comm_id, "Agent Neg", -10.0, -500.0)

        split = conn.execute("SELECT * FROM commission_splits WHERE id=?", (split_id,)).fetchone()
        assert split["split_percentage"] == -10.0

    def test_split_percentage_very_small(self, commission_db):
        """Very small split percentage (0.01%) should be stored correctly."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)  # Total = 5000
        split_id = create_split(conn, comm_id, "Agent Tiny", 0.01, 0.5)

        split = conn.execute("SELECT * FROM commission_splits WHERE id=?", (split_id,)).fetchone()
        assert split["split_percentage"] == 0.01
        assert split["split_amount"] == pytest.approx(0.5, abs=0.01)


# ===========================================================================
# Split Amount Calculation
# ===========================================================================

class TestSplitAmountCalculation:
    """Test split amount calculation from percentage."""

    def test_split_amount_60_percent(self, commission_db):
        """60% of 5000 = 3000."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)  # Total = 5000
        split_amount = 5000 * (60 / 100)
        split_id = create_split(conn, comm_id, "Agent 60%", 60.0, split_amount)

        split = conn.execute("SELECT * FROM commission_splits WHERE id=?", (split_id,)).fetchone()
        assert split["split_amount"] == pytest.approx(3000.0, abs=0.01)

    def test_split_amount_33_percent(self, commission_db):
        """33.33% of 5000 = 1666.5."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)  # Total = 5000
        split_amount = round(5000 * (33.33 / 100), 2)
        split_id = create_split(conn, comm_id, "Agent Third", 33.33, split_amount)

        split = conn.execute("SELECT * FROM commission_splits WHERE id=?", (split_id,)).fetchone()
        assert split["split_amount"] == pytest.approx(1666.5, abs=0.01)

    def test_split_amount_rounding(self, commission_db):
        """Test rounding behavior for split amounts."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 3.33)  # Total = 100000 * 3.33/100 = 3330
        # 33.33% of 3330 = 1109.4889, rounded to 1109.49
        expected_amount = round(3330 * (33.33 / 100), 2)
        split_id = create_split(conn, comm_id, "Agent Round", 33.33, expected_amount)

        split = conn.execute("SELECT * FROM commission_splits WHERE id=?", (split_id,)).fetchone()
        assert split["split_amount"] == pytest.approx(expected_amount, abs=0.01)


# ===========================================================================
# Total Split Percentage Across Multiple Splits
# ===========================================================================

class TestTotalSplitPercentage:
    """Test total split percentage across multiple splits."""

    def test_two_splits_50_50(self, commission_db):
        """Two 50% splits should total 100%."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)  # Total = 5000
        create_split(conn, comm_id, "Agent A", 50.0, 2500.0)
        create_split(conn, comm_id, "Agent B", 50.0, 2500.0)

        splits = conn.execute("SELECT * FROM commission_splits WHERE commission_id=?", (comm_id,)).fetchall()
        total_pct = sum(s["split_percentage"] for s in splits)
        total_amount = sum(s["split_amount"] for s in splits)

        assert total_pct == 100.0
        assert total_amount == pytest.approx(5000.0, abs=0.01)

    def test_three_splits_uneven(self, commission_db):
        """Three uneven splits (60%, 30%, 10%) should total 100%."""
        _, conn = commission_db
        comm_id = create_commission(conn, 200000, 5.0)  # Total = 10000
        create_split(conn, comm_id, "Agent A", 60.0, 6000.0)
        create_split(conn, comm_id, "Agent B", 30.0, 3000.0)
        create_split(conn, comm_id, "Agent C", 10.0, 1000.0)

        splits = conn.execute("SELECT * FROM commission_splits WHERE commission_id=?", (comm_id,)).fetchall()
        total_pct = sum(s["split_percentage"] for s in splits)

        assert total_pct == 100.0

    def test_splits_exceed_100_percent(self, commission_db):
        """Splits exceeding 100% total should be detectable."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)  # Total = 5000
        create_split(conn, comm_id, "Agent A", 60.0, 3000.0)
        create_split(conn, comm_id, "Agent B", 60.0, 3000.0)  # Total = 120%

        splits = conn.execute("SELECT * FROM commission_splits WHERE commission_id=?", (comm_id,)).fetchall()
        total_pct = sum(s["split_percentage"] for s in splits)

        assert total_pct == 120.0  # Should be detectable as invalid

    def test_splits_less_than_100_percent(self, commission_db):
        """Splits totaling less than 100% should be detectable."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)  # Total = 5000
        create_split(conn, comm_id, "Agent A", 30.0, 1500.0)
        create_split(conn, comm_id, "Agent B", 30.0, 1500.0)  # Total = 60%

        splits = conn.execute("SELECT * FROM commission_splits WHERE commission_id=?", (comm_id,)).fetchall()
        total_pct = sum(s["split_percentage"] for s in splits)

        assert total_pct == 60.0  # Should be detectable as incomplete

    def test_single_split_100_percent(self, commission_db):
        """Single 100% split should be valid."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)
        create_split(conn, comm_id, "Solo Agent", 100.0, 5000.0)

        splits = conn.execute("SELECT * FROM commission_splits WHERE commission_id=?", (comm_id,)).fetchall()
        assert len(splits) == 1
        assert splits[0]["split_percentage"] == 100.0


# ===========================================================================
# Commission Rate Validation
# ===========================================================================

class TestCommissionRateValidation:
    """Test commission rate validation edge cases."""

    def test_commission_rate_zero(self, commission_db):
        """0% commission rate should result in 0 total commission."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 0.0)

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm["commission_rate"] == 0.0
        assert comm["total_commission"] == 0.0

    def test_commission_rate_100_percent(self, commission_db):
        """100% commission rate should equal deal amount."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 100.0)

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm["commission_rate"] == 100.0
        assert comm["total_commission"] == pytest.approx(100000.0, abs=0.01)

    def test_commission_rate_over_100_percent(self, commission_db):
        """Commission rate > 100% should be allowed in database."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 150.0)

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm["commission_rate"] == 150.0
        assert comm["total_commission"] == pytest.approx(150000.0, abs=0.01)

    def test_commission_rate_negative(self, commission_db):
        """Negative commission rate should be allowed in database."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, -5.0)

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm["commission_rate"] == -5.0
        assert comm["total_commission"] == pytest.approx(-5000.0, abs=0.01)

    def test_commission_rate_very_small(self, commission_db):
        """Very small commission rate (0.01%) should be stored correctly."""
        _, conn = commission_db
        comm_id = create_commission(conn, 1000000, 0.01)  # 0.01% of 1M = 100

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm["commission_rate"] == 0.01
        assert comm["total_commission"] == pytest.approx(100.0, abs=0.01)


# ===========================================================================
# Commission Status Transitions
# ===========================================================================

class TestCommissionStatusTransitions:
    """Test commission status transition edge cases."""

    def test_pending_to_approved(self, commission_db):
        """Pending commission can be approved."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0, "Pending")

        conn.execute("UPDATE commissions SET status='Approved', approved_by='admin', approved_at=? WHERE id=?",
                     (datetime.now().isoformat(), comm_id))
        conn.commit()

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm["status"] == "Approved"
        assert comm["approved_by"] == "admin"

    def test_approved_to_paid(self, commission_db):
        """Approved commission can be marked as paid."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0, "Approved")

        conn.execute("UPDATE commissions SET status='Paid', paid_at=? WHERE id=?",
                     (datetime.now().isoformat(), comm_id))
        conn.commit()

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm["status"] == "Paid"
        assert comm["paid_at"] is not None

    def test_pending_to_cancelled(self, commission_db):
        """Pending commission can be cancelled."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0, "Pending")

        conn.execute("UPDATE commissions SET status='Cancelled' WHERE id=?", (comm_id,))
        conn.commit()

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm["status"] == "Cancelled"

    def test_paid_to_pending_invalid(self, commission_db):
        """Paid commission should not be reverted to Pending (business rule)."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0, "Paid")

        # Database allows it, but app should prevent
        conn.execute("UPDATE commissions SET status='Pending' WHERE id=?", (comm_id,))
        conn.commit()

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        # Database allows the change (app should validate)
        assert comm["status"] == "Pending"


# ===========================================================================
# Commission Split Status
# ===========================================================================

class TestCommissionSplitStatus:
    """Test commission split status edge cases."""

    def test_split_pending_to_paid(self, commission_db):
        """Pending split can be marked as paid."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)
        split_id = create_split(conn, comm_id, "Agent A", 100.0, 5000.0)

        conn.execute("UPDATE commission_splits SET status='Paid', paid_at=? WHERE id=?",
                     (datetime.now().isoformat(), split_id))
        conn.commit()

        split = conn.execute("SELECT * FROM commission_splits WHERE id=?", (split_id,)).fetchone()
        assert split["status"] == "Paid"
        assert split["paid_at"] is not None

    def test_split_with_payment_method(self, commission_db):
        """Split with payment method should be stored correctly."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)
        split_id = create_split(conn, comm_id, "Agent A", 100.0, 5000.0)

        conn.execute("UPDATE commission_splits SET status='Paid', payment_method='Bank Transfer', paid_at=? WHERE id=?",
                     (datetime.now().isoformat(), split_id))
        conn.commit()

        split = conn.execute("SELECT * FROM commission_splits WHERE id=?", (split_id,)).fetchone()
        assert split["status"] == "Paid"
        assert split["payment_method"] == "Bank Transfer"


# ===========================================================================
# Edge Cases for Deal Amount
# ===========================================================================

class TestDealAmountEdgeCases:
    """Test deal amount edge cases."""

    def test_deal_amount_zero(self, commission_db):
        """Zero deal amount should result in zero commission."""
        _, conn = commission_db
        comm_id = create_commission(conn, 0, 5.0)

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm["deal_amount"] == 0
        assert comm["total_commission"] == 0.0

    def test_deal_amount_very_large(self, commission_db):
        """Very large deal amount should be stored correctly."""
        _, conn = commission_db
        large_amount = 999999999999.99
        comm_id = create_commission(conn, large_amount, 5.0)

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm["deal_amount"] == pytest.approx(large_amount, abs=0.01)
        assert comm["total_commission"] == pytest.approx(large_amount * 0.05, abs=0.01)

    def test_deal_amount_negative(self, commission_db):
        """Negative deal amount should be allowed in database."""
        _, conn = commission_db
        comm_id = create_commission(conn, -100000, 5.0)

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm["deal_amount"] == -100000
        assert comm["total_commission"] == pytest.approx(-5000.0, abs=0.01)

    def test_deal_amount_very_small(self, commission_db):
        """Very small deal amount should be stored correctly."""
        _, conn = commission_db
        comm_id = create_commission(conn, 0.01, 5.0)

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm["deal_amount"] == pytest.approx(0.01, abs=0.001)
        assert comm["total_commission"] == pytest.approx(0.0005, abs=0.0001)


# ===========================================================================
# Multiple Splits Sum Validation
# ===========================================================================

class TestMultipleSplitsSumValidation:
    """Test validation of multiple splits summing to total commission."""

    def test_split_amounts_sum_to_total(self, commission_db):
        """Split amounts should sum to total commission."""
        _, conn = commission_db
        comm_id = create_commission(conn, 200000, 5.0)  # Total = 10000
        create_split(conn, comm_id, "Agent A", 50.0, 5000.0)
        create_split(conn, comm_id, "Agent B", 30.0, 3000.0)
        create_split(conn, comm_id, "Agent C", 20.0, 2000.0)

        splits = conn.execute("SELECT * FROM commission_splits WHERE commission_id=?", (comm_id,)).fetchall()
        total_split_amount = sum(s["split_amount"] for s in splits)

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert total_split_amount == pytest.approx(comm["total_commission"], abs=0.01)

    def test_split_amounts_exceed_total(self, commission_db):
        """Split amounts exceeding total commission should be detectable."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)  # Total = 5000
        create_split(conn, comm_id, "Agent A", 60.0, 3000.0)
        create_split(conn, comm_id, "Agent B", 60.0, 3000.0)  # Total = 6000

        splits = conn.execute("SELECT * FROM commission_splits WHERE commission_id=?", (comm_id,)).fetchall()
        total_split_amount = sum(s["split_amount"] for s in splits)

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert total_split_amount > comm["total_commission"]

    def test_split_amounts_less_than_total(self, commission_db):
        """Split amounts less than total commission should be detectable."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)  # Total = 5000
        create_split(conn, comm_id, "Agent A", 30.0, 1500.0)
        create_split(conn, comm_id, "Agent B", 30.0, 1500.0)  # Total = 3000

        splits = conn.execute("SELECT * FROM commission_splits WHERE commission_id=?", (comm_id,)).fetchall()
        total_split_amount = sum(s["split_amount"] for s in splits)

        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert total_split_amount < comm["total_commission"]


# ===========================================================================
# Foreign Key and Referential Integrity
# ===========================================================================

class TestReferentialIntegrity:
    """Test referential integrity for commission splits."""

    def test_split_references_valid_commission(self, commission_db):
        """Split should reference a valid commission."""
        _, conn = commission_db
        comm_id = create_commission(conn, 100000, 5.0)
        split_id = create_split(conn, comm_id, "Agent A", 100.0, 5000.0)

        split = conn.execute("SELECT * FROM commission_splits WHERE id=?", (split_id,)).fetchone()
        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (split["commission_id"],)).fetchone()
        assert comm is not None

    def test_delete_commission_cascades_to_splits(self, commission_db):
        """Deleting a commission should affect its splits (RESTRICT behavior)."""
        _, conn = commission_db
        conn.execute("PRAGMA foreign_keys=ON")
        comm_id = create_commission(conn, 100000, 5.0)
        create_split(conn, comm_id, "Agent A", 100.0, 5000.0)

        # With RESTRICT, delete should fail if splits exist
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM commissions WHERE id=?", (comm_id,))
            conn.commit()

        # Verify commission still exists
        comm = conn.execute("SELECT * FROM commissions WHERE id=?", (comm_id,)).fetchone()
        assert comm is not None
