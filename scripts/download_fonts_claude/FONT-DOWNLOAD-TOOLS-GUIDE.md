# 🚀 Descargar Google Fonts → WOFF2 + CSS

Guía de las **mejores herramientas comprobadas y funcionando** para descargar fuentes de Google Fonts en WOFF2.

---

## ✅ HERRAMIENTAS RECOMENDADAS Y PROBADAS

### **Opción 1: goog-webfont-dl (NPM)** ⭐⭐⭐ MÁS FÁCIL

Herramienta CLI sencilla que descarga fuentes y genera CSS automáticamente.

#### Instalación:
```bash
npm install -g goog-webfont-dl
```

#### Uso básico:
```bash
# Una fuente
goog-webfont-dl -f "Roboto" -W -d ./fonts -o ./fonts.css

# Múltiples fuentes
goog-webfont-dl -f "Open Sans" -W -d ./fonts -o ./fonts.css
goog-webfont-dl -f "Lato" -W -d ./fonts -o ./fonts.css
```

#### Opciones:
- `-f, --font NAME` - Nombre de la fuente
- `-W, --woff2` - Descargar formato WOFF2 (recomendado)
- `-w, --woff` - Descargar formato WOFF
- `-t, --ttf` - Descargar formato TTF
- `-a, --all` - Descargar todos los formatos
- `-d, --destination DIR` - Carpeta destino (default: nombre de fuente)
- `-o, --out FILE` - Archivo CSS de salida

#### Ejemplo completo:
```bash
mkdir -p my-project/fonts
cd my-project

# Descargar varias fuentes
goog-webfont-dl -f "Roboto" -W -d ./fonts -o ./fonts.css
goog-webfont-dl -f "Open Sans" -W -d ./fonts -o ./fonts.css
goog-webfont-dl -f "Playfair Display" -W -d ./fonts -o ./fonts.css
```

---

### **Opción 2: Script Bash automatizado** ⭐⭐⭐ BATCH

Usa el script `download-fonts.sh` incluido para descargar múltiples fuentes de una vez.

#### Requisitos:
```bash
npm install -g goog-webfont-dl
chmod +x download-fonts.sh
```

#### Uso:
```bash
# Usar configuración por defecto (fonts-config.txt)
./download-fonts.sh

# Especificar carpeta destino
./download-fonts.sh -d ./assets/fonts -o ./assets/fonts.css

# Desde archivo de configuración
./download-fonts.sh -c mi-fuentes.txt

# Descargar fuente específica
./download-fonts.sh -f "Roboto"
```

#### Archivo de configuración (fonts-config.txt):
```
Roboto|regular,700,700i
Open Sans|400,600,700
Playfair Display|regular,700
Lato|400,700,900
```

---

### **Opción 3: Sin instalar nada - Descarga directa** ⭐⭐ SIMPLE

Usa curl directamente en la API de Google Webfonts Helper.

```bash
# Descargar Roboto en WOFF2
curl -o fonts.zip "https://gwfh.mranftl.com/api/fonts/roboto?download=zip&formats=woff2"

# Extraer
unzip fonts.zip -d ./fonts
```

**Ventaja:** No necesitas instalar nada  
**Desventaja:** No genera CSS automáticamente (tienes que hacerlo manualmente)

#### Ejemplo para múltiples fuentes:
```bash
mkdir -p fonts

# Roboto
curl -o roboto.zip "https://gwfh.mranftl.com/api/fonts/roboto?download=zip&formats=woff2" && unzip -o roboto.zip -d ./fonts && rm roboto.zip

# Open Sans
curl -o opensans.zip "https://gwfh.mranftl.com/api/fonts/open-sans?download=zip&formats=woff2" && unzip -o opensans.zip -d ./fonts && rm opensans.zip

# Lato
curl -o lato.zip "https://gwfh.mranftl.com/api/fonts/lato?download=zip&formats=woff2" && unzip -o lato.zip -d ./fonts && rm lato.zip
```

---

### **Opción 4: glyphhanger (NPM) - Para optimización** ⭐⭐⭐ AVANZADO

Si tienes archivos TTF/OTF locales y quieres convertir a WOFF2 + subsetting.

#### Instalación:
```bash
npm install -g glyphhanger
```

#### Uso:
```bash
# Convertir y optimizar TTF → WOFF2
glyphhanger --whitelist=U+0-10FFFF font.ttf

# Resultado: font-subset.woff2
```

---

## 📊 COMPARATIVA RÁPIDA

| Herramienta | Setup | Automatización | WOFF2 | Múltiples | CSS |
|---|---|---|---|---|---|
| **goog-webfont-dl** | 1 min | ⭐⭐⭐ | ✅ | ✅ | ✅ |
| **Script Bash** | 2 min | ⭐⭐⭐⭐ | ✅ | ✅✅ | ✅ |
| **curl directo** | Inmediato | ⭐ | ✅ | ✅ | ❌ |
| **glyphhanger** | 3 min | ⭐⭐⭐ | ✅ | ✅ | ❌ |

---

## 🚀 GUÍA RÁPIDA DE INICIO

### **Escenario A: Quiero lo más sencillo**

