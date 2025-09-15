# Step 10 — Build a minimal task-def JSON and register it
# This is the GPT script with one small improvement (UTF8 encoding)

# Load the edited taskdef (with your NEW image)
$td = Get-Content .\taskdef-new.json | ConvertFrom-Json

# Keep only fields allowed by register-task-definition
$payload = [ordered]@{
  family                 = $td.family
  taskRoleArn            = $td.taskRoleArn
  executionRoleArn       = $td.executionRoleArn
  networkMode            = $td.networkMode
  containerDefinitions   = $td.containerDefinitions
  volumes                = $td.volumes
  placementConstraints   = $td.placementConstraints
  requiresCompatibilities= $td.requiresCompatibilities
  cpu                    = $td.cpu
  memory                 = $td.memory
  pidMode                = $td.pidMode
  ipcMode                = $td.ipcMode
  proxyConfiguration     = $td.proxyConfiguration
  inferenceAccelerators  = $td.inferenceAccelerators
  ephemeralStorage       = $td.ephemeralStorage
  runtimePlatform        = $td.runtimePlatform
}

# Write clean JSON (CHANGED: UTF8 instead of ascii)
$payload | ConvertTo-Json -Depth 50 | Set-Content .\taskdef-min.json -Encoding UTF8

# Register new revision
$NEW_TD_ARN = (aws ecs register-task-definition --cli-input-json file://taskdef-min.json --region eu-north-1 `
  --query 'taskDefinition.taskDefinitionArn' --output text)

Write-Host "New Task Definition ARN: $NEW_TD_ARN"
