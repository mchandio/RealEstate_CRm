param(
    [string]$OutputPath = (Join-Path $PSScriptRoot "Expenses_Manager.accdb")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$dbFailOnError = 128
$dbAttachment = 101

function Sql-Text([AllowNull()][string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) { return "Null" }
    return "'" + $Value.Replace("'", "''") + "'"
}

function Sql-Date([datetime]$Value) {
    return "DateSerial($($Value.Year),$($Value.Month),$($Value.Day))"
}

function Sql-Money([decimal]$Value) {
    return [string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0:0.00}", $Value)
}

function Add-DbProperty($Database, [string]$Name, [int]$Type, $Value) {
    try {
        $Database.Properties($Name).Value = $Value
    } catch {
        $property = $Database.CreateProperty($Name, $Type, $Value)
        $Database.Properties.Append($property)
    }
}

function Invoke-Db($Database, [string]$Sql) {
    $Database.Execute($Sql, $script:dbFailOnError)
}

function Twips([double]$Inches) {
    return [int][Math]::Round($Inches * 1440)
}

function Access-Rgb([int]$R, [int]$G, [int]$B) {
    return $R + ($G * 256) + ($B * 65536)
}

function Try-Set($Object, [string]$PropertyName, $Value) {
    try { $Object.$PropertyName = $Value } catch {}
}

function Set-PlainNumberFormats($Database) {
    try { $Database.TableDefs.Refresh() } catch {}
    foreach ($spec in @(
        @("Capital Balance", "Amount"),
        @("Expenses", "Amount"),
        @("Remaining Balance", "Remaining Balance")
    )) {
        $field = $Database.TableDefs($spec[0]).Fields($spec[1])
        try {
            $field.Properties("Format").Value = "#,##0.00"
        } catch {
            $property = $field.CreateProperty("Format", 10, "#,##0.00")
            $field.Properties.Append($property)
        }
    }
}

function Add-Label($Access, [string]$FormName, [int]$Section, [string]$Caption, [double]$Left, [double]$Top, [double]$Width, [double]$Height = 0.22, [int]$Size = 9, [bool]$Bold = $true, [int]$Color = -1, [int]$BackColor = -1) {
    $control = $Access.CreateControl($FormName, 100, $Section, "", "", (Twips $Left), (Twips $Top), (Twips $Width), (Twips $Height))
    $control.Caption = $Caption
    $control.FontSize = $Size
    $control.FontBold = $Bold
    if ($BackColor -ge 0) {
        $control.BackStyle = 1
        $control.BackColor = $BackColor
    } else {
        $control.BackStyle = 0
    }
    if ($Color -ge 0) { $control.ForeColor = $Color }
    return $control
}

function Add-Text($Access, [string]$FormName, [string]$Name, [string]$Source, [double]$Left, [double]$Top, [double]$Width, [double]$Height = 0.3, [string]$Format = "#,##0.00") {
    $control = $Access.CreateControl($FormName, 109, 0, "", "", (Twips $Left), (Twips $Top), (Twips $Width), (Twips $Height))
    Try-Set $control "Name" $Name
    $control.ControlSource = $Source
    $control.FontSize = 12
    $control.FontBold = $true
    if ($Format) { $control.Format = $Format }
    Try-Set $control "Locked" $true
    Try-Set $control "BackColor" (Access-Rgb 255 255 255)
    return $control
}

function Add-Button($Access, [string]$FormName, [string]$Caption, [string]$OnClick, [double]$Left, [double]$Top, [double]$Width, [int]$Section = 0) {
    $control = $Access.CreateControl($FormName, 104, $Section, "", "", (Twips $Left), (Twips $Top), (Twips $Width), (Twips 0.36))
    $control.Caption = $Caption
    $control.OnClick = $OnClick
    $control.FontSize = 9
    $control.FontBold = $true
    return $control
}

function Create-ThreeTableSchema($Database) {
    Invoke-Db $Database @"
CREATE TABLE [Capital Balance] (
    [ID] COUNTER CONSTRAINT [pk_CapitalBalance] PRIMARY KEY,
    [Date] DATETIME,
    [Description] MEMO,
    [Amount] CURRENCY
)
"@

    Invoke-Db $Database @"
CREATE TABLE [Expenses] (
    [ID] COUNTER CONSTRAINT [pk_Expenses] PRIMARY KEY,
    [Date] DATETIME,
    [Description] MEMO,
    [Amount] CURRENCY
)
"@

    $expenses = $Database.TableDefs("Expenses")
    $expenses.Fields.Append($expenses.CreateField("Upload Bill", $script:dbAttachment))

    Invoke-Db $Database @"
CREATE TABLE [Remaining Balance] (
    [ID] COUNTER CONSTRAINT [pk_RemainingBalance] PRIMARY KEY,
    [Date] DATETIME,
    [VoucherID] LONG,
    [Remaining Balance] CURRENCY
)
"@

    Invoke-Db $Database "CREATE INDEX [ix_Expenses_Date] ON [Expenses]([Date])"
    Invoke-Db $Database "CREATE INDEX [ix_RemainingBalance_VoucherID] ON [Remaining Balance]([VoucherID])"
}

function Create-AppModule($Access) {
    $code = @'
Option Explicit
Private Const APP_TITLE As String = "Expenses Manager"

Public Function OpenTableNamed(ByVal TableName As String) As Boolean
On Error GoTo ErrHandler
    DoCmd.OpenTable TableName
    OpenTableNamed = True
    Exit Function
ErrHandler:
    MsgBox "Unable to open table: " & TableName & vbCrLf & Err.Description, vbExclamation, APP_TITLE
End Function

Public Function OpenFormNamed(ByVal FormName As String) As Boolean
On Error GoTo ErrHandler
    DoCmd.OpenForm FormName
    OpenFormNamed = True
    Exit Function
ErrHandler:
    MsgBox "Unable to open form: " & FormName & vbCrLf & Err.Description, vbExclamation, APP_TITLE
End Function

Public Function NewRecord() As Boolean
On Error GoTo ErrHandler
    DoCmd.GoToRecord , , acNewRec
    NewRecord = True
    Exit Function
ErrHandler:
    MsgBox "Unable to create a new record." & vbCrLf & Err.Description, vbExclamation, APP_TITLE
End Function

Public Function SaveAndRebuild() As Boolean
On Error GoTo ErrHandler
    If Screen.ActiveForm.Dirty Then Screen.ActiveForm.Dirty = False
    RebuildRemainingBalance
    RefreshOpenDashboard
    SaveAndRebuild = True
    Exit Function
ErrHandler:
    MsgBox "Unable to save and rebuild balance." & vbCrLf & Err.Description, vbExclamation, APP_TITLE
End Function

Public Function DeleteAndRebuild() As Boolean
On Error GoTo ErrHandler
    If Screen.ActiveForm.NewRecord Then Exit Function
    If MsgBox("Delete the current record?", vbQuestion + vbYesNo, APP_TITLE) = vbYes Then
        DoCmd.RunCommand acCmdSelectRecord
        DoCmd.RunCommand acCmdDeleteRecord
        RebuildRemainingBalance
        RefreshOpenDashboard
    End If
    DeleteAndRebuild = True
    Exit Function
ErrHandler:
    MsgBox "Unable to delete this record." & vbCrLf & Err.Description, vbExclamation, APP_TITLE
End Function

Public Function RebuildAfterChange() As Boolean
On Error Resume Next
    RebuildRemainingBalance
    RefreshOpenDashboard
    RebuildAfterChange = True
End Function

Public Function RebuildRemainingBalance() As Boolean
On Error GoTo ErrHandler
    Dim db As DAO.Database
    Dim rs As DAO.Recordset
    Dim balance As Currency
    Dim sqlText As String
    Set db = CurrentDb

    balance = Nz(DSum("[Amount]", "[Capital Balance]"), 0)
    db.Execute "DELETE FROM [Remaining Balance]", dbFailOnError

    Set rs = db.OpenRecordset("SELECT [ID], [Date], [Amount] FROM [Expenses] ORDER BY [Date], [ID]", dbOpenSnapshot)
    Do While Not rs.EOF
        balance = balance - Nz(rs![Amount], 0)
        sqlText = "INSERT INTO [Remaining Balance] ([Date], [VoucherID], [Remaining Balance]) VALUES (#" & Format(rs![Date], "yyyy-mm-dd") & "#, " & CLng(rs![ID]) & ", " & Replace(Format(balance, "0.00"), ",", "") & ")"
        db.Execute sqlText, dbFailOnError
        rs.MoveNext
    Loop
    rs.Close
    RebuildRemainingBalance = True
    Exit Function
ErrHandler:
    MsgBox "Unable to rebuild remaining balance." & vbCrLf & Err.Description, vbExclamation, APP_TITLE
End Function

Public Function RefreshOpenDashboard() As Boolean
On Error Resume Next
    Forms!frmDashboard.Requery
    Forms!frmDashboard!lstRecentExpenses.Requery
    Forms!frmDashboard!lstRemainingBalance.Requery
    RefreshOpenDashboard = True
End Function

Public Function RefreshDashboard() As Boolean
On Error Resume Next
    RebuildRemainingBalance
    RefreshOpenDashboard
    RefreshDashboard = True
End Function
'@

    $component = $Access.VBE.ActiveVBProject.VBComponents.Add(1)
    $component.Name = "modExpensesManager"
    $component.CodeModule.AddFromString($code)
    $Access.DoCmd.Save(5, "modExpensesManager")
    try { $Access.DoCmd.Close(5, "modExpensesManager", 1) } catch {}
    try { $Access.DoCmd.RunCommand(126) } catch {}
}

function Create-Dashboard($Access) {
    $form = $Access.CreateForm()
    $name = $form.Name
    $form.Caption = "Expenses Dashboard"
    $form.Width = Twips 10.8
    $form.RecordSelectors = $false
    $form.NavigationButtons = $false
    $form.ScrollBars = 0
    $form.AutoCenter = $true
    $form.OnLoad = '=RefreshDashboard()'
    $form.OnActivate = '=RefreshDashboard()'
    $form.Section(0).Height = Twips 6.2
    $form.Section(0).BackColor = Access-Rgb 248 250 252
    $Access.DoCmd.RunCommand(36)
    $form.Section(1).Height = Twips 0.78
    $form.Section(1).BackColor = Access-Rgb 30 58 95
    $form.Section(2).Height = Twips 0.25
    $form.Section(2).BackColor = Access-Rgb 226 232 240

    [void](Add-Label $Access $name 1 "Expenses Dashboard" 0.3 0.18 2.8 0.34 16 $true (Access-Rgb 255 255 255))
    [void](Add-Label $Access $name 1 "Capital, vouchers, uploaded bills, and cash in hand" 3.1 0.24 4.2 0.22 9 $false (Access-Rgb 226 232 240))

    $cards = @(
        @{ Title = "Capital Balance"; Source = '=Nz(DSum("[Amount]","[Capital Balance]"),0)'; Left = 0.35 },
        @{ Title = "Total Expenses"; Source = '=Nz(DSum("[Amount]","[Expenses]"),0)'; Left = 2.75 },
        @{ Title = "Cash In Hand"; Source = '=Nz(DSum("[Amount]","[Capital Balance]"),0)-Nz(DSum("[Amount]","[Expenses]"),0)'; Left = 5.15 },
        @{ Title = "Vouchers"; Source = '=DCount("*","[Expenses]")'; Left = 7.55; Format = "0" }
    )

    foreach ($card in $cards) {
        $rect = $Access.CreateControl($name, 101, 0, "", "", (Twips $card.Left), (Twips 0.35), (Twips 1.95), (Twips 0.95))
        $rect.BackStyle = 1
        $rect.BackColor = Access-Rgb 255 255 255
        $rect.BorderColor = Access-Rgb 203 213 225
        [void](Add-Label $Access $name 0 $card.Title ($card.Left + 0.12) 0.48 1.65 0.2 8 $true (Access-Rgb 71 85 105))
        $format = if ($card.ContainsKey("Format")) { $card.Format } else { "#,##0.00" }
        $text = Add-Text $Access $name ("txt" + $card.Title.Replace(" ", "")) $card.Source ($card.Left + 0.12) 0.74 1.55 0.32 $format
        $text.TextAlign = 3
    }

    [void](Add-Button $Access $name "Capital Balance" '=OpenFormNamed("frmCapitalBalance")' 0.35 1.7 1.55)
    [void](Add-Button $Access $name "Expenses / Bills" '=OpenFormNamed("frmExpenses")' 2.15 1.7 1.55)
    [void](Add-Button $Access $name "Remaining Balance" '=OpenFormNamed("frmRemainingBalance")' 3.95 1.7 1.75)

    [void](Add-Label $Access $name 0 "Recent Expenses" 0.35 2.35 1.8 0.25 12 $true (Access-Rgb 15 23 42))
    $list = $Access.CreateControl($name, 110, 0, "", "", (Twips 0.35), (Twips 2.68), (Twips 5.1), (Twips 2.45))
    Try-Set $list "Name" "lstRecentExpenses"
    $list.RowSourceType = "Table/Query"
    $list.RowSource = 'SELECT TOP 12 [ID], Format([Date],"dd/mm/yyyy") AS [Date], [Description], Format([Amount],"#,##0.00") AS [Amount] FROM [Expenses] ORDER BY [Date] DESC, [ID] DESC;'
    $list.ColumnCount = 4
    $list.ColumnHeads = $true
    $list.ColumnWidths = "0.55in;0.85in;2.2in;0.95in"

    [void](Add-Label $Access $name 0 "Remaining Balance" 5.85 2.35 2.0 0.25 12 $true (Access-Rgb 15 23 42))
    $balance = $Access.CreateControl($name, 110, 0, "", "", (Twips 5.85), (Twips 2.68), (Twips 3.8), (Twips 2.45))
    Try-Set $balance "Name" "lstRemainingBalance"
    $balance.RowSourceType = "Table/Query"
    $balance.RowSource = 'SELECT [VoucherID], Format([Date],"dd/mm/yyyy") AS [Date], Format([Remaining Balance],"#,##0.00") AS [Cash In Hand] FROM [Remaining Balance] ORDER BY [Date], [VoucherID];'
    $balance.ColumnCount = 3
    $balance.ColumnHeads = $true
    $balance.ColumnWidths = "0.75in;0.85in;1.25in"

    $Access.DoCmd.Save(2, $name)
    $Access.DoCmd.Close(2, $name, 1)
    $Access.DoCmd.Rename("frmDashboard", 2, $name)
    try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($form) } catch {}
}

