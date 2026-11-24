[CmdletBinding()]
param(
    [ValidateSet('Start','Status','Scale','Verify','Stop')][string]$Action = 'Status',
    [ValidateRange(1,3)][int]$Replicas = 1,
    [switch]$SkipBuild
)
$ErrorActionPreference = 'Stop'
$DemoRoot = $PSScriptRoot
$AppRoot = (Resolve-Path (Join-Path $DemoRoot '../..')).Path
$LocalRoot = Join-Path $DemoRoot '.local'
$ReportRoot = Join-Path $DemoRoot 'reports'
$EdgeName = 'corestream-trv09-local'
function Invoke-Docker {
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "Docker fallo: $($args[0]) $($args[1])" }
}
function Wait-Service([string]$Name, [int]$Count) {
    $deadline = (Get-Date).AddMinutes(5)
    do {
        $ids = @(& docker ps -q --filter "label=com.docker.swarm.service.name=$Name")
        $healthy = @()
        foreach ($id in $ids) {
            if ($id) {
                $state = & docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $id
                if ($state -eq 'healthy') { $healthy += $id }
            }
        }
        $update = & docker service inspect --format '{{if .UpdateStatus}}{{.UpdateStatus.State}}{{end}}' $Name
        if ($update -in @('paused','rollback_paused')) { throw "Actualizacion detenida: $Name" }
        if ($healthy.Count -eq $Count -and $ids.Count -eq $Count -and $update -notin @('updating','rollback_started')) { return }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "El servicio $Name no alcanzo $Count instancias saludables. Revisar docker service ps $Name"
}
function Require-Demo {
    $exists = & docker service inspect trv09_api --format '{{index .Spec.Labels "com.docker.stack.namespace"}}' 2>$null
    if ($LASTEXITCODE -ne 0 -or $exists -ne 'trv09') { throw 'Primero ejecutar -Action Start.' }
}
function Measure-Demo([int]$Count, [string]$Name) {
    $id = @(& docker ps -q --filter 'label=com.docker.swarm.service.name=trv09_api')[0]
    $json = Invoke-Docker exec $id python /opt/trv09/verify.py --replicas $Count
    $result = $json | ConvertFrom-Json
    if ($result.errors -ne 0) { throw 'La prueba registro errores.' }
    $json | Set-Content -LiteralPath (Join-Path $ReportRoot "$Name.json") -Encoding utf8
    $result | Select-Object replicas,requests,errors,requests_per_second,median_ms,p95_ms,shared_file_ok,session_refresh_ok | Format-Table
}
switch ($Action) {
    'Start' {
        $os = Invoke-Docker info --format '{{.OSType}}'
        if ($os -ne 'linux') { throw 'Docker debe usar contenedores Linux.' }
        New-Item -ItemType Directory -Force $LocalRoot,$ReportRoot | Out-Null
        foreach ($name in @('db_password','jwt_key','redis_password','demo_password')) {
            $file = Join-Path $LocalRoot $name
            if (-not (Test-Path -LiteralPath $file)) {
                $bytes = New-Object byte[] 32
                $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
                try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
                $value = [BitConverter]::ToString($bytes).Replace('-','').ToLowerInvariant()
                [IO.File]::WriteAllText($file,$value)
            }
        }
        if (-not $SkipBuild) {
            Invoke-Docker build -t corestream-trv09-api-base:local (Join-Path $AppRoot 'backend')
            Invoke-Docker build -t corestream-trv09-web-base:local (Join-Path $AppRoot 'frontend')
            Invoke-Docker build -t corestream-trv09-api:local -f (Join-Path $DemoRoot 'api.Dockerfile') $DemoRoot
            Invoke-Docker build -t corestream-trv09-web:local -f (Join-Path $DemoRoot 'web.Dockerfile') $DemoRoot
        }
        # Etiquetas por contenido: Swarm detecta las imagenes nuevas al desplegar.
        $apiId = Invoke-Docker image inspect --format '{{.Id}}' corestream-trv09-api:local
        $webId = Invoke-Docker image inspect --format '{{.Id}}' corestream-trv09-web:local
        $apiVersion = 'corestream-trv09-api:demo-' + $apiId.Substring(7,12)
        $webVersion = 'corestream-trv09-web:demo-' + $webId.Substring(7,12)
        Invoke-Docker tag corestream-trv09-api:local $apiVersion
        Invoke-Docker tag corestream-trv09-web:local $webVersion
        $env:TRV09_API_IMAGE = $apiVersion
        $env:TRV09_WEB_IMAGE = $webVersion
        $swarm = Invoke-Docker info --format '{{.Swarm.LocalNodeState}}'
        if ($swarm -eq 'inactive') { Invoke-Docker swarm init | Out-Null }
        $manager = Invoke-Docker info --format '{{.Swarm.ControlAvailable}}'
        if ($manager -ne 'true') { throw 'El nodo debe ser administrador de Swarm.' }
        $nodeId = Invoke-Docker info --format '{{.Swarm.NodeID}}'
        Invoke-Docker node update --label-add corestream.trv09=true $nodeId
        $secrets = @{db_password='corestream-trv09-db'; jwt_key='corestream-trv09-jwt'; redis_password='corestream-trv09-redis'; demo_password='corestream-trv09-admin'}
        foreach ($name in $secrets.Keys) {
            $found = & docker secret ls --filter "name=$($secrets[$name])" --format '{{.Name}}'
            if ($found -ne $secrets[$name]) { Invoke-Docker secret create $secrets[$name] (Join-Path $LocalRoot $name) | Out-Null }
        }
        # Datos primero. Las migraciones se ejecutan una vez, fuera de las replicas.
        $env:TRV09_REPLICAS = '0'
        Invoke-Docker stack deploy --resolve-image never -c (Join-Path $DemoRoot 'stack.yml') trv09
        Wait-Service trv09_postgres 1
        Wait-Service trv09_redis 1
        $runArgs = @('run','--rm','--network','trv09_internal','--env','ENVIRONMENT=demo','--env','DEBUG=false','--env','STORAGE_BACKEND=local')
        foreach ($name in $secrets.Keys) { $runArgs += @('--mount',"type=bind,source=$(Join-Path $LocalRoot $name),target=/run/secrets/$name,readonly") }
        Invoke-Docker @runArgs $apiVersion alembic upgrade head
        Invoke-Docker @runArgs $apiVersion python /opt/trv09/seed.py
        Invoke-Docker service scale --detach "trv09_api=$Replicas"
        Wait-Service trv09_api $Replicas
        Wait-Service trv09_web 1
        $edge = @(& docker ps -a -q --filter "name=^/$EdgeName`$")
        if ($edge.Count -gt 0) {
            $label = Invoke-Docker inspect --format '{{index .Config.Labels "com.corestream.demo"}}' $EdgeName
            if ($label -ne 'trv09') { throw 'Existe una puerta local ajena a esta demostracion.' }
            Invoke-Docker rm -f $EdgeName | Out-Null
        }
        Invoke-Docker run -d --name $EdgeName --label com.corestream.demo=trv09 --network trv09_internal -p 127.0.0.1:18080:8080 --memory 64m --cpus 0.25 --restart unless-stopped $webVersion nginx -c /etc/nginx/trv09-edge.conf -g 'daemon off;'
        Write-Host 'Laboratorio disponible: http://127.0.0.1:18080/#/login'
        Write-Host 'Correo: admin.trv09@example.org. Clave local en deploy/trv09/.local/demo_password (no subir a GitHub).'
    }
    'Status' { Invoke-Docker stack services trv09; Invoke-Docker service ps trv09_api }
    'Scale' {
        Require-Demo
        Invoke-Docker service scale --detach "trv09_api=$Replicas"
        Wait-Service trv09_api $Replicas
        Invoke-Docker service ls --filter name=trv09_api
    }
    'Verify' {
        Require-Demo
        New-Item -ItemType Directory -Force $ReportRoot | Out-Null
        Invoke-Docker service scale --detach trv09_api=1
        Wait-Service trv09_api 1
        Measure-Demo 1 '01-una-replica'
        Invoke-Docker service scale --detach trv09_api=3
        Wait-Service trv09_api 3
        Measure-Demo 3 '02-tres-replicas'
        $before = @(& docker ps -q --filter 'label=com.docker.swarm.service.name=trv09_api')
        if ($before.Count -ne 3) { throw 'Se requieren tres contenedores antes de probar recuperacion.' }
        $killed = $before[0]
        # Solo detener una instancia del laboratorio, identificada por la etiqueta Swarm.
        Invoke-Docker kill $killed | Out-Null
        Wait-Service trv09_api 3
        $after = @(& docker ps -q --filter 'label=com.docker.swarm.service.name=trv09_api')
        $new = @($after | Where-Object { $_ -notin $before })
        if ($new.Count -lt 1 -or $killed -in $after) { throw 'No se verifico el reemplazo del contenedor detenido.' }
        @{stopped=$killed;replacement=$new;before=$before;after=$after} | ConvertTo-Json | Set-Content (Join-Path $ReportRoot '03-recuperacion.json') -Encoding utf8
        Measure-Demo 3 '04-despues-recuperacion'
        Invoke-Docker service ps trv09_api | Out-File (Join-Path $ReportRoot 'tareas.txt') -Encoding utf8
        Write-Host 'Pruebas completas. Informes en deploy/trv09/reports/. Se mantienen tres replicas.'
    }
    'Stop' {
        Require-Demo
        $edge = @(& docker ps -a -q --filter "name=^/$EdgeName`$")
        if ($edge.Count -gt 0) {
            $label = Invoke-Docker inspect --format '{{index .Config.Labels "com.corestream.demo"}}' $EdgeName
            if ($label -ne 'trv09') { throw 'El contenedor encontrado no pertenece al laboratorio.' }
            Invoke-Docker rm -f $EdgeName | Out-Null
        }
        Invoke-Docker stack rm trv09
        $deadline = (Get-Date).AddMinutes(2)
        do {
            $network = @(& docker network ls --filter name=trv09_internal --format '{{.Name}}')
            if ('trv09_internal' -notin $network) { break }
            Start-Sleep -Seconds 2
        } while ((Get-Date) -lt $deadline)
        if ('trv09_internal' -in $network) { throw 'La red sigue retirandose. Esperar antes de iniciar de nuevo.' }
        Write-Host 'Laboratorio detenido. Se conservan datos, archivos y secretos. Swarm permanece habilitado.'
    }
}
