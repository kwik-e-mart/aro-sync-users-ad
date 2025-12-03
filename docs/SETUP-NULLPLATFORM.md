# Guía de Configuración en Nullplatform

## Arquitectura de la Aplicación

Esta aplicación está diseñada para sincronizar usuarios de Entra ID con Nullplatform de forma automatizada. Consta de dos componentes principales:

### Componentes

#### 1. API REST (Python FastAPI)
- **Dockerfile**: `Dockerfile`
- **Tipo de Scope**: Kubernetes (k8s)
- **Puerto**: 8080
- **Función**: Procesa la sincronización de usuarios leyendo archivos CSV desde S3 y actualizando usuarios/roles en Nullplatform

#### 2. Cron Job (Alpine + curl)
- **Dockerfile**: `Dockerfile.cron`
- **Tipo de Scope**: Cron Job
- **Función**: Ejecuta periódicamente una llamada HTTP POST al endpoint de la API REST para disparar la sincronización

### Flujo de Ejecución

```
┌─────────────────────┐
│   S3 Bucket         │
│  ┌──────────────┐   │
│  │ users.csv    │   │
│  │ mapping.csv  │   │
│  └──────────────┘   │
└──────────┬──────────┘
           │
           │ lee archivos
           │
┌──────────▼──────────────────────────────────┐
│  Scope K8s (API REST)                       │
│  ┌────────────────────────────────────┐    │
│  │  FastAPI Application               │    │
│  │  POST /sync-from-s3                │    │
│  │                                     │    │
│  │  - Lee CSVs desde S3               │    │
│  │  - Sincroniza usuarios             │    │
│  │  - Actualiza roles                 │    │
│  │  - Guarda resultados en S3         │    │
│  └────────────────────────────────────┘    │
└──────────▲──────────────────────────────────┘
           │
           │ HTTP POST
           │
┌──────────┴──────────┐
│  Scope Cron Job     │
│  ┌──────────────┐   │
│  │ trigger-sync │   │
│  │    script    │   │
│  └──────────────┘   │
│  (Ejecuta cada X)   │
└─────────────────────┘
```

---

## Configuración en Nullplatform

### Paso 1: Crear API Key de Nullplatform

Antes de configurar los scopes, necesitas crear un API key que la aplicación usará para autenticarse con Nullplatform.

#### 1.1 Acceder a la Configuración de API Keys

1. Inicia sesión en [Nullplatform Console](https://app.nullplatform.com)
2. Haz clic en tu avatar o nombre de usuario en la esquina superior derecha
3. Selecciona **"Organization Settings"** (Configuración de Organización)
4. En el menú lateral, selecciona **"API Keys"**

#### 1.2 Crear Nueva API Key

1. Haz clic en el botón **"Create API Key"** o **"New API Key"**
2. Completa la información:
   - **Name**: Dale un nombre descriptivo (ej: `sync-users-api-key`)
   - **Description**: (Opcional) Describe el propósito (ej: "API key para sincronización de usuarios Entra ID")
   - **Expiration**: Selecciona un período de expiración o "Never" (nunca expira)
   - **Permissions**: Asegúrate de que tenga permisos para:
     - Leer y escribir usuarios (`users:read`, `users:write`)
     - Gestionar roles y grants (`authz:read`, `authz:write`)

3. Haz clic en **"Create"** o **"Generate"**

#### 1.3 Guardar la API Key

**⚠️ IMPORTANTE**: La API key se mostrará **solo una vez**. Asegúrate de copiarla y guardarla en un lugar seguro.

La API key tendrá un formato similar a:
```
MjEwOTY4NDQxNQ==.Zmo9ZU0xYXdiMz1QR3dHbEBkMElwJFdYY29JeWZMb0Q=
```

**Notas de seguridad**:
- ❌ No compartas esta key en repositorios públicos
- ❌ No la incluyas en archivos de configuración versionados
- ✅ Úsala solo en variables de entorno o sistemas de gestión de secrets
- ✅ Rótala periódicamente por seguridad

#### 1.4 Obtener Organization ID

Mientras estás en la configuración de la organización:
1. Ve a **"Organization Settings"** > **"General"**
2. Copia el **Organization ID** (será un número como `1850605908`)
3. Guarda este ID, lo necesitarás más adelante

---

### Paso 2: Crear Bucket S3

Necesitas crear un bucket S3 para almacenar los archivos CSV de entrada y los resultados de sincronización.

1. Crea un bucket S3 (por ejemplo: `sync-users-bucket`)
2. Estructura de carpetas recomendada:
   ```
   sync-users-bucket/
   ├── input/
   │   ├── users.csv
   │   └── mapping.csv
   └── results/
       └── (archivos JSON generados)
   ```

---

### Paso 3: Configurar Scope API REST (K8s)

#### 3.1 Crear Application y Scope

1. En Nullplatform, crea una nueva **Application** llamada `sync-users` o similar
2. Dentro de la aplicación, crea un **Scope** de tipo **Kubernetes** llamado `api`

#### 3.2 Configurar Asset

1. Vincula el asset Docker generado por CI/CD:
   - **Asset name**: `sync-users-ad`
   - **Asset type**: `docker-image`

#### 3.3 Configurar Variables de Entorno

Configura las siguientes variables de entorno en el scope:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `NULLPLATFORM_API_KEY` | API key de Nullplatform (Secret) | `MjEwOTY4NDQxNQ==...` |
| `ORGANIZATION_ID` | ID de tu organización | `1850605908` |
| `AUTH_API_URL` | URL del API de autenticación | `https://auth.nullplatform.io` |
| `USERS_API_URL` | URL del API de usuarios | `https://users.nullplatform.io` |
| `S3_BUCKET` | Nombre del bucket S3 | `sync-users-bucket` |
| `S3_AD_USERS_FILE` | Ruta del archivo de usuarios en S3 | `input/users.csv` |
| `S3_MAPPING_FILE` | Ruta del archivo de mapeo en S3 | `input/mapping.csv` |
| `S3_RESULTS_PREFIX` | Prefijo para archivos de resultado | `results/` |
| `AWS_REGION` | Región de AWS | `us-east-1` |

**⚠️ Importante**: Asegúrate de que `NULLPLATFORM_API_KEY` esté marcado como **Secret** en Nullplatform.

#### 3.4 Configurar Service Account (Permisos S3)

El scope necesita permisos de lectura y escritura en S3:

1. En la configuración del scope, ve a **Service Account**
2. Asigna o crea un Service Account con la siguiente política IAM:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::*",
        "arn:aws:s3:::*/*"
      ]
    }
  ]
}
```

#### 3.5 Configurar Networking

1. Configura el **Service** para exponer el puerto **8080**
2. Si necesitas acceso externo, configura un **Ingress** (opcional)

---

### Paso 4: Configurar Scope Cron Job

#### 4.1 Crear Scope Cron

1. En la misma aplicación `sync-users`, crea un nuevo **Scope** de tipo **Cron Job** llamado `sync-trigger`
2. Configura el schedule según tus necesidades (ejemplo) cada hora

#### 4.2 Configurar Asset

1. Vincula el asset Docker del cron job:
   - **Asset name**: `sync-users-ad-cron`
   - **Asset type**: `docker-image`

#### 4.3 Configurar Variables de Entorno

Configura la siguiente variable de entorno:

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `SYNC_API_URL` | URL del servicio API REST | `http://sync-users-api:8080` |

