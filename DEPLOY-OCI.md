# Paso a paso: SofB Train en Oracle Cloud (OCI) Always Free

Esta guía asume que vas a correr la app con **Docker** en una **VM Ampere (ARM)** con Ubuntu o Oracle Linux, con **IP pública** y datos en disco local de la VM (persistente).

**Tiempo aproximado:** 45–90 min la primera vez (cuenta + red + VM + deploy).

---

## 0. Requisitos

- Tarjeta de crédito/débito (Oracle la usa para verificación; el tier Always Free no debería cobrarte por lo descrito en su política, pero leé los términos vigentes).
- Navegador y, si podés, un cliente **SSH** (PowerShell con `ssh`, PuTTY, etc.).

---

## 1. Crear la cuenta y el “Home Region”

1. Entrá a [https://www.oracle.com/cloud/free/](https://www.oracle.com/cloud/free/) y creá una cuenta **Free Tier**.
2. Elegí una **región “Home”** donde exista **Always Free** (p. ej. `Santiago`, `São Paulo`, `Ashburn`). Después **no podés** cambiar el Home Region fácilmente: elegí la más cercana a tus usuarios.
3. Completá verificación de identidad y pago si lo piden.

---

## 2. Crear la red (VCN) y dejar la VM accesible por Internet

En la consola OCI: **Networking → Virtual Cloud Networks** → **Start VCN Wizard** (o creación manual).

### IPv4 CIDR Blocks (campo obligatorio)

Oracle te pide uno o más rangos **privados** en notación CIDR. Valores típicos (el asistente suele sugerirlos igual):

| Dónde | Qué poner (ejemplo) |
|--------|----------------------|
| **VCN** (red principal) | `10.0.0.0/16` |
| **Subnet pública** (si la pide aparte) | `10.0.0.0/24` |

- **`/16`**: la VCN tiene muchas IPs para varias subredes.
- **`/24`**: una subred con 256 direcciones; debe estar **dentro** del bloque de la VCN (p. ej. `10.0.0.0/24` dentro de `10.0.0.0/16`).

Otras VCN en el mismo tenancy no deberían repetir el mismo rango si se van a enlazar; para una sola VCN, **`10.0.0.0/16`** está bien.

1. **Nombre:** por ejemplo `vcn-tren`.
2. **DNS resolution:** habilitado.
3. **Subred pública:** que el asistente cree una subnet con **ruta a Internet Gateway** (tráfico `0.0.0.0/0` → Internet Gateway).
4. **Reglas de entrada (Ingress)** en el **Security List** de esa subnet (o en un **Network Security Group** asociado a la VM):
   - **TCP 22** desde tu IP (`tu.ip/32`) o temporalmente `0.0.0.0/0` si no sabés la IP (menos seguro; después restringí).
   - **TCP 8000** desde `0.0.0.0/0` (para probar la web) **o** solo tu IP si es uso interno.

> Para producción conviene poner **HTTPS en el puerto 443** con un proxy (Caddy / Nginx + Let’s Encrypt) y cerrar el 8000 al mundo. Eso es un paso extra al final.

---

## 3. Crear la instancia de cómputo (Always Free ARM)

**Compute → Instances → Create instance**

1. **Name:** `tren-web` (ejemplo).
2. **Placement:** misma región que tu VCN.
3. **Image:** **Canonical Ubuntu 22.04** (aarch64) u **Oracle Linux 8/9** ARM.
4. **Shape:** **Ampere A1 Flex** (`VM.Standard.A1.Flex`).
   - En Always Free suele alcanzar **1 OCPU y 6 GB RAM** (revisá el límite actual en la consola).
5. **Networking:** elegí la **VCN** y la **subnet pública** del paso 2.
6. **Public IPv4 address:** **Assign** (necesitás IP pública para entrar desde el navegador sin VPN).
7. **SSH keys:** generá un par nuevo en la consola **o** subí tu clave **pública** `.pub`. **Guardá la privada** en tu PC.
8. **Boot volume:** el mínimo suele bastar (50 GB max free según política vigente).
9. **Create**.

Esperá a que el estado pase a **RUNNING** y anotá la **IP pública** de la instancia.

---

## 4. Probar SSH

Desde tu PC (ajustá la ruta de la clave y la IP):

```bash
ssh -i ruta/a/tu_clave_privada opcion@IP_PUBLICA
```

En **Ubuntu** el usuario suele ser `ubuntu`. En **Oracle Linux** suele ser `opc`.

---

## 5. Instalar Docker en la VM

**Ubuntu 22.04 (ARM)** — resumen oficial de Docker:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
```

Cerrá sesión y volvé a entrar (o `newgrp docker`) para usar Docker sin `sudo`.

---

## 6. Subir el código al servidor

Elegí **una** de estas dos:

### A) Clonar desde Git (recomendado)

En la VM:

```bash
sudo mkdir -p /opt/tren && sudo chown $USER:$USER /opt/tren
cd /opt/tren
git clone https://github.com/TU_USUARIO/TU_REPO.git app
cd app
```

### B) Copiar desde tu PC con `scp`

Desde tu PC (PowerShell), desde la carpeta del proyecto:

```powershell
git
```

Luego en la VM: `cd /opt/tren/app`.

---

## 7. Directorio de datos persistente

En la VM:

```bash
sudo mkdir -p /opt/tren-data && sudo chown $USER:$USER /opt/tren-data
```

Ahí vivirán `datos_tren.db` y `estado_tren.json` (vía `TREN_DATA_DIR`).

---

## 8. Construir y ejecutar el contenedor

Desde la carpeta del proyecto en la VM (donde está el `Dockerfile`):

```bash
docker build -t sofb-tren:latest .
docker run -d --name sofb-tren --restart unless-stopped \
  -p 8000:8000 \
  -e TREN_DATA_DIR=/data \
  -v /opt/tren-data:/data \
  sofb-tren:latest
```

Comprobación:

```bash
docker ps
curl -s http://127.0.0.1:8000/health
```

Desde tu navegador: `http://IP_PUBLICA:8000/`

---

## 9. Firewall dentro de la VM (Ubuntu)

Si `curl` local funciona pero el navegador no llega:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 8000/tcp
sudo ufw enable
sudo ufw status
```

Recordá que **OCI Security List** también debe permitir **8000** (paso 2).

---

## 10. Actualizar cuando cambies el código

```bash
cd /opt/tren/app
git pull   # o volvé a subir archivos con scp
docker build -t sofb-tren:latest .
docker rm -f sofb-tren
docker run -d --name sofb-tren --restart unless-stopped \
  -p 8000:8000 \
  -e TREN_DATA_DIR=/data \
  -v /opt/tren-data:/data \
  sofb-tren:latest
```

Los datos en `/opt/tren-data` **no** se pierden al reconstruir la imagen.

---

## 11. (Opcional) HTTPS con Caddy en el host

No es obligatorio para pruebas. Idea: Caddy escucha en **443**, hace TLS automático con Let’s Encrypt, y reenvía a `127.0.0.1:8000`.

1. Apuntá un **DNS** (ej. `tren.tudominio.com`) a la **IP pública**.
2. Instalá Caddy en la VM, abrí **443** en OCI Security List y en `ufw`.
3. Configurá un `reverse_proxy` a `127.0.0.1:8000` y cerrá el acceso público directo al 8000 si querés endurecer.

---

## 12. Límites y buenas prácticas Always Free

- Revisá en la documentación de Oracle los **límites actuales** de OCPU / RAM / Ampere por tenancy.
- Hacé **snapshots** o backup periódico de `/opt/tren-data` (los dos archivos o un `.tar.gz`).
- La app **no tiene autenticación** todavía: cualquiera con la URL puede operar. Restringí IP en Security List o poné delante un túnel/VPN hasta que agregues login o API key.

---

## Referencia rápida de variables

| Variable | En OCI con este `docker run` |
|----------|------------------------------|
| `TREN_DATA_DIR` | `/data` (dentro del contenedor) |
| Volumen host | `/opt/tren-data` → `/data` |

Más detalle genérico: `DEPLOY.md`.
