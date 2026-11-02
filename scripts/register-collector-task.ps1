param([string]$At = '08:00', [string]$TaskName = 'Alugai-OLX-Collector')
$ErrorActionPreference = 'Stop'
$runner = Join-Path $PSScriptRoot 'run-collector.ps1'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -NonInteractive -WindowStyle Hidden -File "{0}"' -f $runner)
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
# Existing tasks are not overwritten. Runs under the current user when logged in.
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description 'Coletor OLX Alugai; interrompe em bloqueios.'