**Nota**: El formato de la URL depende de cómo esté configurado el servicio de Kubernetes:
- Mismo namespace: `http://<service-name>:8080`
- Diferente namespace: `http://<service-name>.<namespace>.svc.cluster.local:8080`

---

## Paso 5: Preparar Archivos CSV

### Archivo de Usuarios (users.csv)

Formato esperado:

```csv
Nombre,Correo,Grupo
Juan Pérez,juan.perez@example.com,Developers
María García,maria.garcia@example.com,Admins
Pedro López,pedro.lopez@example.com,Viewers
```

### Archivo de Mapeo (mapping.csv)

Formato esperado:

```csv
grupo,nrn,roles
Developers,organization=1850605908:account=123:namespace=456,"developer,member"
Admins,organization=1850605908:account=123:namespace=456,admin
Viewers,*,"viewer,member"
```

#### Formato del campo NRN

El campo `nrn` puede tener tres formatos:

1. **NRN Completo**: Para acceso a recursos específicos
   ```
   organization=1850605908:account=123:namespace=456
   ```

2. **NRN Múltiple**: Para acceso a múltiples recursos (separado por comas)
   ```
   organization=1850605908:account=123,organization=1850605908:namespace=789
   ```

3. **Wildcard (`*`)**: Para acceso a nivel organización
   ```
   *
   ```
   Se resuelve automáticamente a `organization={ORGANIZATION_ID}`

### Subir Archivos a S3

```bash
# Usando AWS CLI
aws s3 cp users.csv s3://sync-users-bucket/input/users.csv
aws s3 cp mapping.csv s3://sync-users-bucket/input/mapping.csv
```

---

## Paso 6: Desplegar

### 5.1 Push de Assets

Los assets se construyen y se envían automáticamente a través del CI/CD cuando haces push a las ramas configuradas (`main` o `feat/*`).

El workflow de GitHub Actions (`.github/workflows/ci.yml`) se encarga de:
1. Construir ambas imágenes Docker
2. Enviarlas a Nullplatform
3. Notificar el estado del build

### 5.2 Verificar Deployment

1. En Nullplatform, ve a tu aplicación `sync-users`
2. Verifica que ambos scopes estén desplegados correctamente:
   - **api** (K8s) - Estado: Running
   - **sync-trigger** (Cron Job) - Estado: Active

---

## Paso 7: Pruebas

### Prueba Manual del API