function New-ControlName([string]$Prefix, [string]$FieldName) {
    return $Prefix + ($FieldName -replace '[^A-Za-z0-9]', '')
}

function Add-BoundControl($Access, [string]$FormName, [hashtable]$Field, [double]$Top) {
    [void](Add-Label $Access $FormName 0 $Field.Label 0.35 $Top 1.35 0.22 9 $true (Access-Rgb 51 65 85))
    $height = if ($Field.ContainsKey("Height")) { [double]$Field.Height } else { 0.32 }
    $width = if ($Field.ContainsKey("Width")) { [double]$Field.Width } else { 3.6 }
    $type = if ($Field.ContainsKey("ControlType")) { [int]$Field.ControlType } else { 109 }
    $control = $Access.CreateControl($FormName, $type, 0, "", "", (Twips 1.85), (Twips $Top), (Twips $width), (Twips $height))
    Try-Set $control "Name" (New-ControlName "ctl" $Field.Label)
    $control.ControlSource = $Field.Source
    Try-Set $control "FontSize" 10
    if ($Field.ContainsKey("Format")) { $control.Format = $Field.Format }
    if ($Field.ContainsKey("Locked") -and $Field.Locked) { Try-Set $control "Locked" $true }
    if ($Field.ContainsKey("DefaultValue")) { Try-Set $control "DefaultValue" $Field.DefaultValue }
    if ($Field.ContainsKey("TextAlign")) { Try-Set $control "TextAlign" $Field.TextAlign }
    return $control
}

