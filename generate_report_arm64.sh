#!/bin/bash
# Script para generar informes con Python ARM64 compatible con WeasyPrint

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Generando informe con Python ARM64...${NC}"

# Usar Python ARM64 del sistema
PYTHON_ARM64="/usr/local/bin/python3"

# Verificar arquitectura
ARCH=$($PYTHON_ARM64 -c "import platform; print(platform.machine())")
echo "Arquitectura de Python: $ARCH"

if [ "$ARCH" != "arm64" ]; then
    echo -e "${RED}❌ Error: Python no está en modo ARM64${NC}"
    exit 1
fi

# Usar Python ARM64 directamente (sin venv x86_64)
echo "Usando Python ARM64 del sistema..."

# Ejecutar el comando con Python ARM64
$PYTHON_ARM64 main.py "$@"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Informe generado exitosamente${NC}"
else
    echo -e "${RED}❌ Error al generar informe (código: $EXIT_CODE)${NC}"
fi

exit $EXIT_CODE

