"""CRM Widget components."""

from CRM.widgets.table import ExcelTableWidget
from CRM.widgets.delegates import WrappingItemDelegate
from CRM.widgets.table import (
    configure_multi_select_table, configure_table_for_readability,
    responsive_table_columns, apply_responsive_table_layout,
    style_workflow_table_item, selected_table_row_indexes,
    select_all_table_rows, clear_table_selection,
    RESPONSIVE_TABLE_COLUMN_KEYS, LOW_PRIORITY_TABLE_COLUMN_KEYS,
    STATUS_COLUMN_KEYS, PROPERTY_COLUMN_KEYS,
)
from CRM.widgets.charts import DashboardBarChart, DashboardDonut, DashboardLineChart
from CRM.widgets.cards import MetricCard, NavItem

from CRM.widgets.dashboard import DashboardWidget