function Create-EntryForm($Access, [string]$FormName, [string]$TableName, [string]$Caption, [array]$Fields, [bool]$ReadOnly = $false) {
    $form = $Access.CreateForm()
    $tempName = $form.Name
    $form.Caption = $Caption
    $form.RecordSource = "[$TableName]"
    $form.Width = Twips 7.0
    $form.AutoCenter = $true
    $form.Section(0).Height = Twips 3.6
    $form.Section(0).BackColor = Access-Rgb 248 250 252
    $Access.DoCmd.RunCommand(36)
    $form.Section(1).Height = Twips 0.72
    $form.Section(1).BackColor = Access-Rgb 30 58 95
    $form.Section(2).Height = Twips 0.18
    $form.Section(2).BackColor = Access-Rgb 226 232 240
    [void](Add-Label $Access $tempName 1 $Caption 0.35 0.2 2.8 0.3 14 $true (Access-Rgb 255 255 255))

    if ($ReadOnly) {
        $form.AllowEdits = $false
        $form.AllowAdditions = $false
        $form.AllowDeletions = $false
    } else {
        $form.AfterUpdate = '=RebuildAfterChange()'
        $form.AfterInsert = '=RebuildAfterChange()'
        $form.AfterDelConfirm = '=RebuildAfterChange()'
        $form.OnClose = '=RebuildAfterChange()'
        [void](Add-Button $Access $tempName "New" '=NewRecord()' 3.7 0.18 0.7 1)
        [void](Add-Button $Access $tempName "Save" '=SaveAndRebuild()' 4.55 0.18 0.8 1)
        [void](Add-Button $Access $tempName "Delete" '=DeleteAndRebuild()' 5.5 0.18 0.8 1)
    }

    $top = 0.45
    foreach ($field in $Fields) {
        [void](Add-BoundControl $Access $tempName $field $top)
        $top += if ($field.ContainsKey("Height")) { [double]$field.Height + 0.25 } else { 0.55 }
    }

    $Access.DoCmd.Save(2, $tempName)
    $Access.DoCmd.Close(2, $tempName, 1)
    $Access.DoCmd.Rename($FormName, 2, $tempName)
    try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($form) } catch {}
}