Puedes probar el endpoint manualmente antes de que el cron job lo ejecute:

```bash
# Usando kubectl port-forward
kubectl port-forward -n <namespace> svc/sync-users-api 8080:8080

# En otra terminal, ejecuta la sincronización
curl -X POST "http://localhost:8080/sync-from-s3" | jq .

# Prueba en modo dry-run (sin hacer cambios)
curl -X POST "http://localhost:8080/sync-from-s3?dry_run=true" | jq .
```

### Ver Logs

#### Logs del API (K8s)
```bash
kubectl logs -n <namespace> -l app=sync-users-api --tail=100 -f
```

#### Logs del Cron Job
```bash
# Ver últimas ejecuciones
kubectl get jobs -n <namespace>

# Ver logs de una ejecución específica
kubectl logs -n <namespace> <job-name>
```

### Ver Resultados en S3

```bash
# Listar resultados
aws s3 ls s3://sync-users-bucket/results/

# Descargar un resultado específico
aws s3 cp s3://sync-users-bucket/results/<md5-hash>.json resultado.json

# Ver contenido
cat resultado.json | jq .
```

---

## Troubleshooting

### El Cron Job no puede conectarse al API

**Síntoma**: Error de conexión en los logs del cron job

**Solución**:
1. Verifica que `SYNC_API_URL` apunte al servicio correcto
2. Asegúrate de que ambos scopes estén en el mismo namespace o usa FQDN
3. Verifica que el servicio API esté expuesto en el puerto 8080

```bash
# Verificar servicio
kubectl get svc -n <namespace> sync-users-api
```

### Error de DNS "[Errno -2] Name or service not known"

**Síntoma**: La aplicación no puede resolver nombres de dominio

**Soluciones**:
1. Verifica que `AWS_ENDPOINT_URL` **NO** esté configurado (o esté vacío) en producción
2. Comprueba la conectividad DNS del cluster:
   ```bash
   kubectl exec -it <pod-name> -- nslookup s3.us-east-1.amazonaws.com
   ```

### Archivos no encontrados en S3

**Síntoma**: Error "NoSuchKey" en los logs

**Soluciones**:
1. Verifica que los archivos existan en S3:
   ```bash
   aws s3 ls s3://sync-users-bucket/input/
   ```
2. Comprueba que las variables `S3_AD_USERS_FILE` y `S3_MAPPING_FILE` tengan las rutas correctas
3. Verifica que el Service Account tenga permisos de lectura en S3

### Permisos insuficientes en S3

**Síntoma**: Error "Access Denied" al leer/escribir en S3

**Solución**:
Revisa la política IAM del Service Account y asegúrate de que incluya:
- `s3:GetObject` - Para leer archivos
- `s3:PutObject` - Para escribir resultados
- `s3:ListBucket` - Para listar contenidos

---

## Mantenimiento

### Actualizar Archivos CSV

Simplemente reemplaza los archivos en S3. La próxima ejecución del cron job usará los nuevos archivos:

```bash
aws s3 cp users.csv s3://sync-users-bucket/input/users.csv
aws s3 cp mapping.csv s3://sync-users-bucket/input/mapping.csv
```

### Forzar Sincronización Inmediata

Si no quieres esperar al próximo cron job:

```bash
# Port-forward al servicio
kubectl port-forward -n <namespace> svc/sync-users-api 8080:8080

# Ejecutar sincronización manualmente
curl -X POST "http://localhost:8080/sync-from-s3" | jq .
```

### Actualizar la Aplicación

Simplemente haz push a la rama `main` o `feat/*`. El CI/CD automáticamente:
1. Construirá las nuevas imágenes
2. Las enviará a Nullplatform
3. Nullplatform desplegará las nuevas versiones

---

## Seguridad

### Mejores Prácticas

1. **Secrets**: Nunca incluyas credenciales en el código o variables de entorno visibles
2. **API Key**: Usa el sistema de secrets de Nullplatform para `NULLPLATFORM_API_KEY`
3. **S3 Bucket**: Configura políticas de bucket para permitir acceso solo desde el Service Account del cluster
4. **Network Policies**: Restringe el tráfico de red entre pods usando Network Policies de Kubernetes
5. **RBAC**: Limita los permisos del Service Account solo a lo necesario

### Rotación de Credenciales

Para rotar el `NULLPLATFORM_API_KEY`:
1. Genera un nuevo API key en Nullplatform
2. Actualiza la variable de entorno en el scope `api`
3. Reinicia el deployment para que tome el nuevo valor

---

## Soporte

Para más información, consulta:
- [README.md](../README.md) - Documentación general de la aplicación
- [WILDCARD-NRN-FEATURE.md](WILDCARD-NRN-FEATURE.md) - Documentación sobre el uso de wildcards en NRN
- [technical_proposal.md](../docs/technical_proposal.md) - Propuesta técnica detallada

Para reportar issues: [GitHub Issues](https://github.com/your-org/sync-users-ad/issues)
