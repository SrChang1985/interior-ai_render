#!/bin/bash

# Forzar no usar MKL
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

# Deshabilitar MKL completamente
export MKL_THREADING_LAYER=GNU
export KMP_DUPLICATE_LIB_OK=TRUE

# Activar entorno
source venv/bin/activate

# Ejecutar
python main.py