function Create-EntryForms($Access) {
    $moneyFormat = "#,##0.00"
    Create-EntryForm $Access "frmCapitalBalance" "Capital Balance" "Capital Balance" @(
        @{ Label = "ID"; Source = "[ID]"; Locked = $true; Width = 1.2 },
        @{ Label = "Date"; Source = "[Date]"; Format = "Short Date"; DefaultValue = "=Date()"; Width = 1.5 },
        @{ Label = "Amount"; Source = "[Amount]"; Format = $moneyFormat; Width = 1.5; TextAlign = 3 },
        @{ Label = "Description"; Source = "[Description]"; Width = 4.2; Height = 0.75 }
    )

    Create-EntryForm $Access "frmExpenses" "Expenses" "Expenses / Bills" @(
        @{ Label = "ID"; Source = "[ID]"; Locked = $true; Width = 1.2 },
        @{ Label = "Date"; Source = "[Date]"; Format = "Short Date"; DefaultValue = "=Date()"; Width = 1.5 },
        @{ Label = "Amount"; Source = "[Amount]"; Format = $moneyFormat; Width = 1.5; TextAlign = 3 },
        @{ Label = "Description"; Source = "[Description]"; Width = 4.2; Height = 0.75 },
        @{ Label = "Upload Bill"; Source = "[Upload Bill]"; ControlType = 126; Width = 4.2; Height = 0.65 }
    )

    Create-EntryForm $Access "frmRemainingBalance" "Remaining Balance" "Remaining Balance" @(
        @{ Label = "ID"; Source = "[ID]"; Locked = $true; Width = 1.2 },
        @{ Label = "Date"; Source = "[Date]"; Format = "Short Date"; Locked = $true; Width = 1.5 },
        @{ Label = "VoucherID"; Source = "[VoucherID]"; Locked = $true; Width = 1.2 },
        @{ Label = "Remaining Balance"; Source = "[Remaining Balance]"; Format = $moneyFormat; Locked = $true; Width = 1.7; TextAlign = 3 }
    ) $true
}