```bash
# 1. Instalar
npm install -g goog-webfont-dl

# 2. Crear carpeta
mkdir -p my-project/fonts
cd my-project

# 3. Descargar una fuente
goog-webfont-dl -f "Roboto" -W -d ./fonts -o ./fonts.css

# 4. Usar en HTML
# <link rel="stylesheet" href="fonts.css">
# body { font-family: 'Roboto', sans-serif; }
```

---

### **Escenario B: Quiero descargar múltiples fuentes**

```bash
# 1. Instalar
npm install -g goog-webfont-dl

# 2. Usar el script (en la carpeta del proyecto)
chmod +x download-fonts.sh
./download-fonts.sh

# ✅ Listo. Genera:
# - ./fonts/*.woff2 (todos los archivos)
# - ./fonts.css (CSS automático)
```

---

### **Escenario C: Sin instalar nada (solo curl)**

```bash
#!/bin/bash
mkdir -p fonts

# Crear CSS
cat > fonts.css << 'EOF'
@font-face {
    font-family: 'Roboto';
    src: url('./fonts/roboto-regular-normal-latin.woff2') format('woff2');
    font-weight: 400;
    font-style: normal;
    font-display: swap;
}
EOF

# Descargar fuentes
for font in "roboto" "open-sans" "lato"; do
    curl -s -o $font.zip "https://gwfh.mranftl.com/api/fonts/$font?download=zip&formats=woff2"
    unzip -o $font.zip -d ./fonts
    rm $font.zip
done
```

---

## 📁 ESTRUCTURA FINAL

```
proyecto/
├── fonts/
│   ├── roboto-regular-normal-latin.woff2
│   ├── roboto-700-normal-latin.woff2
│   ├── open-sans-400-normal-latin.woff2
│   └── lato-700-normal-latin.woff2
├── fonts.css
└── index.html
```

---

## 📝 ARCHIVO CSS GENERADO

```css
/* Generated by Google Fonts Downloader */
/* Date: 2025-04-17 14:30:45 */
/* Total fonts: 3 */

@font-face {
    font-family: 'Roboto';
    src: url('./fonts/roboto-regular-normal-latin.woff2') format('woff2');
    font-weight: 400;
    font-style: normal;
    font-display: swap;
}

@font-face {
    font-family: 'Roboto';
    src: url('./fonts/roboto-700-normal-latin.woff2') format('woff2');
    font-weight: 700;
    font-style: normal;
    font-display: swap;
}

@font-face {
    font-family: 'Open Sans';
    src: url('./fonts/open-sans-400-normal-latin.woff2') format('woff2');
    font-weight: 400;
    font-style: normal;
    font-display: swap;
}
```

---

## 💻 USO EN HTML

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <link rel="stylesheet" href="fonts.css">
    <style>
        body {
            font-family: 'Roboto', sans-serif;
            font-weight: 400;
        }
        h1 {
            font-family: 'Playfair Display', serif;
            font-weight: 700;
        }
        strong {
            font-weight: 700;
        }
    </style>
</head>
<body>
    <h1>Hola Mundo</h1>
    <p>Este texto usa Roboto</p>
    <strong>Texto bold</strong>
</body>
</html>
```

---

## 🛠️ SOLUCIÓN DE PROBLEMAS

### ❌ "goog-webfont-dl: command not found"
```bash
# Instalar globalmente
npm install -g goog-webfont-dl

# O verificar que está en PATH
which goog-webfont-dl
```

### ❌ "Font not found"
Verifica que el nombre sea exacto:
```bash
✅ Roboto, Open Sans, Playfair Display
❌ roboto, opensans, playfair
```

### ❌ "Permission denied" en script
```bash
chmod +x download-fonts.sh
./download-fonts.sh
```

### ❌ No descarga WOFF2
Asegúrate de usar `-W` (mayúscula):
```bash
✅ goog-webfont-dl -f "Roboto" -W
❌ goog-webfont-dl -f "Roboto" -w  (eso es para WOFF)
```

---

## 📊 TAMAÑOS TÍPICOS

| Fuente | WOFF2 | TTF | Compresión |
|---|---|---|---|
| Roboto Regular | ~18 KB | ~130 KB | 86% |
| Lato Bold | ~22 KB | ~160 KB | 86% |
| Playfair Display | ~25 KB | ~180 KB | 86% |

---

## ✨ MEJORES PRÁCTICAS

1. **Usa WOFF2:** Es el formato más moderno y comprimido
2. **Especifica pesos:** Solo descarga los pesos que necesitas
3. **Usa font-display: swap:** Muestra el texto de inmediato
4. **Aloja localmente:** No dependas de servidores externos
5. **Limpia variantes:** No descargues 900i si solo usas 400 y 700

---

## 📚 REFERENCIAS

- **goog-webfont-dl:** https://www.npmjs.com/package/goog-webfont-dl
- **Google Webfonts Helper:** https://gwfh.mranftl.com/
- **glyphhanger:** https://www.npmjs.com/package/glyphhanger
- **Google Fonts:** https://fonts.google.com/

---

## 🎯 CONCLUSIÓN

**Recomendación final:**
- Para empezar: **goog-webfont-dl** (1 min setup, muy fácil)
- Para automatizar: **Script Bash** (descarga múltiples fuentes de una vez)
- Para optimizar: **glyphhanger** (si tienes archivos locales)
- Para no instalar nada: **curl + gwfh.mranftl.com** (pero más manual)

¡Elige la que mejor se adapte a tu flujo de trabajo! 🚀
