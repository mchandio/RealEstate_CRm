"""CRM Feature modules."""

from CRM.modules.data_table import DataTablePage
from CRM.modules.installments import InstallmentModule
from CRM.modules.commissions import CommissionModule
from CRM.modules.deals import DealModule
from CRM.modules.phase_one import (
    PhaseOneSectionSpec, PhaseOneForm, PhaseOneSectionPage,
    PhaseOneApprovalsPage, PhaseOneSettingsPage, PhaseOneDesk,
    SummaryPage, MatchResultsDialog, ImportPreviewDialog,
    SettingsListEditor,
)
from CRM.modules.financial import FinancialModule
from CRM.modules.attendance import AttendancePage
from CRM.modules.salary import SalaryPage
from CRM.modules.employees import EmployeesModule
from CRM.modules.reports import ReportsModule
from CRM.modules.ai_insights import AIInsightsModule
from CRM.modules.users import UsersModule
from CRM.modules.settings import SettingsModule
from CRM.modules.success_factors import (
    SFEmployeeCentralPage, SFRecruitingPage, SFPerformancePage,
    SFMustWinBattlesPage, SFKPIsPage, SFLearningPage,
    SFCompensationPage, SFOnboardingPage, SFPositionsPage,
    SFDashboardPage, SuccessFactorsModule,
)
from CRM.modules.workflow import WFDashboardPage, WorkflowModule

# New decomposed modules
from CRM.modules.property_sync import PropertySyncService
from CRM.modules.report_helpers import build_financial_text, generic_report, attendance_report, get_report_for_kind