function Seed-SampleData($Database) {
    $expenseRows = @(
        @{ ID = 68; Date = [datetime]"2026-05-11"; Description = "E-Stamp C"; Amount = [decimal]300 },
        @{ ID = 69; Date = [datetime]"2026-05-11"; Description = "E-Stamp 1"; Amount = [decimal]1400 },
        @{ ID = 70; Date = [datetime]"2026-05-13"; Description = "Chacha Ch"; Amount = [decimal]300 },
        @{ ID = 71; Date = [datetime]"2026-05-13"; Description = "Petrol"; Amount = [decimal]200 }
    )

    $openingCapital = [decimal](($expenseRows | ForEach-Object { [decimal]$_["Amount"] } | Measure-Object -Sum).Sum)
    Invoke-Db $Database "INSERT INTO [Capital Balance] ([Date], [Description], [Amount]) VALUES ($(Sql-Date ([datetime]'2026-05-11')), 'Opening Capital Balance', $(Sql-Money $openingCapital))"

    foreach ($row in $expenseRows) {
        Invoke-Db $Database "INSERT INTO [Expenses] ([ID], [Date], [Description], [Amount]) VALUES ($($row["ID"]), $(Sql-Date $row["Date"]), $(Sql-Text $row["Description"]), $(Sql-Money $row["Amount"]))"
    }

    $runningBalance = $openingCapital
    foreach ($row in $expenseRows) {
        $runningBalance -= [decimal]$row["Amount"]
        Invoke-Db $Database "INSERT INTO [Remaining Balance] ([Date], [VoucherID], [Remaining Balance]) VALUES ($(Sql-Date $row["Date"]), $($row["ID"]), $(Sql-Money $runningBalance))"
    }
}

$resolvedOutput = [IO.Path]::GetFullPath($OutputPath)
$outputDir = Split-Path -Parent $resolvedOutput
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}

if (Test-Path $resolvedOutput) {
    Remove-Item -LiteralPath $resolvedOutput -Force
}

$access = $null
try {
    $access = New-Object -ComObject Access.Application
    $access.Visible = $false
    $access.NewCurrentDatabase($resolvedOutput)
    $db = $access.CurrentDb()

    Create-ThreeTableSchema $db
    Seed-SampleData $db
    Set-PlainNumberFormats $db
    Create-AppModule $access
    Create-Dashboard $access
    Create-EntryForms $access

    Add-DbProperty $db "AppTitle" 10 "Expenses Manager"
    Add-DbProperty $db "StartupForm" 10 "frmDashboard"
    Add-DbProperty $db "StartUpShowDBWindow" 1 $true

    $access.CloseCurrentDatabase()
    $access.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($access)

    Write-Output "Created simplified Access expenses database: $resolvedOutput"
} catch {
    if ($access -ne $null) {
        try { $access.Quit() } catch {}
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($access)
    }
    throw
}
